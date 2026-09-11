from __future__ import annotations

import json
from typing import Any

import pytest

from rdp_workflow.analysis import analyze_intake, derive_models, review_convergence
from rdp_workflow.models import (
    ArchitectureView,
    CapabilityValue,
    ConvergenceResult,
    Decision,
    DecisionOption,
    DomainView,
    OptionSelection,
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


def test_analyze_intake_requests_all_required_checks_against_active_authority() -> None:
    authority = {"source_prd": "# Expenses", "human_decisions": ()}
    ai = ScriptedAI(intake_decision())

    result = analyze_intake(authority, ai)

    assert result == intake_decision()
    assert len(ai.calls) == 1
    assert ai.calls[0]["operation"] == "intake"
    assert ai.calls[0]["payload"]["active_authority"] is authority
    assert ai.calls[0]["payload"]["analysis_required"] == (
        "material ambiguity",
        "material contradiction",
        "missing material information or constraints",
    )
    assert ai.calls[0]["payload"]["intake_contract"] == {
        "material_dimensions": (
            "product behavior",
            "release scope",
            "actors and permissions",
            "domain semantics",
            "feature and responsibility boundaries",
            "ownership",
            "high-level architecture",
            "security",
            "material non-functional requirements",
        ),
        "authority_rules": (
            "Only the Source PRD and accepted Human Decisions are Material Authority.",
            "Accepted Human Decisions take precedence over conflicting Source PRD "
            "meaning within their decided scope.",
            "AI recommendations are never Authority.",
            "Do not answer a Material Unknown.",
            "If a Material Unknown remains, return exactly one earliest consequential "
            "Human Decision.",
            "Otherwise, return no blocking Decision.",
        ),
    }
    assert ai.calls[0]["payload"]["result_rule"] == (
        "A returned Human Decision must be a MATERIAL Decision that asks one "
        "concrete question, gives context, contains 2-4 materially different "
        "options, and identifies one advisory recommendation with its rationale."
    )


def test_analyze_intake_returns_none_when_no_material_unknown_blocks_modeling() -> None:
    assert analyze_intake(
        {"source_prd": "Complete authority", "human_decisions": ()},
        ScriptedAI(None),
    ) is None


@pytest.mark.parametrize(
    "invalid_result",
    [
        Decision(
            decision_id="deferred-1",
            classification="DEFERRED",
            question="Which helper name should be used?",
            safe_to_defer_rationale="It cannot affect product behavior.",
            downstream_constraints=("Preserve established behavior.",),
        ),
        intake_decision().model_copy(update={"origin_state": WorkflowState.MODELING}),
        intake_decision().model_copy(
            update={"status": "RESOLVED", "answer": OptionSelection(option_id="A")}
        ),
    ],
)
def test_analyze_intake_rejects_any_result_other_than_one_pending_intake_decision(
    invalid_result: Decision,
) -> None:
    with pytest.raises(ValueError, match="pending intake-origin MATERIAL Decision"):
        analyze_intake({}, ScriptedAI(invalid_result))


def test_derive_models_passes_active_authority_and_fresh_views_in_strict_order() -> None:
    authority = {
        "source_prd": "# Expenses",
        "human_decisions": ({"answer": {"text": "Human authority"}},),
    }
    ai = ScriptedAI(
        (product_context(), domain_view()),
        capability_values(),
        (architecture_view(), (deferred_decision(),)),
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


def test_slice3_ai_operation_contracts_are_self_contained() -> None:
    authority = {"source_prd": "# Expenses", "human_decisions": ()}
    ai = ScriptedAI(
        (product_context(), domain_view()),
        capability_values(),
        (architecture_view(), (deferred_decision(),)),
        ConvergenceResult(status="PASS"),
    )
    models = derive_models(authority, (), ai)
    review_convergence(authority, models, ai)

    domain_contract = json.dumps(ai.calls[0]["payload"]["domain_contract"])
    capability_contract = json.dumps(ai.calls[1]["payload"]["capability_contract"])
    architecture_contract = json.dumps(
        ai.calls[2]["payload"]["architecture_contract"]
    )
    convergence_contract = json.dumps(
        ai.calls[3]["payload"]["convergence_contract"]
    )

    for contract in (
        domain_contract,
        capability_contract,
        architecture_contract,
        convergence_contract,
    ):
        assert "Source PRD" in contract
        assert "Human Decisions" in contract
        assert "AI recommendations" in contract
        assert "not Authority" in contract
    assert "business language" in domain_contract
    assert "implementation technologies" in domain_contract
    assert "what the product must do" in capability_contract
    assert "downstream specification Feature" in capability_contract
    assert "displaying, using, or transmitting" in architecture_contract
    assert "frameworks, databases, cloud services" in architecture_contract
    assert "every reasonable allowed downstream choice" in architecture_contract
    assert "unresolved Material Unknowns" in convergence_contract
    assert "FAIL with REMODEL" in convergence_contract
    assert "FAIL with HUMAN_DECISION" in convergence_contract
    assert "exactly one MATERIAL Decision" in convergence_contract


def test_review_convergence_is_a_separate_fresh_ai_invocation() -> None:
    authority = {"source_prd": "# Expenses", "human_decisions": ()}
    ai = ScriptedAI(
        (product_context(), domain_view()),
        capability_values(),
        (architecture_view(), ()),
        ConvergenceResult(
            status="FAIL",
            findings=("Architecture omitted the review owner.",),
            remediation="REMODEL",
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
