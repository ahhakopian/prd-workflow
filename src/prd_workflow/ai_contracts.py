"""Provider-facing structured-output contracts for fixed AI operations."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from prd_workflow.models import (
    ArchitectureView,
    CapabilityValue,
    Decision,
    DecisionOption,
    DomainView,
    ProductContext,
    WorkflowState,
)


def _non_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("value must not be empty or whitespace")
    return value


class MaterialDecisionDraft(BaseModel):
    """Only the fields an AI supplies for one unresolved material question."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str
    question: str
    context: str
    options: Annotated[tuple[DecisionOption, ...], Field(min_length=2, max_length=4)]
    recommended_option_id: str
    recommendation_rationale: str
    supersedes_decision_id: str | None = None

    _validate_text = field_validator(
        "decision_id",
        "question",
        "context",
        "recommended_option_id",
        "recommendation_rationale",
    )(_non_blank)

    @field_validator("supersedes_decision_id")
    @classmethod
    def _validate_optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _non_blank(value)

    @model_validator(mode="after")
    def _validate_options(self) -> Self:
        option_ids = [option.option_id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("Decision option IDs must be unique")
        if self.recommended_option_id not in option_ids:
            raise ValueError("recommended_option_id must identify a proposed option")
        return self


class DeferredDecisionDraft(BaseModel):
    """Only the fields an AI supplies for one demonstrably safe deferral."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str
    question: str
    context: str | None = None
    safe_to_defer_rationale: str
    downstream_constraints: Annotated[tuple[str, ...], Field(min_length=1)]

    _validate_required_text = field_validator(
        "decision_id", "question", "safe_to_defer_rationale"
    )(_non_blank)

    @field_validator("context")
    @classmethod
    def _validate_context(cls, value: str | None) -> str | None:
        return None if value is None else _non_blank(value)

    @field_validator("downstream_constraints")
    @classmethod
    def _validate_constraints(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            _non_blank(value)
        return values


class DomainOutput(BaseModel):
    """Named output of domain derivation."""

    model_config = ConfigDict(extra="forbid")

    product_context: ProductContext
    domain: DomainView


class CapabilitiesOutput(BaseModel):
    """Named output of capability derivation."""

    model_config = ConfigDict(extra="forbid")

    capabilities: tuple[CapabilityValue, ...]


class ArchitectureOutput(BaseModel):
    """Named output of architecture derivation and safe deferral drafting."""

    model_config = ConfigDict(extra="forbid")

    architecture: ArchitectureView
    deferred_decisions: tuple[DeferredDecisionDraft, ...]


class _FindingsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: Annotated[tuple[str, ...], Field(min_length=1)]

    @field_validator("findings")
    @classmethod
    def _validate_findings(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            _non_blank(value)
        return values


class ConvergencePassOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["PASS"]


class ConvergenceRemodelOutput(_FindingsOutput):
    outcome: Literal["REMODEL"]


class ConvergenceHumanDecisionOutput(_FindingsOutput):
    outcome: Literal["HUMAN_DECISION"]
    decision: MaterialDecisionDraft


ConvergenceOutput = Annotated[
    ConvergencePassOutput
    | ConvergenceRemodelOutput
    | ConvergenceHumanDecisionOutput,
    Field(discriminator="outcome"),
]


class AuditPassOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["PASS"]


class AuditEditorialOutput(_FindingsOutput):
    outcome: Literal["EDITORIAL"]


class AuditRemodelOutput(_FindingsOutput):
    outcome: Literal["REMODEL"]


class AuditHumanDecisionOutput(_FindingsOutput):
    outcome: Literal["HUMAN_DECISION"]
    decision: MaterialDecisionDraft


AuditOutput = Annotated[
    AuditPassOutput
    | AuditEditorialOutput
    | AuditRemodelOutput
    | AuditHumanDecisionOutput,
    Field(discriminator="outcome"),
]


def material_decision_from_draft(
    draft: MaterialDecisionDraft,
    origin_state: WorkflowState,
) -> Decision:
    """Assign workflow-owned lifecycle fields to a material AI draft."""

    return Decision(
        decision_id=draft.decision_id,
        classification="MATERIAL",
        origin_state=origin_state,
        question=draft.question,
        context=draft.context,
        options=draft.options,
        recommended_option_id=draft.recommended_option_id,
        recommendation_rationale=draft.recommendation_rationale,
        status="PENDING",
        answer=None,
        supersedes_decision_id=draft.supersedes_decision_id,
    )


def deferred_decision_from_draft(draft: DeferredDecisionDraft) -> Decision:
    """Assign the workflow-owned classification to a deferred AI draft."""

    return Decision(
        decision_id=draft.decision_id,
        classification="DEFERRED",
        question=draft.question,
        context=draft.context,
        safe_to_defer_rationale=draft.safe_to_defer_rationale,
        downstream_constraints=draft.downstream_constraints,
    )
