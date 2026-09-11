from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from rdp_workflow.canonical import (
    audit_canonical,
    compose_canonical,
    final_canonical_path,
    render_markdown,
    validate_contract,
)
from rdp_workflow.models import (
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
    CanonicalRDP,
    CanonicalResponsibilityBoundaries,
    CanonicalResponsibilityBoundary,
    CanonicalScope,
    CanonicalScopeEntry,
    CanonicalSystemBoundaries,
    CapabilityValue,
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


def canonical_document(label: str = "candidate") -> CanonicalRDP:
    return CanonicalRDP(
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


def test_composer_receives_authority_converged_model_and_self_contained_contract() -> None:
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
    contract = json.dumps(payload["canonical_composer_contract"])
    assert "ten required sections" in contract
    assert "non-authoritative" in contract
    assert "accepted, non-superseded Human Decisions" in contract
    assert "invent product behavior" in contract
    assert "answer a Material Unknown" in contract
    assert "Previous findings are non-authoritative" in contract


def test_renderer_is_deterministic_and_emits_exactly_ten_normative_sections() -> None:
    document = canonical_document()

    first = render_markdown(document)
    second = render_markdown(document.model_copy(deep=True))

    assert first == second
    assert re.findall(r"^## \d+\. .+$", first, flags=re.MULTILINE) == [
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


def test_contract_validation_rejects_missing_sections_and_required_content() -> None:
    missing = CanonicalRDP.model_construct()
    empty_legacy = CanonicalRDP(
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
    assert "material_open_questions" not in CanonicalRDP.model_fields


def test_audit_is_fresh_and_receives_structured_document_and_exact_markdown() -> None:
    authority = {"source_prd": "# Expenses", "human_decisions": ()}
    models = modeling_result()
    document = canonical_document()
    exact_markdown = render_markdown(document)
    ai = ScriptedAI(AuditResult(status="PASS"))

    result = audit_canonical(authority, models, document, exact_markdown, ai)

    assert result == AuditResult(status="PASS")
    assert [call["operation"] for call in ai.calls] == ["audit_canonical"]
    payload = ai.calls[0]["payload"]
    assert payload["active_authority"] is authority
    assert payload["converged_modeling_result"] == models.model_dump(mode="json")
    assert payload["structured_canonical_rdp"] == document.model_dump(mode="json")
    assert payload["exact_rendered_markdown_candidate"] == exact_markdown
    contract = json.dumps(payload["canonical_audit_contract"])
    assert "fresh independent Canonical Audit" in contract
    assert "With ONLY this exact Canonical Markdown" in contract
    assert "If NO, Audit cannot PASS" in contract
    assert "never Authority" in contract


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


def test_final_canonical_path_exposes_only_done_canonical_file(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    expected = run_dir / "canonical-rdp.md"
    expected.write_text("# Canonical RDP\n", encoding="utf-8")
    (run_dir / "run.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="only for a DONE run"):
        final_canonical_path(
            WorkflowRun(run_id="run-1", state=WorkflowState.CANONICALIZATION),
            run_dir,
        )

    assert (
        final_canonical_path(
            WorkflowRun(run_id="run-1", state=WorkflowState.DONE), run_dir
        )
        == expected
    )
