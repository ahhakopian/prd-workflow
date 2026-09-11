"""The explicit, fixed workflow finite state machine."""

from __future__ import annotations

from pathlib import Path

from rdp_workflow.ai import AIExecutor
from rdp_workflow.analysis import analyze_intake, derive_models, review_convergence
from rdp_workflow.canonical import (
    audit_canonical,
    compose_canonical,
    render_markdown,
    validate_contract,
)
from rdp_workflow.decisions import accept_answer, active_authority
from rdp_workflow.models import HumanAnswer, WorkflowRun, WorkflowState
from rdp_workflow.storage import FileStorage


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


class WorkflowService:
    """Orchestrate the implemented phases while the persisted FSM owns lifecycle."""

    def __init__(self, storage: FileStorage, ai: AIExecutor) -> None:
        self.storage = storage
        self.ai = ai

    def start(self, source_path: Path) -> WorkflowRun:
        return self.storage.create_run(source_path)

    def advance(self, run_id: str) -> WorkflowRun:
        run = self.storage.load_run(run_id)

        match run.state:
            case WorkflowState.INTAKE:
                return self._advance_intake(run)
            case WorkflowState.MODELING:
                return self._advance_modeling(run)
            case WorkflowState.CANONICALIZATION:
                return self._advance_canonicalization(run)
            case WorkflowState.WAITING_HUMAN:
                raise ValueError("workflow is waiting for the current Human Decision")
            case _:
                raise NotImplementedError(
                    f"{run.state.value} has no active phase execution"
                )

    def answer(
        self,
        run_id: str,
        decision_id: str,
        answer: HumanAnswer,
    ) -> WorkflowRun:
        run = self.storage.load_run(run_id)
        origin = run.pending_decision_origin

        accept_answer(run, decision_id, answer)
        if origin is WorkflowState.INTAKE:
            transition(run, WorkflowState.INTAKE)
        elif origin in {WorkflowState.MODELING, WorkflowState.CANONICALIZATION}:
            run.modeling_result = None
            run.convergence_result = None
            run.canonical_candidate = None
            run.audit_result = None
            run.diagnostics = ()
            transition(run, WorkflowState.MODELING)
        else:  # accept_answer rejects a missing or inconsistent pending origin first
            raise ValueError("pending Decision has no supported origin")
        self.storage.save_run(run)
        return run

    def status(self, run_id: str) -> WorkflowRun:
        return self.storage.load_run(run_id)

    def _advance_intake(self, run: WorkflowRun) -> WorkflowRun:
        if any(
            decision.classification == "MATERIAL" and decision.status == "PENDING"
            for decision in run.decisions
        ):
            raise ValueError("INTAKE cannot advance with an existing pending Decision")

        authority = active_authority(run, self.storage.load_source(run.run_id))
        decision = analyze_intake(authority, self.ai)
        if decision is None:
            transition(run, WorkflowState.MODELING)
        else:
            if any(
                existing.decision_id == decision.decision_id
                for existing in run.decisions
            ):
                raise ValueError("Decision IDs must be unique within a run")
            run.decisions = (*run.decisions, decision)
            run.pending_decision_origin = WorkflowState.INTAKE
            transition(run, WorkflowState.WAITING_HUMAN)

        self.storage.save_run(run)
        return run

    def _advance_modeling(self, run: WorkflowRun) -> WorkflowRun:
        if any(
            decision.classification == "MATERIAL" and decision.status == "PENDING"
            for decision in run.decisions
        ):
            raise ValueError("MODELING cannot advance with an existing pending Decision")

        authority = active_authority(run, self.storage.load_source(run.run_id))
        prior_findings = (
            run.convergence_result.findings
            if run.convergence_result is not None
            and run.convergence_result.status == "FAIL"
            and run.convergence_result.remediation == "REMODEL"
            else run.diagnostics
        )
        models = derive_models(authority, prior_findings, self.ai)
        convergence = review_convergence(authority, models, self.ai)

        run.modeling_result = models
        run.convergence_result = convergence
        run.diagnostics = ()

        if convergence.status == "PASS":
            transition(run, WorkflowState.CANONICALIZATION)
        elif convergence.remediation == "REMODEL":
            transition(run, WorkflowState.MODELING)
        else:
            decision = convergence.decision
            if decision is None:  # guarded by ConvergenceResult validation
                raise ValueError("HUMAN_DECISION remediation has no Decision")
            if any(
                existing.decision_id == decision.decision_id
                for existing in run.decisions
            ):
                raise ValueError("Decision IDs must be unique within a run")
            run.decisions = (*run.decisions, decision)
            run.pending_decision_origin = WorkflowState.MODELING
            transition(run, WorkflowState.WAITING_HUMAN)

        self.storage.save_run(run)
        return run

    def _advance_canonicalization(self, run: WorkflowRun) -> WorkflowRun:
        if any(
            decision.classification == "MATERIAL" and decision.status == "PENDING"
            for decision in run.decisions
        ):
            raise ValueError(
                "CANONICALIZATION cannot advance with an existing pending Decision"
            )
        if run.modeling_result is None or run.convergence_result is None:
            raise ValueError(
                "CANONICALIZATION requires a complete converged ModelingResult"
            )
        if run.convergence_result.status != "PASS":
            raise ValueError("CANONICALIZATION requires Convergence PASS")

        authority = active_authority(run, self.storage.load_source(run.run_id))
        document = compose_canonical(
            authority,
            run.modeling_result,
            run.diagnostics,
            self.ai,
        )
        markdown = render_markdown(document)
        validation_findings = validate_contract(document)

        if validation_findings:
            run.canonical_candidate = document
            run.audit_result = None
            run.diagnostics = validation_findings
            transition(run, WorkflowState.CANONICALIZATION)
            self.storage.save_run(run)
            return run

        audit = audit_canonical(
            authority,
            run.modeling_result,
            document,
            markdown,
            self.ai,
        )

        if audit.status == "PASS":
            run.canonical_candidate = document
            run.audit_result = audit
            run.diagnostics = ()
            self.storage.write_canonical(run.run_id, markdown)
            transition(run, WorkflowState.DONE)
        elif audit.remediation == "EDITORIAL":
            run.canonical_candidate = document
            run.audit_result = audit
            run.diagnostics = audit.findings
            transition(run, WorkflowState.CANONICALIZATION)
        elif audit.remediation == "REMODEL":
            run.canonical_candidate = None
            run.audit_result = None
            run.diagnostics = audit.findings
            transition(run, WorkflowState.MODELING)
        else:
            decision = audit.decision
            if decision is None:  # guarded by AuditResult validation
                raise ValueError("HUMAN_DECISION remediation has no Decision")
            if any(
                existing.decision_id == decision.decision_id
                for existing in run.decisions
            ):
                raise ValueError("Decision IDs must be unique within a run")
            run.canonical_candidate = document
            run.audit_result = audit
            run.diagnostics = audit.findings
            run.decisions = (*run.decisions, decision)
            run.pending_decision_origin = WorkflowState.CANONICALIZATION
            transition(run, WorkflowState.WAITING_HUMAN)

        self.storage.save_run(run)
        return run
