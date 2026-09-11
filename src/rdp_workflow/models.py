"""Persisted domain models for the RDP Convergence Workflow."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WorkflowState(str, Enum):
    """The complete set of workflow lifecycle states."""

    INTAKE = "INTAKE"
    MODELING = "MODELING"
    CANONICALIZATION = "CANONICALIZATION"
    WAITING_HUMAN = "WAITING_HUMAN"
    BLOCKED = "BLOCKED"
    DONE = "DONE"


def _non_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("value must not be empty or whitespace")
    return value


class DecisionOption(BaseModel):
    """One proposed answer and its material consequence."""

    model_config = ConfigDict(extra="forbid")

    option_id: str
    text: str
    consequence: str

    _validate_text = field_validator("option_id", "text", "consequence")(_non_blank)


class OptionSelection(BaseModel):
    """A human selects one proposed option."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["option_selection"] = "option_selection"
    option_id: str

    _validate_option_id = field_validator("option_id")(_non_blank)


class OptionWithClarification(BaseModel):
    """A selected option plus separate, equally authoritative text."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["option_with_clarification"] = "option_with_clarification"
    option_id: str
    clarification: str

    _validate_text = field_validator("option_id", "clarification")(_non_blank)


class CustomAnswer(BaseModel):
    """An authoritative answer written by the human."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["custom"] = "custom"
    text: str

    _validate_text = field_validator("text")(_non_blank)


HumanAnswer = Annotated[
    OptionSelection | OptionWithClarification | CustomAnswer,
    Field(discriminator="kind"),
]


class Decision(BaseModel):
    """A material Human Decision packet or a safely deferred decision."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str
    classification: Literal["MATERIAL", "DEFERRED"]
    origin_state: WorkflowState | None = None
    question: str
    context: str | None = None
    options: tuple[DecisionOption, ...] = ()
    recommended_option_id: str | None = None
    recommendation_rationale: str | None = None
    status: Literal["PENDING", "RESOLVED", "SUPERSEDED"] | None = None
    answer: HumanAnswer | None = None
    supersedes_decision_id: str | None = None
    safe_to_defer_rationale: str | None = None
    downstream_constraints: tuple[str, ...] = ()

    _validate_required_ids = field_validator("decision_id", "question")(_non_blank)

    @field_validator(
        "context",
        "recommended_option_id",
        "recommendation_rationale",
        "supersedes_decision_id",
        "safe_to_defer_rationale",
    )
    @classmethod
    def _validate_optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _non_blank(value)

    @field_validator("downstream_constraints")
    @classmethod
    def _validate_constraints(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            _non_blank(value)
        return values

    @model_validator(mode="after")
    def _validate_conditional_shape(self) -> Self:
        if self.classification == "MATERIAL":
            if self.status is None:
                self.status = "PENDING"
            if self.status == "PENDING" and self.answer is not None:
                raise ValueError("a PENDING Decision cannot have a HumanAnswer")
            if self.status in {"RESOLVED", "SUPERSEDED"} and self.answer is None:
                raise ValueError(f"a {self.status} Decision requires a HumanAnswer")
            if self.origin_state not in {
                WorkflowState.INTAKE,
                WorkflowState.MODELING,
                WorkflowState.CANONICALIZATION,
            }:
                raise ValueError("a MATERIAL Decision requires an active origin state")
            if self.context is None:
                raise ValueError("a MATERIAL Decision requires context")
            if not 2 <= len(self.options) <= 4:
                raise ValueError("a MATERIAL Decision requires 2 to 4 options")
            option_ids = [option.option_id for option in self.options]
            if len(option_ids) != len(set(option_ids)):
                raise ValueError("Decision option IDs must be unique")
            if self.recommended_option_id not in option_ids:
                raise ValueError("recommended_option_id must identify a proposed option")
            if self.recommendation_rationale is None:
                raise ValueError("a MATERIAL Decision requires a recommendation rationale")
            if self.safe_to_defer_rationale is not None or self.downstream_constraints:
                raise ValueError("a MATERIAL Decision cannot contain deferral fields")
        else:
            if self.status is not None:
                raise ValueError("a DEFERRED Decision cannot have a MATERIAL lifecycle status")
            if self.origin_state is not None:
                raise ValueError("a DEFERRED Decision cannot have an origin state")
            if self.options or self.recommended_option_id or self.recommendation_rationale:
                raise ValueError("a DEFERRED Decision cannot contain recommendation fields")
            if self.answer is not None:
                raise ValueError("a DEFERRED Decision cannot contain a HumanAnswer")
            if self.supersedes_decision_id is not None:
                raise ValueError("a DEFERRED Decision cannot supersede a Decision")
            if self.safe_to_defer_rationale is None:
                raise ValueError("a DEFERRED Decision requires a safe-to-defer rationale")
            if not self.downstream_constraints:
                raise ValueError("a DEFERRED Decision requires downstream constraints")
        return self


class ProductContext(BaseModel):
    """Shallow product context within a ModelingResult."""

    model_config = ConfigDict(extra="forbid")

    problem: str
    target_users: tuple[str, ...]
    intended_outcome: str
    goals: tuple[str, ...] = ()
    non_goals: tuple[str, ...] = ()


class DomainView(BaseModel):
    """Shallow domain values within a ModelingResult."""

    model_config = ConfigDict(extra="forbid")

    concepts: tuple[str, ...] = ()
    relationships: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    terminology: tuple[str, ...] = ()


class CapabilityValue(BaseModel):
    """One shallow capability value within a ModelingResult."""

    model_config = ConfigDict(extra="forbid")

    name: str
    purpose: str
    release_status: Literal["IN", "PARTIAL", "OUT", "FUTURE"]
    actors: tuple[str, ...] = ()
    required_behavior: tuple[str, ...] = ()
    business_rules: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    failure_conditions: tuple[str, ...] = ()


class ArchitectureView(BaseModel):
    """Shallow architecture values within a ModelingResult."""

    model_config = ConfigDict(extra="forbid")

    responsibility_areas: tuple[str, ...] = ()
    system_boundaries: tuple[str, ...] = ()
    ownership: tuple[str, ...] = ()
    interactions: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    cross_cutting_requirements: tuple[str, ...] = ()


class ModelingResult(BaseModel):
    """Current shallow derived model set; never lifecycle state."""

    model_config = ConfigDict(extra="forbid")

    product_context: ProductContext
    domain: DomainView
    capabilities: tuple[CapabilityValue, ...] = ()
    architecture: ArchitectureView
    deferred_decisions: tuple[Decision, ...] = ()

    @model_validator(mode="after")
    def _validate_deferred_decisions(self) -> Self:
        if any(
            decision.classification != "DEFERRED"
            for decision in self.deferred_decisions
        ):
            raise ValueError(
                "ModelingResult deferred_decisions may contain only DEFERRED Decisions"
            )
        decision_ids = [
            decision.decision_id for decision in self.deferred_decisions
        ]
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("deferred Decision IDs must be unique within a model set")
        return self


class ConvergenceResult(BaseModel):
    """Current convergence review output; not a transition by itself."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["PASS", "FAIL"]
    findings: tuple[str, ...] = ()
    remediation: Literal["HUMAN_DECISION", "REMODEL"] | None = None
    decision: Decision | None = None

    @field_validator("findings")
    @classmethod
    def _validate_findings(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            _non_blank(value)
        return values

    @model_validator(mode="after")
    def _validate_result(self) -> Self:
        if self.status == "PASS":
            if self.remediation is not None:
                raise ValueError("a PASS ConvergenceResult cannot require remediation")
            if self.decision is not None:
                raise ValueError("a PASS ConvergenceResult cannot contain a Decision")
        elif not self.findings:
            raise ValueError("a FAIL ConvergenceResult requires findings")
        elif self.remediation == "REMODEL":
            if self.decision is not None:
                raise ValueError(
                    "a REMODEL ConvergenceResult cannot contain a Decision"
                )
        elif self.remediation == "HUMAN_DECISION":
            decision = self.decision
            if (
                decision is None
                or decision.classification != "MATERIAL"
                or decision.status != "PENDING"
                or decision.origin_state is not WorkflowState.MODELING
            ):
                raise ValueError(
                    "HUMAN_DECISION requires exactly one pending "
                    "MODELING-origin MATERIAL Decision"
                )
        else:
            raise ValueError("a FAIL ConvergenceResult requires remediation")
        return self


class _CanonicalSection(BaseModel):
    """Common explicit content carried by every Canonical section."""

    model_config = ConfigDict(extra="forbid")

    summary: str

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_section_text(cls, value: object) -> object:
        """Keep persisted Slice 1 values readable as one typed representation."""

        if isinstance(value, str):
            return {"summary": value}
        return value


class CanonicalProductDefinition(_CanonicalSection):
    """Product intent and its explicitly identified goals and non-goals."""

    problem: str = ""
    target_actor_ids: tuple[str, ...] = ()
    intended_outcome: str = ""
    goals: tuple[str, ...] = ()
    non_goals: tuple[str, ...] = ()


class CanonicalScopeEntry(BaseModel):
    """The target-release classification for one material capability."""

    model_config = ConfigDict(extra="forbid")

    capability_id: str
    status: Literal["IN", "PARTIAL", "OUT", "FUTURE"]
    included: tuple[str, ...] = ()
    excluded: tuple[str, ...] = ()


class CanonicalScope(_CanonicalSection):
    """Target release and the explicit scope of every material capability."""

    target_release: str = ""
    capabilities: tuple[CanonicalScopeEntry, ...] = ()


class CanonicalActor(BaseModel):
    """One human, system, or external actor referenced by the document."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str
    name: str
    kind: Literal["HUMAN", "SYSTEM", "EXTERNAL"]
    purpose: str
    may_do: tuple[str, ...] = ()
    must_do: tuple[str, ...] = ()
    must_not_do: tuple[str, ...] = ()
    permission_boundaries: tuple[str, ...] = ()


class CanonicalActorsAndRoles(_CanonicalSection):
    """All material actors and their role or permission semantics."""

    actors: tuple[CanonicalActor, ...] = ()


class CanonicalDomainModel(_CanonicalSection):
    """Shared business meaning without implementation structure."""

    concepts: tuple[str, ...] = ()
    relationships: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    terminology: tuple[str, ...] = ()


class CanonicalCapability(BaseModel):
    """One material user or business capability."""

    model_config = ConfigDict(extra="forbid")

    capability_id: str
    name: str
    purpose: str
    actor_ids: tuple[str, ...] = ()
    required_behavior: tuple[str, ...] = ()
    business_rules: tuple[str, ...] = ()
    dependency_capability_ids: tuple[str, ...] = ()
    failure_conditions: tuple[str, ...] = ()


class CanonicalFunctionalCapabilities(_CanonicalSection):
    """Material capabilities whose release status is defined by CanonicalScope."""

    capabilities: tuple[CanonicalCapability, ...] = ()


class CanonicalSystemBoundaries(_CanonicalSection):
    """Inside/outside responsibilities, dependencies, and ownership."""

    inside_system: tuple[str, ...] = ()
    outside_system: tuple[str, ...] = ()
    external_dependencies: tuple[str, ...] = ()
    data_ownership: tuple[str, ...] = ()
    decision_ownership: tuple[str, ...] = ()
    responsibility_ownership: tuple[str, ...] = ()
    systems_of_record: tuple[str, ...] = ()


class CanonicalArchitecture(_CanonicalSection):
    """Only high-level architectural constraints downstream must preserve."""

    responsibility_areas: tuple[str, ...] = ()
    non_responsibilities: tuple[str, ...] = ()
    interactions: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    dependency_directions: tuple[str, ...] = ()


class CanonicalCrossCuttingRequirements(_CanonicalSection):
    """Material cross-capability and non-functional requirements."""

    requirements: tuple[str, ...] = ()


class CanonicalResponsibilityBoundary(BaseModel):
    """A boundary downstream Feature decomposition must preserve."""

    model_config = ConfigDict(extra="forbid")

    boundary_id: str
    name: str
    owns: tuple[str, ...]
    does_not_own: tuple[str, ...] = ()
    may_depend_on_boundary_ids: tuple[str, ...] = ()
    must_not_depend_on_boundary_ids: tuple[str, ...] = ()
    supported_capability_ids: tuple[str, ...] = ()


class CanonicalResponsibilityBoundaries(_CanonicalSection):
    """Normative responsibility boundaries for downstream decomposition."""

    boundaries: tuple[CanonicalResponsibilityBoundary, ...] = ()


class CanonicalDeferredDecision(BaseModel):
    """One undecided matter proven safe for downstream resolution."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str
    question: str
    reason_safe_to_defer: str
    downstream_constraints: tuple[str, ...]


class CanonicalDeferredDecisions(_CanonicalSection):
    """Safe deferrals and the upstream constraints that must remain fixed."""

    decisions: tuple[CanonicalDeferredDecision, ...] = ()
    fixed_upstream_constraints: tuple[str, ...] = ()


class CanonicalRDP(BaseModel):
    """The ten required sections of a Canonical RDP candidate."""

    model_config = ConfigDict(extra="forbid")

    product_definition: CanonicalProductDefinition
    scope_and_release_boundary: CanonicalScope
    actors_and_roles: CanonicalActorsAndRoles
    domain_model: CanonicalDomainModel
    functional_capabilities: CanonicalFunctionalCapabilities
    system_boundaries_and_ownership: CanonicalSystemBoundaries
    high_level_architecture: CanonicalArchitecture
    cross_cutting_and_non_functional_requirements: CanonicalCrossCuttingRequirements
    required_responsibility_boundaries: CanonicalResponsibilityBoundaries
    deferred_decisions_and_handoff_constraints: CanonicalDeferredDecisions


class AuditResult(BaseModel):
    """Current independent Canonical Audit output."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["PASS", "FAIL"]
    findings: tuple[str, ...] = ()
    remediation: Literal["HUMAN_DECISION", "REMODEL", "EDITORIAL"] | None = None
    decision: Decision | None = None

    @field_validator("findings")
    @classmethod
    def _validate_findings(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            _non_blank(value)
        return values

    @model_validator(mode="after")
    def _validate_result(self) -> Self:
        if self.status == "PASS":
            if self.remediation is not None:
                raise ValueError("a PASS AuditResult cannot require remediation")
            if self.decision is not None:
                raise ValueError("a PASS AuditResult cannot contain a Decision")
        elif not self.findings:
            raise ValueError("a FAIL AuditResult requires findings")
        elif self.remediation in {"EDITORIAL", "REMODEL"}:
            if self.decision is not None:
                raise ValueError(
                    f"a {self.remediation} AuditResult cannot contain a Decision"
                )
        elif self.remediation == "HUMAN_DECISION":
            decision = self.decision
            if (
                decision is None
                or decision.classification != "MATERIAL"
                or decision.status != "PENDING"
                or decision.origin_state is not WorkflowState.CANONICALIZATION
            ):
                raise ValueError(
                    "HUMAN_DECISION requires exactly one pending "
                    "CANONICALIZATION-origin MATERIAL Decision"
                )
        else:
            raise ValueError("a FAIL AuditResult requires remediation")
        return self


class WorkflowRun(BaseModel):
    """The persisted aggregate and sole holder of lifecycle state."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    run_id: str
    state: WorkflowState = WorkflowState.INTAKE
    pending_decision_origin: WorkflowState | None = None
    decisions: tuple[Decision, ...] = ()
    modeling_result: ModelingResult | None = None
    convergence_result: ConvergenceResult | None = None
    canonical_candidate: CanonicalRDP | None = None
    audit_result: AuditResult | None = None
    diagnostics: tuple[str, ...] = ()

    _validate_run_id = field_validator("run_id")(_non_blank)

    @field_validator("pending_decision_origin")
    @classmethod
    def _validate_pending_origin(
        cls, value: WorkflowState | None
    ) -> WorkflowState | None:
        if value is not None and value not in {
            WorkflowState.INTAKE,
            WorkflowState.MODELING,
            WorkflowState.CANONICALIZATION,
        }:
            raise ValueError("pending Decision origin must be an active decision-making state")
        return value

    @model_validator(mode="after")
    def _validate_single_pending_material_decision(self) -> Self:
        pending_count = sum(
            decision.classification == "MATERIAL" and decision.status == "PENDING"
            for decision in self.decisions
        )
        if pending_count > 1:
            raise ValueError("a WorkflowRun can have at most one pending MATERIAL Decision")
        return self
