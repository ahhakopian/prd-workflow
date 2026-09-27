"""Execution-layer regressions for the approved dual-mode workflow."""

from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

import prd_workflow.cli as cli
import prd_workflow.workflow as workflow
from prd_workflow.ai import result_type_for_operation
from prd_workflow.ai_contracts import (
    AuditEditorialOutput,
    AuditHumanDecisionOutput,
    AuditPassOutput,
    AuditRemodelOutput,
    ConvergenceHumanDecisionOutput,
    ConvergencePassOutput,
    ConvergenceRemodelOutput,
)
from prd_workflow.canonical import final_canonical_path, render_markdown
from prd_workflow.decisions import active_authority
from prd_workflow.models import WorkflowState
from prd_workflow.storage import FileStorage
from prd_workflow.workflow import WorkflowService
from test_iteration1_acceptance import (
    CLARIFICATION,
    MISSING_EDIT_FINDING,
    edit_decision,
    edit_decision_draft,
    expense_source_bytes,
    final_document,
    model_outputs,
)


class ScriptedProvider:
    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.calls: list[str] = []

    def invoke(self, *, operation: str, payload: dict[str, object], result_type: Any) -> object:
        self.calls.append(operation)
        value = self.results.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def outputs() -> tuple[object, ...]:
    return (
        None,
        *model_outputs("pre-answer"),
        ConvergenceHumanDecisionOutput(
            outcome="HUMAN_DECISION",
            findings=(MISSING_EDIT_FINDING,),
            decision=edit_decision_draft(),
        ),
        *model_outputs("post-answer"),
        ConvergencePassOutput(outcome="PASS"),
        final_document(),
        AuditPassOutput(outcome="PASS"),
    )


def start(tmp_path: Path, name: str, ai: object | None = None) -> tuple[WorkflowService, str]:
    source = tmp_path / f"{name}.md"
    source.write_bytes(expense_source_bytes())
    service = WorkflowService(FileStorage(tmp_path / name), ai)
    return service, service.start(source).run_id


def submit_model(service: WorkflowService, run_id: str, result: object) -> object:
    task = service.next(run_id)
    assert task["kind"] == "model"
    raw = TypeAdapter(result_type_for_operation(task["operation"])).dump_python(result, mode="json")
    return service.submit(run_id, task["task_token"], raw)


def test_interactive_and_direct_modes_commit_equivalent_semantics(tmp_path: Path) -> None:
    interactive, interactive_id = start(tmp_path, "interactive")
    scripted = ScriptedProvider(*outputs())
    direct, direct_id = start(tmp_path, "direct", scripted)
    expected = list(outputs())

    first_direct = direct.run(direct_id)
    assert first_direct.reason == "waiting_human"
    assert first_direct.completed_tasks == 5
    for result in expected[:5]:
        task = interactive.next(interactive_id)
        assert interactive.next(interactive_id) == task
        assert task["kind"] == "model"
        submit_model(interactive, interactive_id, result)
        interactive = WorkflowService(FileStorage(tmp_path / "interactive"))

    assert interactive.status(interactive_id).state is WorkflowState.WAITING_HUMAN
    for service, run_id in ((interactive, interactive_id), (direct, direct_id)):
        task = service.next(run_id)
        assert task["kind"] == "human"
        assert task["decision"]["recommended_option_id"] == "A"
        service.submit(run_id, task["task_token"], {
            "kind": "option_with_clarification",
            "option_id": "B",
            "clarification": CLARIFICATION,
        })

    second_direct = direct.run(direct_id)
    assert second_direct.reason == "terminal"
    assert second_direct.completed_tasks == 6
    for result in expected[5:]:
        submit_model(interactive, interactive_id, result)
        interactive = WorkflowService(FileStorage(tmp_path / "interactive"))

    left = interactive.status(interactive_id)
    right = direct.status(direct_id)
    excluded = {"run_id", "revision", "pending_task"}
    assert left.model_dump(exclude=excluded) == right.model_dump(exclude=excluded)
    assert left.state is WorkflowState.DONE
    assert scripted.calls == [
        "intake", "derive_domain", "derive_capabilities", "derive_architecture",
        "review_convergence", "derive_domain", "derive_capabilities",
        "derive_architecture", "review_convergence", "compose_canonical", "audit_canonical",
    ]
    for service, run_id in ((interactive, interactive_id), (direct, direct_id)):
        run = service.status(run_id)
        markdown = final_canonical_path(run, service.storage.run_directory(run_id)).read_text()
        assert markdown == render_markdown(final_document())
        assert CLARIFICATION in markdown


def _same_semantics(left: object, right: object) -> None:
    excluded = {"run_id", "revision", "pending_task"}
    assert left.model_dump(exclude=excluded) == right.model_dump(exclude=excluded)


def test_convergence_remodel_has_identical_mode_semantics(tmp_path: Path) -> None:
    results = (*model_outputs("pre-answer"), ConvergenceRemodelOutput(
        outcome="REMODEL", findings=("Rebuild the ownership view.",),
    ))
    interactive, left_id = start(tmp_path, "remodel-interactive")
    direct, right_id = start(tmp_path, "remodel-direct", ScriptedProvider(*results))
    for service, run_id in ((interactive, left_id), (direct, right_id)):
        run = service.status(run_id)
        run.state = WorkflowState.MODELING
        service.storage.save_run(run)
    for result in results:
        submit_model(interactive, left_id, result)
    outcome = direct.run(right_id, max_tasks=4)
    assert outcome.reason == "task_limit"
    assert outcome.run.state is WorkflowState.MODELING
    assert outcome.run.operation_cursor == "derive_domain"
    _same_semantics(interactive.status(left_id), direct.status(right_id))


@pytest.mark.parametrize("audit_output,expected_state,expected_cursor", [
    (AuditEditorialOutput(outcome="EDITORIAL", findings=("Fix wording.",)), WorkflowState.CANONICALIZATION, "compose_canonical"),
    (AuditRemodelOutput(outcome="REMODEL", findings=("Rebuild ownership.",)), WorkflowState.MODELING, "derive_domain"),
    (AuditHumanDecisionOutput(
        outcome="HUMAN_DECISION", findings=("Need authority.",),
        decision=edit_decision_draft(),
    ), WorkflowState.WAITING_HUMAN, None),
])
def test_audit_remediation_has_identical_mode_semantics(
    tmp_path: Path, audit_output: object,
    expected_state: WorkflowState, expected_cursor: str | None,
) -> None:
    from prd_workflow.models import ConvergenceResult
    from test_canonical import modeling_result

    result_set = (final_document(), audit_output)
    interactive, left_id = start(tmp_path, "audit-interactive")
    direct, right_id = start(tmp_path, "audit-direct", ScriptedProvider(*result_set))
    for service, run_id in ((interactive, left_id), (direct, right_id)):
        run = service.status(run_id)
        run.state = WorkflowState.CANONICALIZATION
        run.modeling_result = modeling_result()
        run.convergence_result = ConvergenceResult(status="PASS")
        service.storage.save_run(run)
    for result in result_set:
        submit_model(interactive, left_id, result)
    outcome = direct.run(right_id, max_tasks=2)
    assert outcome.run.state is expected_state
    assert outcome.run.operation_cursor == expected_cursor
    _same_semantics(interactive.status(left_id), direct.status(right_id))


def test_canonical_validation_failure_skips_audit_in_both_modes(tmp_path: Path) -> None:
    from prd_workflow.models import ConvergenceResult
    from test_canonical import modeling_result

    candidate = final_document().model_copy(deep=True)
    candidate.functional_capabilities.capabilities[0].actor_ids = ("missing-role",)
    interactive, left_id = start(tmp_path, "invalid-interactive")
    provider = ScriptedProvider(candidate)
    direct, right_id = start(tmp_path, "invalid-direct", provider)
    for service, run_id in ((interactive, left_id), (direct, right_id)):
        run = service.status(run_id)
        run.state = WorkflowState.CANONICALIZATION
        run.modeling_result = modeling_result()
        run.convergence_result = ConvergenceResult(status="PASS")
        service.storage.save_run(run)
    submit_model(interactive, left_id, candidate)
    outcome = direct.run(right_id, max_tasks=1)
    assert outcome.run.operation_cursor == "compose_canonical"
    assert provider.calls == ["compose_canonical"]
    _same_semantics(interactive.status(left_id), direct.status(right_id))


def test_cli_next_and_submit_never_construct_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "source.md"
    source.write_text("# Product\n", encoding="utf-8")
    run = FileStorage().create_run(source)

    def forbidden() -> object:
        raise AssertionError("interactive command constructed an internal provider")

    monkeypatch.setattr(cli, "CodexAIExecutor", forbidden)
    assert cli.main(["next", run.run_id, "--json"]) == 0
    task = json.loads(capsys.readouterr().out)
    assert task["operation"] == "intake"
    assert task["instruction"] and task["output_schema"]
    output = tmp_path / "result.json"
    output.write_text("null", encoding="utf-8")
    assert cli.main(["submit", run.run_id, "--task-token", task["task_token"], "--input", str(output)]) == 0
    assert "state: MODELING" in capsys.readouterr().out


def test_replay_wrong_run_invalid_output_and_restart_preserve_state(tmp_path: Path) -> None:
    service, run_id = start(tmp_path, "one")
    other, other_id = start(tmp_path, "two")
    task = service.next(run_id)
    before = service.storage.run_directory(run_id).joinpath("run.json").read_bytes()
    restarted = WorkflowService(FileStorage(tmp_path / "one"))
    assert restarted.next(run_id) == task
    with pytest.raises(ValueError, match="token"):
        other.submit(other_id, task["task_token"], None)
    with pytest.raises(ValidationError):
        restarted.submit(run_id, task["task_token"], {"unexpected": True})
    assert restarted.storage.run_directory(run_id).joinpath("run.json").read_bytes() == before
    restarted.submit(run_id, task["task_token"], None)
    with pytest.raises(ValueError, match="token"):
        restarted.submit(run_id, task["task_token"], None)
    assert restarted.status(run_id).state is WorkflowState.MODELING


def test_legacy_run_without_new_fields_resumes_from_phase_start(tmp_path: Path) -> None:
    service, run_id = start(tmp_path, "legacy")
    path = service.storage.run_directory(run_id) / "run.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for field in ("revision", "operation_cursor", "modeling_progress", "pending_task"):
        data.pop(field)
    path.write_text(json.dumps(data), encoding="utf-8")
    restarted = WorkflowService(FileStorage(tmp_path / "legacy"))
    task = restarted.next(run_id)
    assert task["operation"] == "intake"
    assert restarted.status(run_id).revision == 1


def test_changed_contract_invalidates_token_without_accepting_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, run_id = start(tmp_path, "drift")
    task = service.next(run_id)
    original = workflow.load_prompt
    monkeypatch.setattr(workflow, "load_prompt", lambda operation: original(operation) + "\nChanged")
    with pytest.raises(ValueError, match="contract changed"):
        service.submit(run_id, task["task_token"], None)
    assert service.status(run_id).revision == 1
    replacement = service.next(run_id)
    assert replacement["task_token"] != task["task_token"]
    with pytest.raises(ValueError, match="token"):
        service.submit(run_id, task["task_token"], None)


def test_changed_schema_invalidates_issued_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, run_id = start(tmp_path, "schema-drift")
    task = service.next(run_id)
    original = workflow.load_committed_schema

    def changed_schema(operation: str) -> dict[str, object]:
        schema = original(operation)
        schema["description"] = "Changed installed schema"
        return schema

    monkeypatch.setattr(workflow, "load_committed_schema", changed_schema)
    with pytest.raises(ValueError, match="contract changed"):
        service.submit(run_id, task["task_token"], None)
    replacement = service.next(run_id)
    assert replacement["task_token"] != task["task_token"]


def test_changed_capabilities_contract_preserves_domain_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, run_id = start(tmp_path, "modeling-contract-drift")
    submit_model(service, run_id, None)
    submit_model(service, run_id, model_outputs("pre-answer")[0])
    checkpoint = service.status(run_id).modeling_progress.model_copy(deep=True)
    task = service.next(run_id)
    assert task["operation"] == "derive_capabilities"

    original = workflow.load_prompt
    monkeypatch.setattr(
        workflow, "load_prompt",
        lambda operation: original(operation) + "\nChanged" if operation == "derive_capabilities" else original(operation),
    )
    replacement = service.next(run_id)
    run = service.status(run_id)

    assert replacement["task_token"] != task["task_token"]
    assert replacement["operation"] == "derive_capabilities"
    assert run.operation_cursor == "derive_capabilities"
    assert run.modeling_progress == checkpoint


def test_changed_audit_contract_preserves_canonical_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prd_workflow.models import ConvergenceResult
    from test_canonical import modeling_result

    service, run_id = start(tmp_path, "audit-contract-drift")
    run = service.status(run_id)
    run.state = WorkflowState.CANONICALIZATION
    run.modeling_result = modeling_result()
    run.convergence_result = ConvergenceResult(status="PASS")
    service.storage.save_run(run)
    submit_model(service, run_id, final_document())
    checkpoint = service.status(run_id).canonical_candidate.model_copy(deep=True)
    task = service.next(run_id)
    assert task["operation"] == "audit_canonical"

    original = workflow.load_prompt
    monkeypatch.setattr(
        workflow, "load_prompt",
        lambda operation: original(operation) + "\nChanged" if operation == "audit_canonical" else original(operation),
    )
    replacement = service.next(run_id)
    run = service.status(run_id)

    assert replacement["task_token"] != task["task_token"]
    assert replacement["operation"] == "audit_canonical"
    assert run.operation_cursor == "audit_canonical"
    assert run.canonical_candidate == checkpoint


def test_concurrent_submissions_commit_once(tmp_path: Path) -> None:
    service, run_id = start(tmp_path, "race")
    task = service.next(run_id)

    def attempt(_: int) -> bool:
        try:
            WorkflowService(FileStorage(tmp_path / "race")).submit(run_id, task["task_token"], None)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == [False, True]
    run = service.status(run_id)
    assert run.state is WorkflowState.MODELING
    assert run.revision == 2


@pytest.mark.parametrize("answer", [
    {"kind": "option_selection", "option_id": "A"},
    {"kind": "option_with_clarification", "option_id": "B", "clarification": "Exact constraint"},
    {"kind": "custom", "text": "Exact custom decision"},
])
def test_human_task_requires_explicit_valid_answer_and_preserves_authority(
    tmp_path: Path, answer: dict[str, str],
) -> None:
    service, run_id = start(tmp_path, answer["kind"])
    run = service.status(run_id)
    run.state = WorkflowState.WAITING_HUMAN
    run.pending_decision_origin = WorkflowState.MODELING
    run.decisions = (edit_decision(),)
    service.storage.save_run(run)
    task = service.next(run_id)
    before = service.storage.run_directory(run_id).joinpath("run.json").read_bytes()
    with pytest.raises(ValidationError):
        service.submit(run_id, task["task_token"], {"kind": "custom", "text": " "})
    assert service.storage.run_directory(run_id).joinpath("run.json").read_bytes() == before
    result = service.submit(run_id, task["task_token"], answer)
    assert result.state is WorkflowState.MODELING
    assert result.decisions[0].answer.model_dump() == answer
    authority = active_authority(result, service.storage.load_source(result))
    assert authority["human_decisions"][0]["answer"]["kind"] == answer["kind"]
    assert "recommended_option_id" not in json.dumps(authority)


def test_provider_failure_keeps_task_and_checkpoint_for_retry(tmp_path: Path) -> None:
    ai = ScriptedProvider(None, *model_outputs("pre-answer"), RuntimeError("unavailable"))
    service, run_id = start(tmp_path, "provider-failure", ai)
    with pytest.raises(RuntimeError, match="unavailable"):
        service.run(run_id)
    run = service.status(run_id)
    assert run.state is WorkflowState.MODELING
    assert run.operation_cursor == "review_convergence"
    assert run.modeling_result is not None
    assert run.pending_task.operation == "review_convergence"
    assert service.next(run_id)["task_token"] == run.pending_task.token


def test_source_tamper_rejects_submission_then_blocks_on_next(tmp_path: Path) -> None:
    service, run_id = start(tmp_path, "tamper")
    task = service.next(run_id)
    source = service.storage.run_directory(run_id) / "source-prd.md"
    source.write_text("# Changed\n", encoding="utf-8")
    before = service.storage.run_directory(run_id).joinpath("run.json").read_bytes()
    with pytest.raises(ValueError, match="Source PRD integrity"):
        service.submit(run_id, task["task_token"], None)
    assert service.storage.run_directory(run_id).joinpath("run.json").read_bytes() == before
    assert service.next(run_id)["state"] == "BLOCKED"


def test_direct_task_limit_is_resumable(tmp_path: Path) -> None:
    ai = ScriptedProvider(None)
    service, run_id = start(tmp_path, "limit", ai)
    outcome = service.run(run_id, max_tasks=1)
    assert outcome.reason == "task_limit"
    assert outcome.run.state is WorkflowState.MODELING
    assert outcome.completed_tasks == 1
    assert ai.calls == ["intake"]



def test_direct_codex_adapter_executes_the_issued_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, run_id = start(tmp_path, "real-adapter")
    issued = service.next(run_id)
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["request"] = json.loads(str(kwargs["input"]))
        schema_path = Path(command[command.index("--output-schema") + 1])
        observed["schema"] = json.loads(schema_path.read_text(encoding="utf-8"))
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text('{"result":null}', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    outcome = service.run(run_id, max_tasks=1)
    assert outcome.run.state is WorkflowState.MODELING
    assert observed["request"] == {
        "instruction": issued["instruction"],
        "operation": issued["operation"],
        "payload": issued["payload"],
    }
    assert observed["schema"]["properties"]["result"]


def test_cli_rejects_malformed_and_oversized_json_without_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "source.md"
    source.write_text("# Product\n", encoding="utf-8")
    run = FileStorage().create_run(source)
    task = WorkflowService(FileStorage()).next(run.run_id)
    path = tmp_path / "response.json"
    before = FileStorage().run_directory(run.run_id).joinpath("run.json").read_bytes()

    path.write_text("{not-json", encoding="utf-8")
    command = ["submit", run.run_id, "--task-token", task["task_token"], "--input", str(path)]
    assert cli.main(command) == 1
    assert "error:" in capsys.readouterr().err
    assert FileStorage().run_directory(run.run_id).joinpath("run.json").read_bytes() == before

    path.write_bytes(b" " * (32 * 1024 * 1024 + 1))
    assert cli.main(command) == 1
    assert "exceeds 32 MiB" in capsys.readouterr().err
    assert FileStorage().run_directory(run.run_id).joinpath("run.json").read_bytes() == before


def test_external_state_change_invalidates_issued_task(tmp_path: Path) -> None:
    service, run_id = start(tmp_path, "wrong-state")
    task = service.next(run_id)
    changed = service.status(run_id)
    changed.state = WorkflowState.MODELING
    changed.revision += 1
    service.storage.save_run(changed)
    before = service.storage.run_directory(run_id).joinpath("run.json").read_bytes()
    with pytest.raises(ValueError, match="stale"):
        service.submit(run_id, task["task_token"], None)
    assert service.storage.run_directory(run_id).joinpath("run.json").read_bytes() == before
    fresh = service.next(run_id)
    assert fresh["operation"] == "derive_domain"
    assert fresh["task_token"] != task["task_token"]


def test_done_terminal_exposes_only_guarded_canonical_path(tmp_path: Path) -> None:
    service, run_id = start(tmp_path, "terminal")
    run = service.status(run_id)
    run.state = WorkflowState.CANONICALIZATION
    from prd_workflow.models import ConvergenceResult
    from test_canonical import modeling_result

    run.modeling_result = modeling_result()
    run.convergence_result = ConvergenceResult(status="PASS")
    service.storage.save_run(run)
    submit_model(service, run_id, final_document())
    audit_task = service.next(run_id)
    assert audit_task["operation"] == "audit_canonical"
    assert service.status(run_id).state is WorkflowState.CANONICALIZATION
    with pytest.raises(ValueError, match="DONE"):
        final_canonical_path(service.status(run_id), service.storage.run_directory(run_id))
    submit_model(service, run_id, AuditPassOutput(outcome="PASS"))
    terminal = service.next(run_id)
    assert terminal["kind"] == "terminal"
    assert terminal["canonical_path"] == str(
        final_canonical_path(service.status(run_id), service.storage.run_directory(run_id))
    )


def test_final_file_orphan_after_failed_done_save_never_enables_handoff(tmp_path: Path) -> None:
    from prd_workflow.models import ConvergenceResult
    from test_canonical import modeling_result

    class FailingDoneStorage(FileStorage):
        def save_run(self, run: Any) -> None:
            if run.state is WorkflowState.DONE:
                raise OSError("simulated crash before DONE commit")
            super().save_run(run)

    source = tmp_path / "crash.md"
    source.write_text("# Product\n", encoding="utf-8")
    storage = FailingDoneStorage(tmp_path / "crash-run")
    service = WorkflowService(storage)
    run = service.start(source)
    run.state = WorkflowState.CANONICALIZATION
    run.modeling_result = modeling_result()
    run.convergence_result = ConvergenceResult(status="PASS")
    storage.save_run(run)
    submit_model(service, run.run_id, final_document())
    audit = service.next(run.run_id)
    with pytest.raises(OSError, match="simulated crash"):
        service.submit(run.run_id, audit["task_token"], {"outcome": "PASS"})
    restored = service.status(run.run_id)
    assert restored.state is WorkflowState.CANONICALIZATION
    assert restored.pending_task.token == audit["task_token"]
    assert (storage.run_directory(run.run_id) / "canonical-prd.md").is_file()
    with pytest.raises(ValueError, match="DONE"):
        final_canonical_path(restored, storage.run_directory(run.run_id))
