"""AI-backed analysis operations implemented through the narrow executor boundary."""

from __future__ import annotations

from pydantic import TypeAdapter

from prd_workflow.ai import (
    ARCHITECTURE_RESULT_TYPE,
    CAPABILITIES_RESULT_TYPE,
    CONVERGENCE_RESULT_TYPE,
    DOMAIN_RESULT_TYPE,
    INTAKE_RESULT_TYPE,
    AIExecutor,
)
from prd_workflow.ai_contracts import (
    ArchitectureOutput,
    CapabilitiesOutput,
    ConvergenceHumanDecisionOutput,
    ConvergencePassOutput,
    ConvergenceRemodelOutput,
    DomainOutput,
    deferred_decision_from_draft,
    material_decision_from_draft,
)
from prd_workflow.models import (
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

    result = TypeAdapter(INTAKE_RESULT_TYPE).validate_python(
        ai.invoke(
            operation="intake",
            payload={"active_authority": authority},
            result_type=INTAKE_RESULT_TYPE,
        )
    )
    if result is None:
        return None
    return material_decision_from_draft(result, WorkflowState.INTAKE)


def derive_domain(
    authority: dict[str, object],
    prior_findings: tuple[str, ...],
    ai: AIExecutor,
) -> tuple[ProductContext, DomainView]:
    """Derive product context and business/domain semantics from Active Authority."""

    result = DomainOutput.model_validate(
        ai.invoke(
            operation="derive_domain",
            payload={
                "active_authority": authority,
                "previous_remodel_findings": prior_findings,
            },
            result_type=DOMAIN_RESULT_TYPE,
        )
    )
    return result.product_context, result.domain


def derive_capabilities(
    authority: dict[str, object],
    product_context: ProductContext,
    domain: DomainView,
    prior_findings: tuple[str, ...],
    ai: AIExecutor,
) -> tuple[CapabilityValue, ...]:
    """Derive Functional Capabilities from Authority and the fresh Domain view."""

    result = CapabilitiesOutput.model_validate(
        ai.invoke(
            operation="derive_capabilities",
            payload={
                "active_authority": authority,
                "domain": {
                    "product_context": product_context.model_dump(mode="json"),
                    "view": domain.model_dump(mode="json"),
                },
                "previous_remodel_findings": prior_findings,
            },
            result_type=CAPABILITIES_RESULT_TYPE,
        )
    )
    return result.capabilities


def derive_architecture(
    authority: dict[str, object],
    product_context: ProductContext,
    domain: DomainView,
    capabilities: tuple[CapabilityValue, ...],
    prior_findings: tuple[str, ...],
    ai: AIExecutor,
) -> tuple[ArchitectureView, tuple[Decision, ...]]:
    """Derive high-level architecture and any demonstrably safe deferrals."""

    result = ArchitectureOutput.model_validate(
        ai.invoke(
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
            },
            result_type=ARCHITECTURE_RESULT_TYPE,
        )
    )
    deferred = tuple(
        deferred_decision_from_draft(draft) for draft in result.deferred_decisions
    )
    return result.architecture, deferred


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

    result = TypeAdapter(CONVERGENCE_RESULT_TYPE).validate_python(
        ai.invoke(
            operation="review_convergence",
            payload={
                "active_authority": authority,
                "complete_fresh_modeling_result": models.model_dump(mode="json"),
            },
            result_type=CONVERGENCE_RESULT_TYPE,
        )
    )
    if isinstance(result, ConvergencePassOutput):
        return ConvergenceResult(status="PASS")
    if isinstance(result, ConvergenceRemodelOutput):
        return ConvergenceResult(
            status="FAIL",
            findings=result.findings,
            remediation="REMODEL",
        )
    if isinstance(result, ConvergenceHumanDecisionOutput):
        return ConvergenceResult(
            status="FAIL",
            findings=result.findings,
            remediation="HUMAN_DECISION",
            decision=material_decision_from_draft(
                result.decision, WorkflowState.MODELING
            ),
        )
    raise TypeError(f"unsupported Convergence output: {type(result)!r}")
