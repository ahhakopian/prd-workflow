from __future__ import annotations

import json

import pytest

from prd_workflow.decisions import accept_answer, active_authority
from prd_workflow.models import (
    CustomAnswer,
    Decision,
    DecisionOption,
    HumanAnswer,
    OptionSelection,
    OptionWithClarification,
    WorkflowRun,
    WorkflowState,
)


def material_decision(
    decision_id: str,
    *,
    status: str = "PENDING",
    answer: HumanAnswer | None = None,
    supersedes: str | None = None,
) -> Decision:
    return Decision(
        decision_id=decision_id,
        classification="MATERIAL",
        origin_state=WorkflowState.INTAKE,
        question="Which expense edit policy applies?",
        context="The policy changes observable behavior.",
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
        status=status,
        answer=answer,
        supersedes_decision_id=supersedes,
    )


def waiting_run(*decisions: Decision) -> WorkflowRun:
    return WorkflowRun(
        run_id="run-1",
        state=WorkflowState.WAITING_HUMAN,
        pending_decision_origin=WorkflowState.INTAKE,
        decisions=decisions,
    )


def test_active_authority_contains_source_and_only_active_human_answer_content() -> None:
    superseded = material_decision(
        "decision-1",
        status="SUPERSEDED",
        answer=OptionSelection(option_id="A"),
    )
    active = material_decision(
        "decision-2",
        status="RESOLVED",
        answer=OptionSelection(option_id="B"),
        supersedes="decision-1",
    )
    pending = material_decision("decision-3")
    authority = active_authority(
        WorkflowRun(run_id="run-1", decisions=(superseded, active, pending)),
        "# Source\nExact text.  \n",
    )

    assert authority["source_prd"] == "# Source\nExact text.  \n"
    assert authority["human_decisions"] == (
        {
            "decision_id": "decision-2",
            "question": "Which expense edit policy applies?",
            "context": "The policy changes observable behavior.",
            "answer": {
                "kind": "option_selection",
                "option_id": "B",
                "option_text": "Edits are allowed before review.",
            },
        },
    )
    serialized = json.dumps(authority)
    assert "recommend" not in serialized
    assert "No edits after submission" not in serialized


def test_active_authority_preserves_option_and_clarification_as_separate_equal_parts() -> None:
    clarification = "  Only until a manager acts.\nReset the timestamp.  "
    decision = material_decision(
        "decision-1",
        status="RESOLVED",
        answer=OptionWithClarification(option_id="B", clarification=clarification),
    )

    answer = active_authority(
        WorkflowRun(run_id="run-1", decisions=(decision,)), "source"
    )["human_decisions"][0]["answer"]

    assert answer["option_text"] == "Edits are allowed before review."
    assert answer["clarification"] == clarification


def test_active_authority_preserves_custom_answer_verbatim_without_option_mapping() -> None:
    text = "  Require both employee and manager approval.\nKeep exactly.  "
    decision = material_decision(
        "decision-1", status="RESOLVED", answer=CustomAnswer(text=text)
    )

    answer = active_authority(
        WorkflowRun(run_id="run-1", decisions=(decision,)), "source"
    )["human_decisions"][0]["answer"]

    assert answer == {"kind": "custom", "text": text}


@pytest.mark.parametrize(
    "answer",
    [
        OptionSelection(option_id="A"),
        OptionWithClarification(
            option_id="B", clarification="  Preserve this clarification.  "
        ),
        CustomAnswer(text="  Preserve this custom answer.  "),
    ],
)
def test_accept_answer_structurally_accepts_all_three_answer_forms(
    answer: HumanAnswer,
) -> None:
    run = waiting_run(material_decision("decision-1"))

    returned = accept_answer(run, "decision-1", answer)

    assert returned is run
    assert run.decisions[0].status == "RESOLVED"
    assert run.decisions[0].answer == answer
    assert run.pending_decision_origin is None


def test_accept_answer_requires_waiting_state_and_current_decision_id() -> None:
    intake_run = WorkflowRun(
        run_id="run-1",
        state=WorkflowState.INTAKE,
        pending_decision_origin=WorkflowState.INTAKE,
        decisions=(material_decision("decision-1"),),
    )
    with pytest.raises(ValueError, match="only while WAITING_HUMAN"):
        accept_answer(intake_run, "decision-1", OptionSelection(option_id="A"))

    run = waiting_run(material_decision("decision-1"))
    with pytest.raises(ValueError, match="current pending Decision"):
        accept_answer(run, "another-id", OptionSelection(option_id="A"))

    assert run.decisions[0].status == "PENDING"


def test_accept_answer_rejects_unknown_option_and_empty_required_text() -> None:
    run = waiting_run(material_decision("decision-1"))
    with pytest.raises(ValueError, match="selected option does not exist"):
        accept_answer(run, "decision-1", OptionSelection(option_id="unknown"))

    empty = CustomAnswer.model_construct(text="  ")
    with pytest.raises(ValueError, match="empty or whitespace"):
        accept_answer(run, "decision-1", empty)

    assert run.decisions[0].status == "PENDING"


def test_accept_answer_applies_one_direct_supersession_only() -> None:
    first = material_decision(
        "decision-1", status="RESOLVED", answer=OptionSelection(option_id="A")
    )
    unrelated = material_decision(
        "decision-2", status="RESOLVED", answer=OptionSelection(option_id="A")
    )
    replacement = material_decision("decision-3", supersedes="decision-1")
    run = waiting_run(first, unrelated, replacement)

    accept_answer(run, "decision-3", OptionSelection(option_id="B"))

    assert [decision.status for decision in run.decisions] == [
        "SUPERSEDED",
        "RESOLVED",
        "RESOLVED",
    ]
    assert run.decisions[2].supersedes_decision_id == "decision-1"


def test_accept_answer_rejects_nonexistent_supersession_target() -> None:
    run = waiting_run(material_decision("decision-2", supersedes="missing"))

    with pytest.raises(ValueError, match="existing resolved Decision"):
        accept_answer(run, "decision-2", OptionSelection(option_id="A"))

    assert run.decisions[0].status == "PENDING"
