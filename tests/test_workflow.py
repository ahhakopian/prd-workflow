from __future__ import annotations

import pytest

from prd_workflow.models import WorkflowRun, WorkflowState
from prd_workflow.workflow import IllegalTransitionError, transition


EXPECTED_TRANSITIONS = {
    WorkflowState.INTAKE: {
        WorkflowState.MODELING,
        WorkflowState.WAITING_HUMAN,
        WorkflowState.BLOCKED,
    },
    WorkflowState.WAITING_HUMAN: {
        WorkflowState.INTAKE,
        WorkflowState.MODELING,
        WorkflowState.BLOCKED,
    },
    WorkflowState.MODELING: {
        WorkflowState.MODELING,
        WorkflowState.WAITING_HUMAN,
        WorkflowState.CANONICALIZATION,
        WorkflowState.BLOCKED,
    },
    WorkflowState.CANONICALIZATION: {
        WorkflowState.CANONICALIZATION,
        WorkflowState.MODELING,
        WorkflowState.WAITING_HUMAN,
        WorkflowState.DONE,
        WorkflowState.BLOCKED,
    },
    WorkflowState.DONE: set(),
    WorkflowState.BLOCKED: set(),
}


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (source, target)
        for source, targets in EXPECTED_TRANSITIONS.items()
        for target in targets
    ],
)
def test_every_legal_transition_succeeds(
    source: WorkflowState, target: WorkflowState
) -> None:
    run = WorkflowRun(run_id="run-1", state=source)

    returned = transition(run, target)

    assert returned is run
    assert run.state is target


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (source, target)
        for source in WorkflowState
        for target in WorkflowState
        if target not in EXPECTED_TRANSITIONS[source]
    ],
)
def test_every_transition_outside_the_table_fails(
    source: WorkflowState, target: WorkflowState
) -> None:
    run = WorkflowRun(run_id="run-1", state=source)

    with pytest.raises(
        IllegalTransitionError,
        match=f"{source.value} -> {target.value}",
    ):
        transition(run, target)

    assert run.state is source


@pytest.mark.parametrize("terminal", [WorkflowState.DONE, WorkflowState.BLOCKED])
def test_terminal_states_have_no_outgoing_transitions(terminal: WorkflowState) -> None:
    for target in WorkflowState:
        with pytest.raises(IllegalTransitionError):
            transition(WorkflowRun(run_id="run-1", state=terminal), target)
