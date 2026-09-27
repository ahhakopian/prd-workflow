"""Narrow structured-output boundary for AI-backed workflow operations."""

from __future__ import annotations

import json
import subprocess
import tempfile
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, Protocol, TypeVar

from pydantic import TypeAdapter, ValidationError

from prd_workflow.ai_contracts import (
    ArchitectureOutput,
    AuditOutput,
    CapabilitiesOutput,
    ConvergenceOutput,
    DomainOutput,
    MaterialDecisionDraft,
)
from prd_workflow.models import CanonicalPRD, PendingTask


ResultT = TypeVar("ResultT")

INTAKE_RESULT_TYPE = MaterialDecisionDraft | None
DOMAIN_RESULT_TYPE = DomainOutput
CAPABILITIES_RESULT_TYPE = CapabilitiesOutput
ARCHITECTURE_RESULT_TYPE = ArchitectureOutput
CONVERGENCE_RESULT_TYPE = ConvergenceOutput
CANONICAL_RESULT_TYPE = CanonicalPRD
CANONICAL_AUDIT_RESULT_TYPE = AuditOutput

_PROMPT_FILES = {
    "intake": "intake.md",
    "derive_domain": "domain.md",
    "derive_capabilities": "capabilities.md",
    "derive_architecture": "architecture.md",
    "review_convergence": "convergence.md",
    "compose_canonical": "canonical-compose.md",
    "audit_canonical": "canonical-audit.md",
}

_SCHEMA_FILES = {
    "intake": "intake.schema.json",
    "derive_domain": "domain.schema.json",
    "derive_capabilities": "capabilities.schema.json",
    "derive_architecture": "architecture.schema.json",
    "review_convergence": "convergence.schema.json",
    "compose_canonical": "canonical-prd.schema.json",
    "audit_canonical": "canonical-audit.schema.json",
}

_RESULT_TYPES: dict[str, Any] = {
    "intake": INTAKE_RESULT_TYPE,
    "derive_domain": DOMAIN_RESULT_TYPE,
    "derive_capabilities": CAPABILITIES_RESULT_TYPE,
    "derive_architecture": ARCHITECTURE_RESULT_TYPE,
    "review_convergence": CONVERGENCE_RESULT_TYPE,
    "compose_canonical": CANONICAL_RESULT_TYPE,
    "audit_canonical": CANONICAL_AUDIT_RESULT_TYPE,
}


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
        expected_result_type = result_type_for_operation(operation)
        if result_type != expected_result_type:
            raise ValueError(
                f"result_type does not match the fixed contract for operation "
                f"{operation!r}"
            )
        return self._invoke_prepared(
            operation=operation, payload=payload, result_type=result_type,
            instruction=load_prompt(operation), schema=load_committed_schema(operation),
            use_committed_schema_path=True,
        )

    def invoke_task(self, task: PendingTask) -> object:
        """Execute the exact persisted model request issued by WorkflowService."""

        if task.kind != "model" or task.operation is None or task.payload is None:
            raise ValueError("CodexAIExecutor requires a prepared model task")
        return self._invoke_prepared(
            operation=task.operation, payload=task.payload,
            result_type=result_type_for_operation(task.operation),
            instruction=task.instruction, schema=task.output_schema,
            use_committed_schema_path=False,
        )

    def _invoke_prepared(
        self, *, operation: str, payload: dict[str, object],
        result_type: type[ResultT], instruction: str,
        schema: dict[str, object], use_committed_schema_path: bool,
    ) -> ResultT:
        adapter = TypeAdapter(result_type)
        request = json.dumps(
            {
                "instruction": instruction,
                "operation": operation,
                "payload": payload,
            },
            ensure_ascii=False,
        )

        schema_asset = schema_resource(operation)
        with resources.as_file(schema_asset) as committed_schema_path, tempfile.TemporaryDirectory(
            prefix="prd-codex-"
        ) as temporary:
            directory = Path(temporary)
            output_path = directory / "result.json"
            schema = json.loads(json.dumps(schema))
            wrapped = schema.get("type") != "object"
            schema_path = committed_schema_path
            if not use_committed_schema_path and not wrapped:
                schema_path = directory / "task-schema.json"
                schema_path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
            if wrapped:
                definitions = schema.pop("$defs", {})
                schema.pop("discriminator", None)
                if "oneOf" in schema:
                    schema["anyOf"] = schema.pop("oneOf")
                provider_schema = {
                    "$defs": definitions,
                    "type": "object",
                    "properties": {"result": schema},
                    "required": ["result"],
                    "additionalProperties": False,
                }
                schema_path = directory / "provider-schema.json"
                schema_path.write_text(
                    json.dumps(provider_schema, ensure_ascii=False), encoding="utf-8"
                )

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
                raise RuntimeError(
                    f"AI operation {operation!r} failed during process launch: {exc}"
                ) from exc

            if completed.returncode != 0:
                detail = completed.stderr.strip() or "no error detail"
                raise RuntimeError(
                    f"AI operation {operation!r} failed during provider execution: "
                    f"{detail}"
                )

            try:
                output = json.loads(output_path.read_text(encoding="utf-8"))
                if wrapped:
                    output = output["result"]
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
                raise RuntimeError(
                    f"AI operation {operation!r} failed during structured-output "
                    f"decoding: {exc}"
                ) from exc
            try:
                return adapter.validate_python(output)
            except ValidationError as exc:
                raise RuntimeError(
                    f"AI operation {operation!r} failed during local result-type "
                    f"validation: {exc}"
                ) from exc


def load_prompt(operation: str) -> str:
    """Load one fixed operation prompt from the installed package."""

    return _resource("prompts", _mapped_name(_PROMPT_FILES, operation, "prompt")).read_text(
        encoding="utf-8"
    )


def schema_resource(operation: str) -> Traversable:
    """Return the committed schema resource for one fixed operation."""

    return _resource("schemas", _mapped_name(_SCHEMA_FILES, operation, "schema"))


def load_committed_schema(operation: str) -> dict[str, object]:
    """Load one committed strict JSON Schema from the installed package."""

    return json.loads(schema_resource(operation).read_text(encoding="utf-8"))


def result_type_for_operation(operation: str) -> Any:
    """Return the fixed Pydantic result type used by one AI operation."""

    try:
        return _RESULT_TYPES[operation]
    except KeyError as exc:
        raise ValueError(f"unknown AI operation: {operation!r}") from exc


def generated_strict_schema(operation: str) -> dict[str, object]:
    """Generate the deterministic strict schema for one fixed result type."""

    schema = TypeAdapter(result_type_for_operation(operation)).json_schema()
    _make_schema_strict(schema)
    return schema


def canonical_schema_json(schema: dict[str, object]) -> str:
    """Serialize committed schemas deterministically."""

    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _resource(directory: str, filename: str) -> Traversable:
    return resources.files("prd_workflow").joinpath(directory, filename)


def _mapped_name(mapping: dict[str, str], operation: str, kind: str) -> str:
    try:
        return mapping[operation]
    except KeyError as exc:
        raise ValueError(f"unknown AI operation for {kind}: {operation!r}") from exc


def _make_schema_strict(value: object) -> None:
    if isinstance(value, dict):
        value.pop("default", None)
        properties = value.get("properties")
        if isinstance(properties, dict):
            value["required"] = list(properties)
        for nested in value.values():
            _make_schema_strict(nested)
    elif isinstance(value, list):
        for nested in value:
            _make_schema_strict(nested)
