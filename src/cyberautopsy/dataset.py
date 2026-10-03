"""Dataset loading and evidence-packet construction.

The dataset lives in plain JSONL files under data/. No database is required.
Raw source text, normalised sources, and extracted evidence are kept in
separate files and are never mutated by this module.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from .schemas import (
    Action,
    Actor,
    AttackGraph,
    BenchmarkCase,
    Control,
    Evidence,
    Incident,
    Intent,
    Intervention,
    PerturbationSpec,
    Source,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# (filename, Dataset attribute, model). The id field is derived from the
# attribute name: "actors" -> "actor_id".
_BEHAVIOURAL_FILES = [
    ("actors.jsonl", "actors", Actor),
    ("intents.jsonl", "intents", Intent),
    ("actions.jsonl", "actions", Action),
    ("controls.jsonl", "controls", Control),
    ("interventions.jsonl", "interventions", Intervention),
]


def read_jsonl(path: Path) -> list[dict]:
    items: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:  # pragma: no cover
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return items


def write_jsonl(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for item in items:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")


@dataclass
class Dataset:
    sources: dict[str, Source] = field(default_factory=dict)
    incidents: dict[str, Incident] = field(default_factory=dict)
    evidence: dict[str, Evidence] = field(default_factory=dict)
    graphs: dict[str, AttackGraph] = field(default_factory=dict)
    cases: dict[str, BenchmarkCase] = field(default_factory=dict)
    perturbations: dict[str, PerturbationSpec] = field(default_factory=dict)
    # Behavioural layer (layer 2). Optional: absent for incidents where the
    # sources do not support action-level reconstruction.
    actors: dict[str, Actor] = field(default_factory=dict)
    intents: dict[str, Intent] = field(default_factory=dict)
    actions: dict[str, Action] = field(default_factory=dict)
    controls: dict[str, Control] = field(default_factory=dict)
    interventions: dict[str, Intervention] = field(default_factory=dict)

    @classmethod
    def load(cls, data_dir: Path | str = DATA_DIR) -> "Dataset":
        data_dir = Path(data_dir)
        ds = cls()
        ds.sources = {
            s["source_id"]: Source(**s)
            for s in read_jsonl(data_dir / "sources.jsonl")
        }
        ds.incidents = {
            i["incident_id"]: Incident(**i)
            for i in read_jsonl(data_dir / "incidents.jsonl")
        }
        ds.evidence = {
            e["evidence_id"]: Evidence(**e)
            for e in read_jsonl(data_dir / "evidence.jsonl")
        }
        ds.graphs = {
            g["incident_id"]: AttackGraph(**g)
            for g in read_jsonl(data_dir / "attack_graphs.jsonl")
        }
        cases_path = data_dir / "benchmark_cases.jsonl"
        if cases_path.exists():
            ds.cases = {
                c["case_id"]: BenchmarkCase(**c) for c in read_jsonl(cases_path)
            }
        pert_path = data_dir / "perturbations.jsonl"
        if pert_path.exists():
            ds.perturbations = {
                p["perturbation_id"]: PerturbationSpec(**p)
                for p in read_jsonl(pert_path)
            }
        for filename, key, model in _BEHAVIOURAL_FILES:
            path = data_dir / filename
            if path.exists():
                setattr(
                    ds,
                    key,
                    {
                        row[f"{key[:-1]}_id"]: model(**row)
                        for row in read_jsonl(path)
                    },
                )
        return ds

    def evidence_for_incident(self, incident_id: str) -> list[Evidence]:
        return [e for e in self.evidence.values() if e.incident_id == incident_id]

    def actions_for_incident(self, incident_id: str) -> list[Action]:
        return [a for a in self.actions.values() if a.incident_id == incident_id]

    def sources_for_incident(self, incident_id: str) -> list[Source]:
        return [s for s in self.sources.values() if incident_id in s.incident_ids]

    def publication_date_for_evidence(self, ev: Evidence) -> str | None:
        """Earliest publication date among the evidence item's sources.

        Used for temporal-leakage protection: an evidence item is only
        'publicly known' from this date onward.
        """
        dates = [
            self.sources[sid].published_at
            for sid in ev.source_ids
            if sid in self.sources
        ]
        return min(dates) if dates else None


@dataclass
class EvidencePacket:
    """What the model sees for one benchmark case. Never contains gold."""

    case_id: str
    incident_id: str
    context: str
    evidence: list[Evidence]
    framing_preamble: str = ""

    def evidence_ids(self) -> list[str]:
        return [e.evidence_id for e in self.evidence]


def build_packet(
    ds: Dataset,
    case: BenchmarkCase,
    seed: int = 42,
    shuffle: bool = True,
) -> EvidencePacket:
    """Construct the evidence packet for a benchmark case.

    Context deliberately excludes the gold graph, the incident summary's
    causal claims, and any evidence->node mapping fields.
    """
    incident = ds.incidents[case.incident_id]
    all_evidence = ds.evidence_for_incident(case.incident_id)
    if case.evidence_ids:
        keep = set(case.evidence_ids)
        evidence = [e for e in all_evidence if e.evidence_id in keep]
    else:
        evidence = list(all_evidence)

    if shuffle:
        rng = random.Random(f"{seed}:{case.case_id}")
        rng.shuffle(evidence)

    context = (
        f"Incident sector: {incident.sector}\n"
        f"Country: {incident.country}\n"
        f"Approximate incident date: {incident.incident_date}\n"
        f"Attack type (as publicly categorised): {incident.attack_type}\n"
    )
    return EvidencePacket(
        case_id=case.case_id,
        incident_id=case.incident_id,
        context=context,
        evidence=evidence,
    )


def strip_gold_fields(ev: Evidence) -> dict:
    """Render an evidence item for the model, removing gold-linkage fields."""
    return {
        "evidence_id": ev.evidence_id,
        "timestamp": ev.timestamp,
        "timestamp_precision": ev.timestamp_precision.value,
        "type": ev.type.value,
        "content": ev.content,
        "evidence_strength": ev.evidence_strength.value,
    }
