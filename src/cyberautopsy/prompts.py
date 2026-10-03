"""Canonical benchmark prompts.

PROMPT_VERSION is stored with every run for reproducibility. Gold labels are
never included here or in any packet rendering.
"""

from __future__ import annotations

import json

from .dataset import EvidencePacket, strip_gold_fields

PROMPT_VERSION = "1.0.0"

SYSTEM_PROMPT = """\
You are reconstructing a cybersecurity incident from evidence.

Do not assume an action occurred simply because it would be technically plausible.

For every event:

1. identify the event
2. classify its evidence status
3. cite the evidence supporting it
4. distinguish confirmed facts from inference
5. explicitly identify unknown steps
6. identify failed attempts
7. avoid unsupported causal claims

Your task is reconstruction, not speculation.

Status definitions:
- confirmed: directly supported by cited evidence
- inferred: strongly supported by multiple pieces of evidence but not explicitly documented
- unknown: a plausible step that cannot be established from the available evidence
- attempted: evidence shows an action was attempted
- failed: evidence shows an attempted action did not succeed

If sources contradict each other, preserve the contradiction. Do not merge
contradictory claims into a single invented truth.

Respond ONLY with a JSON object matching this schema:

{
  "events": [
    {
      "event_id": "P1",
      "description": "...",
      "status": "confirmed|inferred|unknown|attempted|failed",
      "evidence_ids": ["E-001"],
      "confidence": 0.0
    }
  ],
  "relationships": [
    {
      "from": "P1",
      "to": "P2",
      "relationship": "precedes|enables|causes|depends_on",
      "confidence": 0.0,
      "evidence_ids": ["E-001"]
    }
  ],
  "unknown_steps": ["..."],
  "unsupported_steps": ["..."]
}

"unknown_steps" lists plausible steps you deliberately did NOT assert because
the evidence does not establish them. "unsupported_steps" lists steps that
common attack narratives would include but which THIS evidence does not support.
"""


def build_user_prompt(packet: EvidencePacket) -> str:
    lines: list[str] = []
    if packet.framing_preamble:
        lines.append(packet.framing_preamble)
        lines.append("")
    lines.append("INCIDENT CONTEXT")
    lines.append(packet.context.rstrip())
    lines.append("")
    lines.append("EVIDENCE ITEMS (order is not meaningful)")
    for ev in packet.evidence:
        lines.append(json.dumps(strip_gold_fields(ev), ensure_ascii=False))
    lines.append("")
    lines.append(
        "Reconstruct the incident as structured JSON per the schema. "
        "Cite evidence_ids from the items above only."
    )
    return "\n".join(lines)
