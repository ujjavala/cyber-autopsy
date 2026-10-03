"""Controlled perturbation experiments (counterfactual variants).

All perturbed content comes from authored PerturbationSpec records in
data/perturbations.jsonl and is marked synthetic=True. Synthetic content is
never written back into the real evidence files.

Variants:
  A_full          unmodified packet
  B_removed       one critical evidence item removed
  C_flipped       one fact changed (authored replacement text)
  D_false         plausible-but-false event injected (authored)
  E_irrelevant    true-but-irrelevant item injected (authored)
  F_contradictory authored contradictory report injected
"""

from __future__ import annotations

from copy import deepcopy

from .dataset import EvidencePacket
from .schemas import Evidence, EvidenceStrength, PerturbationSpec, PerturbationVariant


def apply_perturbation(
    packet: EvidencePacket, spec: PerturbationSpec
) -> EvidencePacket:
    out = EvidencePacket(
        case_id=f"{packet.case_id}:{spec.variant.value}",
        incident_id=packet.incident_id,
        context=packet.context,
        evidence=[deepcopy(e) for e in packet.evidence],
        framing_preamble=packet.framing_preamble,
    )

    if spec.variant == PerturbationVariant.full:
        return out

    if spec.variant == PerturbationVariant.removed:
        remove = set(spec.remove_evidence_ids)
        if not remove:
            raise ValueError(f"{spec.perturbation_id}: B_removed needs evidence ids")
        out.evidence = [e for e in out.evidence if e.evidence_id not in remove]
        return out

    if spec.variant == PerturbationVariant.flipped:
        if not spec.flip_evidence_id or not spec.flip_replacement_content:
            raise ValueError(
                f"{spec.perturbation_id}: C_flipped needs flip_evidence_id "
                "and flip_replacement_content"
            )
        flipped = False
        for ev in out.evidence:
            if ev.evidence_id == spec.flip_evidence_id:
                ev.content = spec.flip_replacement_content
                ev.synthetic = True
                flipped = True
        if not flipped:
            raise ValueError(
                f"{spec.perturbation_id}: evidence {spec.flip_evidence_id} "
                "not present in packet"
            )
        return out

    if spec.variant in (
        PerturbationVariant.false_evidence,
        PerturbationVariant.irrelevant,
        PerturbationVariant.contradictory,
    ):
        if not spec.inject_content:
            raise ValueError(f"{spec.perturbation_id}: inject_content required")
        injected = Evidence(
            evidence_id=f"E-SYN-{spec.perturbation_id}",
            incident_id=packet.incident_id,
            type=spec.inject_type,
            content=spec.inject_content,
            source_ids=[],
            evidence_strength=EvidenceStrength.reported,
            synthetic=True,
        )
        # Deterministic insertion position: middle of the packet.
        out.evidence.insert(len(out.evidence) // 2, injected)
        return out

    raise ValueError(f"unsupported variant {spec.variant}")
