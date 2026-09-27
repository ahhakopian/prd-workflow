from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from prd_workflow.ai_contracts import (
    ArchitectureOutput,
    AuditEditorialOutput,
    AuditHumanDecisionOutput,
    AuditPassOutput,
    AuditRemodelOutput,
    CapabilitiesOutput,
    ConvergencePassOutput,
    DomainOutput,
    MaterialDecisionDraft,
)
from prd_workflow.canonical import final_canonical_path, render_markdown
from prd_workflow.models import (
    ArchitectureView,
    AuditResult,
    CapabilityValue,
    ConvergenceResult,
    Decision,
    DecisionOption,
    DomainView,
    OptionSelection,
    ProductContext,
    WorkflowState,
)
from prd_workflow.storage import FileStorage
from prd_workflow.workflow import WorkflowService
from test_canonical import canonical_document, modeling_result


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
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def source_at(tmp_path: Path) -> Path:
    source = tmp_path / "source.md"
    source.write_text(
        "# Expense product\n\nEmployees submit expenses for manager review.\n",
        encoding="utf-8",
    )
    return source


def service_in_canonicalization(
    tmp_path: Path,
    ai: ScriptedAI,
    *,
    convergence: ConvergenceResult | None = None,
) -> tuple[WorkflowService, str]:
    service = WorkflowService(FileStorage(tmp_path / ".prd"), ai)
    run = service.start(source_at(tmp_path))
    run.state = WorkflowState.CANONICALIZATION
    run.modeling_result = modeling_result()
    run.convergence_result = convergence or ConvergenceResult(status="PASS")
    service.storage.save_run(run)
    return service, run.run_id


def canonical_decision() -> Decision:
    return Decision(
        decision_id="audit-decision-1",
        classification="MATERIAL",
        origin_state=WorkflowState.CANONICALIZATION,
        question="May employees edit a submitted expense before review?",
        context="The answer changes product behavior and employee permissions.",
        options=(
            DecisionOption(
                option_id="A",
                text="Do not allow edits after submission.",
                consequence="Submitted expenses are immutable.",
            ),
            DecisionOption(
                option_id="B",
                text="Allow edits until review begins.",
                consequence="Submitted expenses remain temporarily mutable.",
            ),
        ),
        recommended_option_id="A",
        recommendation_rationale="Immutability gives a simpler audit trail.",
    )


def canonical_decision_draft() -> MaterialDecisionDraft:
    decision = canonical_decision()
    return MaterialDecisionDraft(
        decision_id=decision.decision_id,
        question=decision.question,
        context=decision.context,
        options=decision.options,
        recommended_option_id=decision.recommended_option_id,
        recommendation_rationale=decision.recommendation_rationale,
    )


def rebuilt_model_outputs() -> tuple[object, object, object]:
    product = ProductContext(
        problem="Employees need rebuilt reimbursement support.",
        target_users=("Employee", "Manager"),
        intended_outcome="Expenses can be approved.",
    )
    domain = DomainView(
        concepts=("Rebuilt expense",),
        relationships=("An employee owns an expense.",),
        invariants=("An expense has one owner.",),
    )
    capabilities = (
        CapabilityValue(
            name="Rebuilt submission",
            purpose="Request reimbursement.",
            release_status="IN",
            actors=("Employee",),
            required_behavior=("Submit an expense.",),
        ),
    )
    architecture = ArchitectureView(
        responsibility_areas=("Rebuilt expense intake",),
        system_boundaries=("Payment stays external.",),
    )
    return (
        DomainOutput(product_context=product, domain=domain),
        CapabilitiesOutput(capabilities=capabilities),
        ArchitectureOutput(architecture=architecture, deferred_decisions=()),
    )


def test_canonicalization_without_convergence_pass_becomes_blocked(
    tmp_path: Path,
) -> None:
    failure = ConvergenceResult(
        status="FAIL",
        findings=("The model needs correction.",),
        remediation="REMODEL",
    )
    service, run_id = service_in_canonicalization(
        tmp_path, ScriptedAI(), convergence=failure
    )

    blocked = service.advance(run_id)

    assert service.ai.calls == []
    assert blocked.state is WorkflowState.BLOCKED
    assert blocked.diagnostics == ("CANONICALIZATION requires Convergence PASS.",)
    assert service.status(run_id).state is WorkflowState.BLOCKED


def test_validation_failure_stays_in_canonicalization_and_is_reprocessed(
    tmp_path: Path,
) -> None:
    invalid = canonical_document("invalid").model_copy(deep=True)
    invalid.scope_and_release_boundary.capabilities = ()
    corrected = canonical_document("corrected")
    ai = ScriptedAI(invalid, corrected, AuditPassOutput(outcome="PASS"))
    service, run_id = service_in_canonicalization(tmp_path, ai)

    failed = service.advance(run_id)

    assert failed.state is WorkflowState.CANONICALIZATION
    assert failed.canonical_candidate == invalid
    assert failed.audit_result is None
    assert [call["operation"] for call in ai.calls] == ["compose_canonical"]
    assert not (service.storage.run_directory(run_id) / "canonical-prd.md").exists()

    completed = service.advance(run_id)

    assert completed.state is WorkflowState.DONE
    assert [call["operation"] for call in ai.calls] == [
        "compose_canonical",
        "compose_canonical",
        "audit_canonical",
    ]
    assert ai.calls[1]["payload"][
        "previous_editorial_or_validation_findings"
    ] == list(failed.diagnostics)
    assert ai.calls[2]["payload"]["exact_rendered_markdown_candidate"] == (
        render_markdown(corrected)
    )


def test_editorial_failure_recomposes_and_reaudits_next_candidate(
    tmp_path: Path,
) -> None:
    first = canonical_document("first")
    second = canonical_document("second")
    editorial = AuditResult(
        status="FAIL",
        findings=("Clarify one non-material cross-reference.",),
        remediation="EDITORIAL",
    )
    ai = ScriptedAI(
        first,
        AuditEditorialOutput(
            outcome="EDITORIAL", findings=editorial.findings
        ),
        second,
        AuditPassOutput(outcome="PASS"),
    )
    service, run_id = service_in_canonicalization(tmp_path, ai)

    failed = service.advance(run_id)
    completed = service.advance(run_id)

    assert failed.state is WorkflowState.CANONICALIZATION
    assert failed.audit_result == editorial
    assert completed.state is WorkflowState.DONE
    assert completed.canonical_candidate == second
    assert [call["operation"] for call in ai.calls] == [
        "compose_canonical",
        "audit_canonical",
        "compose_canonical",
        "audit_canonical",
    ]
    assert ai.calls[2]["payload"][
        "previous_editorial_or_validation_findings"
    ] == list(editorial.findings)
    assert ai.calls[3]["payload"]["exact_rendered_markdown_candidate"] == (
        render_markdown(second)
    )


def test_audit_remodel_returns_to_modeling_and_rebuilds_complete_model_set(
    tmp_path: Path,
) -> None:
    finding = "The model omitted authoritative approval ownership."
    ai = ScriptedAI(
        canonical_document(),
        AuditRemodelOutput(outcome="REMODEL", findings=(finding,)),
        *rebuilt_model_outputs(),
        ConvergencePassOutput(outcome="PASS"),
    )
    service, run_id = service_in_canonicalization(tmp_path, ai)

    routed = service.advance(run_id)

    assert routed.state is WorkflowState.MODELING
    assert routed.canonical_candidate is None
    assert routed.audit_result is None
    assert routed.diagnostics == (finding,)

    rebuilt = service.advance(run_id)

    assert rebuilt.state is WorkflowState.CANONICALIZATION
    assert rebuilt.modeling_result is not None
    assert rebuilt.modeling_result.product_context.problem.startswith("Employees need rebuilt")
    assert [call["operation"] for call in ai.calls[2:6]] == [
        "derive_domain",
        "derive_capabilities",
        "derive_architecture",
        "review_convergence",
    ]
    assert all(
        call["payload"]["previous_remodel_findings"] == [finding]
        for call in ai.calls[2:5]
    )


def test_audit_human_decision_waits_then_answer_clears_every_old_derived_value(
    tmp_path: Path,
) -> None:
    audit = AuditHumanDecisionOutput(
        outcome="HUMAN_DECISION",
        findings=("Authority does not define post-submission edits.",),
        decision=canonical_decision_draft(),
    )
    ai = ScriptedAI(canonical_document(), audit)
    service, run_id = service_in_canonicalization(tmp_path, ai)

    waiting = service.advance(run_id)

    assert waiting.state is WorkflowState.WAITING_HUMAN
    assert waiting.pending_decision_origin is WorkflowState.CANONICALIZATION
    assert waiting.decisions[-1] == canonical_decision()

    answered = service.answer(
        run_id, "audit-decision-1", OptionSelection(option_id="B")
    )

    assert answered.state is WorkflowState.MODELING
    assert answered.decisions[-1].status == "RESOLVED"
    assert answered.modeling_result is None
    assert answered.convergence_result is None
    assert answered.canonical_candidate is None
    assert answered.audit_result is None
    assert answered.diagnostics == ()


def test_validation_pass_without_audit_pass_never_reaches_done(tmp_path: Path) -> None:
    ai = ScriptedAI(canonical_document(), RuntimeError("audit provider unavailable"))
    service, run_id = service_in_canonicalization(tmp_path, ai)

    with pytest.raises(RuntimeError, match="audit provider unavailable"):
        service.advance(run_id)

    restored = service.status(run_id)
    assert restored.state is WorkflowState.CANONICALIZATION
    assert restored.canonical_candidate is not None
    assert restored.operation_cursor == "audit_canonical"
    assert restored.audit_result is None
    assert not (service.storage.run_directory(run_id) / "canonical-prd.md").exists()
    assert [call["operation"] for call in ai.calls] == [
        "compose_canonical",
        "audit_canonical",
    ]


def test_composer_provider_failure_preserves_canonicalization_for_explicit_retry(
    tmp_path: Path,
) -> None:
    ai = ScriptedAI(RuntimeError("composer schema failure"))
    service, run_id = service_in_canonicalization(tmp_path, ai)

    with pytest.raises(RuntimeError, match="composer schema failure"):
        service.advance(run_id)

    restored = service.status(run_id)
    assert restored.state is WorkflowState.CANONICALIZATION
    assert restored.canonical_candidate is None
    assert restored.audit_result is None
    assert not (service.storage.run_directory(run_id) / "canonical-prd.md").exists()
    assert [call["operation"] for call in ai.calls] == ["compose_canonical"]


def test_audit_pass_cannot_override_current_validation_failure(tmp_path: Path) -> None:
    invalid = canonical_document().model_copy(deep=True)
    invalid.functional_capabilities.capabilities[0].actor_ids = ("unknown-role",)
    ai = ScriptedAI(invalid)
    service, run_id = service_in_canonicalization(tmp_path, ai)
    persisted = service.status(run_id)
    persisted.audit_result = AuditResult(status="PASS")
    service.storage.save_run(persisted)

    advanced = service.advance(run_id)

    assert advanced.state is WorkflowState.CANONICALIZATION
    assert advanced.audit_result is None
    assert [call["operation"] for call in ai.calls] == ["compose_canonical"]
    assert not (service.storage.run_directory(run_id) / "canonical-prd.md").exists()


def test_both_validation_and_audit_pass_write_exact_markdown_before_done(
    tmp_path: Path,
) -> None:
    class OrderingStorage(FileStorage):
        saw_final_before_done_save = False

        def save_run(self, run: Any) -> None:
            if run.state is WorkflowState.DONE:
                self.saw_final_before_done_save = (
                    self.run_directory(run.run_id) / "canonical-prd.md"
                ).is_file()
            super().save_run(run)

    candidate = canonical_document()
    ai = ScriptedAI(candidate, AuditPassOutput(outcome="PASS"))
    storage = OrderingStorage(tmp_path / ".prd")
    service = WorkflowService(storage, ai)
    run = service.start(source_at(tmp_path))
    run.state = WorkflowState.CANONICALIZATION
    run.modeling_result = modeling_result()
    run.convergence_result = ConvergenceResult(status="PASS")
    storage.save_run(run)

    completed = service.advance(run.run_id)
    final_path = final_canonical_path(completed, storage.run_directory(run.run_id))

    assert completed.state is WorkflowState.DONE
    assert storage.saw_final_before_done_save
    assert final_path.name == "canonical-prd.md"
    assert final_path.read_text(encoding="utf-8") == render_markdown(candidate)


def test_canonical_file_presence_never_implies_done_or_enables_exposure(
    tmp_path: Path,
) -> None:
    service, run_id = service_in_canonicalization(tmp_path, ScriptedAI())
    run_dir = service.storage.run_directory(run_id)
    (run_dir / "canonical-prd.md").write_text("# Untrusted\n", encoding="utf-8")

    restored = service.status(run_id)

    assert restored.state is WorkflowState.CANONICALIZATION
    with pytest.raises(ValueError, match="only for a DONE run"):
        final_canonical_path(restored, run_dir)


def test_slice4_adds_no_lifecycle_or_freshness_mechanism() -> None:
    assert {state.value for state in WorkflowState} == {
        "INTAKE",
        "MODELING",
        "CANONICALIZATION",
        "WAITING_HUMAN",
        "BLOCKED",
        "DONE",
    }
    forbidden = {
        "composition_state",
        "render_state",
        "validation_state",
        "audit_state",
        "repair_state",
        "promotion_state",
        "handoff_state",
        "freshness",
        "is_stale",
    }
    from prd_workflow.models import WorkflowRun

    assert forbidden.isdisjoint(WorkflowRun.model_fields)
