"""Aggregate reporting: statistics, complexity banding, report generation.

No conclusions are generated without actual benchmark results.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from .dataset import Dataset
from .graph import branching_factor, gold_to_nx, graph_depth


def incident_complexity(ds: Dataset, incident_id: str) -> str:
    """Transparent complexity banding used for stratified reporting."""
    evidence_n = len(ds.evidence_for_incident(incident_id))
    graph = ds.graphs.get(incident_id)
    nodes_n = len(graph.nodes) if graph else 0
    depth = graph_depth(gold_to_nx(graph)) if graph else 0
    score = evidence_n + nodes_n + 2 * depth
    if score <= 24:
        return "simple"
    if score <= 40:
        return "medium"
    return "complex"


def dataset_stats(ds: Dataset) -> dict:
    graphs = list(ds.graphs.values())
    status_counts: dict[str, int] = {}
    for g in graphs:
        for n in g.nodes:
            status_counts[n.status.value] = status_counts.get(n.status.value, 0) + 1
    contradiction_rate = (
        sum(1 for e in ds.evidence.values() if e.contradicts)
        / len(ds.evidence)
        if ds.evidence
        else 0.0
    )
    return {
        "incidents": len(ds.incidents),
        "evidence_items": len(ds.evidence),
        "sources": len(ds.sources),
        "graph_nodes": sum(len(g.nodes) for g in graphs),
        "graph_edges": sum(len(g.edges) for g in graphs),
        "node_status_counts": status_counts,
        "contradiction_rate": round(contradiction_rate, 4),
        "incidents_by_year": _count(ds, lambda i: i.incident_date[:4]),
        "incidents_by_attack_type": _count(ds, lambda i: i.attack_type),
        "incidents_by_sector": _count(ds, lambda i: i.sector),
        "incidents_by_country": _count(ds, lambda i: i.country),
        "complexity_bands": {
            iid: incident_complexity(ds, iid) for iid in ds.incidents
        },
        "mean_branching": round(
            sum(branching_factor(gold_to_nx(g)) for g in graphs) / len(graphs), 3
        )
        if graphs
        else 0.0,
    }


def _count(ds: Dataset, keyfn) -> dict[str, int]:
    counts: dict[str, int] = {}
    for inc in ds.incidents.values():
        k = keyfn(inc)
        counts[k] = counts.get(k, 0) + 1
    return dict(sorted(counts.items()))


def bias_warnings(ds: Dataset) -> list[str]:
    """Anti-bias checks over the dataset itself."""
    warnings: list[str] = []
    stats = dataset_stats(ds)
    n = stats["incidents"] or 1

    for atype, count in stats["incidents_by_attack_type"].items():
        share = count / n
        if share > 0.5:
            warnings.append(
                f"WARNING: {share:.0%} of incidents are '{atype}'. The benchmark "
                f"may underrepresent other attack classes."
            )
    pub_counts: dict[str, int] = {}
    for s in ds.sources.values():
        pub_counts[s.publisher] = pub_counts.get(s.publisher, 0) + 1
    for pub, count in pub_counts.items():
        if ds.sources and count / len(ds.sources) > 0.4:
            warnings.append(
                f"WARNING: {count}/{len(ds.sources)} sources come from "
                f"'{pub}'. Excessive reliance on one publisher."
            )
    for iid in ds.incidents:
        ev_n = len(ds.evidence_for_incident(iid))
        if ev_n < 6:
            warnings.append(
                f"WARNING: {iid} has only {ev_n} evidence items; may be "
                f"insufficient for a defensible graph."
            )
        srcs = ds.sources_for_incident(iid)
        if len(srcs) < 2:
            warnings.append(
                f"WARNING: {iid} relies on a single source; contradiction "
                f"checks are impossible."
            )
    return warnings


def bootstrap_ci(
    values: list[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 42
) -> tuple[float, float] | None:
    if len(values) < 3:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        sample = [rng.choice(values) for _ in values]
        means.append(sum(sample) / len(sample))
    means.sort()
    lo = means[int(math.floor(alpha / 2 * n_boot))]
    hi = means[int(math.ceil((1 - alpha / 2) * n_boot)) - 1]
    return (round(lo, 4), round(hi, 4))


def summarize_results(results_dir: Path) -> dict:
    """Collect metrics.json files across models into a leaderboard dict."""
    board: dict[str, dict] = {}
    if not results_dir.exists():
        return board
    for model_dir in sorted(results_dir.iterdir()):
        mfile = model_dir / "metrics.json"
        if mfile.is_file():
            board[model_dir.name] = json.loads(mfile.read_text())
    return board
