"""Generate self-contained Kaggle Benchmarks task files.

A task pushed to Kaggle runs in isolation. It cannot import this project, so
everything it needs — the evidence packet, the gold graph, the prompts and the
scoring code — is inlined into a single file here.

Generating rather than hand-writing those files is deliberate: the data in
``kaggle/build/`` is then provably the same data as ``data/``, and the scoring
is provably the same formula as ``src/cyberautopsy/metrics.py`` (enforced by
``tests/test_scoring_parity.py``).

Usage:
    python scripts/build_kaggle_tasks.py            # build every case
    python scripts/build_kaggle_tasks.py CASE-001   # build one case
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cyberautopsy.dataset import Dataset, build_packet, strip_gold_fields  # noqa: E402
from cyberautopsy.framing import AI_AGENT_PREAMBLE, HUMAN_PREAMBLE  # noqa: E402
from cyberautopsy.prompts import PROMPT_VERSION, SYSTEM_PROMPT  # noqa: E402

DATA_DIR = ROOT / "data"
SCORING_SRC = ROOT / "kaggle" / "tasks" / "_scoring.py"
BUILD_DIR = ROOT / "kaggle" / "build"

# Cases that are built as standalone Kaggle tasks. Perturbation and
# progressive cases need a driver that mutates the packet first and are not
# emitted yet.
BUILDABLE_MODES = {"full", "temporal", "framing"}

FRAMING_PREAMBLES = {"human": HUMAN_PREAMBLE, "ai_agent": AI_AGENT_PREAMBLE}

TASK_DESCRIPTIONS = {
    "CASE-001": (
        "Reconstruct the full reported RansomHub intrusion, from password "
        "spraying and remote access through data theft and ransomware. "
        "The 28-event reference rewards evidence-backed claims and penalizes "
        "unsupported ones."
    ),
    "CASE-002": (
        "Reconstruct Anthropic's reported GTG-1002 espionage campaign. "
        "Distinguish attempted, successful, failed, and unknown actions "
        "across 17 reference events. This case is based on vendor reporting, "
        "not public victim-side logs."
    ),
    "CASE-003": (
        "Reconstruct the reported Claude Code-assisted data-extortion "
        "operation from a short public report. The source gives less "
        "step-by-step detail than a forensic case; the reference contains "
        "8 events and preserves what the report leaves unknown."
    ),
    "CASE-004": (
        "Reconstruct only the first day of the RansomHub intrusion. Later "
        "evidence is withheld, so do not claim that later events such as "
        "ransomware deployment are established. The evidence-limited "
        "reference contains 15 events."
    ),
    "CASE-011": (
        "Reconstruct the GTG-1002 campaign using the same evidence as "
        "CASE-012, but with the operator described as human-led. This tests "
        "whether wording changes the reconstruction; it does not compare "
        "real human and AI attacker behavior."
    ),
    "CASE-012": (
        "Reconstruct the GTG-1002 campaign using the same evidence as "
        "CASE-011, but with the operator described as AI-agent-led. Compare "
        "with CASE-011 to examine sensitivity to actor framing, not real "
        "attacker behavior."
    ),
    "CASE-013": (
        "Reconstruct Google's reported AI-enabled credential-harvesting "
        "campaign from its public account. Keep the sequence grounded in "
        "what the vendor report establishes; the reference contains 7 "
        "events, and victim-side logs are not public."
    ),
    "CASE-014": (
        "Reconstruct the reported AI-agent access to Australia's Medicare "
        "statistics portal. This is a separate statistics service, not the "
        "personal Medicare claims system; investigation findings were still "
        "preliminary in the cited government briefings."
    ),
    "CASE-015": (
        "Reconstruct a Hong Kong executive-impersonation transfer scam "
        "involving a prerecorded video meeting. The official source leaves "
        "the company unnamed and qualifies police beliefs about the media."
    ),
    "CASE-016": (
        "Reconstruct the reported BumbleBee-to-Akira ransomware intrusion, "
        "from poisoned software search results to data theft and encryption. "
        "Exclude the separate Swisscom intrusion described in the same report."
    ),
    "CASE-017": "Reconstruct what Microsoft had disclosed by 19 January 2024 about the Midnight Blizzard corporate email compromise. Use this early snapshot only; do not import details from later updates.",
    "CASE-018": "Reconstruct Microsoft's Midnight Blizzard incident using its January and March 2024 updates. Distinguish internal-system access from the separately reported status of customer-facing services.",
    "CASE-019": "Reconstruct the Change Healthcare ransomware incident from its initial filing and later Senate testimony. Preserve the evolving scope and attribute claims made by the victim CEO.",
    "CASE-020": "Reconstruct Mandiant's UNC5537 campaign against Snowflake customer instances. This is a multi-victim campaign, not a single-victim or Snowflake corporate-breach case.",
}


def _scoring_body() -> str:
    """The scoring module with its import header stripped, ready to inline."""
    text = SCORING_SRC.read_text(encoding="utf-8")
    marker = "MATCH_THRESHOLD = 0.25"
    index = text.index(marker)
    return text[index:].rstrip()


def _task_name(case) -> str:
    """Unique, human-readable task name.

    The case id is part of the name because the SDK derives the Kaggle slug
    from it, and two cases can otherwise collide: CASE-011 and CASE-012 are
    both "INC-002 framing" and differ only in the actor label.
    """
    if case.case_id == "CASE-012":
        return "Cyber Autopsy CASE-012: GTG-1002 with AI-agent framing"
    if case.case_id == "CASE-013":
        return "Cyber Autopsy CASE-013: AI-enabled credential harvesting"
    if case.case_id == "CASE-014":
        return "Cyber Autopsy CASE-014: Medicare statistics portal incident"
    if case.case_id == "CASE-015":
        return "Cyber Autopsy CASE-015: Hong Kong deepfake transfer scam"
    if case.case_id == "CASE-016":
        return "Cyber Autopsy CASE-016: BumbleBee to Akira ransomware"
    if case.case_id == "CASE-017":
        return "Cyber Autopsy CASE-017: Midnight Blizzard initial disclosure"
    if case.case_id == "CASE-018":
        return "Cyber Autopsy CASE-018: Midnight Blizzard later findings"
    if case.case_id == "CASE-019":
        return "Cyber Autopsy CASE-019: Change Healthcare ransomware"
    if case.case_id == "CASE-020":
        return "Cyber Autopsy CASE-020: UNC5537 Snowflake campaign"

    suffix = case.mode.value
    if case.framing_actor:
        suffix = f"{suffix}, framed as {case.framing_actor}"
    if case.temporal_cutoff:
        suffix = f"{suffix}, cutoff {case.temporal_cutoff}"
    return f"Cyber Autopsy {case.case_id}: reconstruct {case.incident_id} ({suffix})"


def _slug(name: str) -> str:
    """Mirror the SDK's name-to-slug normalisation so docs can quote it."""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def build_case(ds: Dataset, case_id: str, bootstrap_model: str | None = None) -> Path:
    case = ds.cases[case_id]
    packet = build_packet(ds, case)
    graph = ds.graphs[case.incident_id]

    preamble = FRAMING_PREAMBLES[case.framing_actor] if case.framing_actor else ""

    evidence_payload = [strip_gold_fields(ev) for ev in packet.evidence]
    available_evidence = {ev.evidence_id for ev in packet.evidence}

    # A case may show the model only part of the evidence (temporal cutoff,
    # perturbation). Scoring it against gold nodes whose evidence it was never
    # shown would penalise it for not being clairvoyant, so the gold graph is
    # restricted to nodes with at least one piece of available supporting
    # evidence. "At least one" rather than "all": partial support is still a
    # fair basis for an inference, and the status labels already carry the
    # distinction between confirmed and inferred.
    kept_nodes = [
        n for n in graph.nodes if set(n.evidence_ids) & available_evidence
    ]
    kept_ids = {n.id for n in kept_nodes}
    kept_edges = [
        e for e in graph.edges if e.source in kept_ids and e.target in kept_ids
    ]
    dropped_nodes = len(graph.nodes) - len(kept_nodes)
    dropped_edges = len(graph.edges) - len(kept_edges)

    if not kept_nodes:
        raise ValueError(f"{case_id}: no gold node is supported by the shown evidence")

    gold_payload = {
        "nodes": [
            {
                "id": n.id,
                "label": n.label,
                "status": n.status.value,
                "evidence_ids": [
                    e for e in n.evidence_ids if e in available_evidence
                ],
            }
            for n in kept_nodes
        ],
        "edges": [{"source": e.source, "target": e.target} for e in kept_edges],
    }

    if dropped_nodes or dropped_edges:
        scope_note = (
            f"Gold restricted to the evidence shown: {len(kept_nodes)} of "
            f"{len(graph.nodes)} nodes and {len(kept_edges)} of "
            f"{len(graph.edges)} edges. {dropped_nodes} node(s) and "
            f"{dropped_edges} edge(s) rest on evidence this case withholds, so "
            f"the model is not scored on them."
        )
    else:
        scope_note = (
            f"Gold is the complete graph for this incident: {len(kept_nodes)} "
            f"nodes, {len(kept_edges)} edges."
        )

    description = TASK_DESCRIPTIONS[case.case_id]

    task_name = _task_name(case)
    rebuild_command = f"python scripts/build_kaggle_tasks.py {case.case_id}"
    if bootstrap_model:
        rebuild_command += f" --bootstrap-model {bootstrap_model}"
    content = TEMPLATE.format(
        case_id=case.case_id,
        incident_id=case.incident_id,
        mode=case.mode.value,
        variant=case.variant.value,
        slug=_slug(task_name),
        func_name=case.case_id.lower().replace("-", "_"),
        prompt_version=PROMPT_VERSION,
        comparability=case.comparability.value,
        comparability_reason=case.comparability_reason,
        knowledge_cutoff=case.knowledge_cutoff,
        task_name=task_name,
        description=description,
        rebuild_command=rebuild_command,
        initial_model=(
            "kbench.llm"
            if bootstrap_model is None
            else f"kbench.kaggle.load_model({json.dumps(bootstrap_model)})"
        ),
        scope_note=scope_note,
        scoring=_scoring_body(),
        system_prompt=json.dumps(SYSTEM_PROMPT),
        preamble=json.dumps(preamble),
        context=json.dumps(packet.context),
        evidence=json.dumps(evidence_payload, ensure_ascii=False, indent=2),
        gold=json.dumps(gold_payload, ensure_ascii=False, indent=2),
    )

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    out = BUILD_DIR / f"{case.case_id.lower().replace('-', '_')}.py"
    out.write_text(content, encoding="utf-8")
    return out


TEMPLATE = '''\
# %% [markdown]
# # Cyber Autopsy — {task_name}
#
# GENERATED FILE. Do not edit by hand.
# Rebuild with: `{rebuild_command}`
# Push with:    `kaggle b t push {slug} -f kaggle/build/{func_name}.py`
#
# Case: `{case_id}`  |  Incident: `{incident_id}`  |  Mode: `{mode}`  |  Variant: `{variant}`
# Prompt version: `{prompt_version}`
#
# **Question.** Given fragmented evidence from a real cyber incident, can the
# model reconstruct what actually happened — sequence, causal relationships,
# failed attempts, uncertainty, contradictions, and the evidence behind each
# claim?
#
# **Scoring.** Evidence-Grounded Reconstruction Score (EGRS), 0-100, returned
# here as a 0-1 fraction. Deterministic: no LLM judge. Inventing steps is
# penalised; declaring a step unknown is not.
#
# **Comparability.** `{comparability}` —
# {comparability_reason}
#
# **Scope.** {scope_note}
#
# **Leakage.** This incident has been public since `{knowledge_cutoff}`. Models
# trained after that date may have memorised the published account. Timestamps
# are deliberately relative (D1, D2, ...) rather than the absolute dates used in
# the source report, so recall of the article does not directly supply answers.

# %%
import json
import re
from dataclasses import dataclass, field

import kaggle_benchmarks as kbench

# %% [markdown]
# ## Scoring
#
# Inlined from `kaggle/tasks/_scoring.py`. Kept numerically identical to
# `src/cyberautopsy/metrics.py` by `tests/test_scoring_parity.py`.

# %%
{scoring}

# %% [markdown]
# ## Case data
#
# `EVIDENCE` is exactly what the model sees. Every gold-linkage field has been
# stripped from it. `GOLD` is the reference reconstruction and is never shown
# to the model.

# %%
SYSTEM_PROMPT = {system_prompt}

FRAMING_PREAMBLE = {preamble}

CONTEXT = {context}

EVIDENCE = json.loads(r"""
{evidence}
""")

GOLD = json.loads(r"""
{gold}
""")

VALID_EVIDENCE_IDS = {{e["evidence_id"] for e in EVIDENCE}}


def build_user_prompt() -> str:
    lines = []
    if FRAMING_PREAMBLE:
        lines.append(FRAMING_PREAMBLE)
        lines.append("")
    lines.append("INCIDENT CONTEXT")
    lines.append(CONTEXT.rstrip())
    lines.append("")
    lines.append("EVIDENCE ITEMS (order is not meaningful)")
    for item in EVIDENCE:
        lines.append(json.dumps(item, ensure_ascii=False))
    lines.append("")
    lines.append(
        "Reconstruct the incident as structured JSON per the schema. "
        "Cite evidence_ids from the items above only."
    )
    return "\\n".join(lines)


# %% [markdown]
# ## Response schema
#
# `from` is a Python keyword, so the relationship endpoints are named
# `source_event_id` and `target_event_id` here and mapped back when scoring.

# %%
@dataclass
class ReconstructedEvent:
    event_id: str
    description: str
    status: str  # confirmed | inferred | unknown | attempted | failed
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class ReconstructedRelationship:
    source_event_id: str
    target_event_id: str
    relationship: str  # precedes | enables | causes | depends_on


@dataclass
class Reconstruction:
    events: list[ReconstructedEvent] = field(default_factory=list)
    relationships: list[ReconstructedRelationship] = field(default_factory=list)
    unknown_steps: list[str] = field(default_factory=list)
    unsupported_steps: list[str] = field(default_factory=list)


def to_prediction(result: Reconstruction) -> dict:
    def get(value, key, default=None):
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

    return {{
        "events": [
            {{
                "event_id": get(e, "event_id"),
                "description": get(e, "description", ""),
                "status": get(e, "status"),
                "evidence_ids": list(get(e, "evidence_ids") or []),
            }}
            for e in (get(result, "events") or [])
        ],
        "relationships": [
            {{
                "from": get(r, "source_event_id", get(r, "from")),
                "to": get(r, "target_event_id", get(r, "to")),
                "relationship": get(r, "relationship"),
            }}
            for r in (get(result, "relationships") or [])
        ],
        "unknown_steps": list(get(result, "unknown_steps") or []),
        "unsupported_steps": list(get(result, "unsupported_steps") or []),
    }}


# %% [markdown]
# ## Task

# %%
@kbench.task(
    name={task_name!r},
    description={description!r},
)
def {func_name}(llm) -> float:
    message = SYSTEM_PROMPT + "\\n\\n" + build_user_prompt()
    result = llm.prompt(message, schema=Reconstruction, seed=0, temperature=0)

    prediction = to_prediction(result)
    metrics = score_prediction(prediction, GOLD, VALID_EVIDENCE_IDS)

    print(json.dumps(metrics, indent=2))
    return metrics["egrs"] / 100.0


# %%
{func_name}.run({initial_model})
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bootstrap-model",
        help="Use this model for the initial task-creation run only.",
    )
    parser.add_argument("case_ids", nargs="*")
    args = parser.parse_args()

    ds = Dataset.load(DATA_DIR)
    requested = args.case_ids
    if requested:
        case_ids = requested
    else:
        case_ids = [
            c.case_id
            for c in ds.cases.values()
            if c.mode.value in BUILDABLE_MODES
        ]

    for case_id in case_ids:
        if case_id not in ds.cases:
            print(f"unknown case: {case_id}")
            return 1
        out = build_case(ds, case_id, bootstrap_model=args.bootstrap_model)
        print(f"built {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
