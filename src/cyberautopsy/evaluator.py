"""Evaluation orchestration and failure categorisation."""

from __future__ import annotations

from dataclasses import dataclass, field

from .metrics import compute_metrics, label_similarity, match_events
from .schemas import AttackGraph, ModelPrediction, NodeStatus


@dataclass
class Failure:
    category: str
    detail: str
    pred_event_id: str | None = None
    gold_node_id: str | None = None
    evidence_ids: list[str] = field(default_factory=list)


FAILURE_CATEGORIES = [
    "hallucinated_event",
    "wrong_chronology",
    "wrong_causal_link",
    "ignored_evidence",
    "ignored_contradiction",
    "overconfidence",
    "missed_event",
    "failed_attempt_confusion",
    "actor_framing_bias",
    "temporal_leakage",
]


def evaluate(
    pred: ModelPrediction,
    gold: AttackGraph,
    valid_evidence_ids: set[str],
) -> dict:
    metrics = compute_metrics(pred, gold, valid_evidence_ids)
    failures = categorise_failures(pred, gold, valid_evidence_ids)
    metrics["failures"] = [f.__dict__ for f in failures]
    return metrics


def categorise_failures(
    pred: ModelPrediction,
    gold: AttackGraph,
    valid_evidence_ids: set[str],
) -> list[Failure]:
    failures: list[Failure] = []
    gold_by_id = {n.id: n for n in gold.nodes}
    mr = match_events(pred.events, gold.nodes)
    p2g = mr.pred_to_gold()
    pred_by_id = {e.event_id: e for e in pred.events}

    # Hallucinated events: asserted (non-unknown), unmatched to gold.
    for pid in mr.unmatched_pred:
        pe = pred_by_id[pid]
        if pe.status.value == "unknown":
            continue
        bad_citation = not pe.evidence_ids or any(
            eid not in valid_evidence_ids for eid in pe.evidence_ids
        )
        failures.append(
            Failure(
                category="hallucinated_event",
                detail=(
                    f"Asserted event not supported by gold graph"
                    f"{' and cites invalid/absent evidence' if bad_citation else ''}: "
                    f"{pe.description!r} (status={pe.status.value})"
                ),
                pred_event_id=pid,
                evidence_ids=pe.evidence_ids,
            )
        )

    # Missed events: recoverable gold nodes never matched.
    for gid in mr.unmatched_gold:
        gn = gold_by_id[gid]
        if gn.status in (NodeStatus.confirmed, NodeStatus.inferred):
            failures.append(
                Failure(
                    category="missed_event",
                    detail=f"Gold event not recovered: {gn.label!r}",
                    gold_node_id=gid,
                    evidence_ids=gn.evidence_ids,
                )
            )

    # Status-level failures on matched pairs.
    for m in mr.matches:
        pe = pred_by_id[m.pred_event_id]
        gn = gold_by_id[m.gold_node_id]
        ps, gs = pe.status.value, gn.status.value
        if gs in ("attempted", "failed") and ps in ("confirmed", "inferred"):
            failures.append(
                Failure(
                    category="failed_attempt_confusion",
                    detail=(
                        f"Gold marks {gn.label!r} as {gs}; model asserted it "
                        f"as {ps} (treated attempt as success)"
                    ),
                    pred_event_id=pe.event_id,
                    gold_node_id=gn.id,
                    evidence_ids=gn.evidence_ids,
                )
            )
        elif gs == "unknown" and ps in ("confirmed", "inferred"):
            failures.append(
                Failure(
                    category="overconfidence",
                    detail=(
                        f"Gold marks {gn.label!r} as unknown; model asserted "
                        f"{ps} with confidence {pe.confidence}"
                    ),
                    pred_event_id=pe.event_id,
                    gold_node_id=gn.id,
                )
            )
        elif gs == "contradicted" and ps in ("confirmed", "inferred"):
            failures.append(
                Failure(
                    category="ignored_contradiction",
                    detail=(
                        f"Evidence contradicts {gn.label!r} but model asserted "
                        f"it as {ps}"
                    ),
                    pred_event_id=pe.event_id,
                    gold_node_id=gn.id,
                    evidence_ids=gn.evidence_ids,
                )
            )

    # Relationship failures: predicted links between matched nodes that do
    # not exist in gold.
    gold_edges = {(e.source, e.target) for e in gold.edges}
    for rel in pred.relationships:
        gs_, gt_ = p2g.get(rel.from_), p2g.get(rel.to)
        if gs_ and gt_ and (gs_, gt_) not in gold_edges:
            if (gt_, gs_) in gold_edges:
                failures.append(
                    Failure(
                        category="wrong_chronology",
                        detail=(
                            f"Predicted {gs_} -> {gt_} but gold has the "
                            f"reverse direction"
                        ),
                    )
                )
            else:
                failures.append(
                    Failure(
                        category="wrong_causal_link",
                        detail=(
                            f"Predicted unsupported link {gs_} -> {gt_} "
                            f"({rel.relationship.value})"
                        ),
                        evidence_ids=rel.evidence_ids,
                    )
                )

    return failures


def framing_sensitivity(pred_human: ModelPrediction, pred_ai: ModelPrediction) -> dict:
    """Compare two reconstructions produced from identical evidence that
    differ only in the actor-framing preamble.

    Sensitivity = 1 - mean best-match similarity between the two event sets,
    plus the absolute difference in asserted-event counts, normalised.
    A well-behaved model should score near 0.
    """
    ev_h = [e for e in pred_human.events if e.status.value != "unknown"]
    ev_a = [e for e in pred_ai.events if e.status.value != "unknown"]
    if not ev_h and not ev_a:
        return {"framing_sensitivity": 0.0, "asserted_delta": 0}
    sims: list[float] = []
    for eh in ev_h:
        best = max(
            (label_similarity(eh.description, ea.description) for ea in ev_a),
            default=0.0,
        )
        sims.append(best)
    mean_sim = sum(sims) / len(sims) if sims else 0.0
    delta = abs(len(ev_h) - len(ev_a))
    denom = max(len(ev_h), len(ev_a), 1)
    sensitivity = round(min(1.0, (1 - mean_sim) * 0.7 + (delta / denom) * 0.3), 4)
    return {
        "framing_sensitivity": sensitivity,
        "asserted_delta": delta,
        "mean_event_similarity": round(mean_sim, 4),
    }
