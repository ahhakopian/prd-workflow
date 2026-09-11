"""AI-backed analysis operations implemented through the narrow executor boundary."""

from __future__ import annotations

from pydantic import TypeAdapter

from rdp_workflow.ai import AIExecutor
from rdp_workflow.models import (
    ArchitectureView,
    CapabilityValue,
    ConvergenceResult,
    Decision,
    DomainView,
    ModelingResult,
    ProductContext,
    WorkflowState,
)


def analyze_intake(
    authority: dict[str, object],
    ai: AIExecutor,
) -> Decision | None:
    """Return the one intake-blocking Material Decision, or no blocker."""

    result = ai.invoke(
        operation="intake",
        payload={
            "active_authority": authority,
            "analysis_required": (
                "material ambiguity",
                "material contradiction",
                "missing material information or constraints",
            ),
            "intake_contract": {
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
                    "Only the Source PRD and accepted Human Decisions are "
                    "Material Authority.",
                    "Accepted Human Decisions take precedence over conflicting "
                    "Source PRD meaning within their decided scope.",
                    "AI recommendations are never Authority.",
                    "Do not answer a Material Unknown.",
                    "If a Material Unknown remains, return exactly one earliest "
                    "consequential Human Decision.",
                    "Otherwise, return no blocking Decision.",
                ),
            },
            "result_rule": (
                "A returned Human Decision must be a MATERIAL Decision that asks "
                "one concrete question, gives context, contains 2-4 materially "
                "different options, and identifies one advisory recommendation "
                "with its rationale."
            ),
        },
        result_type=Decision | None,
    )
    if result is None:
        return None

    decision = Decision.model_validate(result.model_dump())
    if (
        decision.classification != "MATERIAL"
        or decision.status != "PENDING"
        or decision.origin_state is not WorkflowState.INTAKE
    ):
        raise ValueError("intake must return one pending intake-origin MATERIAL Decision")
    return decision


def derive_domain(
    authority: dict[str, object],
    prior_findings: tuple[str, ...],
    ai: AIExecutor,
) -> tuple[ProductContext, DomainView]:
    """Derive product context and business/domain semantics from Active Authority."""

    result_type = tuple[ProductContext, DomainView]
    result = ai.invoke(
        operation="derive_domain",
        payload={
            "active_authority": authority,
            "previous_remodel_findings": prior_findings,
            "domain_contract": {
                "derive_only": (
                    "product problem, intended outcome, target users, goals, and "
                    "explicit non-goals when established",
                    "downstream-significant domain concepts and relationships",
                    "canonical business terminology where ambiguity matters",
                    "domain invariants that follow from the supplied authority",
                ),
                "authority_rules": (
                    "Only the supplied Source PRD and accepted, non-superseded "
                    "Human Decisions are Material Authority.",
                    "Within their decided scope, supplied Human Decisions outrank "
                    "conflicting Source PRD meaning.",
                    "Previous remodel findings are corrective feedback, not Authority.",
                    "AI recommendations and all derived artifacts are not Authority.",
                ),
                "required_limits": (
                    "Use business language and include only semantics that can affect "
                    "downstream product or system interpretation.",
                    "Do not invent technical entities or select implementation "
                    "technologies.",
                    "Do not add product behavior, scope, roles, ownership, domain "
                    "meaning, architecture, security, or material quality requirements "
                    "that do not follow unambiguously from Authority.",
                    "Do not resolve a material unknown. Different reasonable answers "
                    "are material when they could change product behavior, release "
                    "scope, actors or permissions, domain meaning, ownership, system "
                    "or responsibility boundaries, major dependency direction, "
                    "high-level architecture, security or privacy, externally visible "
                    "failure behavior, or a material non-functional requirement.",
                    "Do not manufacture content merely to make the result look complete.",
                ),
            },
        },
        result_type=result_type,
    )
    return TypeAdapter(result_type).validate_python(result)


def derive_capabilities(
    authority: dict[str, object],
    product_context: ProductContext,
    domain: DomainView,
    prior_findings: tuple[str, ...],
    ai: AIExecutor,
) -> tuple[CapabilityValue, ...]:
    """Derive Functional Capabilities from Authority and the fresh Domain view."""

    result_type = tuple[CapabilityValue, ...]
    result = ai.invoke(
        operation="derive_capabilities",
        payload={
            "active_authority": authority,
            "domain": {
                "product_context": product_context.model_dump(mode="json"),
                "view": domain.model_dump(mode="json"),
            },
            "previous_remodel_findings": prior_findings,
            "capability_contract": {
                "meaning": (
                    "A Functional Capability is a meaningful user or business ability: "
                    "what the product must do, not an implementation component, task, "
                    "or downstream specification Feature."
                ),
                "capture_when_applicable": (
                    "capability name and purpose",
                    "target-release status IN, PARTIAL, OUT, or FUTURE",
                    "actors",
                    "required behavior",
                    "business rules",
                    "material capability dependencies",
                    "externally meaningful failure or rejection conditions",
                ),
                "authority_rules": (
                    "Only the supplied Source PRD and accepted, non-superseded "
                    "Human Decisions are Material Authority.",
                    "Within their decided scope, supplied Human Decisions outrank "
                    "conflicting Source PRD meaning.",
                    "The fresh Domain view and previous remodel findings are derived "
                    "inputs, not Authority.",
                    "AI recommendations are not Authority.",
                ),
                "required_limits": (
                    "Derive behavior only when it follows unambiguously from Active "
                    "Authority and is consistent with the supplied fresh Domain view.",
                    "Do not invent behavior, rules, actors, permissions, release scope, "
                    "dependencies, or failure handling to make the model complete.",
                    "Do not perform downstream Feature decomposition or describe "
                    "frameworks, databases, APIs, modules, or implementation tasks.",
                    "Do not resolve a material unknown or establish new Material "
                    "Authority. A question is material when different answers could "
                    "change behavior, release scope, roles or permissions, business "
                    "rules, domain meaning, ownership, boundaries, dependency direction, "
                    "architecture, security or privacy, visible failure behavior, or a "
                    "material non-functional requirement.",
                ),
            },
        },
        result_type=result_type,
    )
    return TypeAdapter(result_type).validate_python(result)


def derive_architecture(
    authority: dict[str, object],
    product_context: ProductContext,
    domain: DomainView,
    capabilities: tuple[CapabilityValue, ...],
    prior_findings: tuple[str, ...],
    ai: AIExecutor,
) -> tuple[ArchitectureView, tuple[Decision, ...]]:
    """Derive high-level architecture and any demonstrably safe deferrals."""

    result_type = tuple[ArchitectureView, tuple[Decision, ...]]
    result = ai.invoke(
        operation="derive_architecture",
        payload={
            "active_authority": authority,
            "domain": {
                "product_context": product_context.model_dump(mode="json"),
                "view": domain.model_dump(mode="json"),
            },
            "functional_capabilities": tuple(
                capability.model_dump(mode="json") for capability in capabilities
            ),
            "previous_remodel_findings": prior_findings,
            "architecture_contract": {
                "derive_only": (
                    "major responsibility areas and their responsibilities or material "
                    "non-responsibilities",
                    "inside/outside system boundaries and external responsibilities",
                    "data, decision, and responsibility ownership when established",
                    "major interactions and material dependency directions",
                    "required responsibility boundaries",
                    "high-level architectural constraints and invariants",
                    "material cross-cutting and non-functional requirements",
                ),
                "authority_rules": (
                    "Only the supplied Source PRD and accepted, non-superseded "
                    "Human Decisions are Material Authority.",
                    "Within their decided scope, supplied Human Decisions outrank "
                    "conflicting Source PRD meaning.",
                    "Domain, Capabilities, previous findings, architecture, and "
                    "deferral classifications are derived artifacts, not Authority.",
                    "AI recommendations are not Authority.",
                ),
                "required_limits": (
                    "Support the supplied Capabilities while preserving Domain meaning "
                    "and all authoritative role, scope, ownership, security, boundary, "
                    "and material quality constraints.",
                    "Distinguish displaying, using, or transmitting policy or data from "
                    "owning that policy, data, decision, or responsibility.",
                    "Do not silently resolve ownership, responsibility, system-boundary, "
                    "permission, security, dependency-direction, or architecture ambiguity.",
                    "Do not select frameworks, databases, cloud services, deployment "
                    "technologies, API styles, or implementation structures unless "
                    "explicitly required by Authority.",
                    "Do not add implementation detail for completeness, resolve a "
                    "material unknown, or establish new Material Authority.",
                ),
                "deferred_decision_rule": (
                    "Return only DEFERRED Decisions. A question is safe to defer only "
                    "when every reasonable allowed downstream choice preserves product "
                    "behavior, release scope, actors and permissions, domain semantics, "
                    "responsibility and feature boundaries, data/decision/responsibility "
                    "ownership, system boundaries, major dependency direction, high-level "
                    "architecture invariants, security and privacy, externally visible "
                    "failure behavior, and material non-functional meaning. It must be "
                    "independently decidable downstream without invalidating Authority. "
                    "If any condition is false or unknown, it is a Material Unknown and "
                    "must not be returned as DEFERRED. Every DEFERRED Decision must state "
                    "its question, why it is safe, and constraints downstream must preserve."
                ),
            },
        },
        result_type=result_type,
    )
    architecture, deferred = TypeAdapter(result_type).validate_python(result)
    if any(decision.classification != "DEFERRED" for decision in deferred):
        raise ValueError("architecture derivation may return only DEFERRED Decisions")
    return architecture, deferred


def derive_models(
    authority: dict[str, object],
    prior_findings: tuple[str, ...],
    ai: AIExecutor,
) -> ModelingResult:
    """Rebuild the complete ordered model set in one MODELING execution."""

    product_context, domain = derive_domain(authority, prior_findings, ai)
    capabilities = derive_capabilities(
        authority, product_context, domain, prior_findings, ai
    )
    architecture, deferred_decisions = derive_architecture(
        authority,
        product_context,
        domain,
        capabilities,
        prior_findings,
        ai,
    )
    return ModelingResult(
        product_context=product_context,
        domain=domain,
        capabilities=capabilities,
        architecture=architecture,
        deferred_decisions=deferred_decisions,
    )


def review_convergence(
    authority: dict[str, object],
    models: ModelingResult,
    ai: AIExecutor,
) -> ConvergenceResult:
    """Run one fresh review of the complete, freshly derived model set."""

    result = ai.invoke(
        operation="review_convergence",
        payload={
            "active_authority": authority,
            "complete_fresh_modeling_result": models.model_dump(mode="json"),
            "convergence_contract": {
                "authority_rules": (
                    "Only the supplied Source PRD and accepted, non-superseded "
                    "Human Decisions are Material Authority.",
                    "Within their decided scope, supplied Human Decisions outrank "
                    "conflicting Source PRD meaning.",
                    "Domain, Capabilities, Architecture, Deferred Decisions, findings, "
                    "and other model outputs are derived and never create Authority.",
                    "AI recommendations are advisory and are not Authority.",
                    "Never select or fabricate a Human Answer; only an explicit later "
                    "human answer can create new Material Authority.",
                ),
                "review_at_least": (
                    "unresolved Material Unknowns",
                    "contradictions with Active Authority",
                    "unsupported assumptions or invented material meaning",
                    "Domain-to-Capability inconsistency",
                    "Capability-to-Architecture inconsistency",
                    "actor or permission conflicts",
                    "target-release scope conflicts or missing scope",
                    "data, decision, or responsibility ownership conflicts",
                    "system or responsibility-boundary conflicts",
                    "major dependency-direction conflicts",
                    "architecture drift or unsupported implementation constraints",
                    "unsafe Deferred Decisions",
                    "material authoritative requirements lost from the model",
                    "material security, privacy, failure-behavior, or non-functional gaps",
                ),
                "materiality_rule": (
                    "An unresolved question is MATERIAL when different reasonable "
                    "answers could change product behavior, release scope, actors or "
                    "permissions, business rules, domain meaning, ownership, system or "
                    "responsibility boundaries, major dependency direction, high-level "
                    "architecture, security or privacy, externally visible failure "
                    "behavior, material non-functional meaning, or another established "
                    "requirement. When uncertain, treat it as MATERIAL."
                ),
                "safe_deferral_rule": (
                    "A question is DEFERRED only when every reasonable allowed downstream "
                    "choice preserves product behavior, release scope, actors and "
                    "permissions, domain semantics, responsibility and feature boundaries, "
                    "data/decision/responsibility ownership, system boundaries, major "
                    "dependency direction, high-level architecture invariants, security "
                    "and privacy, externally visible failure behavior, and material "
                    "non-functional meaning; is independently decidable downstream; and "
                    "cannot invalidate established Authority. Otherwise it is MATERIAL."
                ),
                "outcomes": (
                    "Return PASS only when no unresolved Material Decision or material "
                    "contradiction remains; all views are mutually consistent and complete "
                    "for material scope, actors, permissions, domain meaning, ownership, "
                    "boundaries, architecture, cross-cutting requirements, and release "
                    "scope; and every remaining open question is safely DEFERRED. PASS has "
                    "no remediation and no Decision.",
                    "Return FAIL with REMODEL when Active Authority already contains enough "
                    "information and the derived model is wrong, incomplete, contradictory, "
                    "or overreaching. Include corrective findings and no Decision.",
                    "Return FAIL with HUMAN_DECISION only when required material truth is "
                    "not unambiguously present in Active Authority. Never ask the human to "
                    "repair a modeling error that Authority can correct.",
                ),
                "human_decision_rule": (
                    "FAIL/HUMAN_DECISION must contain exactly one MATERIAL Decision with "
                    "origin_state MODELING, status PENDING, one concrete non-compound "
                    "question, sufficient context, 2-4 plausible and materially distinct "
                    "options with their consequences, exactly one advisory recommended "
                    "option, and a concise recommendation rationale. It must contain no "
                    "Human Answer and no deferral fields. The recommendation is advisory "
                    "and must not be treated as selected Authority."
                ),
            },
        },
        result_type=ConvergenceResult,
    )
    return ConvergenceResult.model_validate(result.model_dump())
