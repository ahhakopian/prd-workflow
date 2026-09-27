from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from prd_workflow.ai import (
    CONVERGENCE_RESULT_TYPE,
    CodexAIExecutor,
    load_committed_schema,
    load_prompt,
    result_type_for_operation,
)
from prd_workflow.ai_contracts import ConvergencePassOutput


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
        observed["schema_name"] = schema_path.name
        output_path.write_text(
            ConvergencePassOutput(outcome="PASS").model_dump_json(), encoding="utf-8"
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = CodexAIExecutor().invoke(
        operation="review_convergence",
        payload={"source_prd": "# Product"},
        result_type=CONVERGENCE_RESULT_TYPE,
    )

    assert result == ConvergencePassOutput(outcome="PASS")
    assert "--ignore-user-config" in observed["command"]
    assert "--ignore-rules" in observed["command"]
    assert "--ephemeral" in observed["command"]
    assert observed["command"][observed["command"].index("--sandbox") + 1] == "read-only"
    assert "--output-schema" in observed["command"]
    assert "--output-last-message" in observed["command"]
    assert observed["request"] == {
        "instruction": load_prompt("review_convergence"),
        "operation": "review_convergence",
        "payload": {"source_prd": "# Product"},
    }
    assert observed["schema_name"] == "convergence.schema.json"
    assert observed["schema"] == load_committed_schema("review_convergence")
    assert observed["schema"]["discriminator"]["propertyName"] == "outcome"
    assert len(observed["schema"]["oneOf"]) == 3


def test_codex_adapter_reports_local_validation_failure_with_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text('{"unexpected":true}', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(
        RuntimeError,
        match=(
            "AI operation 'review_convergence' failed during local "
            "result-type validation"
        ),
    ) as error:
        CodexAIExecutor().invoke(
            operation="review_convergence",
            payload={},
            result_type=CONVERGENCE_RESULT_TYPE,
        )

    assert isinstance(error.value.__cause__, ValidationError)
    assert calls == 1


def test_codex_adapter_reports_launch_failure_with_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fake_run(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        raise FileNotFoundError("codex executable missing")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(
        RuntimeError,
        match="AI operation 'review_convergence' failed during process launch",
    ) as error:
        CodexAIExecutor().invoke(
            operation="review_convergence",
            payload={},
            result_type=CONVERGENCE_RESULT_TYPE,
        )

    assert isinstance(error.value.__cause__, FileNotFoundError)
    assert calls == 1


def test_codex_adapter_reports_malformed_json_with_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text("{malformed", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(
        RuntimeError,
        match=(
            "AI operation 'review_convergence' failed during structured-output "
            "decoding"
        ),
    ) as error:
        CodexAIExecutor().invoke(
            operation="review_convergence",
            payload={},
            result_type=CONVERGENCE_RESULT_TYPE,
        )

    assert isinstance(error.value.__cause__, json.JSONDecodeError)
    assert calls == 1


def test_codex_adapter_reports_provider_failure_with_operation_without_retrying(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(command, 7, "", "provider unavailable")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(
        RuntimeError,
        match=(
            "AI operation 'review_convergence' failed during provider execution: "
            "provider unavailable"
        ),
    ):
        CodexAIExecutor().invoke(
            operation="review_convergence",
            payload={},
            result_type=CONVERGENCE_RESULT_TYPE,
        )

    assert calls == 1


@pytest.mark.parametrize(
    "operation",
    (
        "intake",
        "derive_domain",
        "derive_capabilities",
        "derive_architecture",
        "review_convergence",
        "compose_canonical",
        "audit_canonical",
    ),
)
def test_codex_adapter_uses_correct_packaged_prompt_for_every_operation(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_request: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed_request.update(json.loads(str(kwargs["input"])))
        return subprocess.CompletedProcess(command, 7, "", "stop after request capture")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="stop after request capture"):
        CodexAIExecutor().invoke(
            operation=operation,
            payload={"runtime": "data"},
            result_type=result_type_for_operation(operation),
        )

    assert observed_request["instruction"] == load_prompt(operation)
    assert observed_request["operation"] == operation
    assert observed_request["payload"] == {"runtime": "data"}


def test_codex_adapter_rejects_unknown_operations_explicitly() -> None:
    with pytest.raises(ValueError, match="unknown AI operation"):
        CodexAIExecutor().invoke(
            operation="unknown",
            payload={},
            result_type=CONVERGENCE_RESULT_TYPE,
        )
