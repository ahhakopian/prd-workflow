from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from rdp_workflow.models import (
    CustomAnswer,
    Decision,
    DecisionOption,
    OptionSelection,
    OptionWithClarification,
    WorkflowState,
)
from rdp_workflow.storage import FileStorage


def storage_at(tmp_path: Path) -> FileStorage:
    return FileStorage(tmp_path / ".rdp")


def resolved_decision(answer: OptionSelection | OptionWithClarification | CustomAnswer) -> Decision:
    return Decision(
        decision_id="decision-1",
        classification="MATERIAL",
        origin_state=WorkflowState.INTAKE,
        question="Which policy applies?",
        context="The policy changes observable behavior.",
        options=(
            DecisionOption(option_id="A", text="Policy A", consequence="Effect A"),
            DecisionOption(option_id="B", text="Policy B", consequence="Effect B"),
        ),
        recommended_option_id="A",
        recommendation_rationale="Policy A is simpler.",
        status="RESOLVED",
        answer=answer,
    )


def create_source(tmp_path: Path, content: bytes = b"# Product\r\n\r\nExact bytes.\r\n") -> Path:
    source = tmp_path / "input.md"
    source.write_bytes(content)
    return source


def test_run_starts_in_intake_and_source_is_copied_unchanged(tmp_path: Path) -> None:
    source_bytes = "# Café\r\n\r\nPreserve me.  \r\n".encode()
    source = create_source(tmp_path, source_bytes)
    storage = storage_at(tmp_path)

    run = storage.create_run(source)

    assert run.state is WorkflowState.INTAKE
    assert run.source_prd_sha256 == hashlib.sha256(source_bytes).hexdigest()
    assert (storage.run_directory(run.run_id) / "source-prd.md").read_bytes() == source_bytes
    run_json = storage.run_directory(run.run_id) / "run.json"
    assert json.loads(run_json.read_text(encoding="utf-8"))["source_prd_sha256"] == (
        hashlib.sha256(source_bytes).hexdigest()
    )


def test_load_source_preserves_exact_source_text(tmp_path: Path) -> None:
    source_bytes = "# Café\r\n\r\nPreserve me.  \r\n".encode()
    storage = storage_at(tmp_path)
    run = storage.create_run(create_source(tmp_path, source_bytes))

    assert storage.load_source(run.run_id).encode() == source_bytes


def test_missing_and_empty_source_fail_deterministically(tmp_path: Path) -> None:
    storage = storage_at(tmp_path)

    with pytest.raises(FileNotFoundError, match="Source PRD does not exist"):
        storage.create_run(tmp_path / "missing.md")

    empty = create_source(tmp_path, b" \n\t")
    with pytest.raises(ValueError, match="must not be empty"):
        storage.create_run(empty)


def test_non_markdown_and_non_utf8_source_fail_deterministically(tmp_path: Path) -> None:
    storage = storage_at(tmp_path)
    text_file = tmp_path / "input.txt"
    text_file.write_text("content", encoding="utf-8")
    invalid_utf8 = create_source(tmp_path, b"\xff")

    with pytest.raises(ValueError, match="Markdown"):
        storage.create_run(text_file)
    with pytest.raises(ValueError, match="valid UTF-8"):
        storage.create_run(invalid_utf8)


def test_explicit_state_survives_save_and_process_restart(tmp_path: Path) -> None:
    source = create_source(tmp_path)
    root = tmp_path / ".rdp"
    first_process = FileStorage(root)
    run = first_process.create_run(source)
    run.state = WorkflowState.CANONICALIZATION
    first_process.save_run(run)

    second_process = FileStorage(root)
    restored = second_process.load_run(run.run_id)

    assert restored.state is WorkflowState.CANONICALIZATION


@pytest.mark.parametrize(
    "answer",
    [
        OptionSelection(option_id="A"),
        OptionWithClarification(
            option_id="B",
            clarification="  Exact clarification.\nKeep whitespace.  ",
        ),
        CustomAnswer(text="  Exact custom answer.\nKeep whitespace.  "),
    ],
)
def test_every_human_answer_form_survives_storage(
    tmp_path: Path,
    answer: OptionSelection | OptionWithClarification | CustomAnswer,
) -> None:
    storage = storage_at(tmp_path)
    run = storage.create_run(create_source(tmp_path))
    run.decisions = (resolved_decision(answer),)
    storage.save_run(run)

    restored_answer = storage.load_run(run.run_id).decisions[0].answer

    assert restored_answer == answer
    assert type(restored_answer) is type(answer)


def test_option_and_clarification_remain_separate_exact_fields_after_restart(
    tmp_path: Path,
) -> None:
    clarification = "  Only before any review action.\nReset the timestamp.  "
    storage = storage_at(tmp_path)
    run = storage.create_run(create_source(tmp_path))
    run.decisions = (
        resolved_decision(
            OptionWithClarification(option_id="B", clarification=clarification)
        ),
    )
    storage.save_run(run)

    answer = storage.load_run(run.run_id).decisions[0].answer

    assert isinstance(answer, OptionWithClarification)
    assert answer.option_id == "B"
    assert answer.clarification == clarification


def test_file_presence_cannot_change_or_recompute_state(tmp_path: Path) -> None:
    storage = storage_at(tmp_path)
    run = storage.create_run(create_source(tmp_path))
    run.state = WorkflowState.MODELING
    storage.save_run(run)
    run_dir = storage.run_directory(run.run_id)

    (run_dir / "canonical-rdp.md").write_text("# Untrusted file", encoding="utf-8")
    (run_dir / "anything-else.json").write_text(
        '{"state": "DONE"}', encoding="utf-8"
    )

    restarted = FileStorage(storage.root).load_run(run.run_id)

    assert restarted.state is WorkflowState.MODELING


def test_atomic_save_leaves_no_temporary_file(tmp_path: Path) -> None:
    storage = storage_at(tmp_path)
    run = storage.create_run(create_source(tmp_path))
    run.state = WorkflowState.WAITING_HUMAN

    storage.save_run(run)

    run_dir = storage.run_directory(run.run_id)
    assert storage.load_run(run.run_id).state is WorkflowState.WAITING_HUMAN
    assert list(run_dir.glob(".run-*.tmp")) == []
