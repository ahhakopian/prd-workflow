from __future__ import annotations

import pytest
from pydantic import TypeAdapter

from rdp_workflow.models import (
    ArchitectureView,
    AuditResult,
    CanonicalRDP,
    CapabilityValue,
    ConvergenceResult,
    CustomAnswer,
    Decision,
    DecisionOption,
    DomainView,
    HumanAnswer,
    ModelingResult,
    OptionSelection,
    OptionWithClarification,
    ProductContext,
    WorkflowRun,
    WorkflowState,
)


def material_decision(answer: HumanAnswer | None = None) -> Decision:
    return Decision(
        decision_id="decision-1",
        classification="MATERIAL",
        origin_state=WorkflowState.MODELING,
        question="Who may edit a submitted expense?",
        context="The answer changes product behavior and permissions.",
        options=(
            DecisionOption(
                option_id="A",
                text="No edits after submission.",
                consequence="Submitted expenses are immutable.",
            ),
            DecisionOption(
                option_id="B",
                text="Allow edits before review.",
                consequence="A submitted expense may still change.",
            ),
        ),
        recommended_option_id="A",
        recommendation_rationale="Immutability gives the simplest audit trail.",
        status="RESOLVED" if answer is not None else "PENDING",
        answer=answer,
    )


def modeling_result() -> ModelingResult:
    return ModelingResult(
        product_context=ProductContext(
            problem="Employees need reimbursement.",
            target_users=("Employee", "Manager"),
            intended_outcome="Approved expenses can be reimbursed.",
        ),
        domain=DomainView(
            concepts=("Expense",),
            relationships=("An employee submits an expense.",),
            invariants=("An expense has one submitter.",),
        ),
        capabilities=(
            CapabilityValue(
                name="Submit expense",
                purpose="Request reimbursement.",
                release_status="IN",
                actors=("Employee",),
                required_behavior=("Record the submitted expense.",),
            ),
        ),
        architecture=ArchitectureView(
            responsibility_areas=("Expense management",),
            system_boundaries=("Payment execution is external.",),
        ),
    )


def canonical_rdp() -> CanonicalRDP:
    return CanonicalRDP(
        product_definition="Product definition",
        scope_and_release_boundary="Scope and release boundary",
        actors_and_roles="Actors and roles",
        domain_model="Domain model",
        functional_capabilities="Functional capabilities",
        system_boundaries_and_ownership="System boundaries and ownership",
        high_level_architecture="High-level architecture",
        cross_cutting_and_non_functional_requirements="Cross-cutting requirements",
        required_responsibility_boundaries="Required responsibility boundaries",
        deferred_decisions_and_handoff_constraints="No deferred decisions.",
    )


def test_workflow_state_contains_exactly_the_six_normative_values() -> None:
    assert {state.value for state in WorkflowState} == {
        "INTAKE",
        "MODELING",
        "CANONICALIZATION",
        "WAITING_HUMAN",
        "BLOCKED",
        "DONE",
    }


def test_workflow_run_has_no_artifact_lifecycle_or_freshness_fields() -> None:
    forbidden_fields = {
        "domain_state",
        "features_state",
        "architecture_state",
        "canonical_state",
        "is_stale",
        "generated_from",
        "input_hash",
        "prompt_hash",
        "schema_hash",
    }

    assert forbidden_fields.isdisjoint(WorkflowRun.model_fields)


def test_all_human_answer_forms_round_trip_with_discriminator() -> None:
    answers: tuple[HumanAnswer, ...] = (
        OptionSelection(option_id="A"),
        OptionWithClarification(
            option_id="B",
            clarification="  Keep this spacing and punctuation: exactly!  ",
        ),
        CustomAnswer(text="  Use joint approval instead.\nKeep this line.  "),
    )
    adapter = TypeAdapter(HumanAnswer)

    for answer in answers:
        restored = adapter.validate_json(adapter.dump_json(answer))
        assert restored == answer
        assert type(restored) is type(answer)


def test_option_with_clarification_preserves_two_exact_authoritative_parts() -> None:
    answer = OptionWithClarification(
        option_id="B",
        clarification="  Only before review.\nDo not normalize this.  ",
    )
    restored = material_decision(answer).model_copy(deep=True)

    assert isinstance(restored.answer, OptionWithClarification)
    assert restored.answer.option_id == "B"
    assert restored.answer.clarification == "  Only before review.\nDo not normalize this.  "


def test_custom_answer_preserves_text_exactly() -> None:
    text = "  Custom authority.\nSecond line with trailing space.  "
    restored = material_decision(CustomAnswer(text=text)).model_copy(deep=True)

    assert isinstance(restored.answer, CustomAnswer)
    assert restored.answer.text == text


def test_recommendation_is_structurally_distinct_from_human_answer() -> None:
    decision = material_decision(OptionSelection(option_id="B"))

    assert decision.recommended_option_id == "A"
    assert isinstance(decision.answer, OptionSelection)
    assert decision.answer.option_id == "B"


def test_workflow_run_accepts_zero_pending_material_decisions() -> None:
    run = WorkflowRun(
        run_id="run-1",
        decisions=(
            material_decision(OptionSelection(option_id="A")),
            Decision(
                decision_id="deferred-1",
                classification="DEFERRED",
                question="Which internal helper name should be used?",
                safe_to_defer_rationale="The name cannot change product behavior.",
                downstream_constraints=("Preserve the established behavior.",),
            ),
        ),
    )

    assert run.decisions[0].status == "RESOLVED"
    assert run.decisions[1].status is None


def test_workflow_run_accepts_one_pending_material_decision() -> None:
    run = WorkflowRun(run_id="run-1", decisions=(material_decision(),))

    assert run.decisions[0].status == "PENDING"


def test_workflow_run_rejects_two_pending_material_decisions() -> None:
    first = material_decision()
    second = first.model_copy(update={"decision_id": "decision-2"})

    with pytest.raises(ValueError, match="at most one pending MATERIAL Decision"):
        WorkflowRun(run_id="run-1", decisions=(first, second))


def test_deferred_decision_has_no_material_lifecycle_fields() -> None:
    decision = Decision(
        decision_id="deferred-1",
        classification="DEFERRED",
        question="Which internal helper name should be used?",
        safe_to_defer_rationale="The name cannot change product behavior.",
        downstream_constraints=("Preserve the established behavior.",),
    )

    assert decision.status is None
    assert decision.origin_state is None
    assert decision.answer is None
    assert decision.supersedes_decision_id is None
    assert decision.options == ()
    assert decision.recommended_option_id is None
    assert decision.recommendation_rationale is None


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"status": "PENDING"},
        {"origin_state": WorkflowState.INTAKE},
        {"answer": CustomAnswer(text="Human answer")},
        {"supersedes_decision_id": "decision-1"},
        {
            "options": (
                DecisionOption(option_id="A", text="A", consequence="A"),
                DecisionOption(option_id="B", text="B", consequence="B"),
            )
        },
        {"recommended_option_id": "A"},
        {"recommendation_rationale": "Recommendation"},
    ],
)
def test_deferred_decision_rejects_material_only_fields(
    invalid_fields: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "decision_id": "deferred-1",
        "classification": "DEFERRED",
        "question": "Which internal helper name should be used?",
        "safe_to_defer_rationale": "The name cannot change product behavior.",
        "downstream_constraints": ("Preserve the established behavior.",),
    }
    values.update(invalid_fields)

    with pytest.raises(ValueError):
        Decision.model_validate(values)


@pytest.mark.parametrize(
    "missing_field",
    ["safe_to_defer_rationale", "downstream_constraints"],
)
def test_deferred_decision_requires_deferral_justification(
    missing_field: str,
) -> None:
    values: dict[str, object] = {
        "decision_id": "deferred-1",
        "classification": "DEFERRED",
        "question": "Which internal helper name should be used?",
        "safe_to_defer_rationale": "The name cannot change product behavior.",
        "downstream_constraints": ("Preserve the established behavior.",),
    }
    del values[missing_field]

    with pytest.raises(ValueError):
        Decision.model_validate(values)


def test_future_results_persist_without_controlling_lifecycle() -> None:
    run = WorkflowRun(
        run_id="run-1",
        state=WorkflowState.INTAKE,
        modeling_result=modeling_result(),
        convergence_result=ConvergenceResult(status="PASS"),
        canonical_candidate=canonical_rdp(),
        audit_result=AuditResult(status="PASS"),
    )

    restored = WorkflowRun.model_validate_json(run.model_dump_json())

    assert restored.state is WorkflowState.INTAKE
    assert restored.modeling_result == run.modeling_result
    assert restored.convergence_result == run.convergence_result
    assert restored.canonical_candidate == run.canonical_candidate
    assert restored.audit_result == run.audit_result
