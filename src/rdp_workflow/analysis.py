"""AI-backed analysis operations implemented through the narrow executor boundary."""

from __future__ import annotations

from rdp_workflow.ai import AIExecutor
from rdp_workflow.models import Decision, WorkflowState


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
