"""Deterministic benchmark metrics.

No LLM judge. Every number here is reproducible from the prediction, the
gold graph, and the evidence index.

Event matching
--------------
Predicted events are matched to gold nodes with a greedy, deterministic
best-match on normalised token overlap (Jaccard) between the predicted
description and the gold label, with a bonus for overlapping cited
evidence IDs. A pair is a match when score >= MATCH_THRESHOLD.

Composite metric
----------------
Evidence-Grounded Reconstruction Score (EGRS), on a 0-100 scale:

    EGRS = 100 * max(0,
          0.25 * event_recall
        + 0.20 * event_precision
        + 0.15 * link_f1
        + 0.15 * evidence_attribution
        + 0.10 * status_accuracy
        + 0.10 * unknown_calibration
        + 0.05 * failed_recognition
        - 0.25 * hallucinated_event_rate )

The formula is fully documented in SCORING.md and implemented verbatim here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .graph import gold_to_nx, normalized_ged, prediction_to_nx
from .schemas import (
    AttackGraph,
    GraphNode,
    ModelPrediction,
    NodeStatus,
    PredictedEvent,
)

MATCH_THRESHOLD = 0.25
EVIDENCE_BONUS = 0.25

_STOPWORDS = frozenset(
    "a an the of to in on at by for with from was were is are be been "
    "and or that this it its as into via using used".split()
)

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-_.]*")


def _tokens(text: str) -> frozenset[str]:
    return frozenset(
        t for t in _WORD_RE.findall(text.lower()) if t not in _STOPWORDS
    )


def label_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


@dataclass
class EventMatch:
    pred_event_id: str
    gold_node_id: str
    score: float


@dataclass
class MatchResult:
    matches: list[EventMatch] = field(default_factory=list)
    unmatched_pred: list[str] = field(default_factory=list)
    unmatched_gold: list[str] = field(default_factory=list)

    def pred_to_gold(self) -> dict[str, str]:
        return {m.pred_event_id: m.gold_node_id for m in self.matches}


def match_events(
    pred_events: list[PredictedEvent], gold_nodes: list[GraphNode]
) -> MatchResult:
    """Greedy deterministic 1:1 matching, highest similarity first.

    Ties are broken by (pred_event_id, gold_node_id) for determinism.
    """
    candidates: list[tuple[float, str, str]] = []
    gold_by_id = {n.id: n for n in gold_nodes}
    for pe in pred_events:
        for gn in gold_nodes:
            score = label_similarity(pe.description, gn.label)
            if pe.evidence_ids and gn.evidence_ids:
                overlap = set(pe.evidence_ids) & set(gn.evidence_ids)
                if overlap:
                    score += EVIDENCE_BONUS
            if score >= MATCH_THRESHOLD:
                candidates.append((score, pe.event_id, gn.id))
    candidates.sort(key=lambda c: (-c[0], c[1], c[2]))

    used_pred: set[str] = set()
    used_gold: set[str] = set()
    result = MatchResult()
    for score, pid, gid in candidates:
        if pid in used_pred or gid in used_gold:
            continue
        used_pred.add(pid)
        used_gold.add(gid)
        result.matches.append(EventMatch(pid, gid, round(score, 4)))
    result.unmatched_pred = sorted(
        pe.event_id for pe in pred_events if pe.event_id not in used_pred
    )
    result.unmatched_gold = sorted(
        gid for gid in gold_by_id if gid not in used_gold
    )
    return result


# ---------------------------------------------------------------------------
# Individual metrics
# ---------------------------------------------------------------------------

# Gold nodes a model is expected to recover as asserted events.
_RECOVERABLE = {
    NodeStatus.confirmed,
    NodeStatus.inferred,
    NodeStatus.attempted,
    NodeStatus.failed,
}


def compute_metrics(
    pred: ModelPrediction,
    gold: AttackGraph,
    valid_evidence_ids: set[str],
) -> dict:
    gold_nodes = gold.nodes
    gold_by_id = {n.id: n for n in gold_nodes}
    recoverable = [n for n in gold_nodes if n.status in _RECOVERABLE]
    mr = match_events(pred.events, gold_nodes)
    p2g = mr.pred_to_gold()
    matched_gold_ids = set(p2g.values())

    # --- Event recall: matched recoverable gold events / recoverable gold
    recall = (
        sum(1 for n in recoverable if n.id in matched_gold_ids) / len(recoverable)
        if recoverable
        else 0.0
    )

    # --- Event precision: supported predicted events / predicted events.
    # A predicted event is "supported" if it matched a gold node OR every
    # cited evidence id exists in the packet AND it was marked unknown.
    n_pred = len(pred.events)
    supported = 0
    hallucinated = 0
    for pe in pred.events:
        if pe.event_id in p2g:
            supported += 1
        elif pe.status.value == "unknown":
            # Declared uncertainty is not a hallucination, but earns no credit.
            pass
        else:
            cited_ok = bool(pe.evidence_ids) and all(
                eid in valid_evidence_ids for eid in pe.evidence_ids
            )
            if not cited_ok:
                hallucinated += 1
            else:
                # Cites real evidence but matched no gold node: unsupported
                # reconstruction — counts against precision and as
                # hallucination (an asserted event absent from gold).
                hallucinated += 1
    precision = supported / n_pred if n_pred else 0.0
    hallucination_rate = hallucinated / n_pred if n_pred else 0.0

    # --- Link accuracy (edge precision / recall / F1 via node mapping)
    gold_edges = {(e.source, e.target) for e in gold.edges}
    pred_edges_mapped: set[tuple[str, str]] = set()
    n_pred_rels = len(pred.relationships)
    for rel in pred.relationships:
        gs, gt = p2g.get(rel.from_), p2g.get(rel.to)
        if gs and gt:
            pred_edges_mapped.add((gs, gt))
    correct_edges = pred_edges_mapped & gold_edges
    edge_precision = len(correct_edges) / n_pred_rels if n_pred_rels else 0.0
    edge_recall = len(correct_edges) / len(gold_edges) if gold_edges else 0.0
    link_f1 = (
        2 * edge_precision * edge_recall / (edge_precision + edge_recall)
        if (edge_precision + edge_recall) > 0
        else 0.0
    )

    # --- Evidence attribution: for matched events, Jaccard of cited vs gold
    attributions: list[float] = []
    for m in mr.matches:
        pe = next(e for e in pred.events if e.event_id == m.pred_event_id)
        gn = gold_by_id[m.gold_node_id]
        pset, gset = set(pe.evidence_ids), set(gn.evidence_ids)
        if not gset and not pset:
            attributions.append(1.0)
        elif not gset or not pset:
            attributions.append(0.0)
        else:
            attributions.append(len(pset & gset) / len(pset | gset))
    evidence_attribution = (
        sum(attributions) / len(attributions) if attributions else 0.0
    )

    # --- Status accuracy on matched pairs
    status_hits = 0
    for m in mr.matches:
        pe = next(e for e in pred.events if e.event_id == m.pred_event_id)
        gn = gold_by_id[m.gold_node_id]
        if pe.status.value == gn.status.value:
            status_hits += 1
        elif gn.status == NodeStatus.contradicted and pe.status.value == "unknown":
            status_hits += 1  # treating contradicted gold as unknown is acceptable
    status_accuracy = status_hits / len(mr.matches) if mr.matches else 0.0

    # --- Unknown calibration: gold-unknown nodes must NOT be asserted as
    # confirmed/inferred. Credit for matching them as unknown or omitting
    # them while listing them in unknown_steps.
    #
    # Partial credit for silent omission applies only when the model actually
    # attempted a reconstruction. An empty prediction says nothing about
    # calibration, and must not be rewarded for restraint it never exercised.
    gold_unknown = [n for n in gold_nodes if n.status == NodeStatus.unknown]
    attempted_reconstruction = bool(pred.events) or bool(pred.unknown_steps)
    if gold_unknown and attempted_reconstruction:
        cal_hits = 0.0
        unknown_steps_text = " ".join(pred.unknown_steps).lower()
        for gn in gold_unknown:
            matched_pred = next(
                (
                    e
                    for e in pred.events
                    if p2g.get(e.event_id) == gn.id
                ),
                None,
            )
            if matched_pred is not None:
                if matched_pred.status.value == "unknown":
                    cal_hits += 1.0
                # asserted as confirmed/inferred => 0 credit (false certainty)
            else:
                if label_similarity(gn.label, unknown_steps_text) > 0 or any(
                    label_similarity(gn.label, step) >= MATCH_THRESHOLD
                    for step in pred.unknown_steps
                ):
                    cal_hits += 1.0
                else:
                    cal_hits += 0.5  # silently omitted: partial credit
        unknown_calibration = cal_hits / len(gold_unknown)
    elif not attempted_reconstruction:
        unknown_calibration = 0.0
    else:
        unknown_calibration = 1.0

    # --- Failed-attempt recognition: gold attempted/failed nodes must not be
    # credited as successful events.
    gold_af = [
        n for n in gold_nodes if n.status in (NodeStatus.attempted, NodeStatus.failed)
    ]
    if gold_af:
        af_hits = 0
        for gn in gold_af:
            matched_pred = next(
                (e for e in pred.events if p2g.get(e.event_id) == gn.id), None
            )
            if matched_pred is not None and matched_pred.status.value in (
                "attempted",
                "failed",
            ):
                af_hits += 1
        failed_recognition = af_hits / len(gold_af)
    elif not attempted_reconstruction:
        failed_recognition = 0.0
    else:
        failed_recognition = 1.0

    # --- Contradiction handling: gold contradicted nodes must not be
    # asserted as confirmed.
    gold_contra = [n for n in gold_nodes if n.status == NodeStatus.contradicted]
    if gold_contra:
        c_hits = 0
        for gn in gold_contra:
            matched_pred = next(
                (e for e in pred.events if p2g.get(e.event_id) == gn.id), None
            )
            if matched_pred is None or matched_pred.status.value in (
                "unknown",
                "failed",
            ):
                c_hits += 1
        contradiction_handling = c_hits / len(gold_contra)
    else:
        contradiction_handling = 1.0

    # --- Graph-level similarity
    g_gold = gold_to_nx(gold)
    g_pred = prediction_to_nx(pred)
    node_precision = len(matched_gold_ids) / n_pred if n_pred else 0.0
    node_recall = len(matched_gold_ids) / len(gold_nodes) if gold_nodes else 0.0
    graph_f1_parts = [
        x
        for x in (
            _f1(node_precision, node_recall),
            link_f1,
        )
    ]
    graph_f1 = sum(graph_f1_parts) / len(graph_f1_parts)
    ged = normalized_ged(g_gold, g_pred)

    egrs = 100.0 * max(
        0.0,
        0.25 * recall
        + 0.20 * precision
        + 0.15 * link_f1
        + 0.15 * evidence_attribution
        + 0.10 * status_accuracy
        + 0.10 * unknown_calibration
        + 0.05 * failed_recognition
        - 0.25 * hallucination_rate,
    )

    return {
        "event_recall": round(recall, 4),
        "event_precision": round(precision, 4),
        "hallucinated_event_rate": round(hallucination_rate, 4),
        "edge_precision": round(edge_precision, 4),
        "edge_recall": round(edge_recall, 4),
        "link_f1": round(link_f1, 4),
        "evidence_attribution": round(evidence_attribution, 4),
        "status_accuracy": round(status_accuracy, 4),
        "unknown_calibration": round(unknown_calibration, 4),
        "failed_recognition": round(failed_recognition, 4),
        "contradiction_handling": round(contradiction_handling, 4),
        "node_precision": round(node_precision, 4),
        "node_recall": round(node_recall, 4),
        "graph_f1": round(graph_f1, 4),
        "normalized_ged": round(ged, 4) if ged is not None else None,
        "egrs": round(egrs, 2),
        "n_predicted_events": n_pred,
        "n_gold_nodes": len(gold_nodes),
        "n_matches": len(mr.matches),
        "matches": [m.__dict__ for m in mr.matches],
        "unmatched_pred": mr.unmatched_pred,
        "unmatched_gold": mr.unmatched_gold,
    }


def _f1(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0
