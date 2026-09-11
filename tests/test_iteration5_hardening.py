from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from rdp_workflow.models import (
    Decision,
    DecisionOption,
    OptionSelection,
    WorkflowState,
)
from rdp_workflow.storage import FileStorage
from rdp_workflow.workflow import WorkflowService


class RecordingAI:
    def __init__(self, result: object = None) -> None:
        self.result = result
        self.calls: list[str] = []

    def invoke(
        self,
        *,
        operation: str,
        payload: dict[str, object],
        result_type: type[Any],
    ) -> Any:
        self.calls.append(operation)
        return self.result


def _source(tmp_path: Path, content: bytes = b"# Expense reimbursement\n") -> Path:
    path = tmp_path / "source.md"
    path.write_bytes(content)
    return path


def _pending_decision(
    *, origin: WorkflowState = WorkflowState.MODELING
) -> Decision:
    return Decision(
        decision_id="expense-edit-policy",
        classification="MATERIAL",
        origin_state=origin,
        question="May an employee edit a pending expense report?",
        context="The answer changes product behavior and permissions.",
        options=(
            DecisionOption(
                option_id="A",
                text="Do not allow edits.",
                consequence="Submitted reports remain immutable.",
            ),
            DecisionOption(
                option_id="B",
                text="Allow edits before review.",
                consequence="Pending reports may change.",
            ),
        ),
        recommended_option_id="A",
        recommendation_rationale="Immutability is simpler.",
    )


def _service_with_run(tmp_path: Path) -> tuple[WorkflowService, RecordingAI, str]:
    ai = RecordingAI()
    storage = FileStorage(tmp_path / ".rdp")
    run = storage.create_run(_source(tmp_path))
    return WorkflowService(storage, ai), ai, run.run_id


def _assert_source_integrity_blocks(
    service: WorkflowService, ai: RecordingAI, run_id: str
) -> None:
    blocked = service.advance(run_id)

    assert blocked.state is WorkflowState.BLOCKED
    assert blocked.diagnostics
    assert "Source PRD integrity failure" in blocked.diagnostics[0]
    assert ai.calls == []
    assert service.status(run_id).state is WorkflowState.BLOCKED


def test_unchanged_source_integrity_survives_process_restart(tmp_path: Path) -> None:
    storage = FileStorage(tmp_path / ".rdp")
    run = storage.create_run(_source(tmp_path))
    ai = RecordingAI()

    restarted = WorkflowService(FileStorage(storage.root), ai)
    advanced = restarted.advance(run.run_id)

    assert advanced.state is WorkflowState.MODELING
    assert ai.calls == ["intake"]


def test_valid_utf8_source_mutation_blocks_before_ai(tmp_path: Path) -> None:
    service, ai, run_id = _service_with_run(tmp_path)
    source = service.storage.run_directory(run_id) / "source-prd.md"
    source.write_text("# Changed authority\n", encoding="utf-8")

    _assert_source_integrity_blocks(service, ai, run_id)


def test_source_deletion_blocks_before_ai(tmp_path: Path) -> None:
    service, ai, run_id = _service_with_run(tmp_path)
    source = service.storage.run_directory(run_id) / "source-prd.md"
    source.unlink()

    _assert_source_integrity_blocks(service, ai, run_id)


def test_invalid_byte_source_replacement_blocks_before_ai(tmp_path: Path) -> None:
    service, ai, run_id = _service_with_run(tmp_path)
    source = service.storage.run_directory(run_id) / "source-prd.md"
    source.write_bytes(b"\xff\xfe")

    _assert_source_integrity_blocks(service, ai, run_id)


def test_source_integrity_block_preserves_accepted_human_authority(
    tmp_path: Path,
) -> None:
    service, ai, run_id = _service_with_run(tmp_path)
    run = service.status(run_id)
    resolved = _pending_decision(origin=WorkflowState.INTAKE).model_copy(
        update={"status": "RESOLVED", "answer": OptionSelection(option_id="B")}
    )
    run.state = WorkflowState.MODELING
    run.decisions = (resolved,)
    service.storage.save_run(run)
    (service.storage.run_directory(run_id) / "source-prd.md").write_text(
        "# Mutated\n", encoding="utf-8"
    )

    _assert_source_integrity_blocks(service, ai, run_id)
    restored = service.status(run_id)

    assert restored.decisions == (resolved,)
    assert restored.decisions[0].answer == OptionSelection(option_id="B")


@pytest.mark.parametrize("kind", ("missing", "non_markdown", "invalid_utf8", "empty"))
def test_invalid_source_before_creation_creates_no_run(
    tmp_path: Path, kind: str
) -> None:
    storage = FileStorage(tmp_path / ".rdp")
    if kind == "missing":
        source = tmp_path / "missing.md"
        expected = FileNotFoundError
    elif kind == "non_markdown":
        source = tmp_path / "source.txt"
        source.write_text("content", encoding="utf-8")
        expected = ValueError
    elif kind == "invalid_utf8":
        source = _source(tmp_path, b"\xff")
        expected = ValueError
    else:
        source = _source(tmp_path, b" \n\t")
        expected = ValueError

    with pytest.raises(expected):
        storage.create_run(source)

    assert not (storage.root / "runs").exists()


def test_waiting_without_pending_material_decision_becomes_blocked(
    tmp_path: Path,
) -> None:
    service, ai, run_id = _service_with_run(tmp_path)
    run = service.status(run_id)
    run.state = WorkflowState.WAITING_HUMAN
    service.storage.save_run(run)

    blocked = service.advance(run_id)

    assert blocked.state is WorkflowState.BLOCKED
    assert blocked.diagnostics == (
        "WAITING_HUMAN requires exactly one pending MATERIAL Decision.",
    )
    assert ai.calls == []


def test_inconsistent_pending_decision_origin_becomes_blocked(tmp_path: Path) -> None:
    service, ai, run_id = _service_with_run(tmp_path)
    run = service.status(run_id)
    run.state = WorkflowState.WAITING_HUMAN
    run.decisions = (_pending_decision(),)
    run.pending_decision_origin = WorkflowState.INTAKE
    service.storage.save_run(run)

    blocked = service.advance(run_id)

    assert blocked.state is WorkflowState.BLOCKED
    assert blocked.diagnostics
    assert "pending_decision_origin" in blocked.diagnostics[0]
    assert ai.calls == []


def test_modeling_with_pending_material_decision_becomes_blocked(
    tmp_path: Path,
) -> None:
    service, ai, run_id = _service_with_run(tmp_path)
    run = service.status(run_id)
    run.state = WorkflowState.MODELING
    run.decisions = (_pending_decision(),)
    service.storage.save_run(run)

    blocked = service.advance(run_id)

    assert blocked.state is WorkflowState.BLOCKED
    assert blocked.diagnostics
    assert ai.calls == []


def test_canonicalization_without_converged_model_becomes_blocked(
    tmp_path: Path,
) -> None:
    service, ai, run_id = _service_with_run(tmp_path)
    run = service.status(run_id)
    run.state = WorkflowState.CANONICALIZATION
    service.storage.save_run(run)

    blocked = service.advance(run_id)

    assert blocked.state is WorkflowState.BLOCKED
    assert blocked.diagnostics == (
        "CANONICALIZATION requires a complete ModelingResult.",
    )
    assert ai.calls == []


@pytest.mark.parametrize("kind", ("missing", "corrupt"))
def test_untrusted_run_json_error_does_not_fabricate_blocked_run(
    tmp_path: Path, kind: str
) -> None:
    service, ai, run_id = _service_with_run(tmp_path)
    run_path = service.storage.run_directory(run_id) / "run.json"
    if kind == "missing":
        run_path.unlink()
        expected = FileNotFoundError
    else:
        run_path.write_text("{truncated", encoding="utf-8")
        expected = ValidationError

    with pytest.raises(expected):
        service.advance(run_id)

    assert ai.calls == []
    if kind == "missing":
        assert not run_path.exists()
    else:
        assert run_path.read_text(encoding="utf-8") == "{truncated"


def test_run_id_mismatch_remains_storage_error_without_blocking(
    tmp_path: Path,
) -> None:
    service, ai, run_id = _service_with_run(tmp_path)
    run_path = service.storage.run_directory(run_id) / "run.json"
    persisted = json.loads(run_path.read_text(encoding="utf-8"))
    persisted["run_id"] = "different-run"
    run_path.write_text(json.dumps(persisted), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        service.advance(run_id)

    assert ai.calls == []
    assert json.loads(run_path.read_text(encoding="utf-8"))["state"] == "INTAKE"
