from __future__ import annotations

from typing import Any

import pytest

from rdp_workflow.analysis import analyze_intake
from rdp_workflow.models import (
    Decision,
    DecisionOption,
    OptionSelection,
    WorkflowState,
)


class ScriptedAI:
    def __init__(self, result: object) -> None:
        self.result = result
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
        return self.result


def intake_decision() -> Decision:
    return Decision(
        decision_id="decision-1",
        classification="MATERIAL",
        origin_state=WorkflowState.INTAKE,
        question="May employees edit submitted expenses?",
        context="The answer changes product behavior and permissions.",
        options=(
            DecisionOption(
                option_id="A",
                text="Submitted expenses cannot be edited.",
                consequence="Submission is immutable.",
            ),
            DecisionOption(
                option_id="B",
                text="Submitted expenses may be edited before review.",
                consequence="Submission remains mutable for a limited period.",
            ),
        ),
        recommended_option_id="A",
        recommendation_rationale="Immutability gives a simpler audit trail.",
    )


def test_analyze_intake_requests_all_required_checks_against_active_authority() -> None:
    authority = {"source_prd": "# Expenses", "human_decisions": ()}
    ai = ScriptedAI(intake_decision())

    result = analyze_intake(authority, ai)

    assert result == intake_decision()
    assert len(ai.calls) == 1
    assert ai.calls[0]["operation"] == "intake"
    assert ai.calls[0]["payload"]["active_authority"] is authority
    assert ai.calls[0]["payload"]["analysis_required"] == (
        "material ambiguity",
        "material contradiction",
        "missing material information or constraints",
    )
    assert ai.calls[0]["payload"]["intake_contract"] == {
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
            "Only the Source PRD and accepted Human Decisions are Material Authority.",
            "Accepted Human Decisions take precedence over conflicting Source PRD "
            "meaning within their decided scope.",
            "AI recommendations are never Authority.",
            "Do not answer a Material Unknown.",
            "If a Material Unknown remains, return exactly one earliest consequential "
            "Human Decision.",
            "Otherwise, return no blocking Decision.",
        ),
    }
    assert ai.calls[0]["payload"]["result_rule"] == (
        "A returned Human Decision must be a MATERIAL Decision that asks one "
        "concrete question, gives context, contains 2-4 materially different "
        "options, and identifies one advisory recommendation with its rationale."
    )


def test_analyze_intake_returns_none_when_no_material_unknown_blocks_modeling() -> None:
    assert analyze_intake(
        {"source_prd": "Complete authority", "human_decisions": ()},
        ScriptedAI(None),
    ) is None


@pytest.mark.parametrize(
    "invalid_result",
    [
        Decision(
            decision_id="deferred-1",
            classification="DEFERRED",
            question="Which helper name should be used?",
            safe_to_defer_rationale="It cannot affect product behavior.",
            downstream_constraints=("Preserve established behavior.",),
        ),
        intake_decision().model_copy(update={"origin_state": WorkflowState.MODELING}),
        intake_decision().model_copy(
            update={"status": "RESOLVED", "answer": OptionSelection(option_id="A")}
        ),
    ],
)
def test_analyze_intake_rejects_any_result_other_than_one_pending_intake_decision(
    invalid_result: Decision,
) -> None:
    with pytest.raises(ValueError, match="pending intake-origin MATERIAL Decision"):
        analyze_intake({}, ScriptedAI(invalid_result))
