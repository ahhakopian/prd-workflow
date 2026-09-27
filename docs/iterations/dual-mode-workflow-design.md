# Dual-mode PRD workflow refactor — design for implementation

Status: design only. This document specifies a narrow refactor of the current
Iteration 1 implementation; it does not change the PRD methodology or the six
workflow states in `docs/contracts/workflow.md`.

## 1. Current architecture and coupling

`cli.py` constructs `WorkflowService(FileStorage(), CodexAIExecutor())` for
every command. `advance` loads `run.json`, checks controlling invariants and
the immutable Source PRD, then dispatches by state in `workflow.py`:

| State | One current `advance` call | Provider calls |
| --- | --- | --- |
| `INTAKE` | Analyze intake, then enter `MODELING` or `WAITING_HUMAN` | `intake` |
| `MODELING` | Rebuild all models, review convergence, then route | `derive_domain`, `derive_capabilities`, `derive_architecture`, `review_convergence` |
| `CANONICALIZATION` | Compose, render, validate, optionally audit, then route | `compose_canonical`, optionally `audit_canonical` |
| `WAITING_HUMAN` | Refuses `advance`; `answer` accepts authority and routes | None |

The coupling is at `_advance_intake`, `_advance_modeling`, and
`_advance_canonicalization`: these functions both call `analysis.py` or
`canonical.py` with `self.ai` and mutate/persist the FSM. Those modules build
provider payloads at their `ai.invoke` call sites. `ai.py` owns the fixed
operation-to-prompt/schema/type maps and invokes `codex exec` through
`subprocess.run`. Thus an interactive Codex session calling `advance` launches
a second Codex process. The full modeling sequence currently has no durable
checkpoint between its four provider calls. `FileStorage.save_run` atomically
replaces `run.json`; the successful canonical file is written before `DONE`
is saved. `answer` has its own service entry point without task freshness.

## 2. Target architecture and responsibility

```text
CLI next / submit ─┐
                   ├─ WorkflowService: prepare → validate → commit
CLI run ─ provider ┘          │                  │
                       shared operation     six-state FSM,
                       prompt/schema/type    authority, artifacts,
                       definitions           audit, storage, handoff
```

Keep `WorkflowRun` as the sole authoritative aggregate, `_LEGAL_TRANSITIONS`
as the sole lifecycle topology, `FileStorage` as concrete storage, and the
existing `Decision`, modeling, convergence, canonical, audit, and handoff
types/rules. Introduce an **internal operation cursor**, not another workflow
state. It selects one of the seven existing AI operations within `INTAKE`,
`MODELING`, or `CANONICALIZATION`. Human input is the eighth task kind.

Extract request construction from the AI-backed helpers in `analysis.py` and
`canonical.py` into pure shared preparation functions. Extract their
Pydantic parsing and result-to-domain conversion into pure shared acceptance
functions. `CodexAIExecutor` executes a prepared model task; it does not build
a different prompt or payload. `WorkflowService.submit` alone applies accepted
results, decides the next cursor/FSM state, and persists. `run` repeatedly
prepares the same task, invokes the internal provider for model tasks, and
passes its output through that same submit path. It stops at human tasks.
`next` and `submit` never construct or call `CodexAIExecutor`.

## 3. Internal contracts

Suggested interfaces (names may change during coding; behavior may not):

```python
PreparedTask = ModelTask | HumanTask

def prepare_task(run: WorkflowRun, source_text: str | None) -> PreparedTask: ...
def validate_result(task: ModelTask, raw_json: object) -> object: ...
def apply_submission(run: WorkflowRun, task: PreparedTask,
                     validated_input: object) -> WorkflowRun: ...

class WorkflowService:
    def next(self, run_id: str) -> TaskEnvelope | TerminalEnvelope: ...
    def submit(self, run_id: str, task_token: str,
               raw_json: object) -> WorkflowRun: ...
    def run(self, run_id: str, max_tasks: int = 50) -> RunOutcome: ...

class CodexAIExecutor:
    def invoke(self, task: ModelTask) -> object: ...
```

`ModelTask` contains `operation`, exact `instruction` from `load_prompt`,
exact `payload` currently passed by the corresponding helper, committed
`output_schema`, and the fixed Pydantic result type identifier. The prompt
and schema are presentation constraints; local Pydantic validation remains
mandatory. Provider-specific wrapping of root `null`/union schemas stays
inside `CodexAIExecutor`, and its output is unwrapped before shared
validation. The direct adapter serializes its typed result to the same JSON
value accepted by `submit`. A `HumanTask` contains the current pending `Decision` verbatim,
its `decision_id`, and the three permitted `HumanAnswer` forms. Its
recommendation is visibly advisory. It contains no model execution request.

Persist these new, optional `WorkflowRun` fields with defaults for old files:

- `revision: int = 0`, incremented for every committed aggregate mutation;
- `operation_cursor: str | None = None`, with `None` meaning the first operation
  for the current active state on legacy runs;
- `modeling_progress = None`, a typed partial set of validated Domain,
  Capabilities, and Architecture operation outputs for the current full
  rebuild only;
- `pending_task = None`, one task snapshot with `kind`, operation/decision ID,
  issuing `state`, `operation_cursor`, `revision`, exact request/answer
  contract, and a random 256-bit opaque token.

Issuing a task increments `revision`, then records that new value in the
snapshot. The pending snapshot makes repeated `next` idempotent across process restarts:
it returns the same task and token until submission or an authorized mutation
consumes it. For a model task, the snapshot includes the exact instruction,
payload, and schema, so the current Codex and the direct adapter see identical
requests. Compare a stored contract fingerprint with the installed
prompt/schema/type definitions. If those definitions change after issue,
reject submission as stale and replace the task on the next `next`; do not
silently validate an old response against a new contract. Keep the token in
the private run file and compare with `hmac.compare_digest`. It is a freshness
capability within the trusted local filesystem, not an authentication system.

Cursor sequence and commit effects:

| Submitted task | Accepted effect | Next cursor or state |
| --- | --- | --- |
| `intake` | Convert draft to one pending Decision or no blocker | `WAITING_HUMAN` or `MODELING` |
| `derive_domain` | Save validated Domain output in `modeling_progress` | `derive_capabilities` in `MODELING` |
| `derive_capabilities` | Save validated Capabilities output | `derive_architecture` in `MODELING` |
| `derive_architecture` | Save validated Architecture output; assemble current `ModelingResult` | `review_convergence` in `MODELING` |
| `review_convergence` | Save current Convergence result and route exactly as today | `CANONICALIZATION`, fresh `derive_domain` for `REMODEL`, or `WAITING_HUMAN` |
| `compose_canonical` | Save candidate; render and run deterministic `validate_contract` | `audit_canonical` if valid; otherwise fresh `compose_canonical` with findings |
| `audit_canonical` | Audit the exact persisted candidate and rendered Markdown; route exactly as today | `DONE`, fresh `compose_canonical` for `EDITORIAL`, fresh `derive_domain` for `REMODEL`, or `WAITING_HUMAN` |
| human answer | Call existing `accept_answer`, preserve exact answer and supersession, clear stale derived data as today | `INTAKE` or fresh `derive_domain` in `MODELING` |

Each accepted submission commits **one** legal FSM edge, including an allowed
`MODELING → MODELING` or `CANONICALIZATION → CANONICALIZATION` self-loop for an
internal checkpoint. The cursor is not inferred from files or the presence of
old artifacts. On a new modeling cycle, clear `modeling_progress` and rebuild
all three views; preserve previous `REMODEL` findings in the same payloads as
today. A human answer after modeling or audit clears model, convergence,
candidate, audit, diagnostics, and progress before a new modeling cycle.

## 4. CLI protocol

`prd next <run-id> --json` writes exactly one UTF-8 JSON object to stdout. It
performs no provider invocation. For an active model task, the object has
`protocol_version: 1`, `run_id`, `state`, `kind: "model"`, `operation`,
`instruction`, `payload`, `constraints`, `output_schema`, `task_token`, and
`submit_hint`. `constraints` state that the caller must return only a JSON
value matching the schema and must not create new material authority. For a
human task, it has `kind: "human"`, the complete `decision`, `answer_contract`
(one of `{kind: "option_selection", option_id}`,
`{kind: "option_with_clarification", option_id, clarification}`, or
`{kind: "custom", text}`), token, and
submit hint. It says explicitly that only a human may select or author the
answer. For `DONE` or `BLOCKED`, it returns `kind: "terminal"`, state,
diagnostics/path as applicable, and no token. Repeating `next` on an issued
task returns the same snapshot and token. A deterministic controlling
invariant/source-integrity failure may commit `BLOCKED` before returning a
terminal envelope; it never calls a model.

`prd submit <run-id> --task-token <token> --input <file|->` reads exactly one
UTF-8 JSON value from the file or stdin (`-`), capped at 32 MiB.
For model tasks, the value is the operation's schema output (for `intake`,
JSON `null` is permitted). For human tasks, it is exactly one of the existing
`HumanAnswer` JSON objects; e.g. `{ "kind": "option_selection", "option_id":
"A" }`. PRD checks the token, issuing state/cursor/revision, source integrity,
operation/decision identity, fixed output schema/Pydantic type, semantic
guards, and legal transition before saving. Success prints the run ID, new
state, and next action. A malformed, stale, consumed, wrong-state, or invalid
submission exits nonzero with a concrete stderr error and no state mutation.
The CLI never accepts a model-supplied human choice as automatic authority;
an explicit human `submit` action is required. Human answer validation remains
structural, as today; any material ambiguity is revisited by later analysis.

`prd run <run-id> [--max-tasks N]` defaults to a 50-task safety bound. It uses
the same prepared tasks and commit path; for each model task it invokes the
internal Codex provider once, then validates and submits its result. It stops
normally at `WAITING_HUMAN`, `DONE`, or `BLOCKED`, printing state and next
action and exiting zero. At the task bound it prints a resumable limit result
and exits nonzero, so automation cannot confuse a cap with completion.
Provider failure/invalid output exits nonzero, reports the failing operation,
and leaves its task available for retry. `run` never generates or submits a
human answer. A pending interactive model task may be completed by `run`,
which consumes its token; the reverse mode switch also works. `start`,
`status`, and `handoff` retain their roles; `handoff` still exposes only the
validated `DONE` Canonical Markdown.

Retain `advance` and `answer` as deprecated compatibility adapters for existing
operator scripts. `advance` uses the direct provider and completes one old
phase execution, potentially several internal tasks, through the shared
engine. `answer` requires the current decision ID and explicit human input,
then issues/consumes the corresponding human task through shared validation
under the run lock. A failed later provider call may leave earlier validated
checkpoints, while the FSM stays in the phase. Neither command is part of
the interactive protocol. Update operator documentation to teach
`next → submit` and `run`.

## 5. Persistence, atomicity, and resume

Use one per-run exclusive filesystem lock (a stable `.lock` file and
`fcntl.flock` on the current Unix target) around task issue, reload/check,
submission commit, and any legacy mutation command. Do not hold the lock
while Codex reasons or while the direct provider runs. After an invocation,
reacquire it and reject the result if another actor consumed or replaced the
task. `run.json` remains the single aggregate commit point: under the lock,
work on a loaded copy, validate all effects, clear `pending_task`, increment
`revision`, then atomically replace `run.json`. Failed validation never writes
partial aggregate data. A successful modeling suboperation deliberately
commits a checkpoint, enabling resume without repeating earlier model calls.
If source integrity fails during `submit`, reject that submission without
committing its output; the next `next`/`run` applies the existing `BLOCKED`
policy under the lock.

The one cross-file boundary remains finalization: write the exact rendered
`canonical-prd.md` atomically before committing `DONE`. If a crash leaves the
file while state is not `DONE`, ignore it; if `DONE` lacks the matching file,
`handoff` rejects it, as `final_canonical_path` does today. An audit task
references the persisted candidate and its exact deterministic rendering;
the composer cannot self-audit. A source-integrity failure in an active state
continues to enter `BLOCKED` with a diagnostic. Missing/invalid `run.json`
remains a storage error rather than a fabricated transition. No transition
is inferred from a cursor, task file, or canonical file alone.

## 6. Compatibility and migration

Add defaulted fields so existing `run.json` documents load without a rewrite.
On first `next`/`run`, a legacy `INTAKE`, `MODELING`, or `CANONICALIZATION` run
starts at its phase's first operation; a `WAITING_HUMAN` run exposes its sole
pending Decision; `DONE` and `BLOCKED` stay terminal. A legacy
`CANONICALIZATION` candidate is not assumed to have a pending audit: compose
again, retaining current diagnostics. Existing resolved Decisions, Source PRD
digest, model/convergence data, candidate/audit history, and handoff checks
remain readable. The new partial modeling checkpoints are valid only for
runs whose explicit cursor and progress were committed together. Existing
operator scripts using `advance`/`answer` can use the deprecated adapters
during migration; interactive Codex never depends on them. The new checkpoint
granularity means a failed later provider call may leave earlier validated
modeling outputs persisted while the FSM remains `MODELING`.

## 7. Failure and security invariants

- `next`, `submit`, human answering, `status`, and `handoff` perform zero
  internal provider calls. Only the direct runner (`run`, including the
  deprecated `advance` adapter) may invoke `CodexAIExecutor`.
- One live task per run; repeated `next` cannot issue competing tokens.
  A token is bound to run, state, cursor, revision, and request snapshot.
  Replay, wrong-run, wrong-state, and concurrent late results cannot commit.
- Parse JSON and validate with the existing strict operation types and
  `HumanAnswer` union before mutating the loaded aggregate. Unknown fields,
  unknown options, duplicate Decision IDs, invalid supersession, and failed
  deterministic canonical checks cannot bypass current guards.
- Human recommendation and model output never become authority through task
  issuance, `run`, or a default answer. Only an explicit accepted human
  submission updates authoritative Decisions.
- Do not treat prompt text or submitted JSON as instructions to the CLI.
  The local filesystem trust boundary remains the same as current runs;
  tokens do not defend against an actor able to edit `run.json`.
- Keep all existing Convergence `PASS`, independent Audit `PASS`, contract
  validation, exact-file, and `DONE` handoff gates.

## 8. Coding sequence for a GPT-6 Sol Medium pass

1. Add defaulted revision/cursor/progress/pending-task models and locked
   read/modify/write support in `models.py` and `storage.py`; verify old run
   files load and atomic replacement still works.
2. Extract the seven shared operation request builders and output parsers
   from `analysis.py`/`canonical.py`; retain committed prompts, schemas,
   result types, validation, and domain conversions.
3. Replace provider-calling phase methods in `workflow.py` with pure task
   preparation and token-checked submission routing. Preserve transition
   table, invariant guards, authority projection, and finalization order.
4. Make `CodexAIExecutor` consume `ModelTask`; implement bounded `run` using
   the same service preparation and submission methods.
5. Add `next` and `submit` CLI JSON protocol, then compatibility adapters
   and operator docs. Keep the CLI's interactive path free of provider
   construction or invocation.
6. Run existing suite, update tests for suboperation checkpoints, and add
   equivalence/restart/concurrency regressions below.

## 9. Regression proof plan

Use a scripted provider and the same fixture outputs for two runs: one
driven by repeated `next → submit`, the other by `run`. At every completed
operation compare FSM state, cursor, Decisions/Active Authority, modeling and
convergence results, canonical candidate, audit result, diagnostics, and
final rendered Markdown. Cover intake pass/decision; convergence `PASS`,
`REMODEL`, and `HUMAN_DECISION`; canonical structural failure, audit `PASS`,
`EDITORIAL`, `REMODEL`, and `HUMAN_DECISION`; all three human answer forms and
supersession. Compare semantic fields while excluding run IDs, revisions,
tokens, and provider call logs.

Spy on `CodexAIExecutor` construction/invocation and `subprocess.run`:
`next` and `submit` over a full interactive acceptance scenario must cause
zero calls; `run` must call once per model task and never for a human task.
Test restart after task issue and after each modeling/canonical checkpoint;
repeated `next` returns the same task; switching modes consumes exactly one
task. Race two submissions of the same token and assert exactly one commit.
Test stale/wrong-run/wrong-state/consumed tokens, changed prompt/schema,
malformed/oversized JSON, invalid answers, source tampering, provider failure,
and crash before `DONE`; assert no unauthorized mutation and no handoff from
an incomplete run. Existing contract, storage, and final-path tests remain
required gates.

## 10. Unresolved decisions

None required for implementation. The existing local filesystem is the
trust boundary; multi-user remote authorization and distributed locking are
outside this refactor.
