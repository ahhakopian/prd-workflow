from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from prd_workflow.ai_contracts import (
    ArchitectureOutput,
    AuditPassOutput,
    CapabilitiesOutput,
    ConvergenceHumanDecisionOutput,
    ConvergencePassOutput,
    DomainOutput,
    MaterialDecisionDraft,
)
from prd_workflow.canonical import final_canonical_path, render_markdown
from prd_workflow.models import (
    ArchitectureView,
    AuditResult,
    CanonicalActor,
    CanonicalActorsAndRoles,
    CanonicalArchitecture,
    CanonicalCapability,
    CanonicalCrossCuttingRequirements,
    CanonicalDeferredDecisions,
    CanonicalDomainModel,
    CanonicalFunctionalCapabilities,
    CanonicalProductDefinition,
    CanonicalPRD,
    CanonicalResponsibilityBoundaries,
    CanonicalResponsibilityBoundary,
    CanonicalScope,
    CanonicalScopeEntry,
    CanonicalSystemBoundaries,
    CapabilityValue,
    ConvergenceResult,
    Decision,
    DecisionOption,
    DomainView,
    ModelingResult,
    OptionWithClarification,
    ProductContext,
    WorkflowState,
)
from prd_workflow.storage import FileStorage
from prd_workflow.workflow import WorkflowService


CLARIFICATION = (
    "Editing is allowed only before the manager records any review action, "
    "and an edit resets the submission timestamp."
)
MISSING_EDIT_FINDING = (
    "Active Authority does not say whether the submitting employee may edit an "
    "expense report while it is pending review."
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
        self.calls.append({"operation": operation, "payload": payload})
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def expense_source_bytes() -> bytes:
    return (
        "# Expense Reimbursement\r\n"
        "\r\n"
        "## Product and release\r\n"
        "The target release lets employees submit business expense reports and "
        "managers review them so approved reports are ready for external payroll "
        "reimbursement. Payment execution and mobile applications are out of scope.\r\n"
        "\r\n"
        "## Actors and behavior\r\n"
        "An employee may create, view, and submit only their own report with amount, "
        "category, date, business purpose, and receipt. A manager may view and approve "
        "or reject reports assigned to them. A report awaiting manager action is "
        "Pending Review. The PRD does not state whether its submitting employee may "
        "edit it in that state.\r\n"
        "\r\n"
        "## Ownership and boundaries\r\n"
        "The product owns expense-report data, status, submission, and review. Managers "
        "own approval decisions. Payroll remains external and owns payment execution. "
        "Expense intake supplies submitted reports to review; review never owns report "
        "creation.\r\n"
        "\r\n"
        "## Cross-cutting requirements\r\n"
        "Only the submitting employee and assigned manager may access a report. Review "
        "actions must be recorded, and report status changes must be immediately visible.\r\n"
    ).encode("utf-8")


def edit_decision() -> Decision:
    return Decision(
        decision_id="expense-edit-policy",
        classification="MATERIAL",
        origin_state=WorkflowState.MODELING,
        question=(
            "While an expense report is pending review, may its submitting employee "
            "edit it?"
        ),
        context=(
            "The answer changes employee permissions, report state behavior, and the "
            "evidence a manager reviews."
        ),
        options=(
            DecisionOption(
                option_id="A",
                text="The submitting employee may not edit after submission.",
                consequence="Pending reports remain immutable until manager action.",
            ),
            DecisionOption(
                option_id="B",
                text="The submitting employee may edit while the report is pending review.",
                consequence="The product must define the cutoff and review effect of edits.",
            ),
            DecisionOption(
                option_id="C",
                text="The employee must withdraw the report before editing it.",
                consequence="Editing adds an explicit withdrawal and resubmission flow.",
            ),
        ),
        recommended_option_id="A",
        recommendation_rationale="Immutable submissions provide the simplest review trail.",
    )


def edit_decision_draft() -> MaterialDecisionDraft:
    decision = edit_decision()
    return MaterialDecisionDraft(
        decision_id=decision.decision_id,
        question=decision.question,
        context=decision.context,
        options=decision.options,
        recommended_option_id=decision.recommended_option_id,
        recommendation_rationale=decision.recommendation_rationale,
    )


def model_outputs(version: str) -> tuple[object, object, object]:
    edit_rule = (
        ("Pending reports are treated as immutable in this incomplete pre-answer model.",)
        if version == "pre-answer"
        else (CLARIFICATION,)
    )
    product = ProductContext(
        problem=f"Employees need controlled expense reimbursement ({version}).",
        target_users=("Employee", "Manager"),
        intended_outcome="Approved reports are ready for external payroll reimbursement.",
        goals=("Submit and review business expense reports.",),
        non_goals=("Execute reimbursement payments.", "Provide a mobile application."),
    )
    domain = DomainView(
        concepts=("Expense Report", "Pending Review", "Review Action"),
        relationships=("An employee submits a report to an assigned manager.",),
        invariants=("Each report has one submitting employee.", *edit_rule),
        terminology=("Pending Review means submitted with no manager review action.",),
    )
    capabilities = (
        CapabilityValue(
            name="Manage expense report",
            purpose="Create and submit a reimbursement request.",
            release_status="IN",
            actors=("Employee",),
            required_behavior=("Create, view, and submit an owned report.", *edit_rule),
            business_rules=("An employee accesses only their own reports.",),
            failure_conditions=("Reject a report without required evidence.",),
        ),
        CapabilityValue(
            name="Review expense report",
            purpose="Approve or reject an assigned submitted report.",
            release_status="IN",
            actors=("Manager",),
            required_behavior=("Record an approval or rejection.",),
            business_rules=("A manager reviews only assigned reports.",),
            dependencies=("Manage expense report",),
        ),
    )
    architecture = ArchitectureView(
        responsibility_areas=("Expense intake", "Expense review"),
        system_boundaries=("Payroll payment execution is external.",),
        ownership=(
            "Expense intake owns report data and submission.",
            "Expense review owns manager decisions.",
            "Payroll owns payment execution.",
        ),
        interactions=("Expense intake supplies pending reports to expense review.",),
        constraints=("Only the submitter and assigned manager may access a report.",),
        invariants=("Expense review does not own report creation.", *edit_rule),
        cross_cutting_requirements=(
            "Record manager review actions.",
            "Make report status changes immediately visible.",
        ),
    )
    return (
        DomainOutput(product_context=product, domain=domain),
        CapabilitiesOutput(capabilities=capabilities),
        ArchitectureOutput(architecture=architecture, deferred_decisions=()),
    )


def final_document() -> CanonicalPRD:
    return CanonicalPRD(
        product_definition=CanonicalProductDefinition(
            summary="A controlled employee expense submission and manager review product.",
            problem="Employees need business expenses reviewed before reimbursement.",
            target_actor_ids=("employee", "manager"),
            intended_outcome="Approved reports are ready for external payroll reimbursement.",
            goals=("Enable controlled submission and manager review of expense reports.",),
            non_goals=("Execute reimbursement payments.", "Provide a mobile application."),
        ),
        scope_and_release_boundary=CanonicalScope(
            summary="The target release includes report management and manager review.",
            target_release="Iteration 1",
            capabilities=(
                CanonicalScopeEntry(
                    capability_id="manage-expense-report",
                    status="IN",
                    included=("Create, view, submit, and conditionally edit owned reports.",),
                ),
                CanonicalScopeEntry(
                    capability_id="review-expense-report",
                    status="IN",
                    included=("Approve or reject assigned reports.",),
                ),
                CanonicalScopeEntry(
                    capability_id="execute-payment",
                    status="OUT",
                    excluded=("Execute reimbursement payments.",),
                ),
                CanonicalScopeEntry(
                    capability_id="mobile-application",
                    status="OUT",
                    excluded=("Provide a mobile application.",),
                ),
            ),
        ),
        actors_and_roles=CanonicalActorsAndRoles(
            summary="Employees own submissions; assigned managers own review decisions.",
            actors=(
                CanonicalActor(
                    actor_id="employee",
                    name="Employee",
                    kind="HUMAN",
                    purpose="Request reimbursement for business expenses.",
                    may_do=("Create, view, submit, and conditionally edit own reports.",),
                    must_do=("Provide amount, category, date, purpose, and receipt.",),
                    must_not_do=("Access another employee's report.",),
                    permission_boundaries=(CLARIFICATION,),
                ),
                CanonicalActor(
                    actor_id="manager",
                    name="Manager",
                    kind="HUMAN",
                    purpose="Review assigned expense reports.",
                    may_do=("Approve or reject assigned reports.",),
                    must_do=("Record each review action.",),
                    must_not_do=("Review an unassigned report.",),
                    permission_boundaries=("May access only assigned reports.",),
                ),
            ),
        ),
        domain_model=CanonicalDomainModel(
            summary="An expense report moves from employee submission to manager review.",
            concepts=(
                "Expense Report: a request for reimbursement with required evidence.",
                "Pending Review: a submitted report before any manager review action.",
                "Review Action: a manager approval or rejection.",
            ),
            relationships=("One employee submits a report to one assigned manager.",),
            invariants=("Each report has one submitting employee.", CLARIFICATION),
            terminology=("Submitting employee means the employee who owns the report.",),
        ),
        functional_capabilities=CanonicalFunctionalCapabilities(
            summary="The product manages employee reports and manager decisions.",
            capabilities=(
                CanonicalCapability(
                    capability_id="manage-expense-report",
                    name="Manage expense report",
                    purpose="Create and submit a complete reimbursement request.",
                    actor_ids=("employee",),
                    required_behavior=(
                        "Create, view, and submit an owned report.",
                        CLARIFICATION,
                    ),
                    business_rules=("A report requires amount, category, date, purpose, and receipt.",),
                    failure_conditions=("Reject submission when required evidence is absent.",),
                ),
                CanonicalCapability(
                    capability_id="review-expense-report",
                    name="Review expense report",
                    purpose="Make a decision on an assigned submitted report.",
                    actor_ids=("manager",),
                    required_behavior=("Approve or reject an assigned report.",),
                    business_rules=("Record the manager's review action.",),
                    dependency_capability_ids=("manage-expense-report",),
                    failure_conditions=("Reject review by an unassigned manager.",),
                ),
                CanonicalCapability(
                    capability_id="execute-payment",
                    name="Execute reimbursement payment",
                    purpose="Pay an approved expense outside this product.",
                    actor_ids=("manager",),
                    required_behavior=("No payment execution is provided by this product.",),
                ),
                CanonicalCapability(
                    capability_id="mobile-application",
                    name="Provide mobile application",
                    purpose="Offer a native mobile client outside the target release.",
                    actor_ids=("employee",),
                    required_behavior=("No mobile application is provided in the target release.",),
                ),
            ),
        ),
        system_boundaries_and_ownership=CanonicalSystemBoundaries(
            summary="The product owns reports and review; payroll owns payment execution.",
            inside_system=("Report creation, submission, editing, status, and review.",),
            outside_system=("Reimbursement payment execution.",),
            external_dependencies=("External payroll receives approved reports.",),
            data_ownership=("Expense intake owns expense-report data and submission timestamps.",),
            decision_ownership=("The assigned manager owns approval and rejection decisions.",),
            responsibility_ownership=("External payroll owns payment execution.",),
            systems_of_record=("The product is authoritative for reports and review status.",),
        ),
        high_level_architecture=CanonicalArchitecture(
            summary="Expense intake supplies reports to the separate review responsibility.",
            responsibility_areas=("Expense intake", "Expense review"),
            non_responsibilities=("The product does not execute payments.",),
            interactions=("Expense intake supplies pending reports to expense review.",),
            constraints=(CLARIFICATION,),
            invariants=("Expense review does not own report creation.",),
            dependency_directions=("Expense review may depend on expense intake.",),
        ),
        cross_cutting_and_non_functional_requirements=CanonicalCrossCuttingRequirements(
            summary="Access, action recording, and immediate status visibility apply throughout.",
            requirements=(
                "Only the submitter and assigned manager may access a report.",
                "Record every manager review action.",
                "Make report status changes immediately visible.",
            ),
        ),
        required_responsibility_boundaries=CanonicalResponsibilityBoundaries(
            summary="Downstream decomposition must preserve intake and review ownership.",
            boundaries=(
                CanonicalResponsibilityBoundary(
                    boundary_id="expense-intake",
                    name="Expense intake",
                    owns=("Report data, creation, submission, editing, and timestamps.",),
                    does_not_own=("Manager review decisions.",),
                    supported_capability_ids=("manage-expense-report",),
                ),
                CanonicalResponsibilityBoundary(
                    boundary_id="expense-review",
                    name="Expense review",
                    owns=("Manager approval and rejection decisions.",),
                    does_not_own=("Report creation or payment execution.",),
                    may_depend_on_boundary_ids=("expense-intake",),
                    supported_capability_ids=("review-expense-report",),
                ),
            ),
        ),
        deferred_decisions_and_handoff_constraints=CanonicalDeferredDecisions(
            summary="No product or system decision remains open for this target release.",
            decisions=(),
            fixed_upstream_constraints=(
                "Preserve release scope, actors, permissions, domain meaning, ownership, "
                "system boundaries, edit cutoff and timestamp reset behavior, architectural "
                "invariants, and required responsibility boundaries.",
            ),
        ),
    )


def test_iteration_1_walking_skeleton_filesystem_acceptance(tmp_path: Path) -> None:
    source = tmp_path / "expense-reimbursement.md"
    original_bytes = expense_source_bytes()
    source.write_bytes(original_bytes)
    pre_answer_outputs = model_outputs("pre-answer")
    post_answer_outputs = model_outputs("post-answer")
    decision = edit_decision()
    first_convergence_output = ConvergenceHumanDecisionOutput(
        outcome="HUMAN_DECISION",
        findings=(MISSING_EDIT_FINDING,),
        decision=edit_decision_draft(),
    )
    first_convergence = ConvergenceResult(
        status="FAIL",
        findings=first_convergence_output.findings,
        remediation="HUMAN_DECISION",
        decision=decision,
    )
    candidate = final_document()
    ai = ScriptedAI(
        None,
        *pre_answer_outputs,
        first_convergence_output,
        *post_answer_outputs,
        ConvergencePassOutput(outcome="PASS"),
        candidate,
        AuditPassOutput(outcome="PASS"),
    )
    storage_root = tmp_path / ".prd"
    service = WorkflowService(FileStorage(storage_root), ai)

    started = service.start(source)
    assert started.state is WorkflowState.INTAKE
    assert (service.storage.run_directory(started.run_id) / "source-prd.md").read_bytes() == original_bytes

    after_intake = service.advance(started.run_id)
    assert after_intake.state is WorkflowState.MODELING
    with pytest.raises(ValueError, match="only for a DONE run"):
        final_canonical_path(after_intake, service.storage.run_directory(started.run_id))

    waiting = service.advance(started.run_id)
    assert waiting.state is WorkflowState.WAITING_HUMAN
    assert waiting.pending_decision_origin is WorkflowState.MODELING
    assert waiting.decisions[-1] == decision
    assert waiting.convergence_result == first_convergence
    assert waiting.modeling_result is not None
    old_model = waiting.modeling_result.model_copy(deep=True)
    authority_before_answer = ai.calls[1]["payload"]["active_authority"]
    assert authority_before_answer["human_decisions"] == []
    assert decision.recommendation_rationale not in json.dumps(authority_before_answer)

    reloaded_service = WorkflowService(FileStorage(storage_root), ai)
    reloaded_waiting = reloaded_service.status(started.run_id)
    persisted_waiting_json = json.loads(
        (reloaded_service.storage.run_directory(started.run_id) / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert reloaded_waiting.state is WorkflowState.WAITING_HUMAN
    assert reloaded_waiting.decisions[-1] == decision
    assert persisted_waiting_json["state"] == "WAITING_HUMAN"

    answered = reloaded_service.answer(
        started.run_id,
        decision.decision_id,
        OptionWithClarification(option_id="B", clarification=CLARIFICATION),
    )
    assert answered.state is WorkflowState.MODELING
    assert answered.modeling_result is None
    assert answered.convergence_result is None
    assert answered.decisions[-1].answer == OptionWithClarification(
        option_id="B", clarification=CLARIFICATION
    )

    resumed_service = WorkflowService(FileStorage(storage_root), ai)
    resumed = resumed_service.status(started.run_id)
    assert resumed.decisions[-1].answer.clarification == CLARIFICATION
    rebuilt = resumed_service.advance(started.run_id)
    assert rebuilt.state is WorkflowState.CANONICALIZATION
    assert rebuilt.convergence_result == ConvergenceResult(status="PASS")
    assert rebuilt.modeling_result is not None
    assert rebuilt.modeling_result != old_model
    assert rebuilt.modeling_result.product_context.problem.endswith("(post-answer).")
    assert [call["operation"] for call in ai.calls[5:9]] == [
        "derive_domain",
        "derive_capabilities",
        "derive_architecture",
        "review_convergence",
    ]
    for call in ai.calls[5:9]:
        authority = call["payload"]["active_authority"]
        answer = authority["human_decisions"][0]["answer"]
        assert answer == {
            "kind": "option_with_clarification",
            "option_id": "B",
            "option_text": decision.options[1].text,
            "clarification": CLARIFICATION,
        }
        serialized = json.dumps(authority)
        assert decision.options[0].text not in serialized
        assert decision.options[2].text not in serialized
        assert decision.recommendation_rationale not in serialized

    completed = resumed_service.advance(started.run_id)
    persisted = WorkflowService(FileStorage(storage_root), ai).status(started.run_id)
    expected_markdown = render_markdown(candidate)
    run_dir = resumed_service.storage.run_directory(started.run_id)
    handoff = final_canonical_path(persisted, run_dir)

    assert completed.state is WorkflowState.DONE
    assert persisted.state is WorkflowState.DONE
    assert json.loads((run_dir / "run.json").read_text(encoding="utf-8"))["state"] == "DONE"
    assert persisted.audit_result == AuditResult(status="PASS")
    assert [call["operation"] for call in ai.calls[-2:]] == [
        "compose_canonical",
        "audit_canonical",
    ]
    assert ai.calls[-2]["payload"]["converged_modeling_result"] == post_answer_outputs_to_model_dump(post_answer_outputs)
    assert ai.calls[-1]["payload"]["exact_rendered_markdown_candidate"] == expected_markdown
    assert handoff == run_dir / "canonical-prd.md"
    assert handoff.name == "canonical-prd.md"
    assert handoff.read_text(encoding="utf-8") == expected_markdown
    assert CLARIFICATION in expected_markdown
    assert decision.options[0].text not in expected_markdown
    assert decision.options[2].text not in expected_markdown
    assert decision.recommendation_rationale not in expected_markdown
    for forbidden in (
        "AI recommendation",
        "WAITING_HUMAN",
        MISSING_EDIT_FINDING,
        "convergence finding",
        "audit finding",
        "source-prd.md",
        "run.json",
    ):
        assert forbidden not in expected_markdown
    for required in (
        "Employees need business expenses reviewed before reimbursement.",
        "Iteration 1",
        "Employee",
        "Manager",
        "manage-expense-report",
        "expense-intake",
        "External payroll",
    ):
        assert required in expected_markdown
    assert ai.results == []


def post_answer_outputs_to_model_dump(outputs: tuple[object, object, object]) -> dict[str, object]:
    domain_output, capabilities_output, architecture_output = outputs
    return ModelingResult(
        product_context=domain_output.product_context,
        domain=domain_output.domain,
        capabilities=capabilities_output.capabilities,
        architecture=architecture_output.architecture,
        deferred_decisions=(),
    ).model_dump(mode="json")
