"""Graph utilities: NetworkX conversion, validation and similarity."""

from __future__ import annotations

import networkx as nx

from .schemas import AttackGraph, ModelPrediction


def gold_to_nx(graph: AttackGraph) -> nx.DiGraph:
    g = nx.DiGraph()
    for node in graph.nodes:
        g.add_node(node.id, label=node.label, status=node.status.value)
    for edge in graph.edges:
        g.add_edge(edge.source, edge.target, relation=edge.relation.value)
    return g


def prediction_to_nx(pred: ModelPrediction) -> nx.DiGraph:
    g = nx.DiGraph()
    for ev in pred.events:
        g.add_node(ev.event_id, label=ev.description, status=ev.status.value)
    for rel in pred.relationships:
        if rel.from_ in g and rel.to in g:
            g.add_edge(rel.from_, rel.to, relation=rel.relationship.value)
    return g


def validate_graph(graph: AttackGraph, evidence_ids: set[str]) -> list[str]:
    """Return a list of structural problems (empty list = valid)."""
    problems: list[str] = []
    node_ids = [n.id for n in graph.nodes]
    if len(node_ids) != len(set(node_ids)):
        problems.append(f"{graph.incident_id}: duplicate node ids")
    node_set = set(node_ids)
    for edge in graph.edges:
        if edge.source not in node_set:
            problems.append(
                f"{graph.incident_id}: edge references unknown node {edge.source}"
            )
        if edge.target not in node_set:
            problems.append(
                f"{graph.incident_id}: edge references unknown node {edge.target}"
            )
    for node in graph.nodes:
        for eid in node.evidence_ids:
            if eid not in evidence_ids:
                problems.append(
                    f"{graph.incident_id}:{node.id}: unknown evidence {eid}"
                )
        if node.status.value == "confirmed" and not node.evidence_ids:
            problems.append(
                f"{graph.incident_id}:{node.id}: confirmed node without evidence"
            )
    return problems


def graph_depth(g: nx.DiGraph) -> int:
    if g.number_of_nodes() == 0:
        return 0
    if nx.is_directed_acyclic_graph(g):
        return int(nx.dag_longest_path_length(g)) + 1
    return g.number_of_nodes()


def branching_factor(g: nx.DiGraph) -> float:
    degrees = [d for _, d in g.out_degree()]
    return (sum(degrees) / len(degrees)) if degrees else 0.0


def normalized_ged(g1: nx.DiGraph, g2: nx.DiGraph, max_nodes: int = 12) -> float | None:
    """Normalized graph edit distance in [0, 1]; None if it cannot be computed.

    Uses the first (upper-bound) estimate from optimize_graph_edit_distance
    for determinism and bounded runtime. Only run on small graphs.

    Returns None rather than raising when the graphs are too large or when
    SciPy is not installed. GED is a secondary diagnostic, never an input to
    EGRS, so it must never be able to break a scoring run.
    """
    if g1.number_of_nodes() > max_nodes or g2.number_of_nodes() > max_nodes:
        return None
    try:
        gen = nx.optimize_graph_edit_distance(g1, g2)
        ged = next(gen)
    except (StopIteration, nx.NetworkXError, ImportError, ModuleNotFoundError):
        return None
    denom = (
        g1.number_of_nodes()
        + g1.number_of_edges()
        + g2.number_of_nodes()
        + g2.number_of_edges()
    )
    return min(1.0, ged / denom) if denom else 0.0
    denom = (
        g1.number_of_nodes()
        + g1.number_of_edges()
        + g2.number_of_nodes()
        + g2.number_of_edges()
    )
    return min(1.0, ged / denom) if denom else 0.0
