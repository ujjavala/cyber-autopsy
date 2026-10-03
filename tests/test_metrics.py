"""Metric behaviour tests.

These are written around the properties the benchmark claims to measure.
If a change to metrics.py breaks one of these, the claim in SCORING.md has
changed too and the documentation must change with it.
"""

from __future__ import annotations

import pytest

from cyberautopsy.metrics import compute_metrics, label_similarity, match_events
from cyberautopsy.schemas import (
    AttackGraph,
    EdgeRelation,
    GraphEdge,
    GraphNode,
    ModelPrediction,
    NodeStatus,
    PredictedEvent,
    PredictedRelationship,
    PredictedStatus,
)

EVIDENCE_IDS = {"E-1", "E-2", "E-3", "E-4"}


def gold_graph() -> AttackGraph:
    return AttackGraph(
        incident_id="INC-TEST",
        nodes=[
            GraphNode(
                id="N1",
                label="Password spray against internet-facing RDP server",
                status=NodeStatus.confirmed,
                evidence_ids=["E-1"],
            ),
            GraphNode(
                id="N2",
                label="High volume of failed authentication attempts",
                status=NodeStatus.attempted,
                evidence_ids=["E-2"],
            ),
            GraphNode(
                id="N3",
                label="Mimikatz LSASS credential dumping",
                status=NodeStatus.confirmed,
                evidence_ids=["E-3"],
            ),
            GraphNode(
                id="N4",
                label="Origin of the account list used in the password spray",
                status=NodeStatus.unknown,
                evidence_ids=["E-4"],
            ),
        ],
        edges=[
            GraphEdge(
                id="N1->N2", source="N1", target="N2", relation=EdgeRelation.causes
            ),
            GraphEdge(
                id="N1->N3", source="N1", target="N3", relation=EdgeRelation.enables
            ),
        ],
    )


def perfect_prediction() -> ModelPrediction:
    return ModelPrediction(
        events=[
            PredictedEvent(
                event_id="P1",
                description="Password spray against internet-facing RDP server",
                status=PredictedStatus.confirmed,
                evidence_ids=["E-1"],
            ),
            PredictedEvent(
                event_id="P2",
                description="High volume of failed authentication attempts",
                status=PredictedStatus.attempted,
                evidence_ids=["E-2"],
            ),
            PredictedEvent(
                event_id="P3",
                description="Mimikatz LSASS credential dumping",
                status=PredictedStatus.confirmed,
                evidence_ids=["E-3"],
            ),
            PredictedEvent(
                event_id="P4",
                description="Origin of the account list used in the password spray",
                status=PredictedStatus.unknown,
                evidence_ids=["E-4"],
            ),
        ],
        relationships=[
            PredictedRelationship(
                **{"from": "P1", "to": "P2", "relationship": EdgeRelation.causes}
            ),
            PredictedRelationship(
                **{"from": "P1", "to": "P3", "relationship": EdgeRelation.enables}
            ),
        ],
    )


def score(pred: ModelPrediction) -> dict:
    return compute_metrics(pred, gold_graph(), EVIDENCE_IDS)


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------


def test_label_similarity_is_symmetric_and_bounded():
    a, b = "Mimikatz LSASS credential dumping", "credential dumping with Mimikatz"
    assert label_similarity(a, b) == label_similarity(b, a)
    assert 0.0 <= label_similarity(a, b) <= 1.0
    assert label_similarity(a, a) == 1.0
    assert label_similarity("", "anything") == 0.0


def test_matching_is_one_to_one():
    """Two near-identical predictions must not both claim the same gold node."""
    pred = ModelPrediction(
        events=[
            PredictedEvent(
                event_id="P1",
                description="Mimikatz LSASS credential dumping",
                status=PredictedStatus.confirmed,
                evidence_ids=["E-3"],
            ),
            PredictedEvent(
                event_id="P2",
                description="Mimikatz LSASS credential dumping again",
                status=PredictedStatus.confirmed,
                evidence_ids=["E-3"],
            ),
        ]
    )
    result = match_events(pred.events, gold_graph().nodes)
    claimed = [m.gold_node_id for m in result.matches]
    assert len(claimed) == len(set(claimed))
    assert claimed.count("N3") <= 1


def test_matching_is_deterministic():
    nodes = gold_graph().nodes
    events = perfect_prediction().events
    first = match_events(events, nodes)
    for _ in range(5):
        again = match_events(list(reversed(events)), nodes)
        assert again.pred_to_gold() == first.pred_to_gold()


# --------------------------------------------------------------------------
# Composite behaviour
# --------------------------------------------------------------------------


def test_perfect_reconstruction_scores_near_ceiling():
    m = score(perfect_prediction())
    assert m["event_recall"] == 1.0
    assert m["event_precision"] == 1.0
    assert m["hallucinated_event_rate"] == 0.0
    assert m["link_f1"] == 1.0
    assert m["evidence_attribution"] == 1.0
    assert m["status_accuracy"] == 1.0
    assert m["unknown_calibration"] == 1.0
    assert m["failed_recognition"] == 1.0
    assert m["egrs"] == pytest.approx(100.0)


def test_empty_prediction_scores_zero_without_crashing():
    m = score(ModelPrediction())
    assert m["event_recall"] == 0.0
    assert m["event_precision"] == 0.0
    assert m["hallucinated_event_rate"] == 0.0
    assert m["egrs"] == 0.0


def test_hallucinated_event_is_penalised():
    pred = perfect_prediction()
    pred.events.append(
        PredictedEvent(
            event_id="P9",
            description="Cobalt Strike beacon established command and control",
            status=PredictedStatus.confirmed,
            evidence_ids=["E-1"],
        )
    )
    hallucinating = score(pred)
    clean = score(perfect_prediction())
    assert hallucinating["hallucinated_event_rate"] > 0
    assert hallucinating["event_precision"] < clean["event_precision"]
    assert hallucinating["egrs"] < clean["egrs"]


def test_citing_a_nonexistent_evidence_id_counts_as_hallucination():
    pred = perfect_prediction()
    pred.events.append(
        PredictedEvent(
            event_id="P9",
            description="Exfiltration over an unmonitored channel",
            status=PredictedStatus.confirmed,
            evidence_ids=["E-999"],
        )
    )
    assert score(pred)["hallucinated_event_rate"] > 0


def test_declared_uncertainty_is_not_hallucination():
    """Saying 'unknown' costs credit but must not be punished as invention."""
    pred = perfect_prediction()
    pred.events.append(
        PredictedEvent(
            event_id="P9",
            description="Some step we cannot establish from this evidence",
            status=PredictedStatus.unknown,
            evidence_ids=[],
        )
    )
    m = score(pred)
    assert m["hallucinated_event_rate"] == 0.0
    assert m["event_precision"] < 1.0


def test_asserting_a_gold_unknown_destroys_calibration():
    pred = perfect_prediction()
    pred.events[3].status = PredictedStatus.confirmed
    m = score(pred)
    assert m["unknown_calibration"] == 0.0
    assert m["egrs"] < score(perfect_prediction())["egrs"]


def test_omitting_a_gold_unknown_earns_partial_credit():
    pred = perfect_prediction()
    pred.events = pred.events[:3]
    m = score(pred)
    assert 0.0 < m["unknown_calibration"] < 1.0


def test_listing_an_omitted_unknown_in_unknown_steps_earns_full_credit():
    pred = perfect_prediction()
    pred.events = pred.events[:3]
    pred.unknown_steps = [
        "Origin of the account list used in the password spray is not established"
    ]
    assert score(pred)["unknown_calibration"] == 1.0


def test_failed_attempt_reported_as_success_loses_credit():
    pred = perfect_prediction()
    pred.events[1].status = PredictedStatus.confirmed
    m = score(pred)
    assert m["failed_recognition"] == 0.0
    assert m["status_accuracy"] < 1.0


def test_contradicted_node_must_not_be_asserted():
    gold = gold_graph()
    gold.nodes.append(
        GraphNode(
            id="N5",
            label="Account access from three additional external addresses",
            status=NodeStatus.contradicted,
            evidence_ids=["E-4"],
        )
    )
    asserting = ModelPrediction(
        events=[
            PredictedEvent(
                event_id="P1",
                description="Account access from three additional external addresses",
                status=PredictedStatus.confirmed,
                evidence_ids=["E-4"],
            )
        ]
    )
    careful = ModelPrediction(
        events=[
            PredictedEvent(
                event_id="P1",
                description="Account access from three additional external addresses",
                status=PredictedStatus.unknown,
                evidence_ids=["E-4"],
            )
        ]
    )
    assert compute_metrics(asserting, gold, EVIDENCE_IDS)["contradiction_handling"] == 0.0
    assert compute_metrics(careful, gold, EVIDENCE_IDS)["contradiction_handling"] == 1.0


def test_wrong_evidence_citation_lowers_attribution_not_recall():
    pred = perfect_prediction()
    pred.events[2].evidence_ids = ["E-1"]
    m = score(pred)
    assert m["evidence_attribution"] < 1.0
    assert m["event_recall"] == 1.0


def test_relationships_between_unmatched_events_earn_nothing():
    pred = perfect_prediction()
    pred.relationships.append(
        PredictedRelationship(
            **{"from": "GHOST-A", "to": "GHOST-B", "relationship": EdgeRelation.causes}
        )
    )
    m = score(pred)
    assert m["edge_recall"] == 1.0
    assert m["edge_precision"] < 1.0


def test_egrs_is_clamped_at_zero():
    """A prediction that is entirely invention cannot score below zero."""
    pred = ModelPrediction(
        events=[
            PredictedEvent(
                event_id=f"P{i}",
                description=f"Entirely invented step number {i}",
                status=PredictedStatus.confirmed,
                evidence_ids=["E-999"],
            )
            for i in range(10)
        ]
    )
    m = score(pred)
    assert m["hallucinated_event_rate"] == 1.0
    assert m["egrs"] == 0.0


def test_scoring_is_reproducible():
    first = score(perfect_prediction())
    for _ in range(5):
        assert score(perfect_prediction()) == first
