from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rdp_workflow.ai_contracts import MaterialDecisionDraft
from rdp_workflow.models import (
    CustomAnswer,
    Decision,
    DecisionOption,
    HumanAnswer,
    OptionSelection,
    OptionWithClarification,
    WorkflowState,
)
from rdp_workflow.storage import FileStorage
from rdp_workflow.workflow import WorkflowService


class ScriptedAI:
    def __init__(self, *results: MaterialDecisionDraft | None) -> None:
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


def intake_decision() -> Decision:
    return Decision(
        decision_id="decision-1",
        classification="MATERIAL",
        origin_state=WorkflowState.INTAKE,
        question="May employees edit submitted expenses?",
        context="The answer changes product behavior and permissions.",
        options=(
            DecisionOption(
                option_id="A", text="No edits after submission.", consequence="Immutable."
            ),
            DecisionOption(
                option_id="B",
                text="Edits are allowed before review.",
                consequence="Mutable before review.",
            ),
        ),
        recommended_option_id="A",
        recommendation_rationale="This gives the simplest audit trail.",
    )


def intake_decision_draft() -> MaterialDecisionDraft:
    decision = intake_decision()
    return MaterialDecisionDraft(
        decision_id=decision.decision_id,
        question=decision.question,
        context=decision.context,
        options=decision.options,
        recommended_option_id=decision.recommended_option_id,
        recommendation_rationale=decision.recommendation_rationale,
    )


def service_at(tmp_path: Path, ai: ScriptedAI) -> WorkflowService:
    return WorkflowService(FileStorage(tmp_path / ".rdp"), ai)


def source_at(tmp_path: Path) -> Path:
    source = tmp_path / "source.md"
    source.write_text("# Expense product\n", encoding="utf-8")
    return source


def test_workflow_intake_without_blocker_transitions_to_modeling_and_persists(
    tmp_path: Path,
) -> None:
    ai = ScriptedAI(None)
    service = service_at(tmp_path, ai)
    started = service.start(source_at(tmp_path))

    advanced = service.advance(started.run_id)

    assert advanced.state is WorkflowState.MODELING
    assert service.status(started.run_id).state is WorkflowState.MODELING
    assert len(ai.calls) == 1


def test_workflow_intake_with_material_unknown_pauses_with_one_persisted_decision(
    tmp_path: Path,
) -> None:
    ai = ScriptedAI(intake_decision_draft())
    service = service_at(tmp_path, ai)
    started = service.start(source_at(tmp_path))

    advanced = service.advance(started.run_id)
    restarted = WorkflowService(FileStorage(tmp_path / ".rdp"), ai).status(
        started.run_id
    )

    assert advanced.state is WorkflowState.WAITING_HUMAN
    assert restarted.state is WorkflowState.WAITING_HUMAN
    assert restarted.pending_decision_origin is WorkflowState.INTAKE
    assert len(restarted.decisions) == 1
    assert restarted.decisions[0].status == "PENDING"


@pytest.mark.parametrize(
    "answer",
    [
        OptionSelection(option_id="A"),
        OptionWithClarification(
            option_id="B", clarification="  Only before review.\nKeep exact.  "
        ),
        CustomAnswer(text="  Require manager approval.\nKeep exact.  "),
    ],
)
def test_workflow_accepts_and_persists_each_human_answer_form(
    tmp_path: Path,
    answer: HumanAnswer,
) -> None:
    ai = ScriptedAI(intake_decision_draft())
    service = service_at(tmp_path, ai)
    started = service.start(source_at(tmp_path))
    service.advance(started.run_id)

    answered = service.answer(started.run_id, "decision-1", answer)
    restored = service.status(started.run_id)

    assert answered.state is WorkflowState.INTAKE
    assert restored.state is WorkflowState.INTAKE
    assert restored.decisions[0].answer == answer
    assert type(restored.decisions[0].answer) is type(answer)
    assert len(ai.calls) == 1


def test_workflow_resume_rechecks_intake_with_answer_in_active_authority(
    tmp_path: Path,
) -> None:
    clarification = "  Only before the manager records review.  "
    ai = ScriptedAI(intake_decision_draft(), None)
    service = service_at(tmp_path, ai)
    started = service.start(source_at(tmp_path))
    service.advance(started.run_id)
    service.answer(
        started.run_id,
        "decision-1",
        OptionWithClarification(option_id="B", clarification=clarification),
    )

    resumed = WorkflowService(FileStorage(tmp_path / ".rdp"), ai).advance(
        started.run_id
    )

    authority = ai.calls[1]["payload"]["active_authority"]
    assert resumed.state is WorkflowState.MODELING
    assert authority["human_decisions"][0]["answer"] == {
        "kind": "option_with_clarification",
        "option_id": "B",
        "option_text": "Edits are allowed before review.",
        "clarification": clarification,
    }
    assert "recommended_option_id" not in str(authority)


def test_workflow_cannot_advance_while_waiting_for_human_answer(
    tmp_path: Path,
) -> None:
    ai = ScriptedAI(intake_decision_draft())
    service = service_at(tmp_path, ai)
    started = service.start(source_at(tmp_path))
    service.advance(started.run_id)

    with pytest.raises(ValueError, match="waiting for the current Human Decision"):
        service.advance(started.run_id)

    assert service.status(started.run_id).state is WorkflowState.WAITING_HUMAN
    assert len(ai.calls) == 1


def test_workflow_ai_failure_does_not_change_persisted_state(
    tmp_path: Path,
) -> None:
    class FailingAI:
        def invoke(self, **_: object) -> Any:
            raise RuntimeError("invalid structured output")

    storage = FileStorage(tmp_path / ".rdp")
    service = WorkflowService(storage, FailingAI())
    started = service.start(source_at(tmp_path))

    with pytest.raises(RuntimeError, match="invalid structured output"):
        service.advance(started.run_id)

    assert service.status(started.run_id).state is WorkflowState.INTAKE


def test_workflow_intake_advance_does_not_eagerly_execute_modeling(
    tmp_path: Path,
) -> None:
    service = service_at(tmp_path, ScriptedAI(None))
    started = service.start(source_at(tmp_path))
    advanced = service.advance(started.run_id)

    assert advanced.state is WorkflowState.MODELING
    assert service.status(started.run_id).state is WorkflowState.MODELING
    assert [call["operation"] for call in service.ai.calls] == ["intake"]
