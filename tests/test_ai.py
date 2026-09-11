from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from rdp_workflow.ai import CodexAIExecutor


class ExampleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    detail: str | None = None


def test_codex_adapter_requests_strict_schema_and_validates_final_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        schema_path = Path(command[command.index("--output-schema") + 1])
        output_path = Path(command[command.index("--output-last-message") + 1])
        observed["command"] = command
        observed["request"] = json.loads(str(kwargs["input"]))
        observed["schema"] = json.loads(schema_path.read_text(encoding="utf-8"))
        output_path.write_text(
            '{"answer":"validated","detail":null}', encoding="utf-8"
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = CodexAIExecutor().invoke(
        operation="intake",
        payload={"source_prd": "# Product"},
        result_type=ExampleResult,
    )

    assert result == ExampleResult(answer="validated")
    assert "--ignore-user-config" in observed["command"]
    assert "--ignore-rules" in observed["command"]
    assert "--ephemeral" in observed["command"]
    assert observed["command"][observed["command"].index("--sandbox") + 1] == "read-only"
    assert "--output-schema" in observed["command"]
    assert "--output-last-message" in observed["command"]
    assert observed["request"] == {
        "instruction": (
            "Perform only the supplied workflow analysis operation. Use only the "
            "supplied payload as authority and return one JSON value matching the "
            "output schema."
        ),
        "operation": "intake",
        "payload": {"source_prd": "# Product"},
    }
    assert observed["schema"]["required"] == ["answer", "detail"]


def test_codex_adapter_rejects_output_that_does_not_match_the_result_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text('{"unexpected":true}', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ValidationError):
        CodexAIExecutor().invoke(
            operation="intake",
            payload={},
            result_type=ExampleResult,
        )


def test_codex_adapter_reports_one_failed_invocation_without_retrying(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(command, 7, "", "provider unavailable")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        CodexAIExecutor().invoke(
            operation="intake",
            payload={},
            result_type=ExampleResult,
        )

    assert calls == 1
