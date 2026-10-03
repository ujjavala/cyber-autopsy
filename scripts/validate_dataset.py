"""Referential-integrity check for the Cyber Autopsy dataset.

Every identifier that one record points at must exist. This is the cheapest
guard against the failure mode that matters most here: gold data that looks
fine but silently mis-aligns with the evidence it is supposed to be scored
against.

Usage:
    python scripts/validate_dataset.py [data_dir]

Exits non-zero if any reference is dangling.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cyberautopsy.dataset import Dataset  # noqa: E402


def validate(data_dir: Path) -> list[str]:
    ds = Dataset.load(data_dir)
    errors: list[str] = []

    source_ids = set(ds.sources)
    incident_ids = set(ds.incidents)
    evidence_ids = set(ds.evidence)
    actor_ids = set(ds.actors)
    intent_ids = set(ds.intents)
    action_ids = set(ds.actions)

    def check(ok: bool, message: str) -> None:
        if not ok:
            errors.append(message)

    for src in ds.sources.values():
        for iid in src.incident_ids:
            check(iid in incident_ids, f"{src.source_id}: unknown incident {iid}")

    for inc in ds.incidents.values():
        for sid in inc.source_ids:
            check(sid in source_ids, f"{inc.incident_id}: unknown source {sid}")

    node_ids: dict[str, set[str]] = {}
    edge_ids: dict[str, set[str]] = {}
    for graph in ds.graphs.values():
        iid = graph.incident_id
        check(iid in incident_ids, f"graph: unknown incident {iid}")
        node_ids[iid] = {n.id for n in graph.nodes}
        edge_ids[iid] = {e.id for e in graph.edges if e.id}
        seen: set[str] = set()
        for node in graph.nodes:
            check(node.id not in seen, f"{iid}: duplicate node {node.id}")
            seen.add(node.id)
            for eid in node.evidence_ids:
                check(eid in evidence_ids, f"{iid}/{node.id}: unknown evidence {eid}")
        for edge in graph.edges:
            check(
                edge.source in node_ids[iid],
                f"{iid}: edge source {edge.source} is not a node",
            )
            check(
                edge.target in node_ids[iid],
                f"{iid}: edge target {edge.target} is not a node",
            )
            for eid in edge.evidence_ids:
                check(eid in evidence_ids, f"{iid}/edge: unknown evidence {eid}")

    for ev in ds.evidence.values():
        check(
            ev.incident_id in incident_ids,
            f"{ev.evidence_id}: unknown incident {ev.incident_id}",
        )
        for sid in ev.source_ids:
            check(sid in source_ids, f"{ev.evidence_id}: unknown source {sid}")
        for nid in ev.supports_nodes:
            check(
                nid in node_ids.get(ev.incident_id, set()),
                f"{ev.evidence_id}: supports unknown node {nid}",
            )
        for eid in ev.supports_edges:
            check(
                eid in edge_ids.get(ev.incident_id, set()),
                f"{ev.evidence_id}: supports unknown edge {eid}",
            )
        for cid in ev.contradicts:
            check(cid in evidence_ids, f"{ev.evidence_id}: contradicts unknown {cid}")

    for actor in ds.actors.values():
        check(
            actor.incident_id in incident_ids,
            f"{actor.actor_id}: unknown incident {actor.incident_id}",
        )
        for sid in actor.source_ids:
            check(sid in source_ids, f"{actor.actor_id}: unknown source {sid}")

    for intent in ds.intents.values():
        check(intent.actor_id in actor_ids, f"{intent.intent_id}: unknown actor")
        for eid in intent.evidence_ids:
            check(eid in evidence_ids, f"{intent.intent_id}: unknown evidence {eid}")

    for action in ds.actions.values():
        check(action.actor_id in actor_ids, f"{action.action_id}: unknown actor")
        check(
            action.intent_id is None or action.intent_id in intent_ids,
            f"{action.action_id}: unknown intent {action.intent_id}",
        )
        for eid in action.evidence_ids:
            check(eid in evidence_ids, f"{action.action_id}: unknown evidence {eid}")
        for linked in action.preceding_action_ids + action.following_action_ids:
            check(linked in action_ids, f"{action.action_id}: unknown link {linked}")
        if action.failure is not None:
            for eid in action.failure.evidence_ids:
                check(
                    eid in evidence_ids,
                    f"{action.action_id}/failure: unknown evidence {eid}",
                )

    for record in list(ds.controls.values()) + list(ds.interventions.values()):
        label = getattr(record, "control_id", None) or record.intervention_id
        check(
            record.action_id is None or record.action_id in action_ids,
            f"{label}: unknown action {record.action_id}",
        )
        for eid in record.evidence_ids:
            check(eid in evidence_ids, f"{label}: unknown evidence {eid}")

    for case in ds.cases.values():
        check(
            case.incident_id in incident_ids,
            f"{case.case_id}: unknown incident {case.incident_id}",
        )
        for eid in case.evidence_ids:
            check(eid in evidence_ids, f"{case.case_id}: unknown evidence {eid}")

    for spec in ds.perturbations.values():
        check(
            spec.incident_id in incident_ids,
            f"{spec.perturbation_id}: unknown incident {spec.incident_id}",
        )
        for eid in spec.remove_evidence_ids:
            check(eid in evidence_ids, f"{spec.perturbation_id}: unknown {eid}")
        check(
            spec.flip_evidence_id is None or spec.flip_evidence_id in evidence_ids,
            f"{spec.perturbation_id}: unknown flip target {spec.flip_evidence_id}",
        )

    return errors


def main() -> int:
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data"
    ds = Dataset.load(data_dir)
    errors = validate(data_dir)

    print(f"data dir: {data_dir}")
    print(
        f"  sources={len(ds.sources)} incidents={len(ds.incidents)} "
        f"evidence={len(ds.evidence)} graphs={len(ds.graphs)}"
    )
    print(
        f"  actors={len(ds.actors)} intents={len(ds.intents)} "
        f"actions={len(ds.actions)} controls={len(ds.controls)} "
        f"interventions={len(ds.interventions)}"
    )
    print(f"  cases={len(ds.cases)} perturbations={len(ds.perturbations)}")

    if errors:
        print(f"\n{len(errors)} dangling reference(s):")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("\nAll references resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
