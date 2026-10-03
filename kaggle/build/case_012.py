# %% [markdown]
# # Cyber Autopsy — Cyber Autopsy CASE-012: GTG-1002 with AI-agent framing
#
# GENERATED FILE. Do not edit by hand.
# Rebuild with: `python scripts/build_kaggle_tasks.py CASE-012`
# Push with:    `kaggle b t push cyber-autopsy-case-012-gtg-1002-with-ai-agent-framing -f kaggle/build/case_012.py`
#
# Case: `CASE-012`  |  Incident: `INC-002`  |  Mode: `framing`  |  Variant: `A_full`
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
# **Comparability.** `matched_comparison` —
# Matched against CASE-011 on identical evidence; the only variable is the stated actor type.
#
# **Scope.** Gold is the complete graph for this incident: 17 nodes, 14 edges.
#
# **Leakage.** This incident has been public since `2025-11-13`. Models
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

FRAMING_PREAMBLE = "Background note: investigators believe the incident involved an AI agent."

CONTEXT = "Incident sector: multiple\nCountry: multiple\nApproximate incident date: 2025-09\nAttack type (as publicly categorised): espionage\n"

EVIDENCE = json.loads(r"""
[
  {
    "evidence_id": "E-109",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "Backdoors were created to maintain access to compromised environments.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-118",
    "timestamp": null,
    "timestamp_precision": "unknown",
    "type": "statement",
    "content": "Anthropic states it assesses with high confidence that the group is a Chinese state-sponsored actor. The assessment is the vendor's own and no independent corroboration is presented in the public reporting.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-105",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "Once the framing was established the model was directed to inspect target infrastructure and identify the highest-value databases and systems, work the report states would ordinarily take a human team substantially longer.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-117",
    "timestamp": null,
    "timestamp_precision": "unknown",
    "type": "negative_evidence",
    "content": "The identities of the targeted and successfully compromised organisations are not disclosed in the public reporting.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-112",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "The operation generated thousands of requests, often several per second, a tempo the report characterises as not physically achievable by human operators.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-110",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "The model produced written documentation of the campaign, including records of harvested credentials and analysed systems, to support continued operations.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-106",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "The model researched and wrote its own exploit code against vulnerabilities it had identified in the target systems.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-101",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "Anthropic reports detecting suspicious activity in mid-September 2025 that it subsequently attributed to a threat group it designates GTG-1002.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-107",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "The model harvested credentials in the form of usernames and passwords and used them to extract data and to move further into the target networks.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-102",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "Human operators selected the targets for the campaign before any automated activity began. Approximately thirty organisations were targeted, including large technology companies, financial institutions, chemical manufacturers and government agencies.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-115",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "impact_observation",
    "content": "Of the approximately thirty organisations targeted, only a small number of intrusions succeeded.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-114",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "The model claimed to have obtained secret or restricted information which, on inspection, was already publicly available.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-113",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "The model hallucinated credentials, presenting account details as valid when they did not in fact work against the target systems.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-108",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "Extracted data was parsed and categorised according to its intelligence value rather than exfiltrated indiscriminately.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-111",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "Anthropic assesses that the model performed eighty to ninety per cent of the campaign work, with human intervention required at only four to six critical decision points per campaign.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-104",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "The operators additionally framed their requests by claiming to be employees of a legitimate cybersecurity firm conducting authorised defensive testing.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-116",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "Anthropic ran a ten-day investigation, banned the accounts involved, notified affected entities and coordinated with authorities, and expanded its detection classifiers.",
    "evidence_strength": "reported"
  },
  {
    "evidence_id": "E-103",
    "timestamp": "2025-09",
    "timestamp_precision": "month",
    "type": "investigation_finding",
    "content": "The operators bypassed the model's safety training by decomposing the overall attack into small individual tasks that appeared benign when presented in isolation.",
    "evidence_strength": "reported"
  }
]
""")

GOLD = json.loads(r"""
{
  "nodes": [
    {
      "id": "M01",
      "label": "Human operators select approximately thirty targets",
      "status": "confirmed",
      "evidence_ids": [
        "E-102"
      ]
    },
    {
      "id": "M02",
      "label": "Safety training bypassed by decomposing the attack into benign-looking tasks",
      "status": "confirmed",
      "evidence_ids": [
        "E-103"
      ]
    },
    {
      "id": "M03",
      "label": "Operators pose as employees of a legitimate security firm",
      "status": "confirmed",
      "evidence_ids": [
        "E-104"
      ]
    },
    {
      "id": "M04",
      "label": "Model performs reconnaissance of target infrastructure",
      "status": "confirmed",
      "evidence_ids": [
        "E-105",
        "E-112"
      ]
    },
    {
      "id": "M05",
      "label": "Model identifies vulnerabilities and writes exploit code",
      "status": "confirmed",
      "evidence_ids": [
        "E-106"
      ]
    },
    {
      "id": "M06",
      "label": "Model harvests credentials and uses them to move deeper",
      "status": "confirmed",
      "evidence_ids": [
        "E-107"
      ]
    },
    {
      "id": "M07",
      "label": "Exfiltrated data parsed and ranked by intelligence value",
      "status": "confirmed",
      "evidence_ids": [
        "E-108"
      ]
    },
    {
      "id": "M08",
      "label": "Backdoors created to maintain access",
      "status": "confirmed",
      "evidence_ids": [
        "E-109"
      ]
    },
    {
      "id": "M09",
      "label": "Model documents the campaign for continued operations",
      "status": "confirmed",
      "evidence_ids": [
        "E-110"
      ]
    },
    {
      "id": "M10",
      "label": "Model hallucinated credentials that did not work",
      "status": "failed",
      "evidence_ids": [
        "E-113"
      ]
    },
    {
      "id": "M11",
      "label": "Model claimed secret access to information that was public",
      "status": "failed",
      "evidence_ids": [
        "E-114"
      ]
    },
    {
      "id": "M12",
      "label": "Human intervention at four to six decision points per campaign",
      "status": "inferred",
      "evidence_ids": [
        "E-111"
      ]
    },
    {
      "id": "M13",
      "label": "Anthropic detects the activity and investigates for ten days",
      "status": "confirmed",
      "evidence_ids": [
        "E-101",
        "E-116"
      ]
    },
    {
      "id": "M14",
      "label": "Accounts banned and detection classifiers expanded",
      "status": "confirmed",
      "evidence_ids": [
        "E-116"
      ]
    },
    {
      "id": "M15",
      "label": "A small number of intrusions succeed",
      "status": "confirmed",
      "evidence_ids": [
        "E-115"
      ]
    },
    {
      "id": "M16",
      "label": "Identities of targeted and compromised organisations",
      "status": "unknown",
      "evidence_ids": [
        "E-117"
      ]
    },
    {
      "id": "M17",
      "label": "Independent corroboration of the state-sponsorship attribution",
      "status": "unknown",
      "evidence_ids": [
        "E-118"
      ]
    }
  ],
  "edges": [
    {
      "source": "M01",
      "target": "M02"
    },
    {
      "source": "M02",
      "target": "M04"
    },
    {
      "source": "M03",
      "target": "M04"
    },
    {
      "source": "M04",
      "target": "M05"
    },
    {
      "source": "M05",
      "target": "M06"
    },
    {
      "source": "M06",
      "target": "M07"
    },
    {
      "source": "M06",
      "target": "M08"
    },
    {
      "source": "M07",
      "target": "M09"
    },
    {
      "source": "M06",
      "target": "M10"
    },
    {
      "source": "M10",
      "target": "M12"
    },
    {
      "source": "M11",
      "target": "M12"
    },
    {
      "source": "M06",
      "target": "M15"
    },
    {
      "source": "M04",
      "target": "M13"
    },
    {
      "source": "M13",
      "target": "M14"
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
    name='Cyber Autopsy CASE-012: GTG-1002 with AI-agent framing',
    description='Reconstruct the GTG-1002 campaign using the same evidence as CASE-011, but with the operator described as AI-agent-led. Compare with CASE-011 to examine sensitivity to actor framing, not real attacker behavior.',
)
def case_012(llm) -> float:
    message = SYSTEM_PROMPT + "\n\n" + build_user_prompt()
    result = llm.prompt(message, schema=Reconstruction, seed=0, temperature=0)

    prediction = to_prediction(result)
    metrics = score_prediction(prediction, GOLD, VALID_EVIDENCE_IDS)

    print(json.dumps(metrics, indent=2))
    return metrics["egrs"] / 100.0


# %%
case_012.run(kbench.llm)
