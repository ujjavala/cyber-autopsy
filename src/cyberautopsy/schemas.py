"""Pydantic schemas for all Cyber Autopsy dataset and benchmark objects.

These schemas are the single source of truth for:
  data/sources.jsonl        -> Source
  data/incidents.jsonl      -> Incident
  data/evidence.jsonl       -> Evidence
  data/attack_graphs.jsonl  -> AttackGraph
  data/benchmark_cases.jsonl-> BenchmarkCase
  data/perturbations.jsonl  -> PerturbationSpec
  model output              -> ModelPrediction
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SourceType(str, Enum):
    government = "government"
    security_vendor = "security_vendor"
    news = "news"
    incident_report = "incident_report"
    research = "research"
    other = "other"


class ReliabilityTier(str, Enum):
    primary = "primary"
    secondary = "secondary"
    tertiary = "tertiary"
    experimental = "experimental"  # controlled experiment / red-team study
    synthetic = "synthetic"  # benchmark-generated (perturbations only)


class AccessStatus(str, Enum):
    open = "open"
    paywalled = "paywalled"
    registration_required = "registration_required"
    removed = "removed"
    archived_only = "archived_only"


class ClaimStatus(str, Enum):
    """How strongly the content of an evidence item is established."""

    observed = "observed"  # directly observed in logs/telemetry
    experimentally_observed = "experimentally_observed"  # controlled experiment
    explicitly_reported = "explicitly_reported"  # stated by investigators
    source_claim = "source_claim"  # claimed by a party, not independently verified
    inferred = "inferred"
    ambiguous = "ambiguous"
    unknown = "unknown"


class ActorType(str, Enum):
    human = "human"
    group = "group"
    criminal = "criminal"
    state = "state"
    bot = "bot"
    ai_assisted = "ai_assisted"
    ai_agent = "ai_agent"
    unknown = "unknown"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EvidenceType(str, Enum):
    timeline_event = "timeline_event"
    system_observation = "system_observation"
    network_observation = "network_observation"
    authentication_event = "authentication_event"
    access_event = "access_event"
    statement = "statement"
    investigation_finding = "investigation_finding"
    technical_analysis = "technical_analysis"
    impact_observation = "impact_observation"
    negative_evidence = "negative_evidence"
    contradictory_evidence = "contradictory_evidence"


class EvidenceStrength(str, Enum):
    confirmed = "confirmed"
    reported = "reported"
    disputed = "disputed"


class TimestampPrecision(str, Enum):
    exact = "exact"
    minute = "minute"
    hour = "hour"
    day = "day"
    month = "month"
    year = "year"
    unknown = "unknown"


class NodeStatus(str, Enum):
    """Evidence status of a gold graph node.

    confirmed    directly supported by evidence
    inferred     strongly supported by multiple pieces of evidence but not
                 explicitly documented
    unknown      a plausible step that cannot be established from evidence
    attempted    evidence shows an action was attempted
    failed       evidence shows an attempted action failed
    contradicted evidence explicitly conflicts with the proposed event
    """

    confirmed = "confirmed"
    inferred = "inferred"
    unknown = "unknown"
    attempted = "attempted"
    failed = "failed"
    contradicted = "contradicted"


class EdgeRelation(str, Enum):
    precedes = "precedes"
    enables = "enables"
    causes = "causes"
    depends_on = "depends_on"


class ReviewStatus(str, Enum):
    draft = "draft"
    reviewed = "reviewed"
    validated = "validated"
    published = "published"


class BenchmarkMode(str, Enum):
    full = "full"
    temporal = "temporal"
    progressive = "progressive"
    counterfactual = "counterfactual"
    framing = "framing"


class PerturbationVariant(str, Enum):
    full = "A_full"
    removed = "B_removed"
    flipped = "C_flipped"
    false_evidence = "D_false"
    irrelevant = "E_irrelevant"
    contradictory = "F_contradictory"


# ---------------------------------------------------------------------------
# Behavioural layer enumerations (actors, intents, actions, controls)
# ---------------------------------------------------------------------------


class ActorKind(str, Enum):
    """Top-level actor classification for behavioural analysis."""

    human = "human"
    ai_agent = "ai_agent"
    hybrid = "hybrid"  # human-directed AI / AI-assisted human
    unknown = "unknown"


class HumanActorCategory(str, Enum):
    red_team = "red_team"
    penetration_tester = "penetration_tester"
    security_researcher = "security_researcher"
    threat_actor = "threat_actor"
    insider = "insider"
    administrator = "administrator"
    unknown = "unknown"


class AutonomyLevel(str, Enum):
    """Degree of autonomy for AI/hybrid actors, only where documented."""

    fully_autonomous = "fully_autonomous"
    human_in_the_loop = "human_in_the_loop"
    human_directed = "human_directed"  # AI used as a tool per-step
    unknown = "unknown"


class IntentCategory(str, Enum):
    reconnaissance = "reconnaissance"
    initial_access = "initial_access"
    credential_access = "credential_access"
    privilege_escalation = "privilege_escalation"
    lateral_movement = "lateral_movement"
    persistence = "persistence"
    data_access = "data_access"
    collection = "collection"
    exfiltration = "exfiltration"
    disruption = "disruption"
    fraud = "fraud"
    manipulation = "manipulation"
    defense_evasion = "defense_evasion"
    other = "other"
    unknown = "unknown"


class IntentStatus(str, Enum):
    """How the intent is established. Inferred motivation is never fact."""

    observed = "observed"
    stated = "stated"
    inferred = "inferred"
    possible = "possible"
    unknown = "unknown"


class ActionResult(str, Enum):
    successful = "successful"
    failed = "failed"
    blocked = "blocked"
    partially_successful = "partially_successful"
    abandoned = "abandoned"
    unknown = "unknown"


class FailureMode(str, Enum):
    """Why an action failed or was blocked (only where evidence supports it)."""

    guardrail_refusal = "guardrail_refusal"
    tool_denial = "tool_denial"
    permission_denied = "permission_denied"
    authentication_failure = "authentication_failure"
    environment_constraint = "environment_constraint"
    incorrect_assumption = "incorrect_assumption"
    hallucinated_capability = "hallucinated_capability"
    hallucinated_state = "hallucinated_state"
    wrong_target = "wrong_target"
    wrong_attack_path = "wrong_attack_path"
    poor_reasoning = "poor_reasoning"
    insufficient_information = "insufficient_information"
    failure_to_adapt = "failure_to_adapt"
    premature_termination = "premature_termination"
    excessive_persistence = "excessive_persistence"
    human_intervention = "human_intervention"
    monitoring_detection = "monitoring_detection"
    unknown = "unknown"


class FailureClass(str, Enum):
    capability = "capability"
    reasoning = "reasoning"
    tool = "tool"
    environmental = "environmental"
    control_intervention = "control_intervention"
    behavioural = "behavioural"
    unknown = "unknown"


class AdaptationResponse(str, Enum):
    """What the actor did after a failed/blocked action."""

    stopped = "stopped"
    retried = "retried"
    changed_parameters = "changed_parameters"
    changed_tools = "changed_tools"
    changed_target = "changed_target"
    changed_attack_path = "changed_attack_path"
    asked_human_assistance = "asked_human_assistance"
    circumvented_control = "circumvented_control"
    continued_despite_contradiction = "continued_despite_contradiction"
    unknown = "unknown"


class ControlType(str, Enum):
    model_refusal = "model_refusal"
    policy_filter = "policy_filter"
    prompt_guardrail = "prompt_guardrail"
    tool_permission = "tool_permission"
    sandbox = "sandbox"
    network_restriction = "network_restriction"
    authentication = "authentication"
    authorization = "authorization"
    human_approval = "human_approval"
    rate_limit = "rate_limit"
    monitoring = "monitoring"
    detection = "detection"
    alerting = "alerting"
    environment_restriction = "environment_restriction"
    unknown = "unknown"


class ControlOutcome(str, Enum):
    not_encountered = "not_encountered"
    detected = "detected"
    blocked = "blocked"
    altered_behaviour = "altered_behaviour"
    human_intervened = "human_intervened"
    control_failed = "control_failed"
    unknown = "unknown"


class InterventionType(str, Enum):
    """Documented human intervention in AI-agent activity."""

    approval_required = "approval_required"
    denied_action = "denied_action"
    modified_task = "modified_task"
    stopped_agent = "stopped_agent"
    supplied_information = "supplied_information"
    corrected_model = "corrected_model"
    took_over = "took_over"
    unknown = "unknown"


class ComparabilityClass(str, Enum):
    """How a case may be used in AI-vs-human behavioural comparison."""

    direct_comparison = "direct_comparison"  # same task, same environment
    matched_comparison = "matched_comparison"  # similar task/context
    contextual_only = "contextual_only"  # descriptive only, not comparable


# ---------------------------------------------------------------------------
# Dataset objects
# ---------------------------------------------------------------------------


class Source(BaseModel):
    source_id: str
    title: str
    publisher: str
    url: str
    published_at: str  # ISO date of publication (temporal-leakage anchor)
    accessed_at: str
    source_type: SourceType
    reliability_tier: ReliabilityTier
    incident_ids: list[str] = Field(default_factory=list)
    notes: str = ""
    # Collection provenance (internet collection pipeline)
    content_hash: Optional[str] = None  # sha256 of retrieved raw content
    retrieved_at: Optional[str] = None  # ISO timestamp of retrieval
    access_status: AccessStatus = AccessStatus.open
    archive_url: Optional[str] = None  # e.g. Wayback Machine snapshot
    license_notes: str = ""
    cluster_id: Optional[str] = None  # dedupe cluster for repeated reporting

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("source url must be an http(s) URL")
        return v


class ReviewMeta(BaseModel):
    review_status: ReviewStatus = ReviewStatus.draft
    reviewer_count: int = 0
    last_reviewed: Optional[str] = None
    review_notes: str = ""


class Incident(BaseModel):
    incident_id: str
    title: str
    organization: str
    country: str
    sector: str
    incident_date: str
    discovery_date: Optional[str] = None
    public_disclosure_date: Optional[str] = None
    actor: str = "unknown"
    actor_type: ActorType = ActorType.unknown
    attack_type: str
    impact: str
    summary: str
    source_ids: list[str]
    confidence: Confidence
    review: ReviewMeta = Field(default_factory=ReviewMeta)


class Evidence(BaseModel):
    evidence_id: str
    incident_id: str
    timestamp: Optional[str] = None  # event time (when the thing happened)
    timestamp_precision: TimestampPrecision = TimestampPrecision.unknown
    type: EvidenceType
    content: str
    source_ids: list[str]
    evidence_strength: EvidenceStrength = EvidenceStrength.confirmed
    entities: list[str] = Field(default_factory=list)
    supports_nodes: list[str] = Field(default_factory=list)
    supports_edges: list[str] = Field(default_factory=list)
    contradicts: list[str] = Field(default_factory=list)
    redacted: bool = False
    synthetic: bool = False  # True ONLY for controlled perturbation items
    claim_status: ClaimStatus = ClaimStatus.unknown


# ---------------------------------------------------------------------------
# Behavioural layer objects (actors, intents, actions, controls)
#
# The schema follows the evidence: every field defaults to "unknown" and is
# only populated where documentation supports it. Never guess.
# ---------------------------------------------------------------------------


class Actor(BaseModel):
    actor_id: str
    incident_id: str
    actor_kind: ActorKind = ActorKind.unknown
    human_category: HumanActorCategory = HumanActorCategory.unknown
    description: str = ""
    source_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.low
    # AI metadata — populated ONLY where documented, never guessed
    model: Optional[str] = None
    agent_framework: Optional[str] = None
    tool_access: list[str] = Field(default_factory=list)
    autonomy_level: AutonomyLevel = AutonomyLevel.unknown
    human_involvement: str = "unknown"
    system_constraints: str = "unknown"


class Intent(BaseModel):
    intent_id: str
    incident_id: str
    actor_id: Optional[str] = None
    description: str
    category: IntentCategory = IntentCategory.unknown
    status: IntentStatus = IntentStatus.unknown
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.low


class FailureRecord(BaseModel):
    """Failure detail attached to a failed/blocked action."""

    failure_mode: FailureMode = FailureMode.unknown
    failure_class: FailureClass = FailureClass.unknown
    adaptation: AdaptationResponse = AdaptationResponse.unknown
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str = ""


class Action(BaseModel):
    action_id: str
    incident_id: str
    actor_id: Optional[str] = None
    intent_id: Optional[str] = None
    timestamp: Optional[str] = None
    timestamp_precision: TimestampPrecision = TimestampPrecision.unknown
    description: str
    target: str = ""
    result: ActionResult = ActionResult.unknown
    failure: Optional[FailureRecord] = None
    evidence_ids: list[str] = Field(default_factory=list)
    preceding_action_ids: list[str] = Field(default_factory=list)
    following_action_ids: list[str] = Field(default_factory=list)


class Control(BaseModel):
    control_id: str
    incident_id: str
    control_type: ControlType = ControlType.unknown
    description: str = ""
    trigger: str = ""  # what activated the control
    action_id: Optional[str] = None  # the action it acted upon
    outcome: ControlOutcome = ControlOutcome.unknown
    evidence_ids: list[str] = Field(default_factory=list)


class Intervention(BaseModel):
    """Documented human intervention in AI-agent activity."""

    intervention_id: str
    incident_id: str
    intervention_type: InterventionType = InterventionType.unknown
    description: str = ""
    action_id: Optional[str] = None
    evidence_ids: list[str] = Field(default_factory=list)


class MitreMapping(BaseModel):
    mitre_tactic: str
    mitre_technique: str
    mitre_confidence: Confidence = Confidence.medium


class GraphNode(BaseModel):
    id: str
    label: str
    status: NodeStatus
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str = ""
    mitre: Optional[MitreMapping] = None


class GraphEdge(BaseModel):
    id: Optional[str] = None
    source: str
    target: str
    relation: EdgeRelation
    evidence_ids: list[str] = Field(default_factory=list)


class AttackGraph(BaseModel):
    incident_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    review: ReviewMeta = Field(default_factory=ReviewMeta)


class BenchmarkCase(BaseModel):
    case_id: str
    incident_id: str
    mode: BenchmarkMode = BenchmarkMode.full
    variant: PerturbationVariant = PerturbationVariant.full
    evidence_ids: list[str] = Field(default_factory=list)  # empty = all
    temporal_cutoff: Optional[str] = None  # ISO date, temporal mode only
    framing_actor: Optional[str] = None  # "human" | "ai_agent", framing mode
    # Behavioural comparability (explicit, with recorded reason)
    comparability: ComparabilityClass = ComparabilityClass.contextual_only
    comparability_reason: str = ""
    # Temporal-leakage bookkeeping
    knowledge_cutoff: Optional[str] = None  # ISO date models must not exceed
    source_publication_dates: list[str] = Field(default_factory=list)
    notes: str = ""


class PerturbationSpec(BaseModel):
    """Authored, clearly-labelled spec for a controlled perturbation.

    Synthetic content is ONLY permitted here and is never presented as a
    real evidence item in the published dataset.
    """

    perturbation_id: str
    incident_id: str
    variant: PerturbationVariant
    remove_evidence_ids: list[str] = Field(default_factory=list)
    flip_evidence_id: Optional[str] = None
    flip_replacement_content: Optional[str] = None
    inject_content: Optional[str] = None
    inject_type: EvidenceType = EvidenceType.timeline_event
    expected_effect: str = ""  # what a well-calibrated model should do


# ---------------------------------------------------------------------------
# Model output schema (what the model must produce)
# ---------------------------------------------------------------------------


class PredictedStatus(str, Enum):
    confirmed = "confirmed"
    inferred = "inferred"
    unknown = "unknown"
    attempted = "attempted"
    failed = "failed"


class PredictedEvent(BaseModel):
    event_id: str
    description: str
    status: PredictedStatus
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class PredictedRelationship(BaseModel):
    from_: str = Field(alias="from")
    to: str
    relationship: EdgeRelation
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    evidence_ids: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ModelPrediction(BaseModel):
    events: list[PredictedEvent] = Field(default_factory=list)
    relationships: list[PredictedRelationship] = Field(default_factory=list)
    unknown_steps: list[str] = Field(default_factory=list)
    unsupported_steps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Run metadata (reproducibility)
# ---------------------------------------------------------------------------


class RunMetadata(BaseModel):
    run_id: str
    model: str
    model_version: str = "unspecified"
    timestamp: str
    dataset_version: str
    prompt_version: str
    temperature: float = 0.0
    seed: int = 42
    benchmark_mode: BenchmarkMode = BenchmarkMode.full
