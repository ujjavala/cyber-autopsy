"""The embedded Kaggle scoring must agree with the project scoring exactly.

There are two implementations of EGRS: ``src/cyberautopsy/metrics.py`` (rich,
pydantic, networkx) and ``kaggle/tasks/_scoring.py`` (plain dicts, inlined into
generated task files). Duplication is a liability. This test is the thing that
makes it a safe one.
"""

from __future__ import annotations

import importlib.util
import random
from pathlib import Path

import pytest

from cyberautopsy.metrics import compute_metrics
from cyberautopsy.schemas import (
    AttackGraph,
    EdgeRelation,
    GraphEdge,
    GraphNode,
    ModelPrediction,
)

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "kaggle_scoring", ROOT / "kaggle" / "tasks" / "_scoring.py"
)
kaggle_scoring = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kaggle_scoring)

SHARED_KEYS = [
    "event_recall",
    "event_precision",
    "hallucinated_event_rate",
    "edge_precision",
    "edge_recall",
    "link_f1",
    "evidence_attribution",
    "status_accuracy",
    "unknown_calibration",
    "failed_recognition",
    "contradiction_handling",
    "node_precision",
    "node_recall",
    "graph_f1",
    "egrs",
]

STATUSES = ["confirmed", "inferred", "unknown", "attempted", "failed"]
GOLD_STATUSES = STATUSES + ["contradicted"]
RELATIONS = ["precedes", "enables", "causes", "depends_on"]
WORDS = (
    "password spray rdp mimikatz lsass dcsync exfiltration rclone sftp "
    "ransomware shadow copies cleared logs scanner lateral movement backup"
).split()


def random_gold(rng: random.Random) -> dict:
    n = rng.randint(1, 8)
    nodes = [
        {
            "id": f"N{i}",
            "label": " ".join(rng.sample(WORDS, rng.randint(2, 5))),
            "status": rng.choice(GOLD_STATUSES),
            "evidence_ids": rng.sample(
                [f"E-{j}" for j in range(6)], rng.randint(0, 3)
            ),
        }
        for i in range(n)
    ]
    edges = []
    for _ in range(rng.randint(0, n)):
        a, b = rng.choice(nodes)["id"], rng.choice(nodes)["id"]
        edges.append({"source": a, "target": b})
    return {"nodes": nodes, "edges": edges}


def random_pred(rng: random.Random) -> dict:
    n = rng.randint(0, 8)
    events = [
        {
            "event_id": f"P{i}",
            "description": " ".join(rng.sample(WORDS, rng.randint(2, 5))),
            "status": rng.choice(STATUSES),
            "evidence_ids": rng.sample(
                [f"E-{j}" for j in range(8)], rng.randint(0, 3)
            ),
        }
        for i in range(n)
    ]
    rels = []
    if events:
        for _ in range(rng.randint(0, 5)):
            rels.append(
                {
                    "from": rng.choice(events)["event_id"],
                    "to": rng.choice(events)["event_id"],
                    "relationship": rng.choice(RELATIONS),
                }
            )
    return {
        "events": events,
        "relationships": rels,
        "unknown_steps": [
            " ".join(rng.sample(WORDS, 3)) for _ in range(rng.randint(0, 2))
        ],
        "unsupported_steps": [],
    }


def to_models(pred: dict, gold: dict) -> tuple[ModelPrediction, AttackGraph]:
    prediction = ModelPrediction.model_validate(pred)
    graph = AttackGraph(
        incident_id="INC-PARITY",
        nodes=[
            GraphNode(
                id=n["id"],
                label=n["label"],
                status=n["status"],
                evidence_ids=n["evidence_ids"],
            )
            for n in gold["nodes"]
        ],
        edges=[
            GraphEdge(
                source=e["source"], target=e["target"], relation=EdgeRelation.precedes
            )
            for e in gold["edges"]
        ],
    )
    return prediction, graph


@pytest.mark.parametrize("seed", range(60))
def test_scoring_matches_metrics_module(seed: int):
    rng = random.Random(seed)
    gold = random_gold(rng)
    pred = random_pred(rng)
    valid = {f"E-{j}" for j in range(6)}

    prediction, graph = to_models(pred, gold)
    reference = compute_metrics(prediction, graph, valid)
    embedded = kaggle_scoring.score_prediction(pred, gold, valid)

    for key in SHARED_KEYS:
        assert embedded[key] == reference[key], (
            f"seed={seed} key={key}: "
            f"embedded={embedded[key]} reference={reference[key]}"
        )


def test_label_similarity_matches():
    from cyberautopsy.metrics import label_similarity as reference

    pairs = [
        ("Mimikatz LSASS credential dumping", "credential dumping via Mimikatz"),
        ("", "anything at all"),
        ("the of to in", "the of to in"),
        ("Password spray", "PASSWORD SPRAY"),
    ]
    for a, b in pairs:
        assert kaggle_scoring.label_similarity(a, b) == reference(a, b)


def test_constants_match():
    from cyberautopsy import metrics as reference

    assert kaggle_scoring.MATCH_THRESHOLD == reference.MATCH_THRESHOLD
    assert kaggle_scoring.EVIDENCE_BONUS == reference.EVIDENCE_BONUS
