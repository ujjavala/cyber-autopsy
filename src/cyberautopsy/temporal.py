"""Temporal-leakage protection and time-sliced benchmark modes.

Evidence is only "publicly knowable" from the earliest publication date of
its sources. Modes:

  full retrospective   all public evidence (default)
  at-the-time          only evidence whose earliest source publication date
                       is <= the cutoff
  progressive          evidence revealed chronologically by publication date
"""

from __future__ import annotations

from copy import deepcopy
from typing import Iterator

from .dataset import Dataset, EvidencePacket


def filter_at_time(
    ds: Dataset, packet: EvidencePacket, cutoff: str
) -> EvidencePacket:
    """Keep only evidence publicly available on or before `cutoff` (ISO date)."""
    kept = []
    for ev in packet.evidence:
        pub = ds.publication_date_for_evidence(ev)
        if pub is not None and pub <= cutoff:
            kept.append(deepcopy(ev))
    return EvidencePacket(
        case_id=f"{packet.case_id}:cutoff={cutoff}",
        incident_id=packet.incident_id,
        context=packet.context,
        evidence=kept,
        framing_preamble=packet.framing_preamble,
    )


def progressive_disclosure(
    ds: Dataset, packet: EvidencePacket
) -> Iterator[EvidencePacket]:
    """Yield packets with evidence revealed in publication-date order.

    Each step adds every item published on the next distinct date.
    """
    dated = []
    for ev in packet.evidence:
        pub = ds.publication_date_for_evidence(ev)
        if pub is not None:
            dated.append((pub, ev))
    dated.sort(key=lambda t: (t[0], t[1].evidence_id))
    distinct_dates = sorted({d for d, _ in dated})
    for i, date in enumerate(distinct_dates, 1):
        revealed = [deepcopy(ev) for d, ev in dated if d <= date]
        yield EvidencePacket(
            case_id=f"{packet.case_id}:step{i}",
            incident_id=packet.incident_id,
            context=packet.context,
            evidence=revealed,
            framing_preamble=packet.framing_preamble,
        )
