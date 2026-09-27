"""The explicit, fixed workflow finite state machine."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from pathlib import Path

from pydantic import TypeAdapter

from prd_workflow.ai import (
    AIExecutor, CANONICAL_RESULT_TYPE, CodexAIExecutor,
    load_committed_schema, load_prompt, result_type_for_operation,
)
from prd_workflow.ai_contracts import (
    ArchitectureOutput, CapabilitiesOutput, DomainOutput,
    deferred_decision_from_draft, material_decision_from_draft,
)
from prd_workflow.analysis import (
    architecture_payload, capabilities_payload, convergence_payload,
    domain_payload, intake_payload, parse_convergence,
)
from prd_workflow.canonical import (
    audit_payload, compose_payload, final_canonical_path, parse_audit,
    render_markdown, validate_contract,
)
from prd_workflow.decisions import accept_answer, active_authority
from prd_workflow.models import (
    Decision, HumanAnswer, ModelingProgress, ModelingResult, PendingTask,
    WorkflowRun, WorkflowState,
)
from prd_workflow.storage import FileStorage, SourceIntegrityError


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
    """One persisted FSM and task commit path for interactive and direct use."""

    def __init__(self, storage: FileStorage, ai: AIExecutor | None = None) -> None:
        self.storage = storage
        self.ai = ai

    def start(self, source_path: Path) -> WorkflowRun:
        return self.storage.create_run(source_path)

    def status(self, run_id: str) -> WorkflowRun:
        return self.storage.load_run(run_id)

    def next(self, run_id: str) -> dict[str, object]:
        """Issue or repeat exactly one task without invoking a provider."""
        with self.storage.lock_run(run_id):
            run = self.storage.load_run(run_id)
            return self._next_locked(run)

    def _next_locked(self, run: WorkflowRun) -> dict[str, object]:
        if run.state in {WorkflowState.DONE, WorkflowState.BLOCKED}:
            return self._terminal(run)
        failure = _controlling_invariant_failure(run)
        if failure is not None:
            return self._block_locked(run, failure)
        try:
            source_text = self.storage.load_source(run)
        except SourceIntegrityError as exc:
            return self._block_locked(run, str(exc))

        task = run.pending_task
        if task is not None:
            if self._task_matches(run, task, source_text):
                return self._envelope(run, task)
            run.pending_task = None

        cursor = self._cursor(run)
        run.revision += 1
        if run.state is WorkflowState.WAITING_HUMAN:
            decision = self._pending_decision(run)
            task = PendingTask(
                kind="human", token=secrets.token_hex(32), run_id=run.run_id,
                state=run.state, operation_cursor=run.operation_cursor,
                revision=run.revision, decision_id=decision.decision_id,
                decision=decision,
                contract_fingerprint=self._human_fingerprint(),
            )
        else:
            payload = self._json_value(self._payload(run, source_text, cursor))
            task = PendingTask(
                kind="model", token=secrets.token_hex(32), run_id=run.run_id,
                state=run.state, operation_cursor=run.operation_cursor,
                revision=run.revision, operation=cursor,
                instruction=load_prompt(cursor), payload=payload,
                output_schema=load_committed_schema(cursor),
                contract_fingerprint=self._model_fingerprint(cursor),
            )
        run.pending_task = task
        self.storage.save_run(run)
        return self._envelope(run, task)

    def submit(self, run_id: str, task_token: str, raw_json: object) -> WorkflowRun:
        """Validate and atomically commit one task result or Human Answer."""
        with self.storage.lock_run(run_id):
            run = self.storage.load_run(run_id)
            return self._submit_locked(run, task_token, raw_json)

    def _submit_locked(self, run: WorkflowRun, token: str, raw: object) -> WorkflowRun:
        if run.state in {WorkflowState.DONE, WorkflowState.BLOCKED}:
            raise ValueError("terminal run cannot accept a task submission")
        task = run.pending_task
        if task is None or not hmac.compare_digest(task.token, token):
            raise ValueError("stale or invalid task token")
        if (
            task.run_id != run.run_id or task.state is not run.state
            or task.operation_cursor != run.operation_cursor
            or task.revision != run.revision
        ):
            raise ValueError("task is stale for the current run state or revision")
        if not self._task_contract_current(task):
            raise ValueError("task contract changed; call prd next for a fresh task")
        failure = _controlling_invariant_failure(run)
        if failure is not None:
            raise ValueError(failure)
        try:
            source_text = self.storage.load_source(run)
        except SourceIntegrityError as exc:
            raise ValueError(str(exc)) from exc
        if task.kind == "human":
            if run.state is not WorkflowState.WAITING_HUMAN:
                raise ValueError("human task is in the wrong state")
            decision = self._pending_decision(run)
            if task.decision_id != decision.decision_id or task.decision != decision:
                raise ValueError("human task no longer matches the pending Decision")
            answer = TypeAdapter(HumanAnswer).validate_python(raw)
            self._apply_answer(run, decision.decision_id, answer)
        else:
            operation = self._cursor(run)
            if task.operation != operation or task.payload != self._json_value(self._payload(run, source_text, operation)):
                raise ValueError("model task no longer matches the current operation")
            if task.instruction != load_prompt(operation) or task.output_schema != load_committed_schema(operation):
                raise ValueError("model task request changed")
            result = TypeAdapter(result_type_for_operation(operation)).validate_python(raw)
            self._apply_model_result(run, operation, result)
        run.pending_task = None
        run.revision += 1
        self.storage.save_run(run)
        return run

    def run(self, run_id: str, max_tasks: int = 50) -> RunOutcome:
        if max_tasks < 1:
            raise ValueError("max_tasks must be positive")
        ai = self.ai
        completed = 0
        while completed < max_tasks:
            envelope = self.next(run_id)
            if envelope["kind"] == "terminal":
                return RunOutcome(self.status(run_id), "terminal", completed)
            if envelope["kind"] == "human":
                return RunOutcome(self.status(run_id), "waiting_human", completed)
            task = self.status(run_id).pending_task
            if task is None:
                raise RuntimeError("issued model task disappeared")
            if ai is None:
                ai = CodexAIExecutor()
            try:
                if hasattr(ai, "invoke_task"):
                    output = ai.invoke_task(task)
                else:
                    output = ai.invoke(
                        operation=task.operation, payload=task.payload,
                        result_type=result_type_for_operation(task.operation),
                    )
            except Exception as exc:
                raise RuntimeError(f"AI operation {task.operation!r} failed: {exc}") from exc
            raw = TypeAdapter(result_type_for_operation(task.operation)).dump_python(output, mode="json")
            try:
                self.submit(run_id, task.token, raw)
            except Exception as exc:
                raise RuntimeError(f"AI operation {task.operation!r} result was rejected: {exc}") from exc
            completed += 1
        final_run = self.status(run_id)
        if final_run.state in {WorkflowState.DONE, WorkflowState.BLOCKED}:
            return RunOutcome(final_run, "terminal", completed)
        if final_run.state is WorkflowState.WAITING_HUMAN:
            return RunOutcome(final_run, "waiting_human", completed)
        return RunOutcome(final_run, "task_limit", completed)

    def advance(self, run_id: str) -> WorkflowRun:
        """Deprecated direct adapter: finish one old phase execution."""
        initial = self.status(run_id)
        if initial.state is WorkflowState.WAITING_HUMAN:
            failure = _controlling_invariant_failure(initial)
            if failure is not None:
                self.next(run_id)
                return self.status(run_id)
            raise ValueError("workflow is waiting for the current Human Decision")
        if initial.state in {WorkflowState.DONE, WorkflowState.BLOCKED}:
            raise NotImplementedError(f"{initial.state.value} has no active phase execution")
        ai = self.ai or CodexAIExecutor()
        for _ in range(50):
            envelope = self.next(run_id)
            if envelope["kind"] != "model":
                return self.status(run_id)
            task = self.status(run_id).pending_task
            if hasattr(ai, "invoke_task"):
                output = ai.invoke_task(task)
            else:
                output = ai.invoke(
                    operation=task.operation, payload=task.payload,
                    result_type=result_type_for_operation(task.operation),
                )
            raw = TypeAdapter(result_type_for_operation(task.operation)).dump_python(output, mode="json")
            run = self.submit(run_id, task.token, raw)
            if run.state is not initial.state or task.operation in {"intake", "review_convergence", "audit_canonical"}:
                return run
            if task.operation == "compose_canonical" and run.operation_cursor == "compose_canonical":
                return run
        raise RuntimeError("advance exceeded its phase task limit")

    def answer(self, run_id: str, decision_id: str, answer: HumanAnswer) -> WorkflowRun:
        """Deprecated explicit Human Answer adapter through the shared task path."""
        with self.storage.lock_run(run_id):
            run = self.storage.load_run(run_id)
            if run.state is not WorkflowState.WAITING_HUMAN:
                raise ValueError("Human Answers are accepted only while WAITING_HUMAN")
            if self._pending_decision(run).decision_id != decision_id:
                raise ValueError("decision_id does not identify the current pending Decision")
            envelope = self._next_locked(run)
            if envelope["kind"] != "human":
                raise ValueError("run is not awaiting a Human Decision")
            run = self.storage.load_run(run_id)
            return self._submit_locked(run, envelope["task_token"], answer.model_dump(mode="json"))

    def _apply_model_result(self, run: WorkflowRun, operation: str, result: object) -> None:
        if operation == "intake":
            decision = None if result is None else material_decision_from_draft(result, WorkflowState.INTAKE)
            if decision is None:
                transition(run, WorkflowState.MODELING)
                run.operation_cursor = "derive_domain"
            else:
                self._append_decision(run, decision, WorkflowState.INTAKE)
            return
        if operation == "derive_domain":
            result = DomainOutput.model_validate(result)
            run.modeling_progress = ModelingProgress(product_context=result.product_context, domain=result.domain)
            run.operation_cursor = "derive_capabilities"
            transition(run, WorkflowState.MODELING)
            return
        progress = run.modeling_progress
        if operation == "derive_capabilities":
            result = CapabilitiesOutput.model_validate(result)
            progress.capabilities = result.capabilities
            run.operation_cursor = "derive_architecture"
            transition(run, WorkflowState.MODELING)
            return
        if operation == "derive_architecture":
            result = ArchitectureOutput.model_validate(result)
            progress.architecture = result.architecture
            progress.deferred_decisions = tuple(deferred_decision_from_draft(item) for item in result.deferred_decisions)
            run.modeling_result = ModelingResult(
                product_context=progress.product_context, domain=progress.domain,
                capabilities=progress.capabilities, architecture=progress.architecture,
                deferred_decisions=progress.deferred_decisions,
            )
            run.operation_cursor = "review_convergence"
            transition(run, WorkflowState.MODELING)
            return
        if operation == "review_convergence":
            convergence = parse_convergence(result)
            run.convergence_result = convergence
            run.diagnostics = ()
            run.modeling_progress = None
            if convergence.status == "PASS":
                run.operation_cursor = "compose_canonical"
                transition(run, WorkflowState.CANONICALIZATION)
            elif convergence.remediation == "REMODEL":
                run.operation_cursor = "derive_domain"
                transition(run, WorkflowState.MODELING)
            else:
                self._append_decision(run, convergence.decision, WorkflowState.MODELING)
            return
        if operation == "compose_canonical":
            document = TypeAdapter(CANONICAL_RESULT_TYPE).validate_python(result)
            markdown = render_markdown(document)
            findings = validate_contract(document)
            run.canonical_candidate = document
            run.audit_result = None
            if findings:
                run.diagnostics = findings
                run.operation_cursor = "compose_canonical"
            else:
                run.operation_cursor = "audit_canonical"
            transition(run, WorkflowState.CANONICALIZATION)
            return
        if operation == "audit_canonical":
            audit = parse_audit(result)
            run.audit_result = audit
            if audit.status == "PASS":
                run.diagnostics = ()
                markdown = render_markdown(run.canonical_candidate)
                self.storage.write_canonical(run.run_id, markdown)
                run.operation_cursor = None
                transition(run, WorkflowState.DONE)
            elif audit.remediation == "EDITORIAL":
                run.diagnostics = audit.findings
                run.operation_cursor = "compose_canonical"
                transition(run, WorkflowState.CANONICALIZATION)
            elif audit.remediation == "REMODEL":
                run.canonical_candidate = None
                run.audit_result = None
                run.diagnostics = audit.findings
                run.modeling_progress = None
                run.operation_cursor = "derive_domain"
                transition(run, WorkflowState.MODELING)
            else:
                run.diagnostics = audit.findings
                self._append_decision(run, audit.decision, WorkflowState.CANONICALIZATION)
            return
        raise ValueError(f"unknown operation: {operation!r}")

    def _apply_answer(self, run: WorkflowRun, decision_id: str, answer: HumanAnswer) -> None:
        origin = run.pending_decision_origin
        accept_answer(run, decision_id, answer)
        if origin is WorkflowState.INTAKE:
            run.operation_cursor = "intake"
            transition(run, WorkflowState.INTAKE)
        elif origin in {WorkflowState.MODELING, WorkflowState.CANONICALIZATION}:
            run.modeling_result = None
            run.modeling_progress = None
            run.convergence_result = None
            run.canonical_candidate = None
            run.audit_result = None
            run.diagnostics = ()
            run.operation_cursor = "derive_domain"
            transition(run, WorkflowState.MODELING)
        else:
            raise ValueError("pending Decision has no supported origin")

    def _append_decision(self, run: WorkflowRun, decision: Decision, origin: WorkflowState) -> None:
        if any(existing.decision_id == decision.decision_id for existing in run.decisions):
            raise ValueError("Decision IDs must be unique within a run")
        run.decisions = (*run.decisions, decision)
        run.pending_decision_origin = origin
        run.operation_cursor = None
        transition(run, WorkflowState.WAITING_HUMAN)

    def _payload(self, run: WorkflowRun, source_text: str, operation: str) -> dict[str, object]:
        authority = active_authority(run, source_text)
        findings = (
            run.convergence_result.findings
            if run.convergence_result is not None
            and run.convergence_result.status == "FAIL"
            and run.convergence_result.remediation == "REMODEL"
            else run.diagnostics
        )
        if operation == "intake":
            return intake_payload(authority)
        if operation == "derive_domain":
            return domain_payload(authority, findings)
        progress = run.modeling_progress
        if operation == "derive_capabilities":
            return capabilities_payload(authority, progress.product_context, progress.domain, findings)
        if operation == "derive_architecture":
            return architecture_payload(authority, progress.product_context, progress.domain, progress.capabilities, findings)
        if operation == "review_convergence":
            return convergence_payload(authority, run.modeling_result)
        if operation == "compose_canonical":
            return compose_payload(authority, run.modeling_result, run.diagnostics)
        if operation == "audit_canonical":
            return audit_payload(authority, run.modeling_result, run.canonical_candidate, render_markdown(run.canonical_candidate))
        raise ValueError(f"unknown operation: {operation!r}")

    @staticmethod
    def _cursor(run: WorkflowRun) -> str:
        defaults = {
            WorkflowState.INTAKE: "intake",
            WorkflowState.MODELING: "derive_domain",
            WorkflowState.CANONICALIZATION: "compose_canonical",
        }
        if run.state is WorkflowState.WAITING_HUMAN:
            return "human"
        cursor = run.operation_cursor or defaults[run.state]
        allowed = {
            WorkflowState.INTAKE: {"intake"},
            WorkflowState.MODELING: {"derive_domain", "derive_capabilities", "derive_architecture", "review_convergence"},
            WorkflowState.CANONICALIZATION: {"compose_canonical", "audit_canonical"},
        }
        if cursor not in allowed[run.state]:
            raise ValueError(f"invalid operation cursor {cursor!r} for {run.state.value}")
        return cursor

    @staticmethod
    def _pending_decision(run: WorkflowRun) -> Decision:
        pending = [decision for decision in run.decisions if decision.classification == "MATERIAL" and decision.status == "PENDING"]
        if len(pending) != 1:
            raise ValueError("WAITING_HUMAN requires exactly one pending MATERIAL Decision")
        return pending[0]

    @staticmethod
    def _model_fingerprint(operation: str) -> str:
        value = json.dumps({
            "operation": operation, "prompt": load_prompt(operation),
            "schema": load_committed_schema(operation),
            "type": repr(result_type_for_operation(operation)),
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _json_value(value: object) -> object:
        return json.loads(json.dumps(value, ensure_ascii=False))

    @staticmethod
    def _human_fingerprint() -> str:
        value = json.dumps(TypeAdapter(HumanAnswer).json_schema(), sort_keys=True)
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _task_contract_current(self, task: PendingTask) -> bool:
        if task.kind == "human":
            return hmac.compare_digest(task.contract_fingerprint, self._human_fingerprint())
        try:
            current = self._model_fingerprint(task.operation)
        except ValueError:
            return False
        return hmac.compare_digest(task.contract_fingerprint, current)

    def _task_matches(self, run: WorkflowRun, task: PendingTask, source_text: str) -> bool:
        if (
            task.run_id != run.run_id or task.state is not run.state
            or task.operation_cursor != run.operation_cursor
            or task.revision != run.revision
            or not self._task_contract_current(task)
        ):
            return False
        if task.kind == "human":
            return (
                run.state is WorkflowState.WAITING_HUMAN
                and task.decision == self._pending_decision(run)
                and task.decision_id == task.decision.decision_id
            )
        operation = self._cursor(run)
        return (
            task.operation == operation
            and task.instruction == load_prompt(operation)
            and task.output_schema == load_committed_schema(operation)
            and task.payload == self._json_value(self._payload(run, source_text, operation))
        )

    @staticmethod
    def _envelope(run: WorkflowRun, task: PendingTask) -> dict[str, object]:
        common = {
            "protocol_version": 1, "run_id": run.run_id, "state": run.state.value,
            "kind": task.kind, "task_token": task.token,
            "submit_hint": f"prd submit {run.run_id} --task-token <token> --input <file|->",
        }
        if task.kind == "human":
            return {**common, "decision": task.decision.model_dump(mode="json"),
                    "answer_contract": [
                        {"kind": "option_selection", "option_id": "string"},
                        {"kind": "option_with_clarification", "option_id": "string", "clarification": "string"},
                        {"kind": "custom", "text": "string"},
                    ],
                    "constraints": "Only a human may select or author the answer; the recommendation is advisory."}
        return {**common, "operation": task.operation, "instruction": task.instruction,
                "payload": task.payload, "output_schema": task.output_schema,
                "constraints": "Return only a JSON value matching output_schema; do not create new material authority."}

    def _terminal(self, run: WorkflowRun) -> dict[str, object]:
        envelope: dict[str, object] = {
            "protocol_version": 1, "run_id": run.run_id, "state": run.state.value,
            "kind": "terminal", "diagnostics": list(run.diagnostics),
        }
        if run.state is WorkflowState.DONE:
            envelope["canonical_path"] = str(
                final_canonical_path(run, self.storage.run_directory(run.run_id))
            )
        return envelope

    def _block_locked(self, run: WorkflowRun, diagnostic: str) -> dict[str, object]:
        run.diagnostics = (diagnostic,)
        run.pending_task = None
        run.operation_cursor = None
        transition(run, WorkflowState.BLOCKED)
        run.revision += 1
        self.storage.save_run(run)
        return self._terminal(run)


@dataclass(frozen=True)
class RunOutcome:
    run: WorkflowRun
    reason: str
    completed_tasks: int


def _controlling_invariant_failure(run: WorkflowRun) -> str | None:
    pending = tuple(
        decision
        for decision in run.decisions
        if decision.classification == "MATERIAL" and decision.status == "PENDING"
    )
    if run.state is WorkflowState.INTAKE and pending:
        return "INTAKE cannot execute with a pending MATERIAL Decision."
    if run.state is WorkflowState.WAITING_HUMAN:
        if run.operation_cursor is not None:
            return "WAITING_HUMAN cannot have a model operation cursor."
        if len(pending) != 1:
            return "WAITING_HUMAN requires exactly one pending MATERIAL Decision."
        if run.pending_decision_origin is not pending[0].origin_state:
            return (
                "WAITING_HUMAN pending_decision_origin must match the pending "
                "MATERIAL Decision origin_state."
            )
    if run.state is WorkflowState.MODELING and pending:
        return "MODELING cannot execute with a pending MATERIAL Decision."
    if run.state is WorkflowState.INTAKE and run.operation_cursor not in {None, "intake"}:
        return "INTAKE has an invalid operation cursor."
    if run.state is WorkflowState.MODELING:
        cursor = run.operation_cursor
        if cursor not in {None, "derive_domain", "derive_capabilities", "derive_architecture", "review_convergence"}:
            return "MODELING has an invalid operation cursor."
        progress = run.modeling_progress
        if cursor in {"derive_capabilities", "derive_architecture", "review_convergence"}:
            if progress is None or progress.product_context is None or progress.domain is None:
                return "MODELING cursor requires a validated Domain checkpoint."
        if cursor in {"derive_architecture", "review_convergence"} and progress.capabilities is None:
            return "MODELING cursor requires a validated Capabilities checkpoint."
        if cursor == "review_convergence" and run.modeling_result is None:
            return "Convergence review requires a complete fresh ModelingResult."
    if run.state is WorkflowState.CANONICALIZATION:
        if pending:
            return "CANONICALIZATION cannot execute with a pending MATERIAL Decision."
        if run.modeling_result is None:
            return "CANONICALIZATION requires a complete ModelingResult."
        if run.convergence_result is None:
            return "CANONICALIZATION requires a ConvergenceResult."
        if run.convergence_result.status != "PASS":
            return "CANONICALIZATION requires Convergence PASS."
        if run.operation_cursor not in {None, "compose_canonical", "audit_canonical"}:
            return "CANONICALIZATION has an invalid operation cursor."
        if run.operation_cursor == "audit_canonical":
            if run.canonical_candidate is None:
                return "Canonical Audit requires a persisted candidate."
            if validate_contract(run.canonical_candidate):
                return "Canonical Audit requires a contract-valid candidate."
    return None
