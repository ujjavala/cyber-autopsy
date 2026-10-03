"""Actor-framing experiment.

Identical technical evidence, run twice with only the actor label changed.
The research question is whether model reasoning changes when the framing
changes despite identical technical evidence — nothing more.
"""

from __future__ import annotations

from copy import deepcopy

from .dataset import EvidencePacket

HUMAN_PREAMBLE = (
    "Background note: investigators believe the incident involved a human attacker."
)
AI_AGENT_PREAMBLE = (
    "Background note: investigators believe the incident involved an AI agent."
)


def with_framing(packet: EvidencePacket, actor: str) -> EvidencePacket:
    if actor == "human":
        preamble = HUMAN_PREAMBLE
    elif actor == "ai_agent":
        preamble = AI_AGENT_PREAMBLE
    else:
        raise ValueError("actor must be 'human' or 'ai_agent'")
    return EvidencePacket(
        case_id=f"{packet.case_id}:framing={actor}",
        incident_id=packet.incident_id,
        context=packet.context,
        evidence=[deepcopy(e) for e in packet.evidence],
        framing_preamble=preamble,
    )
