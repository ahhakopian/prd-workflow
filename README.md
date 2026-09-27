# PRD Workflow

PRD turns one Source PRD into one audited Canonical PRD. Both execution modes
share the same six-state workflow, human authority rules, and handoff. Runs
live under `.prd/runs/<run-id>/` and resume after a process restart.

Start with a UTF-8 Markdown file:

```console
prd start path/to/source-prd.md
```

## Interactive Codex mode

The current Codex session performs each reasoning task. PRD prepares the
authoritative request and commits its validated result; these commands do not
launch an internal model:

```console
prd next <run-id> --json
prd submit <run-id> --task-token <token-from-next> --input result.json
```

`next` returns one task with its instruction, context payload, constraints,
JSON output schema, and token. Write only the requested JSON value to
`result.json`. Use `--input -` to read it from stdin. Repeat `next` and
`submit` until the run pauses for a human decision or reaches `DONE` or
`BLOCKED`. Repeating `next` before submission returns the same task;
submitted tokens cannot be reused.

For a `human` task, show the complete question, options, consequences, and
advisory recommendation to the human. **Only the human may choose or author an
answer.** Submit their explicit answer as one of:

```json
{"kind":"option_selection","option_id":"A"}
{"kind":"option_with_clarification","option_id":"A","clarification":"Exact human text"}
{"kind":"custom","text":"Exact human decision"}
```

The selected option and any clarification remain distinct, equally
authoritative fields. A custom answer is preserved as written.

## Direct mode

```console
prd run <run-id>
prd run <run-id> --max-tasks 100
```

`run` invokes the internal Codex provider for model tasks through the same
validation and commit path. It stops at a human decision, `DONE`, `BLOCKED`,
or its task limit (50 by default). A task-limit stop is resumable and exits
nonzero. Direct mode never answers a human question. You may switch modes on
the same run.

## Status, handoff, and compatibility

```console
prd status <run-id>
prd handoff <run-id>
```

`handoff` prints only the path to the validated `canonical-prd.md` of a
`DONE` run. SpecKit is not executed by PRD. The older `prd advance` and
`prd answer` commands remain as deprecated compatibility adapters. New
interactive Codex workflows use `next` and `submit`.
