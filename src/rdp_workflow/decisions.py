"""Human Decision acceptance and the computed Active Authority projection."""

from __future__ import annotations

from pydantic import TypeAdapter

from rdp_workflow.models import (
    CustomAnswer,
    Decision,
    HumanAnswer,
    OptionSelection,
    OptionWithClarification,
    WorkflowRun,
    WorkflowState,
)


_ANSWER_ADAPTER = TypeAdapter(HumanAnswer)


def active_authority(run: WorkflowRun, source_text: str) -> dict[str, object]:
    """Project current authority without persisting another authority subsystem."""

    superseded_ids = {
        decision.supersedes_decision_id
        for decision in run.decisions
        if decision.classification == "MATERIAL"
        and decision.status == "RESOLVED"
        and decision.answer is not None
        and decision.supersedes_decision_id is not None
    }
    human_decisions = tuple(
        _authority_entry(decision)
        for decision in run.decisions
        if decision.classification == "MATERIAL"
        and decision.status == "RESOLVED"
        and decision.answer is not None
        and decision.decision_id not in superseded_ids
    )
    return {
        "source_prd": source_text,
        "human_decisions": human_decisions,
    }


def accept_answer(
    run: WorkflowRun,
    decision_id: str,
    answer: HumanAnswer,
) -> WorkflowRun:
    """Structurally accept an answer to the run's sole current Decision."""

    if run.state is not WorkflowState.WAITING_HUMAN:
        raise ValueError("Human Answers are accepted only while WAITING_HUMAN")

    pending = tuple(
        decision
        for decision in run.decisions
        if decision.classification == "MATERIAL" and decision.status == "PENDING"
    )
    if len(pending) != 1:
        raise ValueError("WAITING_HUMAN requires exactly one pending MATERIAL Decision")
    current = pending[0]
    if current.decision_id != decision_id:
        raise ValueError("decision_id does not identify the current pending Decision")
    if run.pending_decision_origin is not current.origin_state:
        raise ValueError("pending Decision origin is inconsistent with the current Decision")

    validated_answer = _ANSWER_ADAPTER.validate_python(answer.model_dump())
    if isinstance(validated_answer, (OptionSelection, OptionWithClarification)):
        option_ids = {option.option_id for option in current.options}
        if validated_answer.option_id not in option_ids:
            raise ValueError("selected option does not exist on the pending Decision")

    superseded_id = current.supersedes_decision_id
    superseded: Decision | None = None
    if superseded_id is not None:
        superseded = next(
            (
                decision
                for decision in run.decisions
                if decision.decision_id == superseded_id
                and decision.classification == "MATERIAL"
                and decision.status == "RESOLVED"
                and decision.answer is not None
            ),
            None,
        )
        if superseded is None:
            raise ValueError(
                "supersedes_decision_id must identify an existing resolved Decision"
            )

    updated: list[Decision] = []
    for decision in run.decisions:
        if decision is current:
            updated.append(
                Decision.model_validate(
                    {
                        **decision.model_dump(),
                        "status": "RESOLVED",
                        "answer": validated_answer.model_dump(),
                    }
                )
            )
        elif decision is superseded:
            updated.append(
                Decision.model_validate(
                    {**decision.model_dump(), "status": "SUPERSEDED"}
                )
            )
        else:
            updated.append(decision)

    run.decisions = tuple(updated)
    run.pending_decision_origin = None
    return run


def _authority_entry(decision: Decision) -> dict[str, object]:
    answer = decision.answer
    if isinstance(answer, OptionSelection):
        authority_answer: dict[str, object] = {
            "kind": answer.kind,
            "option_id": answer.option_id,
            "option_text": _option_text(decision, answer.option_id),
        }
    elif isinstance(answer, OptionWithClarification):
        authority_answer = {
            "kind": answer.kind,
            "option_id": answer.option_id,
            "option_text": _option_text(decision, answer.option_id),
            "clarification": answer.clarification,
        }
    elif isinstance(answer, CustomAnswer):
        authority_answer = {"kind": answer.kind, "text": answer.text}
    else:  # pragma: no cover - guarded by Decision validation and caller filtering
        raise ValueError("resolved Decision has no valid HumanAnswer")

    return {
        "decision_id": decision.decision_id,
        "question": decision.question,
        "context": decision.context,
        "answer": authority_answer,
    }


def _option_text(decision: Decision, option_id: str) -> str:
    return next(option.text for option in decision.options if option.option_id == option_id)
