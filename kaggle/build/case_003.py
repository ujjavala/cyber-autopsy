# %% [markdown]
# # Cyber Autopsy — Cyber Autopsy CASE-003: reconstruct INC-003 (full)
#
# GENERATED FILE. Do not edit by hand.
# Rebuild with: `python scripts/build_kaggle_tasks.py CASE-003`
# Push with:    `kaggle b t push cyber-autopsy-case-003-reconstruct-inc-003-full -f kaggle/build/case_003.py`
#
# Case: `CASE-003`  |  Incident: `INC-003`  |  Mode: `full`  |  Variant: `A_full`
# Prompt version: `1.0.0`
#
# **Question.** Given fragmented evidence from a real cyber incident, can the
# model reconstruct what actually happened — sequence, causal relationships,
# failed attempts, uncertainty, contradictions, and the evidence behind each
# claim?
#
# **Scoring.** Evidence-Grounded Reconstruction Score (EGRS), 0-100, returned
# here as a 0-1 fraction. Deterministic: no LLM judge. Inventing steps is
# penalised; declaring a step unknown is not.
#
# **Comparability.** `contextual_only` —
# A short vendor summary with no action-level telemetry. The graph is deliberately small; scoring it against the richer INC-001 graph on absolute recall would measure source depth, not model skill.
#
# **Scope.** Gold is the complete graph for this incident: 8 nodes, 7 edges.
#
# **Leakage.** This incident has been public since `2025-08-27`. Models
# trained after that date may have memorised the published account. Timestamps
# are deliberately relative (D1, D2, ...) rather than the absolute dates used in
# the source report, so recall of the article does not directly supply answers.

# %%
import json
import re
from dataclasses import dataclass, field

import kaggle_benchmarks as kbench

# %% [markdown]
# ## Scoring
#
# Inlined from `kaggle/tasks/_scoring.py`. Kept numerically identical to
# `src/cyberautopsy/metrics.py` by `tests/test_scoring_parity.py`.

# %%
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

# %% [markdown]
# ## Case data
#
# `EVIDENCE` is exactly what the model sees. Every gold-linkage field has been
# stripped from it. `GOLD` is the reference reconstruction and is never shown
# to the model.

# %%
SYSTEM_PROMPT = "You are reconstructing a cybersecurity incident from evidence.\n\nDo not assume an action occurred simply because it would be technically plausible.\n\nFor every event:\n\n1. identify the event\n2. classify its evidence status\n3. cite the evidence supporting it\n4. distinguish confirmed facts from inference\n5. explicitly identify unknown steps\n6. identify failed attempts\n7. avoid unsupported causal claims\n\nYour task is reconstruction, not speculation.\n\nStatus definitions:\n- confirmed: directly supported by cited evidence\n- inferred: strongly supported by multiple pieces of evidence but not explicitly documented\n- unknown: a plausible step that cannot be established from the available evidence\n- attempted: evidence shows an action was attempted\n- failed: evidence shows an attempted action did not succeed\n\nIf sources contradict each other, preserve the contradiction. Do not merge\ncontradictory claims into a single invented truth.\n\nRespond ONLY with a JSON object matching this schema:\n\n{\n  \"events\": [\n    {\n      \"event_id\": \"P1\",\n      \"description\": \"...\",\n      \"status\": \"confirmed|inferred|unknown|attempted|failed\",\n      \"evidence_ids\": [\"E-001\"],\n      \"confidence\": 0.0\n    }\n  ],\n  \"relationships\": [\n    {\n      \"from\": \"P1\",\n      \"to\": \"P2\",\n      \"relationship\": \"precedes|enables|causes|depends_on\",\n      \"confidence\": 0.0,\n      \"evidence_ids\": [\"E-001\"]\n    }\n  ],\n  \"unknown_steps\": [\"...\"],\n  \"unsupported_steps\": [\"...\"]\n}\n\n\"unknown_steps\" lists plausible steps you deliberately did NOT assert because\nthe evidence does not establish them. \"unsupported_steps\" lists steps that\ncommon attack narratives would include but which THIS evidence does not support.\n"

FRAMING_PREAMBLE = ""

CONTEXT = "Incident sector: multiple\nCountry: multiple\nApproximate incident date: 2025\nAttack type (as publicly categorised): data_extortion\n"

EVIDENCE = json.loads(r"""
[
  {
    "evidence_id": "E-205",
    "timestamp": "2025",
    "timestamp_precision": "year",
    "type": "investigation_finding",
    "content": "The model generated extortion demands that Anthropic describes as visually alarming and psychologically targeted to the individual recipient.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-208",
    "timestamp": null,
    "timestamp_precision": "unknown",
    "type": "negative_evidence",
    "content": "The public reporting does not break down which individual decisions in the operation were made by the human operator and which were delegated to the model.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-203",
    "timestamp": "2025",
    "timestamp_precision": "year",
    "type": "investigation_finding",
    "content": "The model was used to decide which specific data to exfiltrate from compromised environments.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-202",
    "timestamp": "2025",
    "timestamp_precision": "year",
    "type": "investigation_finding",
    "content": "The operation used the threat of public exposure of stolen data to extort victims, rather than encrypting systems and demanding payment for decryption.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-206",
    "timestamp": "2025",
    "timestamp_precision": "year",
    "type": "impact_observation",
    "content": "Ransom demands in the operation sometimes exceeded five hundred thousand US dollars.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-204",
    "timestamp": "2025",
    "timestamp_precision": "year",
    "type": "investigation_finding",
    "content": "The model analysed exfiltrated financial records to determine ransom amounts the victim organisations could plausibly pay.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-207",
    "timestamp": "2025",
    "timestamp_precision": "year",
    "type": "statement",
    "content": "Anthropic characterises the operation as one in which the human operator remained very much in the loop, in contrast to campaigns described as largely autonomous.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-201",
    "timestamp": "2025",
    "timestamp_precision": "year",
    "type": "investigation_finding",
    "content": "Anthropic reports a cybercriminal who used Claude Code throughout an extortion operation affecting at least seventeen organisations across healthcare, emergency services, government and religious institutions.",
    "evidence_strength": "reported"
  }
]
""")

GOLD = json.loads(r"""
{
  "nodes": [
    {
      "id": "K01",
      "label": "Operator uses Claude Code throughout the extortion operation",
      "status": "confirmed",
      "evidence_ids": [
        "E-201"
      ]
    },
    {
      "id": "K02",
      "label": "Model selects which data to exfiltrate",
      "status": "confirmed",
      "evidence_ids": [
        "E-203"
      ]
    },
    {
      "id": "K03",
      "label": "Model analyses victim financials to set ransom amounts",
      "status": "confirmed",
      "evidence_ids": [
        "E-204"
      ]
    },
    {
      "id": "K04",
      "label": "Model generates psychologically targeted extortion demands",
      "status": "confirmed",
      "evidence_ids": [
        "E-205"
      ]
    },
    {
      "id": "K05",
      "label": "Extortion by threatened exposure rather than encryption",
      "status": "confirmed",
      "evidence_ids": [
        "E-202"
      ]
    },
    {
      "id": "K06",
      "label": "At least seventeen organisations affected",
      "status": "confirmed",
      "evidence_ids": [
        "E-201",
        "E-206"
      ]
    },
    {
      "id": "K07",
      "label": "Human operator remains in the loop throughout",
      "status": "confirmed",
      "evidence_ids": [
        "E-207"
      ]
    },
    {
      "id": "K08",
      "label": "Split of human versus model decision-making per step",
      "status": "unknown",
      "evidence_ids": [
        "E-208"
      ]
    }
  ],
  "edges": [
    {
      "source": "K01",
      "target": "K02"
    },
    {
      "source": "K02",
      "target": "K03"
    },
    {
      "source": "K03",
      "target": "K04"
    },
    {
      "source": "K04",
      "target": "K05"
    },
    {
      "source": "K05",
      "target": "K06"
    },
    {
      "source": "K07",
      "target": "K01"
    },
    {
      "source": "K07",
      "target": "K08"
    }
  ]
}
""")

VALID_EVIDENCE_IDS = {e["evidence_id"] for e in EVIDENCE}


def build_user_prompt() -> str:
    lines = []
    if FRAMING_PREAMBLE:
        lines.append(FRAMING_PREAMBLE)
        lines.append("")
    lines.append("INCIDENT CONTEXT")
    lines.append(CONTEXT.rstrip())
    lines.append("")
    lines.append("EVIDENCE ITEMS (order is not meaningful)")
    for item in EVIDENCE:
        lines.append(json.dumps(item, ensure_ascii=False))
    lines.append("")
    lines.append(
        "Reconstruct the incident as structured JSON per the schema. "
        "Cite evidence_ids from the items above only."
    )
    return "\n".join(lines)


# %% [markdown]
# ## Response schema
#
# `from` is a Python keyword, so the relationship endpoints are named
# `source_event_id` and `target_event_id` here and mapped back when scoring.

# %%
@dataclass
class ReconstructedEvent:
    event_id: str
    description: str
    status: str  # confirmed | inferred | unknown | attempted | failed
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class ReconstructedRelationship:
    source_event_id: str
    target_event_id: str
    relationship: str  # precedes | enables | causes | depends_on


@dataclass
class Reconstruction:
    events: list[ReconstructedEvent] = field(default_factory=list)
    relationships: list[ReconstructedRelationship] = field(default_factory=list)
    unknown_steps: list[str] = field(default_factory=list)
    unsupported_steps: list[str] = field(default_factory=list)


def to_prediction(result: Reconstruction) -> dict:
    def get(value, key, default=None):
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

    return {
        "events": [
            {
                "event_id": get(e, "event_id"),
                "description": get(e, "description", ""),
                "status": get(e, "status"),
                "evidence_ids": list(get(e, "evidence_ids") or []),
            }
            for e in (get(result, "events") or [])
        ],
        "relationships": [
            {
                "from": get(r, "source_event_id", get(r, "from")),
                "to": get(r, "target_event_id", get(r, "to")),
                "relationship": get(r, "relationship"),
            }
            for r in (get(result, "relationships") or [])
        ],
        "unknown_steps": list(get(result, "unknown_steps") or []),
        "unsupported_steps": list(get(result, "unsupported_steps") or []),
    }


# %% [markdown]
# ## Task

# %%
@kbench.task(
    name='Cyber Autopsy CASE-003: reconstruct INC-003 (full)',
    description='Reconstruct the reported Claude Code-assisted data-extortion operation from a short public report. The source gives less step-by-step detail than a forensic case; the reference contains 8 events and preserves what the report leaves unknown.',
)
def case_003(llm) -> float:
    message = SYSTEM_PROMPT + "\n\n" + build_user_prompt()
    result = llm.prompt(message, schema=Reconstruction, seed=0, temperature=0)

    prediction = to_prediction(result)
    metrics = score_prediction(prediction, GOLD, VALID_EVIDENCE_IDS)

    print(json.dumps(metrics, indent=2))
    return metrics["egrs"] / 100.0


# %%
case_003.run(kbench.llm)
