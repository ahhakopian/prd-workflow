"""Narrow structured-output boundary for AI-backed workflow operations."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import TypeAdapter


ResultT = TypeVar("ResultT")


class AIExecutor(Protocol):
    """Execute one named operation and return its validated structured result."""

    def invoke(
        self,
        *,
        operation: str,
        payload: dict[str, object],
        result_type: type[ResultT],
    ) -> ResultT: ...


class CodexAIExecutor:
    """Invoke the locally installed Codex CLI with a strict output schema."""

    def invoke(
        self,
        *,
        operation: str,
        payload: dict[str, object],
        result_type: type[ResultT],
    ) -> ResultT:
        adapter = TypeAdapter(result_type)
        schema = adapter.json_schema()
        self._make_schema_strict(schema)
        request = json.dumps(
            {
                "instruction": (
                    "Perform only the supplied workflow analysis operation. "
                    "Use only the supplied payload as authority and return one JSON "
                    "value matching the output schema."
                ),
                "operation": operation,
                "payload": payload,
            },
            ensure_ascii=False,
        )

        with tempfile.TemporaryDirectory(prefix="rdp-codex-") as temporary:
            directory = Path(temporary)
            schema_path = directory / "result-schema.json"
            output_path = directory / "result.json"
            schema_path.write_text(json.dumps(schema), encoding="utf-8")

            try:
                completed = subprocess.run(
                    [
                        "codex",
                        "exec",
                        "--ignore-user-config",
                        "--ignore-rules",
                        "--ephemeral",
                        "--sandbox",
                        "read-only",
                        "--skip-git-repo-check",
                        "--output-schema",
                        str(schema_path),
                        "--output-last-message",
                        str(output_path),
                        "-",
                    ],
                    cwd=directory,
                    input=request,
                    text=True,
                    capture_output=True,
                    check=False,
                )
            except OSError as exc:
                raise RuntimeError(f"Codex execution could not start: {exc}") from exc

            if completed.returncode != 0:
                detail = completed.stderr.strip() or "no error detail"
                raise RuntimeError(f"Codex execution failed: {detail}")

            return adapter.validate_json(output_path.read_text(encoding="utf-8"))

    @classmethod
    def _make_schema_strict(cls, value: object) -> None:
        if isinstance(value, dict):
            value.pop("default", None)
            properties = value.get("properties")
            if isinstance(properties, dict):
                value["required"] = list(properties)
            for nested in value.values():
                cls._make_schema_strict(nested)
        elif isinstance(value, list):
            for nested in value:
                cls._make_schema_strict(nested)
