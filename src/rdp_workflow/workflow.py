"""The explicit, fixed workflow finite state machine."""

from __future__ import annotations

from rdp_workflow.models import WorkflowRun, WorkflowState


_LEGAL_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.INTAKE: frozenset(
        {
            WorkflowState.MODELING,
            WorkflowState.WAITING_HUMAN,
            WorkflowState.BLOCKED,
        }
    ),
    WorkflowState.WAITING_HUMAN: frozenset(
        {
            WorkflowState.INTAKE,
            WorkflowState.MODELING,
            WorkflowState.BLOCKED,
        }
    ),
    WorkflowState.MODELING: frozenset(
        {
            WorkflowState.MODELING,
            WorkflowState.WAITING_HUMAN,
            WorkflowState.CANONICALIZATION,
            WorkflowState.BLOCKED,
        }
    ),
    WorkflowState.CANONICALIZATION: frozenset(
        {
            WorkflowState.CANONICALIZATION,
            WorkflowState.MODELING,
            WorkflowState.WAITING_HUMAN,
            WorkflowState.DONE,
            WorkflowState.BLOCKED,
        }
    ),
    WorkflowState.DONE: frozenset(),
    WorkflowState.BLOCKED: frozenset(),
}


class IllegalTransitionError(ValueError):
    """Raised when a requested transition is absent from the frozen topology."""


def transition(run: WorkflowRun, target_state: WorkflowState) -> WorkflowRun:
    """Apply one legal transition to the explicitly persisted run state.

    Phase-specific semantic guards belong to the phase behavior introduced in
    later slices. This function enforces only the frozen topology.
    """

    try:
        target = WorkflowState(target_state)
    except ValueError as exc:
        raise IllegalTransitionError(f"unknown workflow state: {target_state!r}") from exc

    if target not in _LEGAL_TRANSITIONS[run.state]:
        raise IllegalTransitionError(
            f"illegal workflow transition: {run.state.value} -> {target.value}"
        )

    run.state = target
    return run
