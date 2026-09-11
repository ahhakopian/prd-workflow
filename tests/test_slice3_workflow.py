from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from rdp_workflow.decisions import active_authority
from rdp_workflow.models import (
    ArchitectureView,
    AuditResult,
    CanonicalRDP,
    CapabilityValue,
    ConvergenceResult,
    Decision,
    DecisionOption,
    DomainView,
    OptionSelection,
    ProductContext,
    WorkflowState,
)
from rdp_workflow.storage import FileStorage
from rdp_workflow.workflow import WorkflowService


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


def product_context(version: str = "first") -> ProductContext:
    return ProductContext(
        problem=f"Employees need reimbursement ({version}).",
        target_users=("Employee", "Manager"),
        intended_outcome="Approved expenses can be reimbursed.",
    )


def domain_view(version: str = "first") -> DomainView:
    return DomainView(
        concepts=(f"Expense ({version})", "Review"),
        relationships=("An employee submits an expense for manager review.",),
        invariants=("Each expense has one submitting employee.",),
    )


def capabilities(version: str = "first") -> tuple[CapabilityValue, ...]:
    return (
        CapabilityValue(
            name=f"Submit expense ({version})",
            purpose="Request reimbursement.",
            release_status="IN",
            actors=("Employee",),
            required_behavior=("Accept a valid expense for review.",),
        ),
    )


def architecture(version: str = "first") -> ArchitectureView:
    return ArchitectureView(
        responsibility_areas=(f"Expense management ({version})",),
        system_boundaries=("Payment execution is external.",),
        ownership=("Expense review owns the approval decision.",),
    )


def model_outputs(version: str = "first") -> tuple[object, object, object]:
    return (
        (product_context(version), domain_view(version)),
        capabilities(version),
        (architecture(version), ()),
    )


def modeling_decision() -> Decision:
    return Decision(
        decision_id="modeling-decision-1",
        classification="MATERIAL",
        origin_state=WorkflowState.MODELING,
        question="May employees edit an expense after submission and before review?",
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
        recommendation_rationale="Immutability provides a simpler audit trail.",
    )


def canonical_candidate() -> CanonicalRDP:
    return CanonicalRDP(
        product_definition="Product definition",
        scope_and_release_boundary="Release scope",
        actors_and_roles="Actors and roles",
        domain_model="Domain model",
        functional_capabilities="Functional capabilities",
        system_boundaries_and_ownership="Boundaries and ownership",
        high_level_architecture="Architecture",
        cross_cutting_and_non_functional_requirements="Cross-cutting requirements",
        required_responsibility_boundaries="Responsibility boundaries",
        deferred_decisions_and_handoff_constraints="No deferred decisions.",
    )


def service_at(tmp_path: Path, ai: ScriptedAI) -> WorkflowService:
    return WorkflowService(FileStorage(tmp_path / ".rdp"), ai)


def start_in_modeling(service: WorkflowService, tmp_path: Path) -> str:
    started = service.start(source_at(tmp_path))
    advanced = service.advance(started.run_id)
    assert advanced.state is WorkflowState.MODELING
    return started.run_id


def test_modeling_pass_persists_fresh_results_and_reaches_canonicalization(
    tmp_path: Path,
) -> None:
    ai = ScriptedAI(
        None,
        *model_outputs(),
        ConvergenceResult(status="PASS"),
    )
    service = service_at(tmp_path, ai)
    run_id = start_in_modeling(service, tmp_path)

    advanced = service.advance(run_id)
    restored = service.status(run_id)

    assert advanced.state is WorkflowState.CANONICALIZATION
    assert restored.state is WorkflowState.CANONICALIZATION
    assert restored.modeling_result is not None
    assert restored.modeling_result.domain == domain_view()
    assert restored.convergence_result == ConvergenceResult(status="PASS")
    assert [call["operation"] for call in ai.calls] == [
        "intake",
        "derive_domain",
        "derive_capabilities",
        "derive_architecture",
        "review_convergence",
    ]


def test_modeling_remodel_stays_in_modeling_and_next_run_fully_rebuilds(
    tmp_path: Path,
) -> None:
    finding = "The model assigned approval ownership contrary to Authority."
    ai = ScriptedAI(
        None,
        *model_outputs("first"),
        ConvergenceResult(
            status="FAIL", findings=(finding,), remediation="REMODEL"
        ),
        *model_outputs("rebuilt"),
        ConvergenceResult(status="PASS"),
    )
    service = service_at(tmp_path, ai)
    run_id = start_in_modeling(service, tmp_path)

    failed = service.advance(run_id)

    assert failed.state is WorkflowState.MODELING
    assert failed.modeling_result is not None
    assert failed.modeling_result.domain == domain_view("first")
    assert failed.convergence_result is not None
    assert failed.convergence_result.findings == (finding,)

    rebuilt = service.advance(run_id)

    assert rebuilt.state is WorkflowState.CANONICALIZATION
    assert rebuilt.modeling_result is not None
    assert rebuilt.modeling_result.domain == domain_view("rebuilt")
    assert [call["operation"] for call in ai.calls[5:9]] == [
        "derive_domain",
        "derive_capabilities",
        "derive_architecture",
        "review_convergence",
    ]
    assert all(
        call["payload"]["previous_remodel_findings"] == (finding,)
        for call in ai.calls[5:8]
    )


def test_modeling_human_decision_waits_with_exactly_one_pending_decision(
    tmp_path: Path,
) -> None:
    convergence = ConvergenceResult(
        status="FAIL",
        findings=("Authority does not define post-submission editing.",),
        remediation="HUMAN_DECISION",
        decision=modeling_decision(),
    )
    ai = ScriptedAI(None, *model_outputs(), convergence)
    service = service_at(tmp_path, ai)
    run_id = start_in_modeling(service, tmp_path)

    advanced = service.advance(run_id)
    pending = [decision for decision in advanced.decisions if decision.status == "PENDING"]

    assert advanced.state is WorkflowState.WAITING_HUMAN
    assert advanced.pending_decision_origin is WorkflowState.MODELING
    assert pending == [modeling_decision()]
    assert advanced.convergence_result == convergence


def test_ai_generated_human_decision_cannot_fabricate_active_authority(
    tmp_path: Path,
) -> None:
    convergence = ConvergenceResult(
        status="FAIL",
        findings=("A material edit-policy answer is absent.",),
        remediation="HUMAN_DECISION",
        decision=modeling_decision(),
    )
    ai = ScriptedAI(None, *model_outputs(), convergence)
    service = service_at(tmp_path, ai)
    run_id = start_in_modeling(service, tmp_path)
    waiting = service.advance(run_id)

    authority = active_authority(waiting, service.storage.load_source(run_id))

    assert authority["human_decisions"] == ()
    assert "Do not allow edits" not in json.dumps(authority)
    assert "recommended" not in json.dumps(authority)


def test_modeling_origin_answer_returns_to_modeling_and_clears_all_derived_values(
    tmp_path: Path,
) -> None:
    convergence = ConvergenceResult(
        status="FAIL",
        findings=("A material edit-policy answer is absent.",),
        remediation="HUMAN_DECISION",
        decision=modeling_decision(),
    )
    ai = ScriptedAI(None, *model_outputs(), convergence)
    service = service_at(tmp_path, ai)
    run_id = start_in_modeling(service, tmp_path)
    service.advance(run_id)

    persisted = service.status(run_id)
    persisted.canonical_candidate = canonical_candidate()
    persisted.audit_result = AuditResult(status="PASS")
    service.storage.save_run(persisted)

    answered = service.answer(
        run_id, "modeling-decision-1", OptionSelection(option_id="B")
    )
    restored = service.status(run_id)

    assert answered.state is WorkflowState.MODELING
    assert restored.state is WorkflowState.MODELING
    assert restored.decisions[-1].status == "RESOLVED"
    assert restored.pending_decision_origin is None
    assert restored.modeling_result is None
    assert restored.convergence_result is None
    assert restored.canonical_candidate is None
    assert restored.audit_result is None


def test_next_modeling_execution_after_answer_rebuilds_all_views_from_new_authority(
    tmp_path: Path,
) -> None:
    human_failure = ConvergenceResult(
        status="FAIL",
        findings=("A material edit-policy answer is absent.",),
        remediation="HUMAN_DECISION",
        decision=modeling_decision(),
    )
    ai = ScriptedAI(
        None,
        *model_outputs("before-answer"),
        human_failure,
        *model_outputs("after-answer"),
        ConvergenceResult(status="PASS"),
    )
    service = service_at(tmp_path, ai)
    run_id = start_in_modeling(service, tmp_path)
    service.advance(run_id)
    service.answer(run_id, "modeling-decision-1", OptionSelection(option_id="B"))

    rebuilt = service.advance(run_id)

    assert rebuilt.state is WorkflowState.CANONICALIZATION
    assert rebuilt.modeling_result is not None
    assert rebuilt.modeling_result.product_context == product_context("after-answer")
    assert rebuilt.modeling_result.domain == domain_view("after-answer")
    assert rebuilt.modeling_result.capabilities == capabilities("after-answer")
    assert rebuilt.modeling_result.architecture == architecture("after-answer")
    assert [call["operation"] for call in ai.calls[5:9]] == [
        "derive_domain",
        "derive_capabilities",
        "derive_architecture",
        "review_convergence",
    ]
    domain_authority = ai.calls[5]["payload"]["active_authority"]
    assert domain_authority["human_decisions"][0]["answer"] == {
        "kind": "option_selection",
        "option_id": "B",
        "option_text": "Allow edits until review begins.",
    }
    assert "recommend" not in json.dumps(domain_authority)


def test_modeling_ai_failure_does_not_transition_or_persist_partial_results(
    tmp_path: Path,
) -> None:
    ai = ScriptedAI(
        None,
        *model_outputs(),
        RuntimeError("provider unavailable"),
    )
    service = service_at(tmp_path, ai)
    run_id = start_in_modeling(service, tmp_path)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        service.advance(run_id)

    restored = service.status(run_id)
    assert restored.state is WorkflowState.MODELING
    assert restored.modeling_result is None
    assert restored.convergence_result is None
    assert [call["operation"] for call in ai.calls[-4:]] == [
        "derive_domain",
        "derive_capabilities",
        "derive_architecture",
        "review_convergence",
    ]
