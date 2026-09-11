"""Canonical composition, deterministic checks, audit, and final exposure."""

from __future__ import annotations

from pathlib import Path

from pydantic import TypeAdapter

from rdp_workflow.ai import AIExecutor
from rdp_workflow.models import (
    AuditResult,
    CanonicalActor,
    CanonicalCapability,
    CanonicalDeferredDecision,
    CanonicalRDP,
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


def compose_canonical(
    authority: dict[str, object],
    models: ModelingResult,
    editorial_findings: tuple[str, ...],
    ai: AIExecutor,
) -> CanonicalRDP:
    """Constrain one AI invocation to non-authoritative Canonical composition."""

    result = ai.invoke(
        operation="compose_canonical",
        payload={
            "active_authority": authority,
            "converged_modeling_result": models.model_dump(mode="json"),
            "previous_editorial_or_validation_findings": editorial_findings,
            "canonical_composer_contract": {
                "purpose": (
                    "Compose one structured, self-contained Canonical RDP from the "
                    "supplied Active Authority and Convergence-PASS ModelingResult. "
                    "Composition is derived and non-authoritative."
                ),
                "required_sections_in_order": tuple(
                    title for _, title in _SECTION_FIELDS_AND_TITLES
                ),
                "authority_rules": (
                    "Only the Source PRD and accepted, non-superseded Human Decisions "
                    "inside Active Authority are Material Authority.",
                    "The ModelingResult, previous findings, this composition, and all "
                    "AI recommendations are derived and are not Authority.",
                    "Preserve every accepted non-superseded Human Decision exactly in "
                    "meaning, including selected-option text plus any Human clarification.",
                ),
                "allowed_composition": (
                    "consolidate already-established semantics",
                    "organize content into the ten required sections",
                    "normalize terminology without changing material meaning",
                    "remove workflow history, recommendations, findings, and rejected or "
                    "superseded alternatives",
                    "express already-established semantics clearly",
                ),
                "prohibited_composition": (
                    "create Material Authority or promote an AI recommendation to Authority",
                    "invent product behavior or target-release scope",
                    "invent actors, roles, permissions, domain semantics, or business rules",
                    "invent data, decision, responsibility ownership, system boundaries, "
                    "or required responsibility boundaries",
                    "invent architecture constraints, security requirements, privacy "
                    "requirements, or material non-functional requirements",
                    "answer a Material Unknown, choose between unresolved alternatives, "
                    "or reinterpret a Human Decision",
                    "add implementation technologies or downstream Feature decisions "
                    "unless explicitly required by Active Authority",
                ),
                "structural_rules": (
                    "Every material capability has a stable capability_id and exactly one "
                    "IN, PARTIAL, OUT, or FUTURE scope entry for the target release.",
                    "PARTIAL scope states both included and excluded behavior.",
                    "Every actor referenced by a target user or capability is defined by "
                    "stable actor_id with sufficient role and permission semantics.",
                    "Responsibility boundaries use stable IDs, ownership statements, "
                    "dependency constraints, and supported capability IDs where applicable.",
                    "Every Deferred Decision states what is undecided, why every acceptable "
                    "choice is safe downstream, and constraints those choices must preserve.",
                    "Do not represent any unresolved Material question as finalized content "
                    "or disguise it as a Deferred Decision.",
                    "Each section remains present and explicitly states when no additional "
                    "constraints apply.",
                ),
                "corrective_findings_rule": (
                    "Previous findings are non-authoritative editorial input. Correct only "
                    "representation using established meaning; never treat a finding as a "
                    "new requirement or authoritative answer."
                ),
            },
        },
        result_type=CanonicalRDP,
    )
    return TypeAdapter(CanonicalRDP).validate_python(result)


def render_markdown(document: CanonicalRDP) -> str:
    """Render the exact downstream artifact with no reasoning or AI operation."""

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

    lines = ["# Canonical RDP", "", "## 1. Product Definition", "", product.summary]
    _labeled_text(lines, "Problem", product.problem)
    _labeled_items(lines, "Target actor IDs", product.target_actor_ids)
    _labeled_text(lines, "Intended outcome", product.intended_outcome)
    _labeled_items(lines, "Goals", product.goals)
    _labeled_items(lines, "Explicit non-goals", product.non_goals)

    lines.extend(["", "## 2. Scope & Release Boundary", "", scope.summary])
    _labeled_text(lines, "Target release", scope.target_release)
    for item in scope.capabilities:
        lines.extend(
            [
                "",
                f"### Capability `{item.capability_id}` — {item.status}",
            ]
        )
        _labeled_items(lines, "Included", item.included)
        _labeled_items(lines, "Excluded", item.excluded)

    lines.extend(["", "## 3. Actors & Roles", "", actors.summary])
    for actor in actors.actors:
        lines.extend(["", f"### `{actor.actor_id}` — {actor.name} ({actor.kind})"])
        _labeled_text(lines, "Purpose or responsibility", actor.purpose)
        _labeled_items(lines, "May do", actor.may_do)
        _labeled_items(lines, "Must do", actor.must_do)
        _labeled_items(lines, "Must not do", actor.must_not_do)
        _labeled_items(lines, "Permission boundaries", actor.permission_boundaries)

    lines.extend(["", "## 4. Domain Model", "", domain.summary])
    _labeled_items(lines, "Material concepts", domain.concepts)
    _labeled_items(lines, "Material relationships", domain.relationships)
    _labeled_items(lines, "Domain invariants", domain.invariants)
    _labeled_items(lines, "Canonical terminology", domain.terminology)

    lines.extend(["", "## 5. Functional Capabilities", "", capabilities.summary])
    for capability in capabilities.capabilities:
        lines.extend(
            ["", f"### `{capability.capability_id}` — {capability.name}", "", capability.purpose]
        )
        _labeled_items(lines, "Applicable actor IDs", capability.actor_ids)
        _labeled_items(lines, "Required behavior", capability.required_behavior)
        _labeled_items(lines, "Material business rules", capability.business_rules)
        _labeled_items(
            lines,
            "Capability dependency IDs",
            capability.dependency_capability_ids,
        )
        _labeled_items(lines, "Failure or rejection conditions", capability.failure_conditions)

    lines.extend(
        ["", "## 6. System Boundaries & Ownership", "", boundaries.summary]
    )
    _labeled_items(lines, "Inside the system", boundaries.inside_system)
    _labeled_items(lines, "Outside the system", boundaries.outside_system)
    _labeled_items(lines, "External dependencies", boundaries.external_dependencies)
    _labeled_items(lines, "Data ownership", boundaries.data_ownership)
    _labeled_items(lines, "Decision ownership", boundaries.decision_ownership)
    _labeled_items(
        lines, "Responsibility ownership", boundaries.responsibility_ownership
    )
    _labeled_items(lines, "Authoritative systems of record", boundaries.systems_of_record)

    lines.extend(["", "## 7. High-Level Architecture", "", architecture.summary])
    _labeled_items(lines, "Responsibility areas", architecture.responsibility_areas)
    _labeled_items(lines, "Explicit non-responsibilities", architecture.non_responsibilities)
    _labeled_items(lines, "Major interactions", architecture.interactions)
    _labeled_items(lines, "Architectural constraints", architecture.constraints)
    _labeled_items(lines, "Architectural invariants", architecture.invariants)
    _labeled_items(lines, "Material dependency directions", architecture.dependency_directions)

    lines.extend(
        [
            "",
            "## 8. Cross-Cutting & Non-Functional Requirements",
            "",
            cross_cutting.summary,
        ]
    )
    _labeled_items(lines, "Material requirements", cross_cutting.requirements)

    lines.extend(
        [
            "",
            "## 9. Required Responsibility Boundaries",
            "",
            responsibility_boundaries.summary,
        ]
    )
    for boundary in responsibility_boundaries.boundaries:
        lines.extend(["", f"### `{boundary.boundary_id}` — {boundary.name}"])
        _labeled_items(lines, "Owns", boundary.owns)
        _labeled_items(lines, "Does not own", boundary.does_not_own)
        _labeled_items(
            lines, "May depend on boundary IDs", boundary.may_depend_on_boundary_ids
        )
        _labeled_items(
            lines,
            "Must not depend on boundary IDs",
            boundary.must_not_depend_on_boundary_ids,
        )
        _labeled_items(
            lines, "Supported capability IDs", boundary.supported_capability_ids
        )

    lines.extend(
        [
            "",
            "## 10. Deferred Decisions & Handoff Constraints",
            "",
            deferred.summary,
        ]
    )
    for decision in deferred.decisions:
        lines.extend(["", f"### `{decision.decision_id}`", "", decision.question])
        _labeled_text(lines, "Why safe to defer", decision.reason_safe_to_defer)
        _labeled_items(
            lines, "Constraints downstream must preserve", decision.downstream_constraints
        )
    _labeled_items(
        lines,
        "Fixed upstream constraints that must not be reopened",
        deferred.fixed_upstream_constraints,
    )
    return "\n".join(lines) + "\n"


def validate_contract(document: CanonicalRDP) -> tuple[str, ...]:
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
    document: CanonicalRDP,
    rendered_markdown: str,
    ai: AIExecutor,
) -> AuditResult:
    """Run one fresh, independent semantic audit of the exact rendered candidate."""

    result = ai.invoke(
        operation="audit_canonical",
        payload={
            "active_authority": authority,
            "converged_modeling_result": models.model_dump(mode="json"),
            "structured_canonical_rdp": document.model_dump(mode="json"),
            "exact_rendered_markdown_candidate": rendered_markdown,
            "canonical_audit_contract": {
                "independence": (
                    "Perform a fresh independent Canonical Audit. Do not treat Composer "
                    "output, confidence, or wording as an audit result. Audit findings are "
                    "derived and never Authority."
                ),
                "authority_rules": (
                    "The Source PRD and accepted, non-superseded Human Decisions in "
                    "Active Authority are the only Material Authority.",
                    "Preserve every accepted Human Decision, including the complete "
                    "selected option plus Human clarification, without reinterpretation.",
                    "Never provide an authoritative answer to a Material Unknown and "
                    "never promote an AI recommendation, model, composition, or finding "
                    "to Authority.",
                ),
                "review_at_least": (
                    "preservation of Source PRD Authority",
                    "preservation of every accepted non-superseded Human Decision",
                    "absence of invented material semantics or unresolved Material questions",
                    "internal consistency",
                    "release-scope sufficiency for IN, PARTIAL, OUT, and FUTURE capabilities",
                    "actors, roles, permissions, and domain-semantic sufficiency",
                    "capability behavior, business-rule, dependency, and failure sufficiency",
                    "data, decision, and responsibility ownership plus system boundaries",
                    "high-level architecture constraints, invariants, and dependency direction",
                    "cross-cutting, security, privacy, and material non-functional requirements",
                    "safety and constraints of every Deferred Decision",
                    "Feature decomposition and Required Responsibility Boundary sufficiency",
                    "self-containment and downstream sufficiency of the exact Markdown",
                ),
                "central_question": (
                    "With ONLY this exact Canonical Markdown and no intermediate artifacts, "
                    "can SpecKit correctly determine current scope, actors/roles, capabilities, "
                    "system boundaries, architectural invariants, and cross-feature constraints "
                    "without making a new Material Decision? If NO, Audit cannot PASS."
                ),
                "allowed_outcomes": {
                    "PASS": (
                        "The exact Markdown preserves Authority, is consistent, self-contained, "
                        "and downstream-sufficient; return no remediation and no Decision."
                    ),
                    "FAIL_EDITORIAL": (
                        "Use EDITORIAL only for a non-material representation or completeness "
                        "defect. Return findings and no Decision."
                    ),
                    "FAIL_REMODEL": (
                        "Use REMODEL when Active Authority contains enough truth but the complete "
                        "model is wrong or incomplete, or Canonical exposes a model defect. "
                        "Return findings and no Decision."
                    ),
                    "FAIL_HUMAN_DECISION": (
                        "Use HUMAN_DECISION only when material truth is genuinely absent or "
                        "ambiguous in Active Authority. Return findings and exactly one pending "
                        "CANONICALIZATION-origin MATERIAL Decision with one question, context, "
                        "2-4 materially distinct options, one advisory recommendation, and its "
                        "rationale. Do not answer the question."
                    ),
                },
            },
        },
        result_type=AuditResult,
    )
    return TypeAdapter(AuditResult).validate_python(result)


def final_canonical_path(run: WorkflowRun, run_dir: Path) -> Path:
    """Expose the sole downstream artifact, and only for explicit DONE state."""

    if run.state is not WorkflowState.DONE:
        raise ValueError("final Canonical RDP is available only for a DONE run")
    path = Path(run_dir) / "canonical-rdp.md"
    if not path.is_file():
        raise FileNotFoundError(f"DONE run is missing canonical-rdp.md: {path}")
    return path


def _labeled_text(lines: list[str], label: str, value: str) -> None:
    if value:
        lines.extend(["", f"**{label}:** {value}"])


def _labeled_items(lines: list[str], label: str, values: tuple[str, ...]) -> None:
    if values:
        lines.extend(["", f"**{label}:**"])
        lines.extend(f"- {value}" for value in values)


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
