"""Dependency-free scoring, embedded verbatim into generated Kaggle tasks.

A Kaggle Benchmarks task file runs in isolation: no project imports, no
pydantic, no networkx. This module therefore reimplements the scoring from
``cyberautopsy.metrics`` over plain dicts.

Two implementations of the same formula is a liability, so it is held to
account by ``tests/test_scoring_parity.py``, which asserts that both produce
identical numbers for the same inputs. If you change one, change both and let
the parity test prove it.

The only deliberate omission is ``normalized_ged``, which requires networkx
and SciPy and is a secondary diagnostic that never feeds EGRS.
"""

from __future__ import annotations

import re

MATCH_THRESHOLD = 0.25
EVIDENCE_BONUS = 0.25

_STOPWORDS = frozenset(
    "a an the of to in on at by for with from was were is are be been "
    "and or that this it its as into via using used".split()
)

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-_.]*")

_RECOVERABLE = frozenset({"confirmed", "inferred", "attempted", "failed"})


def _tokens(text):
    return frozenset(t for t in _WORD_RE.findall(text.lower()) if t not in _STOPWORDS)


def label_similarity(a, b):
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def match_events(pred_events, gold_nodes):
    """Greedy deterministic 1:1 matching, highest similarity first."""
    candidates = []
    for pe in pred_events:
        for gn in gold_nodes:
            score = label_similarity(pe.get("description", ""), gn.get("label", ""))
            pe_ev, gn_ev = pe.get("evidence_ids") or [], gn.get("evidence_ids") or []
            if pe_ev and gn_ev and (set(pe_ev) & set(gn_ev)):
                score += EVIDENCE_BONUS
            if score >= MATCH_THRESHOLD:
                candidates.append((score, pe["event_id"], gn["id"]))
    candidates.sort(key=lambda c: (-c[0], c[1], c[2]))

    used_pred, used_gold, mapping = set(), set(), {}
    for _score, pid, gid in candidates:
        if pid in used_pred or gid in used_gold:
            continue
        used_pred.add(pid)
        used_gold.add(gid)
        mapping[pid] = gid
    return mapping


def _f1(precision, recall):
    if precision + recall <= 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def score_prediction(pred, gold, valid_evidence_ids):
    """Return the full metric dict for one prediction. Mirrors compute_metrics."""
    events = pred.get("events") or []
    relationships = pred.get("relationships") or []
    unknown_steps = pred.get("unknown_steps") or []

    gold_nodes = gold.get("nodes") or []
    gold_edges_list = gold.get("edges") or []
    gold_by_id = {n["id"]: n for n in gold_nodes}
    recoverable = [n for n in gold_nodes if n.get("status") in _RECOVERABLE]

    p2g = match_events(events, gold_nodes)
    matched_gold_ids = set(p2g.values())

    recall = (
        sum(1 for n in recoverable if n["id"] in matched_gold_ids) / len(recoverable)
        if recoverable
        else 0.0
    )

    n_pred = len(events)
    supported = 0
    hallucinated = 0
    for pe in events:
        if pe["event_id"] in p2g:
            supported += 1
        elif pe.get("status") == "unknown":
            pass
        else:
            hallucinated += 1
    precision = supported / n_pred if n_pred else 0.0
    hallucination_rate = hallucinated / n_pred if n_pred else 0.0

    gold_edges = {(e["source"], e["target"]) for e in gold_edges_list}
    pred_edges_mapped = set()
    n_pred_rels = len(relationships)
    for rel in relationships:
        gs = p2g.get(rel.get("from"))
        gt = p2g.get(rel.get("to"))
        if gs and gt:
            pred_edges_mapped.add((gs, gt))
    correct_edges = pred_edges_mapped & gold_edges
    edge_precision = len(correct_edges) / n_pred_rels if n_pred_rels else 0.0
    edge_recall = len(correct_edges) / len(gold_edges) if gold_edges else 0.0
    link_f1 = _f1(edge_precision, edge_recall)

    attributions = []
    for pe in events:
        gid = p2g.get(pe["event_id"])
        if gid is None:
            continue
        pset = set(pe.get("evidence_ids") or [])
        gset = set(gold_by_id[gid].get("evidence_ids") or [])
        if not gset and not pset:
            attributions.append(1.0)
        elif not gset or not pset:
            attributions.append(0.0)
        else:
            attributions.append(len(pset & gset) / len(pset | gset))
    evidence_attribution = sum(attributions) / len(attributions) if attributions else 0.0

    status_hits = 0
    for pe in events:
        gid = p2g.get(pe["event_id"])
        if gid is None:
            continue
        gold_status = gold_by_id[gid].get("status")
        if pe.get("status") == gold_status:
            status_hits += 1
        elif gold_status == "contradicted" and pe.get("status") == "unknown":
            status_hits += 1
    status_accuracy = status_hits / len(p2g) if p2g else 0.0

    gold_unknown = [n for n in gold_nodes if n.get("status") == "unknown"]
    attempted_reconstruction = bool(events) or bool(unknown_steps)
    if gold_unknown and attempted_reconstruction:
        cal_hits = 0.0
        unknown_steps_text = " ".join(unknown_steps).lower()
        for gn in gold_unknown:
            matched_pred = next(
                (e for e in events if p2g.get(e["event_id"]) == gn["id"]), None
            )
            if matched_pred is not None:
                if matched_pred.get("status") == "unknown":
                    cal_hits += 1.0
            elif label_similarity(gn["label"], unknown_steps_text) > 0 or any(
                label_similarity(gn["label"], step) >= MATCH_THRESHOLD
                for step in unknown_steps
            ):
                cal_hits += 1.0
            else:
                cal_hits += 0.5
        unknown_calibration = cal_hits / len(gold_unknown)
    elif not attempted_reconstruction:
        unknown_calibration = 0.0
    else:
        unknown_calibration = 1.0

    gold_af = [n for n in gold_nodes if n.get("status") in ("attempted", "failed")]
    if gold_af:
        af_hits = 0
        for gn in gold_af:
            matched_pred = next(
                (e for e in events if p2g.get(e["event_id"]) == gn["id"]), None
            )
            if matched_pred is not None and matched_pred.get("status") in (
                "attempted",
                "failed",
            ):
                af_hits += 1
        failed_recognition = af_hits / len(gold_af)
    elif not attempted_reconstruction:
        failed_recognition = 0.0
    else:
        failed_recognition = 1.0

    gold_contra = [n for n in gold_nodes if n.get("status") == "contradicted"]
    if gold_contra:
        c_hits = 0
        for gn in gold_contra:
            matched_pred = next(
                (e for e in events if p2g.get(e["event_id"]) == gn["id"]), None
            )
            if matched_pred is None or matched_pred.get("status") in (
                "unknown",
                "failed",
            ):
                c_hits += 1
        contradiction_handling = c_hits / len(gold_contra)
    else:
        contradiction_handling = 1.0

    node_precision = len(matched_gold_ids) / n_pred if n_pred else 0.0
    node_recall = len(matched_gold_ids) / len(gold_nodes) if gold_nodes else 0.0
    graph_f1 = (_f1(node_precision, node_recall) + link_f1) / 2

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
        "egrs": round(egrs, 2),
        "n_predicted_events": n_pred,
        "n_gold_nodes": len(gold_nodes),
    }
