"""Canonical composition, deterministic checks, audit, and final exposure."""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

from pydantic import TypeAdapter

from prd_workflow.ai import (
    CANONICAL_AUDIT_RESULT_TYPE,
    CANONICAL_RESULT_TYPE,
    AIExecutor,
)
from prd_workflow.ai_contracts import (
    AuditEditorialOutput,
    AuditHumanDecisionOutput,
    AuditPassOutput,
    AuditRemodelOutput,
    material_decision_from_draft,
)
from prd_workflow.models import (
    AuditResult,
    CanonicalActor,
    CanonicalCapability,
    CanonicalDeferredDecision,
    CanonicalPRD,
    CanonicalResponsibilityBoundary,
    CanonicalScopeEntry,
    ModelingResult,
    WorkflowRun,
    WorkflowState,
)


_SECTION_FIELDS_AND_TITLES = (
    ("product_definition", "Product Definition"),
    ("scope_and_release_boundary", "Scope & Release Boundary"),
    ("actors_and_roles", "Actors & Roles"),
    ("domain_model", "Domain Model"),
    ("functional_capabilities", "Functional Capabilities"),
    ("system_boundaries_and_ownership", "System Boundaries & Ownership"),
    ("high_level_architecture", "High-Level Architecture"),
    (
        "cross_cutting_and_non_functional_requirements",
        "Cross-Cutting & Non-Functional Requirements",
    ),
    ("required_responsibility_boundaries", "Required Responsibility Boundaries"),
    (
        "deferred_decisions_and_handoff_constraints",
        "Deferred Decisions & Handoff Constraints",
    ),
)

_TEMPLATE_PLACEHOLDERS = (
    "{{PRODUCT_SUMMARY}}",
    "{{PRODUCT_PROBLEM}}",
    "{{PRODUCT_TARGET_ACTORS}}",
    "{{PRODUCT_INTENDED_OUTCOME}}",
    "{{PRODUCT_GOALS}}",
    "{{PRODUCT_NON_GOALS}}",
    "{{SCOPE_SUMMARY}}",
    "{{TARGET_RELEASE}}",
    "{{SCOPE_CAPABILITY_BLOCKS}}",
    "{{ACTORS_SUMMARY}}",
    "{{ACTOR_BLOCKS}}",
    "{{DOMAIN_SUMMARY}}",
    "{{DOMAIN_CONCEPTS}}",
    "{{DOMAIN_RELATIONSHIPS}}",
    "{{DOMAIN_INVARIANTS}}",
    "{{DOMAIN_TERMINOLOGY}}",
    "{{CAPABILITIES_SUMMARY}}",
    "{{CAPABILITY_BLOCKS}}",
    "{{BOUNDARIES_SUMMARY}}",
    "{{INSIDE_SYSTEM}}",
    "{{OUTSIDE_SYSTEM}}",
    "{{EXTERNAL_DEPENDENCIES}}",
    "{{DATA_OWNERSHIP}}",
    "{{DECISION_OWNERSHIP}}",
    "{{RESPONSIBILITY_OWNERSHIP}}",
    "{{SYSTEMS_OF_RECORD}}",
    "{{ARCHITECTURE_SUMMARY}}",
    "{{ARCHITECTURE_RESPONSIBILITY_AREAS}}",
    "{{ARCHITECTURE_NON_RESPONSIBILITIES}}",
    "{{ARCHITECTURE_INTERACTIONS}}",
    "{{ARCHITECTURE_CONSTRAINTS}}",
    "{{ARCHITECTURE_INVARIANTS}}",
    "{{ARCHITECTURE_DEPENDENCY_DIRECTIONS}}",
    "{{CROSS_CUTTING_SUMMARY}}",
    "{{CROSS_CUTTING_REQUIREMENTS}}",
    "{{RESPONSIBILITY_BOUNDARIES_SUMMARY}}",
    "{{RESPONSIBILITY_BOUNDARY_BLOCKS}}",
    "{{DEFERRED_SUMMARY}}",
    "{{DEFERRED_DECISION_BLOCKS}}",
    "{{FIXED_UPSTREAM_CONSTRAINTS}}",
)
_PLACEHOLDER_PATTERN = re.compile(r"\{\{[^{}\n]+\}\}")


def compose_canonical(
    authority: dict[str, object],
    models: ModelingResult,
    editorial_findings: tuple[str, ...],
    ai: AIExecutor,
) -> CanonicalPRD:
    """Constrain one AI invocation to non-authoritative Canonical composition."""

    result = ai.invoke(
        operation="compose_canonical",
        payload={
            "active_authority": authority,
            "converged_modeling_result": models.model_dump(mode="json"),
            "previous_editorial_or_validation_findings": editorial_findings,
        },
        result_type=CANONICAL_RESULT_TYPE,
    )
    return TypeAdapter(CANONICAL_RESULT_TYPE).validate_python(result)


def render_markdown(document: CanonicalPRD) -> str:
    """Render the exact downstream artifact with no reasoning or AI operation."""

    values = _render_template_values(document)
    template = load_canonical_template()
    found = _PLACEHOLDER_PATTERN.findall(template)
    expected = set(_TEMPLATE_PLACEHOLDERS)
    missing = [
        placeholder for placeholder in _TEMPLATE_PLACEHOLDERS if placeholder not in found
    ]
    duplicated = [
        placeholder
        for placeholder in _TEMPLATE_PLACEHOLDERS
        if found.count(placeholder) > 1
    ]
    unknown = sorted(set(found) - expected)
    if missing or duplicated or unknown:
        raise ValueError(
            "invalid Canonical template placeholders: "
            f"missing={missing}, duplicated={duplicated}, unknown={unknown}"
        )

    rendered = template
    for placeholder, value in values.items():
        rendered = rendered.replace(placeholder, value)
    if _PLACEHOLDER_PATTERN.search(rendered) or "{{" in rendered or "}}" in rendered:
        raise ValueError("Canonical template contains an unreplaced placeholder")
    return rendered


def load_canonical_template() -> str:
    """Load the fixed Canonical Markdown layout from the installed package."""

    return resources.files("prd_workflow").joinpath(
        "templates", "canonical-prd.md"
    ).read_text(encoding="utf-8")


def _render_template_values(document: CanonicalPRD) -> dict[str, str]:
    product = document.product_definition
    scope = document.scope_and_release_boundary
    actors = document.actors_and_roles
    domain = document.domain_model
    capabilities = document.functional_capabilities
    boundaries = document.system_boundaries_and_ownership
    architecture = document.high_level_architecture
    cross_cutting = document.cross_cutting_and_non_functional_requirements
    responsibility_boundaries = document.required_responsibility_boundaries
    deferred = document.deferred_decisions_and_handoff_constraints

    return {
        "{{PRODUCT_SUMMARY}}": product.summary,
        "{{PRODUCT_PROBLEM}}": product.problem,
        "{{PRODUCT_TARGET_ACTORS}}": _markdown_list(product.target_actor_ids),
        "{{PRODUCT_INTENDED_OUTCOME}}": product.intended_outcome,
        "{{PRODUCT_GOALS}}": _markdown_list(product.goals),
        "{{PRODUCT_NON_GOALS}}": _markdown_list(product.non_goals),
        "{{SCOPE_SUMMARY}}": scope.summary,
        "{{TARGET_RELEASE}}": scope.target_release,
        "{{SCOPE_CAPABILITY_BLOCKS}}": _render_scope_capability_blocks(
            scope.capabilities
        ),
        "{{ACTORS_SUMMARY}}": actors.summary,
        "{{ACTOR_BLOCKS}}": _render_actor_blocks(actors.actors),
        "{{DOMAIN_SUMMARY}}": domain.summary,
        "{{DOMAIN_CONCEPTS}}": _markdown_list(domain.concepts),
        "{{DOMAIN_RELATIONSHIPS}}": _markdown_list(domain.relationships),
        "{{DOMAIN_INVARIANTS}}": _markdown_list(domain.invariants),
        "{{DOMAIN_TERMINOLOGY}}": _markdown_list(domain.terminology),
        "{{CAPABILITIES_SUMMARY}}": capabilities.summary,
        "{{CAPABILITY_BLOCKS}}": _render_capability_blocks(
            capabilities.capabilities
        ),
        "{{BOUNDARIES_SUMMARY}}": boundaries.summary,
        "{{INSIDE_SYSTEM}}": _markdown_list(boundaries.inside_system),
        "{{OUTSIDE_SYSTEM}}": _markdown_list(boundaries.outside_system),
        "{{EXTERNAL_DEPENDENCIES}}": _markdown_list(
            boundaries.external_dependencies
        ),
        "{{DATA_OWNERSHIP}}": _markdown_list(boundaries.data_ownership),
        "{{DECISION_OWNERSHIP}}": _markdown_list(boundaries.decision_ownership),
        "{{RESPONSIBILITY_OWNERSHIP}}": _markdown_list(
            boundaries.responsibility_ownership
        ),
        "{{SYSTEMS_OF_RECORD}}": _markdown_list(boundaries.systems_of_record),
        "{{ARCHITECTURE_SUMMARY}}": architecture.summary,
        "{{ARCHITECTURE_RESPONSIBILITY_AREAS}}": _markdown_list(
            architecture.responsibility_areas
        ),
        "{{ARCHITECTURE_NON_RESPONSIBILITIES}}": _markdown_list(
            architecture.non_responsibilities
        ),
        "{{ARCHITECTURE_INTERACTIONS}}": _markdown_list(architecture.interactions),
        "{{ARCHITECTURE_CONSTRAINTS}}": _markdown_list(architecture.constraints),
        "{{ARCHITECTURE_INVARIANTS}}": _markdown_list(architecture.invariants),
        "{{ARCHITECTURE_DEPENDENCY_DIRECTIONS}}": _markdown_list(
            architecture.dependency_directions
        ),
        "{{CROSS_CUTTING_SUMMARY}}": cross_cutting.summary,
        "{{CROSS_CUTTING_REQUIREMENTS}}": _markdown_list(
            cross_cutting.requirements
        ),
        "{{RESPONSIBILITY_BOUNDARIES_SUMMARY}}": responsibility_boundaries.summary,
        "{{RESPONSIBILITY_BOUNDARY_BLOCKS}}": _render_responsibility_boundary_blocks(
            responsibility_boundaries.boundaries
        ),
        "{{DEFERRED_SUMMARY}}": deferred.summary,
        "{{DEFERRED_DECISION_BLOCKS}}": _render_deferred_decision_blocks(
            deferred.decisions
        ),
        "{{FIXED_UPSTREAM_CONSTRAINTS}}": _markdown_list(
            deferred.fixed_upstream_constraints
        ),
    }


def _markdown_list(values: tuple[str, ...]) -> str:
    if not values:
        return "- None established."
    return "\n".join(f"- {value}" for value in values)


def _render_scope_capability_blocks(
    capabilities: tuple[CanonicalScopeEntry, ...],
) -> str:
    blocks = []
    for item in capabilities:
        blocks.append(
            "\n".join(
                (
                    f"### Capability `{item.capability_id}` — {item.status}",
                    "",
                    "**Included:**",
                    _markdown_list(item.included),
                    "",
                    "**Excluded:**",
                    _markdown_list(item.excluded),
                )
            )
        )
    return "\n\n".join(blocks) if blocks else "- None established."


def _render_actor_blocks(actors: tuple[CanonicalActor, ...]) -> str:
    blocks = []
    for actor in actors:
        blocks.append(
            "\n".join(
                (
                    f"### `{actor.actor_id}` — {actor.name} ({actor.kind})",
                    "",
                    f"**Purpose or responsibility:** {actor.purpose}",
                    "",
                    "**May do:**",
                    _markdown_list(actor.may_do),
                    "",
                    "**Must do:**",
                    _markdown_list(actor.must_do),
                    "",
                    "**Must not do:**",
                    _markdown_list(actor.must_not_do),
                    "",
                    "**Permission boundaries:**",
                    _markdown_list(actor.permission_boundaries),
                )
            )
        )
    return "\n\n".join(blocks) if blocks else "- None established."


def _render_capability_blocks(
    capabilities: tuple[CanonicalCapability, ...],
) -> str:
    blocks = []
    for capability in capabilities:
        blocks.append(
            "\n".join(
                (
                    f"### `{capability.capability_id}` — {capability.name}",
                    "",
                    capability.purpose,
                    "",
                    "**Applicable actor IDs:**",
                    _markdown_list(capability.actor_ids),
                    "",
                    "**Required behavior:**",
                    _markdown_list(capability.required_behavior),
                    "",
                    "**Material business rules:**",
                    _markdown_list(capability.business_rules),
                    "",
                    "**Capability dependency IDs:**",
                    _markdown_list(capability.dependency_capability_ids),
                    "",
                    "**Failure or rejection conditions:**",
                    _markdown_list(capability.failure_conditions),
                )
            )
        )
    return "\n\n".join(blocks) if blocks else "- None established."


def _render_responsibility_boundary_blocks(
    boundaries: tuple[CanonicalResponsibilityBoundary, ...],
) -> str:
    blocks = []
    for boundary in boundaries:
        blocks.append(
            "\n".join(
                (
                    f"### `{boundary.boundary_id}` — {boundary.name}",
                    "",
                    "**Owns:**",
                    _markdown_list(boundary.owns),
                    "",
                    "**Does not own:**",
                    _markdown_list(boundary.does_not_own),
                    "",
                    "**May depend on boundary IDs:**",
                    _markdown_list(boundary.may_depend_on_boundary_ids),
                    "",
                    "**Must not depend on boundary IDs:**",
                    _markdown_list(boundary.must_not_depend_on_boundary_ids),
                    "",
                    "**Supported capability IDs:**",
                    _markdown_list(boundary.supported_capability_ids),
                )
            )
        )
    return "\n\n".join(blocks) if blocks else "- None established."


def _render_deferred_decision_blocks(
    decisions: tuple[CanonicalDeferredDecision, ...],
) -> str:
    blocks = []
    for decision in decisions:
        blocks.append(
            "\n".join(
                (
                    f"### `{decision.decision_id}`",
                    "",
                    decision.question,
                    "",
                    f"**Why safe to defer:** {decision.reason_safe_to_defer}",
                    "",
                    "**Constraints downstream must preserve:**",
                    _markdown_list(decision.downstream_constraints),
                )
            )
        )
    return "\n\n".join(blocks) if blocks else "- None established."


def validate_contract(document: CanonicalPRD) -> tuple[str, ...]:
    """Return deterministic structural contract findings, without semantic inference."""

    findings: list[str] = []
    for field_name, title in _SECTION_FIELDS_AND_TITLES:
        section = getattr(document, field_name, None)
        if section is None:
            findings.append(f"Missing required section: {title}.")
        elif _is_blank(getattr(section, "summary", "")):
            findings.append(f"{title} requires non-empty summary content.")

    product = getattr(document, "product_definition", None)
    scope = getattr(document, "scope_and_release_boundary", None)
    actors_section = getattr(document, "actors_and_roles", None)
    capabilities_section = getattr(document, "functional_capabilities", None)
    boundaries_section = getattr(document, "system_boundaries_and_ownership", None)
    architecture = getattr(document, "high_level_architecture", None)
    responsibility_section = getattr(
        document, "required_responsibility_boundaries", None
    )
    deferred_section = getattr(
        document, "deferred_decisions_and_handoff_constraints", None
    )

    if product is not None:
        _require_text(findings, product.problem, "Product Definition problem")
        _require_items(
            findings, product.target_actor_ids, "Product Definition target users"
        )
        _require_text(
            findings, product.intended_outcome, "Product Definition intended outcome"
        )
        _require_items(findings, product.goals, "Product Definition goals")
        _require_items(
            findings, product.non_goals, "Product Definition explicit non-goals"
        )

    actors = tuple(getattr(actors_section, "actors", ()))
    actor_ids = _validate_identified_values(findings, actors, "actor_id", "Actor")
    if not actors:
        findings.append("Actors & Roles requires at least one defined actor or role.")
    for actor in actors:
        _validate_actor(findings, actor)

    capabilities = tuple(getattr(capabilities_section, "capabilities", ()))
    capability_ids = _validate_identified_values(
        findings, capabilities, "capability_id", "Capability"
    )
    for capability in capabilities:
        _validate_capability(findings, capability, actor_ids, capability_ids)

    if product is not None:
        _validate_references(
            findings,
            product.target_actor_ids,
            actor_ids,
            "Product Definition target actor",
            "actor",
        )

    scope_entries = tuple(getattr(scope, "capabilities", ()))
    scope_ids = _validate_identified_values(
        findings, scope_entries, "capability_id", "Scope capability"
    )
    if scope is not None:
        _require_text(findings, scope.target_release, "Target release")
        for entry in scope_entries:
            _validate_scope_entry(findings, entry)
    for missing_id in sorted(capability_ids - scope_ids):
        findings.append(
            f"Capability {missing_id!r} has no target-release scope status."
        )
    for unknown_id in sorted(scope_ids - capability_ids):
        findings.append(
            f"Scope references undefined capability {unknown_id!r}."
        )

    if boundaries_section is not None:
        _require_items(
            findings,
            boundaries_section.inside_system,
            "System Boundaries responsibilities inside the system",
        )
        _require_items(
            findings,
            boundaries_section.outside_system,
            "System Boundaries responsibilities outside the system",
        )
        _validate_all_present_items(
            findings,
            boundaries_section,
            (
                "external_dependencies",
                "data_ownership",
                "decision_ownership",
                "responsibility_ownership",
                "systems_of_record",
            ),
            "System Boundaries & Ownership",
        )

    if architecture is not None:
        _validate_all_present_items(
            findings,
            architecture,
            (
                "responsibility_areas",
                "non_responsibilities",
                "interactions",
                "constraints",
                "invariants",
                "dependency_directions",
            ),
            "High-Level Architecture",
        )

    responsibility_boundaries = tuple(
        getattr(responsibility_section, "boundaries", ())
    )
    boundary_ids = _validate_identified_values(
        findings,
        responsibility_boundaries,
        "boundary_id",
        "Responsibility boundary",
    )
    claimed_ownership: dict[str, str] = {}
    for boundary in responsibility_boundaries:
        _validate_responsibility_boundary(
            findings, boundary, boundary_ids, capability_ids, claimed_ownership
        )

    if deferred_section is not None:
        _require_items(
            findings,
            deferred_section.fixed_upstream_constraints,
            "Deferred Decisions fixed upstream constraints",
        )
        deferred_decisions = tuple(deferred_section.decisions)
        _validate_identified_values(
            findings, deferred_decisions, "decision_id", "Deferred Decision"
        )
        for decision in deferred_decisions:
            _validate_deferred_decision(findings, decision)

    domain = getattr(document, "domain_model", None)
    if domain is not None:
        _validate_all_present_items(
            findings,
            domain,
            ("concepts", "relationships", "invariants", "terminology"),
            "Domain Model",
        )
    cross_cutting = getattr(
        document, "cross_cutting_and_non_functional_requirements", None
    )
    if cross_cutting is not None:
        _validate_all_present_items(
            findings,
            cross_cutting,
            ("requirements",),
            "Cross-Cutting & Non-Functional Requirements",
        )

    return tuple(findings)


def audit_canonical(
    authority: dict[str, object],
    models: ModelingResult,
    document: CanonicalPRD,
    rendered_markdown: str,
    ai: AIExecutor,
) -> AuditResult:
    """Run one fresh, independent semantic audit of the exact rendered candidate."""

    result = TypeAdapter(CANONICAL_AUDIT_RESULT_TYPE).validate_python(
        ai.invoke(
            operation="audit_canonical",
            payload={
                "active_authority": authority,
                "converged_modeling_result": models.model_dump(mode="json"),
                "structured_canonical_prd": document.model_dump(mode="json"),
                "exact_rendered_markdown_candidate": rendered_markdown,
            },
            result_type=CANONICAL_AUDIT_RESULT_TYPE,
        )
    )
    if isinstance(result, AuditPassOutput):
        return AuditResult(status="PASS")
    if isinstance(result, AuditEditorialOutput):
        return AuditResult(
            status="FAIL", findings=result.findings, remediation="EDITORIAL"
        )
    if isinstance(result, AuditRemodelOutput):
        return AuditResult(
            status="FAIL", findings=result.findings, remediation="REMODEL"
        )
    if isinstance(result, AuditHumanDecisionOutput):
        return AuditResult(
            status="FAIL",
            findings=result.findings,
            remediation="HUMAN_DECISION",
            decision=material_decision_from_draft(
                result.decision, WorkflowState.CANONICALIZATION
            ),
        )
    raise TypeError(f"unsupported Audit output: {type(result)!r}")


def final_canonical_path(run: WorkflowRun, run_dir: Path) -> Path:
    """Expose the sole downstream artifact only after all terminal gates hold."""

    if run.state is not WorkflowState.DONE:
        raise ValueError("final Canonical PRD is available only for a DONE run")
    if run.convergence_result is None or run.convergence_result.status != "PASS":
        raise ValueError("DONE run requires Convergence PASS")
    if run.canonical_candidate is None:
        raise ValueError("DONE run is missing its Canonical PRD candidate")
    if run.audit_result is None or run.audit_result.status != "PASS":
        raise ValueError("DONE run requires Canonical Audit PASS")
    findings = validate_contract(run.canonical_candidate)
    if findings:
        raise ValueError(
            "DONE run has a contract-invalid Canonical PRD candidate: "
            + "; ".join(findings)
        )
    path = Path(run_dir) / "canonical-prd.md"
    if not path.is_file():
        raise FileNotFoundError(f"DONE run is missing canonical-prd.md: {path}")
    expected = render_markdown(run.canonical_candidate).encode("utf-8")
    if path.read_bytes() != expected:
        raise ValueError(
            "DONE run canonical-prd.md does not match the deterministic rendering "
            "of its persisted Canonical PRD candidate"
        )
    return path


def _is_blank(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def _require_text(findings: list[str], value: object, label: str) -> None:
    if _is_blank(value):
        findings.append(f"{label} must not be empty.")


def _require_items(
    findings: list[str], values: tuple[str, ...], label: str
) -> None:
    if not values:
        findings.append(f"{label} must not be empty.")
    elif any(_is_blank(value) for value in values):
        findings.append(f"{label} contains empty content.")


def _validate_all_present_items(
    findings: list[str], value: object, fields: tuple[str, ...], label: str
) -> None:
    for field in fields:
        items = getattr(value, field, ())
        if any(_is_blank(item) for item in items):
            findings.append(f"{label} {field.replace('_', ' ')} contains empty content.")


def _validate_identified_values(
    findings: list[str],
    values: tuple[object, ...],
    id_field: str,
    label: str,
) -> set[str]:
    identifiers: list[str] = []
    for value in values:
        identifier = getattr(value, id_field, "")
        if _is_blank(identifier):
            findings.append(f"{label} requires a stable non-empty {id_field}.")
        else:
            identifiers.append(identifier)
    duplicates = sorted(
        identifier for identifier in set(identifiers) if identifiers.count(identifier) > 1
    )
    for identifier in duplicates:
        findings.append(f"{label} ID {identifier!r} is duplicated.")
    return set(identifiers)


def _validate_references(
    findings: list[str],
    references: tuple[str, ...],
    defined: set[str],
    label: str,
    target_label: str,
) -> None:
    for reference in references:
        if _is_blank(reference):
            findings.append(f"{label} reference must not be empty.")
        elif reference not in defined:
            findings.append(f"{label} references undefined {target_label} {reference!r}.")


def _validate_actor(findings: list[str], actor: CanonicalActor) -> None:
    _require_text(findings, actor.name, f"Actor {actor.actor_id!r} name")
    _require_text(findings, actor.purpose, f"Actor {actor.actor_id!r} purpose")
    _require_items(findings, actor.may_do, f"Actor {actor.actor_id!r} may-do behavior")
    _validate_all_present_items(
        findings,
        actor,
        ("must_do", "must_not_do", "permission_boundaries"),
        f"Actor {actor.actor_id!r}",
    )


def _validate_capability(
    findings: list[str],
    capability: CanonicalCapability,
    actor_ids: set[str],
    capability_ids: set[str],
) -> None:
    label = f"Capability {capability.capability_id!r}"
    _require_text(findings, capability.name, f"{label} name")
    _require_text(findings, capability.purpose, f"{label} purpose")
    _require_items(findings, capability.actor_ids, f"{label} applicable actors")
    _require_items(findings, capability.required_behavior, f"{label} required behavior")
    _validate_all_present_items(
        findings,
        capability,
        ("business_rules", "failure_conditions"),
        label,
    )
    _validate_references(
        findings, capability.actor_ids, actor_ids, f"{label} actor", "actor"
    )
    _validate_references(
        findings,
        capability.dependency_capability_ids,
        capability_ids,
        f"{label} dependency",
        "capability",
    )


def _validate_scope_entry(findings: list[str], entry: CanonicalScopeEntry) -> None:
    allowed = {"IN", "PARTIAL", "OUT", "FUTURE"}
    if entry.status not in allowed:
        findings.append(
            f"Scope for capability {entry.capability_id!r} has invalid status "
            f"{entry.status!r}."
        )
    if entry.status == "PARTIAL":
        _require_items(
            findings,
            entry.included,
            f"PARTIAL capability {entry.capability_id!r} included behavior",
        )
        _require_items(
            findings,
            entry.excluded,
            f"PARTIAL capability {entry.capability_id!r} excluded behavior",
        )
    else:
        _validate_all_present_items(
            findings, entry, ("included", "excluded"), f"Scope {entry.capability_id!r}"
        )


def _validate_responsibility_boundary(
    findings: list[str],
    boundary: CanonicalResponsibilityBoundary,
    boundary_ids: set[str],
    capability_ids: set[str],
    claimed_ownership: dict[str, str],
) -> None:
    label = f"Responsibility boundary {boundary.boundary_id!r}"
    _require_text(findings, boundary.name, f"{label} name")
    _require_items(findings, boundary.owns, f"{label} owned responsibilities")
    _validate_all_present_items(findings, boundary, ("does_not_own",), label)
    for owned in boundary.owns:
        if _is_blank(owned):
            continue
        previous = claimed_ownership.get(owned)
        if previous is not None and previous != boundary.boundary_id:
            findings.append(
                f"Responsibility {owned!r} is claimed by both {previous!r} and "
                f"{boundary.boundary_id!r}."
            )
        else:
            claimed_ownership[owned] = boundary.boundary_id
    _validate_references(
        findings,
        boundary.may_depend_on_boundary_ids,
        boundary_ids,
        f"{label} allowed dependency",
        "responsibility boundary",
    )
    _validate_references(
        findings,
        boundary.must_not_depend_on_boundary_ids,
        boundary_ids,
        f"{label} forbidden dependency",
        "responsibility boundary",
    )
    overlap = sorted(
        set(boundary.may_depend_on_boundary_ids)
        & set(boundary.must_not_depend_on_boundary_ids)
    )
    for dependency_id in overlap:
        findings.append(
            f"{label} both allows and forbids dependency on {dependency_id!r}."
        )
    _validate_references(
        findings,
        boundary.supported_capability_ids,
        capability_ids,
        f"{label} supported capability",
        "capability",
    )


def _validate_deferred_decision(
    findings: list[str], decision: CanonicalDeferredDecision
) -> None:
    label = f"Deferred Decision {decision.decision_id!r}"
    _require_text(findings, decision.question, f"{label} question")
    _require_text(
        findings,
        decision.reason_safe_to_defer,
        f"{label} reason it is safe to defer",
    )
    _require_items(
        findings,
        decision.downstream_constraints,
        f"{label} downstream constraints",
    )
