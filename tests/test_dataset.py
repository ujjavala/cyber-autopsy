"""Tests against the real dataset in data/.

These are integrity tests, not unit tests. They are the reason a silent
mis-alignment between evidence and gold graphs cannot reach a scoring run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cyberautopsy.dataset import Dataset, build_packet, strip_gold_fields
from cyberautopsy.schemas import ComparabilityClass, NodeStatus

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

GOLD_ONLY_FIELDS = {
    "supports_nodes",
    "supports_edges",
    "contradicts",
    "claim_status",
    "incident_id",
    "source_ids",
    "synthetic",
    "redacted",
    "entities",
}


# --------------------------------------------------------------------------
# Loading and integrity
# --------------------------------------------------------------------------


def test_dataset_loads(dataset: Dataset):
    assert dataset.sources
    assert dataset.incidents
    assert dataset.evidence
    assert dataset.graphs


def test_every_incident_has_a_gold_graph(dataset: Dataset):
    assert set(dataset.graphs) == set(dataset.incidents)


def test_no_dangling_references():
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from validate_dataset import validate

    assert validate(DATA_DIR) == []


def test_every_supports_node_resolves(dataset: Dataset):
    for ev in dataset.evidence.values():
        node_ids = {n.id for n in dataset.graphs[ev.incident_id].nodes}
        for nid in ev.supports_nodes:
            assert nid in node_ids, f"{ev.evidence_id} -> missing node {nid}"


def test_every_gold_node_cites_evidence_unless_unknown(dataset: Dataset):
    """A confirmed node with no evidence is an unfalsifiable assertion."""
    for graph in dataset.graphs.values():
        for node in graph.nodes:
            assert node.evidence_ids, f"{graph.incident_id}/{node.id} cites nothing"


def test_graphs_have_no_duplicate_node_ids(dataset: Dataset):
    for graph in dataset.graphs.values():
        ids = [n.id for n in graph.nodes]
        assert len(ids) == len(set(ids))


def test_graphs_contain_unknowns(dataset: Dataset):
    """If nothing is unknown, the gold data is overclaiming."""
    for graph in dataset.graphs.values():
        statuses = {n.status for n in graph.nodes}
        assert NodeStatus.unknown in statuses, graph.incident_id


def test_no_evidence_item_is_marked_synthetic(dataset: Dataset):
    """Synthetic content is only permitted inside a PerturbationSpec."""
    for ev in dataset.evidence.values():
        assert ev.synthetic is False, ev.evidence_id


def test_perturbation_injections_are_labelled_synthetic(dataset: Dataset):
    for spec in dataset.perturbations.values():
        for text in (spec.inject_content, spec.flip_replacement_content):
            if text:
                assert "SYNTHETIC" in text.upper(), spec.perturbation_id


def test_vendor_reported_incidents_are_not_marked_confirmed(dataset: Dataset):
    """AI-vendor reports remain distinguished from directly observed evidence."""
    for ev in dataset.evidence.values():
        if ev.incident_id in {"INC-002", "INC-003", "INC-004"}:
            assert ev.evidence_strength.value != "confirmed", ev.evidence_id


# --------------------------------------------------------------------------
# Benchmark cases
# --------------------------------------------------------------------------


def test_cases_declare_a_comparability_reason(dataset: Dataset):
    for case in dataset.cases.values():
        assert case.comparability_reason.strip(), case.case_id


def test_cross_incident_cases_are_never_direct_comparisons(dataset: Dataset):
    for case in dataset.cases.values():
        assert case.comparability is not ComparabilityClass.direct_comparison


def test_cases_record_source_publication_dates(dataset: Dataset):
    for case in dataset.cases.values():
        assert case.source_publication_dates, case.case_id


def test_framing_pair_uses_identical_evidence(dataset: Dataset):
    a, b = dataset.cases["CASE-011"], dataset.cases["CASE-012"]
    assert a.incident_id == b.incident_id
    assert a.evidence_ids == b.evidence_ids
    assert a.framing_actor != b.framing_actor


# --------------------------------------------------------------------------
# Packet construction and leakage
# --------------------------------------------------------------------------


def test_build_packet_is_deterministic(dataset: Dataset):
    case = dataset.cases["CASE-001"]
    first = build_packet(dataset, case).evidence_ids()
    for _ in range(5):
        assert build_packet(dataset, case).evidence_ids() == first


def test_build_packet_shuffle_changes_order_but_not_content(dataset: Dataset):
    case = dataset.cases["CASE-001"]
    shuffled = build_packet(dataset, case, shuffle=True).evidence_ids()
    ordered = build_packet(dataset, case, shuffle=False).evidence_ids()
    assert set(shuffled) == set(ordered)
    assert shuffled != ordered


def test_packet_respects_explicit_evidence_list(dataset: Dataset):
    case = dataset.cases["CASE-004"]
    assert set(build_packet(dataset, case).evidence_ids()) == set(case.evidence_ids)


def test_packet_context_leaks_no_gold(dataset: Dataset):
    case = dataset.cases["CASE-001"]
    context = build_packet(dataset, case).context
    graph = dataset.graphs[case.incident_id]
    for node in graph.nodes:
        assert node.id not in context
        assert node.label not in context


def test_stripped_evidence_drops_every_gold_field(dataset: Dataset):
    for ev in dataset.evidence.values():
        rendered = strip_gold_fields(ev)
        assert not (GOLD_ONLY_FIELDS & set(rendered)), ev.evidence_id


def test_stripped_evidence_is_json_serialisable(dataset: Dataset):
    for ev in dataset.evidence.values():
        json.dumps(strip_gold_fields(ev))


def test_publication_date_lookup(dataset: Dataset):
    ev = dataset.evidence["E-001"]
    assert dataset.publication_date_for_evidence(ev) == "2025-06-30"


# --------------------------------------------------------------------------
# Behavioural layer
# --------------------------------------------------------------------------


def test_behavioural_layer_loaded(dataset: Dataset):
    assert dataset.actors
    assert dataset.actions


def test_failures_are_recorded_for_both_actor_kinds(dataset: Dataset):
    """Failures are first-class. If only one actor kind has them, the data
    is flattering one side."""
    kinds = set()
    for action in dataset.actions.values():
        if action.failure is not None:
            kinds.add(dataset.actors[action.actor_id].actor_kind.value)
    assert "human" in kinds
    assert "ai_agent" in kinds


def test_ai_actors_record_an_autonomy_level(dataset: Dataset):
    for actor in dataset.actors.values():
        if actor.actor_kind.value in {"ai_agent", "hybrid"}:
            assert actor.autonomy_level is not None


def test_action_links_are_symmetric(dataset: Dataset):
    for action in dataset.actions.values():
        for nxt in action.following_action_ids:
            assert action.action_id in dataset.actions[nxt].preceding_action_ids, (
                f"{action.action_id} -> {nxt} is not mirrored"
            )
        for prev in action.preceding_action_ids:
            assert action.action_id in dataset.actions[prev].following_action_ids, (
                f"{prev} -> {action.action_id} is not mirrored"
            )


@pytest.mark.parametrize(
    "incident_id",
    ["INC-001", "INC-002", "INC-003", "INC-004", "INC-005", "INC-006", "INC-007", "INC-008", "INC-009", "INC-010"],
)
def test_each_incident_has_evidence_and_nodes(dataset: Dataset, incident_id: str):
    assert dataset.evidence_for_incident(incident_id)
    assert dataset.graphs[incident_id].nodes
