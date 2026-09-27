from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

import prd_workflow.canonical as canonical_module

from prd_workflow.ai import load_prompt
from prd_workflow.ai_contracts import (
    AuditEditorialOutput,
    AuditHumanDecisionOutput,
    AuditPassOutput,
    AuditRemodelOutput,
    MaterialDecisionDraft,
)
from prd_workflow.canonical import (
    audit_canonical,
    compose_canonical,
    final_canonical_path,
    load_canonical_template,
    render_markdown,
    validate_contract,
)
from prd_workflow.models import (
    ArchitectureView,
    AuditResult,
    CanonicalActor,
    CanonicalActorsAndRoles,
    CanonicalArchitecture,
    CanonicalCapability,
    CanonicalCrossCuttingRequirements,
    CanonicalDeferredDecision,
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
    ProductContext,
    WorkflowRun,
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


def modeling_result() -> ModelingResult:
    return ModelingResult(
        product_context=ProductContext(
            problem="Employees need reimbursement.",
            target_users=("Employee", "Manager"),
            intended_outcome="Approved expenses are ready for reimbursement.",
        ),
        domain=DomainView(
            concepts=("Expense", "Review"),
            relationships=("An employee submits an expense for review.",),
            invariants=("Each expense has one submitting employee.",),
        ),
        capabilities=(
            CapabilityValue(
                name="Submit expense",
                purpose="Request reimbursement.",
                release_status="PARTIAL",
                actors=("Employee",),
                required_behavior=("Submit an expense for review.",),
            ),
        ),
        architecture=ArchitectureView(
            responsibility_areas=("Expense intake", "Expense review"),
            system_boundaries=("Payment execution is external.",),
            ownership=("Expense review owns approval decisions.",),
        ),
    )


def canonical_document(label: str = "candidate") -> CanonicalPRD:
    return CanonicalPRD(
        product_definition=CanonicalProductDefinition(
            summary=f"Expense product ({label}).",
            problem="Employees need a controlled reimbursement workflow.",
            target_actor_ids=("employee", "manager"),
            intended_outcome="Approved expenses are ready for reimbursement.",
            goals=("Let employees submit valid expenses.",),
            non_goals=("Executing payment is outside this product.",),
        ),
        scope_and_release_boundary=CanonicalScope(
            summary="The target release supports expense submission before review.",
            target_release="Iteration 1",
            capabilities=(
                CanonicalScopeEntry(
                    capability_id="submit-expense",
                    status="PARTIAL",
                    included=("Create and submit an expense.",),
                    excluded=("Edit an expense after review begins.",),
                ),
            ),
        ),
        actors_and_roles=CanonicalActorsAndRoles(
            summary="Employees submit and managers review expenses.",
            actors=(
                CanonicalActor(
                    actor_id="employee",
                    name="Employee",
                    kind="HUMAN",
                    purpose="Request reimbursement.",
                    may_do=("Create and submit own expenses.",),
                    must_do=("Provide required expense evidence.",),
                    permission_boundaries=("May access only own expenses.",),
                ),
                CanonicalActor(
                    actor_id="manager",
                    name="Manager",
                    kind="HUMAN",
                    purpose="Review submitted expenses.",
                    may_do=("Review assigned expenses.",),
                    permission_boundaries=("May review only assigned expenses.",),
                ),
            ),
        ),
        domain_model=CanonicalDomainModel(
            summary="Expenses are reimbursement requests reviewed by managers.",
            concepts=("Expense: a reimbursement request.", "Review: a manager decision."),
            relationships=("An employee submits an expense for review.",),
            invariants=("Each expense has one submitting employee.",),
            terminology=("Submitter means the employee who owns an expense.",),
        ),
        functional_capabilities=CanonicalFunctionalCapabilities(
            summary="The product accepts expenses for review.",
            capabilities=(
                CanonicalCapability(
                    capability_id="submit-expense",
                    name="Submit expense",
                    purpose="Request reimbursement.",
                    actor_ids=("employee",),
                    required_behavior=("Record a valid expense for manager review.",),
                    business_rules=("The submitter owns the expense.",),
                    failure_conditions=("Reject missing required evidence.",),
                ),
            ),
        ),
        system_boundaries_and_ownership=CanonicalSystemBoundaries(
            summary="The product records and reviews expenses but does not execute payment.",
            inside_system=("Expense submission and review.",),
            outside_system=("Payment execution.",),
            external_dependencies=("An external payroll system executes payment.",),
            data_ownership=("Expense intake owns submitted expense records.",),
            decision_ownership=("Expense review owns approval decisions.",),
            responsibility_ownership=("Payroll owns payment execution.",),
            systems_of_record=("The product is authoritative for expense status.",),
        ),
        high_level_architecture=CanonicalArchitecture(
            summary="Expense intake and review are separate responsibility areas.",
            responsibility_areas=("Expense intake", "Expense review"),
            non_responsibilities=("The product does not execute payment.",),
            interactions=("Expense intake supplies submitted expenses to review.",),
            constraints=("Review consumes immutable submitted evidence.",),
            invariants=("Payment execution remains outside the system.",),
            dependency_directions=("Review may depend on expense intake.",),
        ),
        cross_cutting_and_non_functional_requirements=CanonicalCrossCuttingRequirements(
            summary="Material access and audit constraints apply across capabilities.",
            requirements=(
                "Only authorized actors may view an expense.",
                "Review decisions must be auditable.",
            ),
        ),
        required_responsibility_boundaries=CanonicalResponsibilityBoundaries(
            summary="Feature decomposition must preserve intake ownership.",
            boundaries=(
                CanonicalResponsibilityBoundary(
                    boundary_id="expense-intake",
                    name="Expense intake",
                    owns=("Expense creation and submission.",),
                    does_not_own=("Approval decisions.",),
                    supported_capability_ids=("submit-expense",),
                ),
            ),
        ),
        deferred_decisions_and_handoff_constraints=CanonicalDeferredDecisions(
            summary="Only non-material implementation naming is deferred.",
            decisions=(
                CanonicalDeferredDecision(
                    decision_id="internal-module-names",
                    question="What are the internal module names?",
                    reason_safe_to_defer=(
                        "Every acceptable name preserves behavior and all boundaries."
                    ),
                    downstream_constraints=(
                        "Preserve the expense-intake responsibility boundary.",
                    ),
                ),
            ),
            fixed_upstream_constraints=(
                "Preserve release scope, roles, domain semantics, ownership, system "
                "boundaries, architectural invariants, and responsibility boundaries.",
            ),
        ),
    )


def test_composer_receives_only_authority_converged_model_and_findings() -> None:
    authority = {
        "source_prd": "# Expenses",
        "human_decisions": ({"answer": {"text": "Human authority"}},),
    }
    models = modeling_result()
    candidate = canonical_document()
    ai = ScriptedAI(candidate)

    result = compose_canonical(authority, models, ("Clarify scope text.",), ai)

    assert result == candidate
    assert [call["operation"] for call in ai.calls] == ["compose_canonical"]
    payload = ai.calls[0]["payload"]
    assert payload["active_authority"] is authority
    assert payload["converged_modeling_result"] == models.model_dump(mode="json")
    assert payload["previous_editorial_or_validation_findings"] == (
        "Clarify scope text.",
    )
    assert set(payload) == {
        "active_authority",
        "converged_modeling_result",
        "previous_editorial_or_validation_findings",
    }
    assert "contract" not in json.dumps(payload)


def test_renderer_is_deterministic_and_emits_exactly_ten_normative_sections() -> None:
    document = canonical_document()
    template = load_canonical_template()

    first = render_markdown(document)
    second = render_markdown(document.model_copy(deep=True))

    assert first == second
    expected_headings = [
        "## 1. Product Definition",
        "## 2. Scope & Release Boundary",
        "## 3. Actors & Roles",
        "## 4. Domain Model",
        "## 5. Functional Capabilities",
        "## 6. System Boundaries & Ownership",
        "## 7. High-Level Architecture",
        "## 8. Cross-Cutting & Non-Functional Requirements",
        "## 9. Required Responsibility Boundaries",
        "## 10. Deferred Decisions & Handoff Constraints",
    ]
    expected_placeholders = list(canonical_module._TEMPLATE_PLACEHOLDERS)
    assert re.findall(r"^## \d+\. .+$", template, flags=re.MULTILINE) == expected_headings
    assert re.findall(r"\{\{[^{}\n]+\}\}", template) == expected_placeholders
    assert all(template.count(placeholder) == 1 for placeholder in expected_placeholders)
    assert [title for _, title in canonical_module._SECTION_FIELDS_AND_TITLES] == [
        heading.removeprefix(f"## {index}. ")
        for index, heading in enumerate(expected_headings, start=1)
    ]
    assert re.findall(r"^\d+\. .+$", load_prompt("compose_canonical"), flags=re.MULTILINE) == [
        heading.removeprefix("## ") for heading in expected_headings
    ]
    assert re.findall(r"^## \d+\. .+$", first, flags=re.MULTILINE) == expected_headings
    assert re.search(r"\{\{[^{}\n]+\}\}", first) is None
    assert "### Capability `submit-expense` — PARTIAL" in first
    assert "### `employee` — Employee (HUMAN)" in first
    assert "### `submit-expense` — Submit expense" in first
    assert "### `expense-intake` — Expense intake" in first
    assert "### `internal-module-names`" in first
    assert "- None established." in first


def test_renderer_rejects_invalid_or_unreplaced_template_placeholders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = load_canonical_template()
    placeholder = "{{PRODUCT_SUMMARY}}"
    invalid_templates = (
        template.replace(placeholder, "", 1),
        template + placeholder,
        template + "{{UNKNOWN_SECTION}}\n",
    )
    for invalid in invalid_templates:
        monkeypatch.setattr(canonical_module, "load_canonical_template", lambda: invalid)
        with pytest.raises(ValueError, match="invalid Canonical template placeholders"):
            render_markdown(canonical_document())

    unresolved = canonical_document().model_copy(deep=True)
    unresolved.product_definition.summary = placeholder
    monkeypatch.setattr(canonical_module, "load_canonical_template", lambda: template)
    with pytest.raises(ValueError, match="unreplaced placeholder"):
        render_markdown(unresolved)


def test_contract_validation_rejects_missing_sections_and_required_content() -> None:
    missing = CanonicalPRD.model_construct()
    empty_legacy = CanonicalPRD(
        product_definition="Product",
        scope_and_release_boundary="Scope",
        actors_and_roles="Actors",
        domain_model="Domain",
        functional_capabilities="Capabilities",
        system_boundaries_and_ownership="Boundaries",
        high_level_architecture="Architecture",
        cross_cutting_and_non_functional_requirements="Cross-cutting",
        required_responsibility_boundaries="Responsibilities",
        deferred_decisions_and_handoff_constraints="Deferred",
    )

    assert len(validate_contract(missing)) >= 10
    assert validate_contract(missing)[:10] == (
        "Missing required section: Product Definition.",
        "Missing required section: Scope & Release Boundary.",
        "Missing required section: Actors & Roles.",
        "Missing required section: Domain Model.",
        "Missing required section: Functional Capabilities.",
        "Missing required section: System Boundaries & Ownership.",
        "Missing required section: High-Level Architecture.",
        "Missing required section: Cross-Cutting & Non-Functional Requirements.",
        "Missing required section: Required Responsibility Boundaries.",
        "Missing required section: Deferred Decisions & Handoff Constraints.",
    )
    findings = validate_contract(empty_legacy)
    assert "Product Definition problem must not be empty." in findings
    assert "Target release must not be empty." in findings
    assert "Actors & Roles requires at least one defined actor or role." in findings
    assert "Deferred Decisions fixed upstream constraints must not be empty." in findings


def test_contract_validation_enforces_partial_scope_and_defined_role_references() -> None:
    document = canonical_document().model_copy(deep=True)
    document.scope_and_release_boundary.capabilities = (
        CanonicalScopeEntry(
            capability_id="submit-expense",
            status="PARTIAL",
            included=("Create an expense.",),
        ),
    )
    document.functional_capabilities.capabilities[0].actor_ids = (
        "employee",
        "undefined-auditor",
    )

    findings = validate_contract(document)

    assert any("PARTIAL capability 'submit-expense' excluded behavior" in f for f in findings)
    assert any("undefined actor 'undefined-auditor'" in f for f in findings)


def test_contract_validation_enforces_identifiers_deferrals_and_boundaries() -> None:
    document = canonical_document().model_copy(deep=True)
    document.actors_and_roles.actors = (
        document.actors_and_roles.actors[0],
        document.actors_and_roles.actors[0],
    )
    document.required_responsibility_boundaries.boundaries = (
        CanonicalResponsibilityBoundary(
            boundary_id="expense-intake",
            name="Expense intake",
            owns=(),
            may_depend_on_boundary_ids=("unknown-boundary",),
            supported_capability_ids=("unknown-capability",),
        ),
    )
    document.deferred_decisions_and_handoff_constraints.decisions = (
        CanonicalDeferredDecision(
            decision_id="naming",
            question="Naming?",
            reason_safe_to_defer=" ",
            downstream_constraints=(),
        ),
    )

    findings = validate_contract(document)

    assert "Actor ID 'employee' is duplicated." in findings
    assert any("owned responsibilities must not be empty" in finding for finding in findings)
    assert any(
        "undefined responsibility boundary 'unknown-boundary'" in finding
        for finding in findings
    )
    assert any("undefined capability 'unknown-capability'" in finding for finding in findings)
    assert any("reason it is safe to defer must not be empty" in finding for finding in findings)
    assert any("downstream constraints must not be empty" in finding for finding in findings)
    assert "material_open_questions" not in CanonicalPRD.model_fields


def test_audit_receives_only_current_runtime_inputs() -> None:
    authority = {"source_prd": "# Expenses", "human_decisions": ()}
    models = modeling_result()
    document = canonical_document()
    exact_markdown = render_markdown(document)
    ai = ScriptedAI(AuditPassOutput(outcome="PASS"))

    result = audit_canonical(authority, models, document, exact_markdown, ai)

    assert result == AuditResult(status="PASS")
    assert [call["operation"] for call in ai.calls] == ["audit_canonical"]
    payload = ai.calls[0]["payload"]
    assert payload["active_authority"] is authority
    assert payload["converged_modeling_result"] == models.model_dump(mode="json")
    assert payload["structured_canonical_prd"] == document.model_dump(mode="json")
    assert payload["exact_rendered_markdown_candidate"] == exact_markdown
    assert set(payload) == {
        "active_authority",
        "converged_modeling_result",
        "structured_canonical_prd",
        "exact_rendered_markdown_candidate",
    }
    assert "contract" not in json.dumps(payload)


@pytest.mark.parametrize(
    ("provider_output", "expected"),
    (
        (AuditPassOutput(outcome="PASS"), AuditResult(status="PASS")),
        (
            AuditEditorialOutput(
                outcome="EDITORIAL", findings=("Clarify wording.",)
            ),
            AuditResult(
                status="FAIL",
                findings=("Clarify wording.",),
                remediation="EDITORIAL",
            ),
        ),
        (
            AuditRemodelOutput(
                outcome="REMODEL", findings=("Rebuild ownership.",)
            ),
            AuditResult(
                status="FAIL",
                findings=("Rebuild ownership.",),
                remediation="REMODEL",
            ),
        ),
    ),
)
def test_audit_ai_outcomes_convert_to_existing_audit_result(
    provider_output: object,
    expected: AuditResult,
) -> None:
    document = canonical_document()
    result = audit_canonical(
        {},
        modeling_result(),
        document,
        render_markdown(document),
        ScriptedAI(provider_output),
    )

    assert result == expected


def test_audit_human_decision_draft_gets_canonicalization_lifecycle_fields() -> None:
    expected = Decision(
        decision_id="audit-decision",
        classification="MATERIAL",
        origin_state=WorkflowState.CANONICALIZATION,
        question="Which material policy applies?",
        context="The answer changes product behavior.",
        options=(
            DecisionOption(option_id="A", text="Policy A", consequence="Effect A"),
            DecisionOption(option_id="B", text="Policy B", consequence="Effect B"),
        ),
        recommended_option_id="A",
        recommendation_rationale="Policy A is simpler.",
    )
    draft = MaterialDecisionDraft(
        decision_id=expected.decision_id,
        question=expected.question,
        context=expected.context,
        options=expected.options,
        recommended_option_id=expected.recommended_option_id,
        recommendation_rationale=expected.recommendation_rationale,
    )
    document = canonical_document()

    result = audit_canonical(
        {},
        modeling_result(),
        document,
        render_markdown(document),
        ScriptedAI(
            AuditHumanDecisionOutput(
                outcome="HUMAN_DECISION",
                findings=("Material policy is absent.",),
                decision=draft,
            )
        ),
    )

    assert result == AuditResult(
        status="FAIL",
        findings=("Material policy is absent.",),
        remediation="HUMAN_DECISION",
        decision=expected,
    )


def test_audit_result_strictly_ties_each_outcome_to_its_allowed_payload() -> None:
    decision = Decision(
        decision_id="audit-decision",
        classification="MATERIAL",
        origin_state=WorkflowState.CANONICALIZATION,
        question="Which material policy applies?",
        context="The answer changes product behavior.",
        options=(
            DecisionOption(option_id="A", text="Policy A", consequence="Effect A"),
            DecisionOption(option_id="B", text="Policy B", consequence="Effect B"),
        ),
        recommended_option_id="A",
        recommendation_rationale="Policy A is simpler.",
    )

    assert AuditResult(status="PASS").decision is None
    assert AuditResult(
        status="FAIL", findings=("Fix wording.",), remediation="EDITORIAL"
    ).decision is None
    assert AuditResult(
        status="FAIL", findings=("Rebuild the model.",), remediation="REMODEL"
    ).decision is None
    assert AuditResult(
        status="FAIL",
        findings=("Authority lacks a material answer.",),
        remediation="HUMAN_DECISION",
        decision=decision,
    ).decision == decision

    invalid_values = (
        {"status": "PASS", "decision": decision},
        {
            "status": "FAIL",
            "findings": ("Fix wording.",),
            "remediation": "EDITORIAL",
            "decision": decision,
        },
        {"status": "FAIL", "remediation": "REMODEL"},
        {
            "status": "FAIL",
            "findings": ("Authority lacks a material answer.",),
            "remediation": "HUMAN_DECISION",
        },
        {
            "status": "FAIL",
            "findings": ("Authority lacks a material answer.",),
            "remediation": "HUMAN_DECISION",
            "decision": decision.model_copy(
                update={"origin_state": WorkflowState.MODELING}
            ),
        },
    )
    for values in invalid_values:
        with pytest.raises(ValueError):
            AuditResult.model_validate(values)


def _terminal_run(document: CanonicalPRD | None = None) -> WorkflowRun:
    return WorkflowRun(
        run_id="run-1",
        state=WorkflowState.DONE,
        convergence_result=ConvergenceResult(status="PASS"),
        canonical_candidate=document or canonical_document(),
        audit_result=AuditResult(status="PASS"),
    )


def test_final_canonical_path_exposes_only_valid_done_canonical_file(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    run = _terminal_run()
    expected = run_dir / "canonical-prd.md"
    expected.write_text(render_markdown(run.canonical_candidate), encoding="utf-8")

    with pytest.raises(ValueError, match="only for a DONE run"):
        final_canonical_path(
            run.model_copy(update={"state": WorkflowState.CANONICALIZATION}),
            run_dir,
        )

    assert final_canonical_path(run, run_dir) == expected


@pytest.mark.parametrize("artifact_state", ("missing", "mutated"))
def test_final_canonical_path_rejects_missing_or_mutated_artifact(
    tmp_path: Path, artifact_state: str
) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    run = _terminal_run()
    path = run_dir / "canonical-prd.md"
    if artifact_state == "mutated":
        path.write_text(
            render_markdown(run.canonical_candidate) + "\nChanged.\n",
            encoding="utf-8",
        )

    with pytest.raises((FileNotFoundError, ValueError)):
        final_canonical_path(run, run_dir)


@pytest.mark.parametrize("missing_gate", ("convergence", "candidate", "audit"))
def test_final_canonical_path_rejects_missing_terminal_gate(
    tmp_path: Path, missing_gate: str
) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    run = _terminal_run()
    (run_dir / "canonical-prd.md").write_text(
        render_markdown(run.canonical_candidate), encoding="utf-8"
    )
    if missing_gate == "convergence":
        run.convergence_result = None
    elif missing_gate == "candidate":
        run.canonical_candidate = None
    else:
        run.audit_result = None

    with pytest.raises(ValueError, match="DONE run"):
        final_canonical_path(run, run_dir)


def test_final_canonical_path_rejects_nonpassing_terminal_results(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    run = _terminal_run()
    (run_dir / "canonical-prd.md").write_text(
        render_markdown(run.canonical_candidate), encoding="utf-8"
    )
    run.convergence_result = ConvergenceResult(
        status="FAIL", findings=("Remodel.",), remediation="REMODEL"
    )

    with pytest.raises(ValueError, match="Convergence PASS"):
        final_canonical_path(run, run_dir)

    run.convergence_result = ConvergenceResult(status="PASS")
    run.audit_result = AuditResult(
        status="FAIL", findings=("Edit.",), remediation="EDITORIAL"
    )
    with pytest.raises(ValueError, match="Audit PASS"):
        final_canonical_path(run, run_dir)


def test_final_canonical_path_rejects_contract_invalid_candidate(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    invalid = canonical_document().model_copy(deep=True)
    invalid.product_definition.goals = ()
    run = _terminal_run(invalid)
    (run_dir / "canonical-prd.md").write_text(
        render_markdown(invalid), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="contract-invalid"):
        final_canonical_path(run, run_dir)
