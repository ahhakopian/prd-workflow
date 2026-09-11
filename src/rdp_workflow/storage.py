"""Concrete filesystem persistence for WorkflowRun aggregates."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

from rdp_workflow.models import WorkflowRun


class FileStorage:
    """Store runs under the frozen ``.rdp/runs/<run-id>`` layout."""

    def __init__(self, root: Path = Path(".rdp")) -> None:
        self.root = Path(root)

    def create_run(self, source_path: Path, *, run_id: str | None = None) -> WorkflowRun:
        source = Path(source_path)
        if not source.is_file():
            raise FileNotFoundError(f"Source PRD does not exist: {source}")
        if source.suffix.lower() != ".md":
            raise ValueError("Source PRD must be a Markdown (.md) file")

        source_bytes = source.read_bytes()
        try:
            source_text = source_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Source PRD must be valid UTF-8") from exc
        if not source_text.strip():
            raise ValueError("Source PRD must not be empty")

        new_run = WorkflowRun(run_id=run_id or str(uuid4()))
        run_dir = self._run_dir(new_run.run_id)
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "source-prd.md").write_bytes(source_bytes)
        self.save_run(new_run)
        return new_run

    def load_run(self, run_id: str) -> WorkflowRun:
        run_path = self._run_dir(run_id) / "run.json"
        run = WorkflowRun.model_validate_json(run_path.read_text(encoding="utf-8"))
        if run.run_id != run_id:
            raise ValueError(
                f"Persisted run identity {run.run_id!r} does not match {run_id!r}"
            )
        return run

    def load_source(self, run_id: str) -> str:
        """Load the unchanged UTF-8 Source PRD for a persisted run."""

        return (self._run_dir(run_id) / "source-prd.md").read_bytes().decode("utf-8")

    def save_run(self, run: WorkflowRun) -> None:
        run_dir = self._run_dir(run.run_id)
        if not run_dir.is_dir():
            raise FileNotFoundError(f"Run directory does not exist: {run_dir}")

        destination = run_dir / "run.json"
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=run_dir,
                prefix=".run-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(run.model_dump_json(indent=2))
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, destination)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def write_canonical(self, run_id: str, markdown: str) -> Path:
        """Atomically replace the one final Canonical Markdown candidate."""

        run_dir = self._run_dir(run_id)
        if not run_dir.is_dir():
            raise FileNotFoundError(f"Run directory does not exist: {run_dir}")

        destination = run_dir / "canonical-rdp.md"
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=run_dir,
                prefix=".canonical-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(markdown)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, destination)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
        return destination

    def run_directory(self, run_id: str) -> Path:
        """Return the concrete directory for a run without reading its files."""

        return self._run_dir(run_id)

    def _run_dir(self, run_id: str) -> Path:
        if not run_id or run_id in {".", ".."} or Path(run_id).name != run_id:
            raise ValueError("run_id must be one non-empty path component")
        return self.root / "runs" / run_id
