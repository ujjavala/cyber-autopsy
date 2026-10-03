"""Schema round-trip and validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cyberautopsy.schemas import (
    Action,
    Actor,
    ActorKind,
    ActionResult,
    AttackGraph,
    BenchmarkCase,
    ComparabilityClass,
    Confidence,
    EdgeRelation,
    Evidence,
    EvidenceType,
    FailureClass,
    FailureMode,
    FailureRecord,
    GraphEdge,
    GraphNode,
    Incident,
    ModelPrediction,
    NodeStatus,
    PerturbationSpec,
    PerturbationVariant,
    PredictedEvent,
    PredictedStatus,
    ReliabilityTier,
    Source,
    SourceType,
)


def test_source_rejects_non_http_url():
    with pytest.raises(ValidationError):
        Source(
            source_id="SRC-X",
            title="t",
            publisher="p",
            url="ftp://example.com/report",
            published_at="2025-01-01",
            accessed_at="2025-01-02",
            source_type=SourceType.incident_report,
            reliability_tier=ReliabilityTier.primary,
        )


def test_source_round_trips():
    src = Source(
        source_id="SRC-X",
        title="Report",
        publisher="Publisher",
        url="https://example.com/report",
        published_at="2025-01-01",
        accessed_at="2025-01-02",
        source_type=SourceType.incident_report,
        reliability_tier=ReliabilityTier.primary,
    )
    assert Source(**src.model_dump()) == src


def test_incident_round_trips():
    inc = Incident(
        incident_id="INC-X",
        title="Test incident",
        organization="Undisclosed",
        country="Unknown",
        sector="Unknown",
        incident_date="2025-01",
        attack_type="ransomware",
        impact="Operational disruption",
        summary="A test incident.",
        confidence=Confidence.medium,
        source_ids=["SRC-X"],
    )
    assert Incident(**inc.model_dump()) == inc


def test_evidence_round_trips_through_json():
    ev = Evidence(
        evidence_id="E-X",
        incident_id="INC-X",
        type=EvidenceType.negative_evidence,
        content="No telemetry exists for this step.",
        source_ids=["SRC-X"],
        contradicts=["E-Y"],
    )
    assert Evidence.model_validate_json(ev.model_dump_json()) == ev


def test_attack_graph_round_trips():
    graph = AttackGraph(
        incident_id="INC-X",
        nodes=[GraphNode(id="N1", label="Step one", status=NodeStatus.confirmed)],
        edges=[
            GraphEdge(id="N1->N1", source="N1", target="N1", relation=EdgeRelation.precedes)
        ],
    )
    assert AttackGraph.model_validate_json(graph.model_dump_json()) == graph


def test_graph_node_defaults_to_draft_review_on_graph():
    graph = AttackGraph(incident_id="INC-X", nodes=[], edges=[])
    assert graph.review.review_status.value == "draft"


def test_unknown_enum_member_is_rejected():
    with pytest.raises(ValidationError):
        GraphNode(id="N1", label="x", status="probably")


def test_failure_record_is_optional_on_action():
    action = Action(
        action_id="ACT-X",
        incident_id="INC-X",
        actor_id="A-X",
        description="did something",
        result=ActionResult.successful,
    )
    assert action.failure is None


def test_failure_record_round_trips():
    record = FailureRecord(
        failure_mode=FailureMode.hallucinated_state,
        failure_class=FailureClass.capability,
        evidence_ids=["E-X"],
    )
    assert FailureRecord(**record.model_dump()) == record


def test_actor_defaults_to_unknown_autonomy():
    actor = Actor(actor_id="A-X", incident_id="INC-X", actor_kind=ActorKind.ai_agent)
    assert actor.autonomy_level.value == "unknown"


def test_benchmark_case_defaults_to_contextual_only():
    """Comparability must never silently default to something stronger."""
    case = BenchmarkCase(case_id="CASE-X", incident_id="INC-X")
    assert case.comparability is ComparabilityClass.contextual_only


def test_perturbation_spec_round_trips():
    spec = PerturbationSpec(
        perturbation_id="PERT-X",
        incident_id="INC-X",
        variant=PerturbationVariant.false_evidence,
        inject_content="SYNTHETIC. Something that did not happen.",
        expected_effect="Model should flag this as uncorroborated.",
    )
    assert PerturbationSpec(**spec.model_dump()) == spec
    assert spec.variant.value == "D_false"


def test_prediction_accepts_from_alias():
    pred = ModelPrediction.model_validate(
        {
            "events": [
                {
                    "event_id": "P1",
                    "description": "step",
                    "status": "confirmed",
                    "evidence_ids": ["E-X"],
                }
            ],
            "relationships": [
                {"from": "P1", "to": "P1", "relationship": "precedes"}
            ],
        }
    )
    assert pred.relationships[0].from_ == "P1"


def test_prediction_confidence_is_bounded():
    with pytest.raises(ValidationError):
        PredictedEvent(
            event_id="P1",
            description="x",
            status=PredictedStatus.confirmed,
            confidence=1.5,
        )
