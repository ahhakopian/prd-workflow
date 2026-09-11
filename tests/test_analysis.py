from __future__ import annotations

import json
from typing import Any

import pytest

from rdp_workflow.analysis import analyze_intake, derive_models, review_convergence
from rdp_workflow.ai_contracts import (
    ArchitectureOutput,
    CapabilitiesOutput,
    ConvergenceHumanDecisionOutput,
    ConvergencePassOutput,
    ConvergenceRemodelOutput,
    DeferredDecisionDraft,
    DomainOutput,
    MaterialDecisionDraft,
)
from rdp_workflow.models import (
    ArchitectureView,
    CapabilityValue,
    Decision,
    DecisionOption,
    DomainView,
    ModelingResult,
    ProductContext,
    WorkflowState,
)


class ScriptedAI:
    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.calls: list[dict[str, object]] = []

    def invoke(
        self,
        *,
        operation: str,
        payload: dict[str, object],
        result_type: type[Any],
    ) -> Any:
        self.calls.append(
            {"operation": operation, "payload": payload, "result_type": result_type}
        )
        return self.results.pop(0)


def intake_decision() -> Decision:
    return Decision(
        decision_id="decision-1",
        classification="MATERIAL",
        origin_state=WorkflowState.INTAKE,
        question="May employees edit submitted expenses?",
        context="The answer changes product behavior and permissions.",
        options=(
            DecisionOption(
                option_id="A",
                text="Submitted expenses cannot be edited.",
                consequence="Submission is immutable.",
            ),
            DecisionOption(
                option_id="B",
                text="Submitted expenses may be edited before review.",
                consequence="Submission remains mutable for a limited period.",
            ),
        ),
        recommended_option_id="A",
        recommendation_rationale="Immutability gives a simpler audit trail.",
    )


def intake_draft() -> MaterialDecisionDraft:
    decision = intake_decision()
    return MaterialDecisionDraft(
        decision_id=decision.decision_id,
        question=decision.question,
        context=decision.context,
        options=decision.options,
        recommended_option_id=decision.recommended_option_id,
        recommendation_rationale=decision.recommendation_rationale,
    )


def product_context() -> ProductContext:
    return ProductContext(
        problem="Employees need reimbursement.",
        target_users=("Employee", "Manager"),
        intended_outcome="Valid expenses are approved for reimbursement.",
    )


def domain_view() -> DomainView:
    return DomainView(
        concepts=("Expense", "Review"),
        relationships=("An employee submits an expense for review.",),
        invariants=("Each expense has one submitting employee.",),
        terminology=("Submitter means the employee who owns an expense.",),
    )


def capability_values() -> tuple[CapabilityValue, ...]:
    return (
        CapabilityValue(
            name="Submit expense",
            purpose="Request reimbursement.",
            release_status="IN",
            actors=("Employee",),
            required_behavior=("Accept a valid expense for review.",),
        ),
    )


def architecture_view() -> ArchitectureView:
    return ArchitectureView(
        responsibility_areas=("Expense submission", "Expense review"),
        system_boundaries=("Payment execution remains external.",),
        ownership=("Expense review owns the approval decision.",),
    )


def deferred_decision() -> Decision:
    return Decision(
        decision_id="deferred-1",
        classification="DEFERRED",
        question="How are internal modules named?",
        safe_to_defer_rationale="Names do not change established system behavior.",
        downstream_constraints=("Preserve the responsibility boundaries.",),
    )


def deferred_draft() -> DeferredDecisionDraft:
    decision = deferred_decision()
    return DeferredDecisionDraft(
        decision_id=decision.decision_id,
        question=decision.question,
        safe_to_defer_rationale=decision.safe_to_defer_rationale,
        downstream_constraints=decision.downstream_constraints,
    )


def test_analyze_intake_passes_only_active_authority_as_runtime_payload() -> None:
    authority = {"source_prd": "# Expenses", "human_decisions": ()}
    ai = ScriptedAI(intake_draft())

    result = analyze_intake(authority, ai)

    assert result == intake_decision()
    assert len(ai.calls) == 1
    assert ai.calls[0]["operation"] == "intake"
    assert ai.calls[0]["payload"] == {"active_authority": authority}


def test_analyze_intake_returns_none_when_no_material_unknown_blocks_modeling() -> None:
    assert analyze_intake(
        {"source_prd": "Complete authority", "human_decisions": ()},
        ScriptedAI(None),
    ) is None


def test_analyze_intake_rejects_model_supplied_lifecycle_fields() -> None:
    invalid = {
        **intake_draft().model_dump(mode="json"),
        "classification": "MATERIAL",
        "origin_state": "INTAKE",
        "status": "PENDING",
    }
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        analyze_intake({}, ScriptedAI(invalid))


def test_derive_models_passes_active_authority_and_fresh_views_in_strict_order() -> None:
    authority = {
        "source_prd": "# Expenses",
        "human_decisions": ({"answer": {"text": "Human authority"}},),
    }
    ai = ScriptedAI(
        DomainOutput(product_context=product_context(), domain=domain_view()),
        CapabilitiesOutput(capabilities=capability_values()),
        ArchitectureOutput(
            architecture=architecture_view(), deferred_decisions=(deferred_draft(),)
        ),
    )

    result = derive_models(authority, ("Correct the ownership model.",), ai)

    assert [call["operation"] for call in ai.calls] == [
        "derive_domain",
        "derive_capabilities",
        "derive_architecture",
    ]
    assert ai.calls[0]["payload"]["active_authority"] is authority
    assert "recommend" not in json.dumps(ai.calls[0]["payload"]["active_authority"])
    assert ai.calls[1]["payload"]["active_authority"] is authority
    assert ai.calls[1]["payload"]["domain"] == {
        "product_context": product_context().model_dump(mode="json"),
        "view": domain_view().model_dump(mode="json"),
    }
    assert ai.calls[2]["payload"]["active_authority"] is authority
    assert ai.calls[2]["payload"]["domain"] == ai.calls[1]["payload"]["domain"]
    assert ai.calls[2]["payload"]["functional_capabilities"] == tuple(
        value.model_dump(mode="json") for value in capability_values()
    )
    assert all(
        call["payload"]["previous_remodel_findings"]
        == ("Correct the ownership model.",)
        for call in ai.calls
    )
    assert result.product_context == product_context()
    assert result.domain == domain_view()
    assert result.capabilities == capability_values()
    assert result.architecture == architecture_view()
    assert result.deferred_decisions == (deferred_decision(),)


def test_analysis_operations_pass_only_current_runtime_data() -> None:
    authority = {"source_prd": "# Expenses", "human_decisions": ()}
    ai = ScriptedAI(
        DomainOutput(product_context=product_context(), domain=domain_view()),
        CapabilitiesOutput(capabilities=capability_values()),
        ArchitectureOutput(
            architecture=architecture_view(), deferred_decisions=(deferred_draft(),)
        ),
        ConvergencePassOutput(outcome="PASS"),
    )
    models = derive_models(authority, (), ai)
    review_convergence(authority, models, ai)

    assert set(ai.calls[0]["payload"]) == {
        "active_authority",
        "previous_remodel_findings",
    }
    assert set(ai.calls[1]["payload"]) == {
        "active_authority",
        "domain",
        "previous_remodel_findings",
    }
    assert set(ai.calls[2]["payload"]) == {
        "active_authority",
        "domain",
        "functional_capabilities",
        "previous_remodel_findings",
    }
    assert set(ai.calls[3]["payload"]) == {
        "active_authority",
        "complete_fresh_modeling_result",
    }
    assert all("contract" not in json.dumps(call["payload"]) for call in ai.calls)


def test_review_convergence_is_a_separate_fresh_ai_invocation() -> None:
    authority = {"source_prd": "# Expenses", "human_decisions": ()}
    ai = ScriptedAI(
        DomainOutput(product_context=product_context(), domain=domain_view()),
        CapabilitiesOutput(capabilities=capability_values()),
        ArchitectureOutput(architecture=architecture_view(), deferred_decisions=()),
        ConvergenceRemodelOutput(
            outcome="REMODEL",
            findings=("Architecture omitted the review owner.",),
        ),
    )
    models = derive_models(authority, (), ai)

    result = review_convergence(authority, models, ai)

    assert len(ai.calls) == 4
    assert ai.calls[-1]["operation"] == "review_convergence"
    assert ai.calls[-1]["payload"]["active_authority"] is authority
    assert ai.calls[-1]["payload"]["complete_fresh_modeling_result"] == (
        models.model_dump(mode="json")
    )
    assert result.remediation == "REMODEL"


def test_convergence_human_decision_draft_gets_modeling_lifecycle_fields() -> None:
    models = ModelingResult(
        product_context=product_context(),
        domain=domain_view(),
        capabilities=capability_values(),
        architecture=architecture_view(),
    )
    ai = ScriptedAI(
        ConvergenceHumanDecisionOutput(
            outcome="HUMAN_DECISION",
            findings=("Material policy is absent.",),
            decision=intake_draft(),
        )
    )

    result = review_convergence({}, models, ai)

    assert result.status == "FAIL"
    assert result.remediation == "HUMAN_DECISION"
    assert result.decision == intake_decision().model_copy(
        update={"origin_state": WorkflowState.MODELING}
    )
