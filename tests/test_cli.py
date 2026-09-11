from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import rdp_workflow.cli as cli
from rdp_workflow.models import (
    CustomAnswer,
    Decision,
    DecisionOption,
    OptionSelection,
    OptionWithClarification,
    WorkflowState,
)
from rdp_workflow.storage import FileStorage


class ScriptedAI:
    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.calls: list[str] = []

    def invoke(
        self,
        *,
        operation: str,
        payload: dict[str, object],
        result_type: type[Any],
    ) -> Any:
        self.calls.append(operation)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def source_at(tmp_path: Path) -> Path:
    source = tmp_path / "source.md"
    source.write_text("# Expense reimbursement\n", encoding="utf-8")
    return source


def pending_decision(
    *,
    origin: WorkflowState = WorkflowState.MODELING,
    supersedes_decision_id: str | None = None,
) -> Decision:
    return Decision(
        decision_id="expense-edit-policy",
        classification="MATERIAL",
        origin_state=origin,
        question="May a submitting employee edit a pending expense report?",
        context="The answer changes employee permissions and review behavior.",
        options=(
            DecisionOption(
                option_id="A",
                text="Do not allow edits after submission.",
                consequence="The submitted report remains immutable.",
            ),
            DecisionOption(
                option_id="B",
                text="Allow edits while the report is pending review.",
                consequence="An employee may correct a pending report.",
            ),
            DecisionOption(
                option_id="C",
                text="Require withdrawal before editing.",
                consequence="Editing requires a separate workflow action.",
            ),
        ),
        recommended_option_id="A",
        recommendation_rationale="Immutability gives the simplest audit trail.",
        supersedes_decision_id=supersedes_decision_id,
    )


def install_ai(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ai: ScriptedAI) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "CodexAIExecutor", lambda: ai)


def create_waiting_run(
    tmp_path: Path,
    *,
    decision: Decision | None = None,
) -> tuple[FileStorage, str]:
    storage = FileStorage(tmp_path / ".rdp")
    run = storage.create_run(source_at(tmp_path))
    current = decision or pending_decision()
    run.state = WorkflowState.WAITING_HUMAN
    run.pending_decision_origin = current.origin_state
    run.decisions = (current,)
    storage.save_run(run)
    return storage, run.run_id


def test_cli_start_prints_intake_run_id_and_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ai = ScriptedAI()
    install_ai(monkeypatch, tmp_path, ai)

    result = cli.main(["start", str(source_at(tmp_path))])

    output = capsys.readouterr()
    run_id = output.out.splitlines()[0].removeprefix("run_id: ")
    assert result == 0
    assert output.err == ""
    assert output.out.splitlines()[1:] == [
        "state: INTAKE",
        f"next: rdp advance {run_id}",
    ]
    assert FileStorage().load_run(run_id).state is WorkflowState.INTAKE
    assert ai.calls == []


def test_cli_advance_executes_exactly_one_service_step_and_reports_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ai = ScriptedAI(None)
    install_ai(monkeypatch, tmp_path, ai)
    run = FileStorage().create_run(source_at(tmp_path), run_id="one-step")

    result = cli.main(["advance", run.run_id])

    output = capsys.readouterr()
    assert result == 0
    assert "state: MODELING" in output.out
    assert "outcome: Intake is complete; modeling is ready." in output.out
    assert ai.calls == ["intake"]
    assert FileStorage().load_run(run.run_id).state is WorkflowState.MODELING


def test_cli_advance_surfaces_provider_failure_without_transition_or_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ai = ScriptedAI(RuntimeError("provider schema failure"))
    install_ai(monkeypatch, tmp_path, ai)
    run = FileStorage().create_run(source_at(tmp_path), run_id="provider-failure")

    result = cli.main(["advance", run.run_id])

    output = capsys.readouterr()
    assert result == 1
    assert output.out == ""
    assert output.err == "error: provider schema failure\n"
    assert ai.calls == ["intake"]
    assert FileStorage().load_run(run.run_id).state is WorkflowState.INTAKE


def test_cli_status_shows_operator_state_without_internal_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ai = ScriptedAI()
    install_ai(monkeypatch, tmp_path, ai)
    storage = FileStorage()
    run = storage.create_run(source_at(tmp_path), run_id="status-run")
    run.diagnostics = ("Review the Source PRD on the next intake step.",)
    storage.save_run(run)

    result = cli.main(["status", run.run_id])

    output = capsys.readouterr()
    assert result == 0
    assert "state: INTAKE" in output.out
    assert "human_decision_pending: no" in output.out
    assert "Review the Source PRD on the next intake step." in output.out
    assert "modeling_result" not in output.out
    assert "canonical_candidate" not in output.out
    assert "audit_result" not in output.out
    assert ai.calls == []


def test_cli_status_done_reports_canonical_availability_without_exposing_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ai = ScriptedAI()
    install_ai(monkeypatch, tmp_path, ai)
    storage = FileStorage()
    run = storage.create_run(source_at(tmp_path), run_id="done-status")
    storage.write_canonical(run.run_id, "# Canonical RDP\n")
    run.state = WorkflowState.DONE
    storage.save_run(run)

    result = cli.main(["status", run.run_id])

    output = capsys.readouterr()
    assert result == 0
    assert "state: DONE" in output.out
    assert "canonical_available: yes" in output.out
    assert "canonical-rdp.md" not in output.out
    assert "run.json" not in output.out


def test_cli_waiting_human_display_is_complete_and_labels_recommendation_advisory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    decision = pending_decision(origin=WorkflowState.INTAKE)
    ai = ScriptedAI(decision)
    install_ai(monkeypatch, tmp_path, ai)
    run = FileStorage().create_run(source_at(tmp_path), run_id="waiting-run")

    result = cli.main(["advance", run.run_id])

    output = capsys.readouterr()
    assert result == 0
    assert "state: WAITING_HUMAN" in output.out
    assert "decision_id: expense-edit-policy" in output.out
    assert "origin_state: INTAKE" in output.out
    assert f"question: {decision.question}" in output.out
    assert f"context: {decision.context}" in output.out
    for option in decision.options:
        assert f"    {option.option_id}:" in output.out
        assert f"text: {option.text}" in output.out
        assert f"consequence: {option.consequence}" in output.out
    assert "RECOMMENDATION IS ADVISORY AND IS NOT THE HUMAN DECISION." in output.out
    assert "advisory_recommended_option: A" in output.out
    assert f"recommendation_rationale: {decision.recommendation_rationale}" in output.out


def test_cli_waiting_human_display_shows_superseded_decision_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ai = ScriptedAI()
    install_ai(monkeypatch, tmp_path, ai)
    old = pending_decision().model_copy(
        update={
            "decision_id": "old-edit-policy",
            "status": "RESOLVED",
            "answer": OptionSelection(option_id="A"),
        }
    )
    new = pending_decision(supersedes_decision_id=old.decision_id)
    storage = FileStorage()
    run = storage.create_run(source_at(tmp_path), run_id="supersession-run")
    run.state = WorkflowState.WAITING_HUMAN
    run.pending_decision_origin = WorkflowState.MODELING
    run.decisions = (old, new)
    storage.save_run(run)

    result = cli.main(["status", run.run_id])

    output = capsys.readouterr()
    assert result == 0
    assert "supersedes_decision_id: old-edit-policy" in output.out


def test_cli_answer_accepts_option_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ai = ScriptedAI()
    install_ai(monkeypatch, tmp_path, ai)
    storage, run_id = create_waiting_run(tmp_path)

    result = cli.main(["answer", run_id, "expense-edit-policy", "--option", "B"])

    output = capsys.readouterr()
    answer = storage.load_run(run_id).decisions[-1].answer
    assert result == 0
    assert "state: MODELING" in output.out
    assert answer == OptionSelection(option_id="B")


def test_cli_answer_accepts_option_with_exact_clarification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    clarification = "  Keep this spacing exactly.\nSecond line.  "
    ai = ScriptedAI()
    install_ai(monkeypatch, tmp_path, ai)
    storage, run_id = create_waiting_run(tmp_path)

    result = cli.main(
        [
            "answer",
            run_id,
            "expense-edit-policy",
            "--option",
            "B",
            "--clarification",
            clarification,
        ]
    )

    capsys.readouterr()
    answer = storage.load_run(run_id).decisions[-1].answer
    assert result == 0
    assert answer == OptionWithClarification(
        option_id="B", clarification=clarification
    )


def test_cli_answer_accepts_exact_custom_text_without_mapping_to_option(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    custom = "  Permit edits only after withdrawal.\nKeep exact.  "
    ai = ScriptedAI()
    install_ai(monkeypatch, tmp_path, ai)
    storage, run_id = create_waiting_run(tmp_path)

    result = cli.main(
        ["answer", run_id, "expense-edit-policy", "--custom", custom]
    )

    capsys.readouterr()
    answer = storage.load_run(run_id).decisions[-1].answer
    assert result == 0
    assert answer == CustomAnswer(text=custom)
    assert not isinstance(answer, (OptionSelection, OptionWithClarification))


@pytest.mark.parametrize(
    "arguments",
    (
        ["answer", "run", "decision"],
        ["answer", "run", "decision", "--option", "A", "--custom", "custom"],
        ["answer", "run", "decision", "--custom", "custom", "--clarification", "detail"],
    ),
)
def test_cli_rejects_invalid_or_mutually_exclusive_answer_arguments(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(arguments)

    output = capsys.readouterr()
    assert error.value.code == 2
    assert "error:" in output.err


def test_cli_handoff_rejects_non_done_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ai = ScriptedAI()
    install_ai(monkeypatch, tmp_path, ai)
    run = FileStorage().create_run(source_at(tmp_path), run_id="not-done")

    result = cli.main(["handoff", run.run_id])

    output = capsys.readouterr()
    assert result == 1
    assert output.out == ""
    assert "only for a DONE run" in output.err


def test_cli_handoff_done_prints_only_canonical_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ai = ScriptedAI()
    install_ai(monkeypatch, tmp_path, ai)
    storage = FileStorage()
    run = storage.create_run(source_at(tmp_path), run_id="done-run")
    path = storage.write_canonical(run.run_id, "# Canonical RDP\n")
    run.state = WorkflowState.DONE
    storage.save_run(run)

    result = cli.main(["handoff", run.run_id])

    output = capsys.readouterr()
    assert result == 0
    assert output.err == ""
    assert output.out == f"{path}\n"
    assert "run.json" not in output.out
    assert "source-prd.md" not in output.out
