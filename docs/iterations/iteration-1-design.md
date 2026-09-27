# PRD Convergence Workflow — Iteration 1 Frozen Architecture

Status: frozen for Iteration 1 implementation. Design only; no production implementation is included.

## 1. Goal

Prove that one Source PRD can traverse the complete contracted workflow, pause for and preserve Human Authority, rebuild and converge the product/system understanding, and expose exactly one audited Canonical PRD for SpecKit.

## 2. Architecture rules

1. The persisted coarse FSM is the single source of workflow truth.
2. Progress occurs only through explicit legal FSM transitions. Quality checks are transition guards, not states or a second orchestration mechanism.
3. Files, artifact presence, timestamps, hashes, and freshness never determine workflow state.
4. Active Authority is computed directly as Source PRD plus accepted, non-superseded Human Decisions. It is not a subsystem.
5. AI produces analysis and structured content. Deterministic workflow code owns every transition.
6. Domain, Capabilities, Architecture, Convergence, Canonical composition, validation, audit, and repair are operations inside the normative coarse states.
7. Only one Material Decision may be pending.
8. After accepted Human Authority originating after intake, the complete derived model set is rebuilt. There is no selective invalidation.
9. SpecKit receives only the Canonical PRD from a `DONE` run.

## 3. Non-goals

Iteration 1 excludes:

- artifact freshness, `CURRENT`/`STALE` flags, dependency DAGs, hashes used as lifecycle inputs, or state resolvers;
- prompt, schema, or content fingerprints;
- per-element authority references, provenance graphs, or provenance coverage validation;
- selective or transitive invalidation;
- generic workflow/DAG engines or stage registries;
- databases, repository abstractions, migrations, transaction frameworks, event sourcing, or CQRS;
- parallel agents, distributed execution, or multiple concurrent Human Decisions;
- automatic retry orchestration;
- plugins or speculative extension points;
- web UI, REST API, microservices, external trackers, or research orchestration;
- telemetry or observability platforms;
- SpecKit implementation, older-orchestrator compatibility, or post-`DONE` revision workflows.

## 4. System context

```text
Source PRD
    ->
PRD Convergence Workflow
    ->
Canonical PRD
    ->
SpecKit
```

The Source PRD and explicit Human Decisions are the only sources of Material Authority. Recommendations, models, convergence findings, Canonical candidates, and audits are derived artifacts. SpecKit remains outside the implementation boundary.

## 5. Final FSM

The six normative states are:

```text
INTAKE
MODELING
CANONICALIZATION
WAITING_HUMAN
BLOCKED
DONE
```

`WorkflowRun.state` is persisted explicitly and is the sole lifecycle truth.

| From | To | Guard/reason |
|---|---|---|
| `INTAKE` | `MODELING` | Source usable; no intake-blocking Material Decision |
| `INTAKE` | `WAITING_HUMAN` | One valid pending Decision exists |
| `INTAKE` | `BLOCKED` | Source unusable, empty, or unsupported |
| `WAITING_HUMAN` | `INTAKE` | Structurally valid answer to an intake-origin Decision |
| `WAITING_HUMAN` | `MODELING` | Structurally valid answer to a modeling/canonicalization-origin Decision |
| `WAITING_HUMAN` | `BLOCKED` | Impossible internal state or unrecoverable persistence corruption |
| `MODELING` | `MODELING` | Convergence `FAIL/REMODEL` |
| `MODELING` | `WAITING_HUMAN` | Convergence `FAIL/HUMAN_DECISION` and one valid Decision |
| `MODELING` | `CANONICALIZATION` | Convergence `PASS` and every convergence condition holds |
| `MODELING` | `BLOCKED` | Impossible internal state or unrecoverable persistence corruption |
| `CANONICALIZATION` | `CANONICALIZATION` | Representational/editorial repair is required |
| `CANONICALIZATION` | `MODELING` | Audit finds a model defect already resolvable from Active Authority |
| `CANONICALIZATION` | `WAITING_HUMAN` | Audit exposes a Material Unknown requiring Human Authority |
| `CANONICALIZATION` | `DONE` | Contract validation `PASS` and independent audit `PASS` |
| `CANONICALIZATION` | `BLOCKED` | Impossible internal state or unrecoverable persistence corruption |

`DONE` is the successful terminal state. `BLOCKED` is an unsuccessful terminal state for Iteration 1. Handoff is not a state.

While in `MODELING`, one phase execution performs:

```text
derive Domain Model
    -> derive Functional Capabilities
    -> derive High-Level Architecture
    -> Convergence Review
```

While in `CANONICALIZATION`, one phase execution performs:

```text
constrained Canonical composition
    -> deterministic Markdown rendering
    -> deterministic contract validation
    -> independent Canonical Audit
```

An editorial failure leaves the FSM in `CANONICALIZATION`; the next phase execution repeats composition using the finding. A remodel finding explicitly transitions to `MODELING`. There are no phase substates, artifact flags, or inferred statuses.

## 6. Runtime flows

### Successful path

1. `start(source_path)` copies one UTF-8 Markdown Source PRD, stores `INTAKE`, and persists the run.
2. Intake checks source usability and uses AI for ambiguity, contradiction, missing-material-information, and materiality analysis.
3. With no blocking Material Unknown, the guard performs `INTAKE -> MODELING`.
4. Modeling derives the three required views only from current Active Authority.
5. A separate Convergence Review checks the complete model set against Active Authority and the normative convergence conditions.
6. Only Convergence `PASS` permits `MODELING -> CANONICALIZATION`.
7. A constrained AI Canonical Composer consolidates the converged understanding into structured `CanonicalPRD`. Composition establishes no Authority.
8. A deterministic renderer produces Markdown and deterministic validation checks mechanically enforceable contract rules.
9. A separate fresh AI invocation performs the independent Canonical Audit.
10. Only validation `PASS` plus audit `PASS` permits `CANONICALIZATION -> DONE`.
11. The exact audited Markdown is written as `canonical-prd.md` before `DONE` is committed.
12. The Canonical module exposes that one path only for `DONE`.

### Human Decision path

1. Intake, Convergence, or Audit finds a Material Unknown not answered by Active Authority.
2. The operation returns one `Decision` with one concrete question, 2–4 materially distinct options, a recommendation, and its rationale.
3. Workflow code validates and persists it as the sole `PENDING` Decision, then transitions to `WAITING_HUMAN`.
4. The recommendation and unselected options do not enter Active Authority.
5. The human selects an option, selects an option with clarification, or provides a custom answer.
6. `decisions.py` validates only structure: correct state/current Decision, existing option ID, non-empty required text, and an existing superseded Decision ID when supplied.
7. The exact answer is stored. Option and clarification remain separate equal-authority fields; custom text is verbatim.
8. An intake-origin answer returns to `INTAKE`. A later answer returns to `MODELING` and removes the previous modeling, convergence, Canonical candidate, and audit values so the complete model set is rebuilt.
9. No separate AI subsystem semantically approves answers. If an accepted answer leaves material ambiguity or contradiction, Modeling/Convergence creates the next Human Decision instead of inventing an interpretation.

### BLOCKED path

Before run creation, missing, empty, unsupported, or invalid Source PRD input is a command/input error. After a parseable run has been created, structural corruption of that trusted active aggregate, including immutable Source PRD integrity failure or an impossible controlling FSM/software invariant, uses `BLOCKED` with a concrete diagnostic. Missing, unreadable, truncated, or invalid `run.json` remains an out-of-band storage error because there is no trusted aggregate to transition. Normal product uncertainty uses `WAITING_HUMAN`; derived inconsistency uses `MODELING`; editorial defects use `CANONICALIZATION`. A transient provider/schema-output failure is reported without changing the FSM, allowing an explicit retry.

## 7. Human Decisions and Active Authority

One `Decision` model represents both classifications, with conditional field validation rather than Material/Deferred subclasses.

For `MATERIAL`, it holds ID, origin state, question, context, 2–4 `DecisionOption` values, recommendation, rationale, `PENDING | RESOLVED | SUPERSEDED`, accepted `HumanAnswer`, and optional `supersedes_decision_id`.

For `DEFERRED`, it holds the unresolved question, safe-to-defer rationale, and downstream constraints.

Active Authority is computed when needed:

```text
unchanged Source PRD
+ accepted Human Answers from RESOLVED Decisions
- Decisions explicitly superseded by a later Decision
```

Selected option text becomes Authority. Option plus clarification contributes both exact parts. A custom answer contributes its exact text. Recommendations never enter Authority automatically.

An accepted Decision may override Source PRD meaning identified by its question/context. Decision-to-Decision supersession uses one optional direct ID link. History remains in `WorkflowRun`; there is no authority graph, precedence engine, separate file, freshness, or lifecycle.

## 8. Final core types

Iteration 1 has **9 core domain types**:

1. `WorkflowState` — six normative states.
2. `WorkflowRun` — persisted state and pause/resume data.
3. `Decision` — conditional `MATERIAL | DEFERRED` model.
4. `DecisionOption` — one materially distinct proposed answer and consequence.
5. `HumanAnswer` — discriminated union of the three valid answer forms.
6. `ModelingResult` — shallow Domain, Capability, Architecture, product context, and deferred decisions.
7. `ConvergenceResult` — `PASS | FAIL`, findings, and optional `HUMAN_DECISION | REMODEL` remediation.
8. `CanonicalPRD` — structured ten-section Canonical document.
9. `AuditResult` — `PASS | FAIL`, findings, and optional `HUMAN_DECISION | REMODEL | EDITORIAL` remediation.

`HumanAnswer` is:

```text
OptionSelection(option_id)
OptionWithClarification(option_id, clarification)
CustomAnswer(text)
```

Small literals/enums and nested section values are implementation details, not independent core concepts. There is no core `DecisionPrompt`, `MaterialDecision`, `DeferredDecision`, `AuthorityRef`, `ActiveAuthority`, `IntakeResult`, `ContractValidationResult`, or `BlockingReason`.

`ModelingResult` is not a duplicate Canonical PRD. It contains shallow validated fields for product context; Domain concepts/relationships/invariants; Functional Capabilities/actors/behavior/rules/scope/dependencies/failures; Architecture/boundaries/ownership/interactions/constraints/cross-cutting requirements; and safely Deferred Decisions. It does not reproduce final ten-section prose or schema and carries no per-element provenance.

## 9. AI boundary

`ai.py` holds the one required provider abstraction and one concrete Iteration 1 adapter:

```python
class AIExecutor(Protocol):
    def invoke(
        self,
        *,
        operation: str,
        payload: dict[str, object],
        result_type: type[T],
    ) -> T: ...
```

AI-backed operations are intake analysis; Domain, Capability, and Architecture derivation; fresh Convergence Review; constrained Canonical composition; and fresh independent Canonical Audit.

All outputs are schema-validated. Invalid output is rejected rather than coerced into authority or a transition result. AI never writes storage, changes state, accepts a Human Answer, or promotes a recommendation.

## 10. Canonicalization decision

Iteration 1 uses **constrained AI structured composition**:

```text
Active Authority + Convergence-PASS ModelingResult
    -> constrained AI Canonical Composer
    -> structured CanonicalPRD
    -> deterministic Markdown renderer
    -> deterministic Canonical Contract validation
    -> fresh independent Canonical Audit
```

This is smaller than deterministic model-to-Canonical compilation because deterministic compilation would require `ModelingResult` to duplicate almost the complete ten-section Canonical schema. The composer consolidates and normalizes already converged meaning.

It may organize, normalize terminology, remove workflow history, and consolidate established semantics. It must not invent behavior, scope, actors, permissions, domain meaning, ownership, boundaries, architecture, security, or material non-functional requirements; answer a Material Unknown; alter Human Authority; or treat a recommendation as selected.

Composition remains non-authoritative. Protection comes from the Convergence gate, structured output validation, deterministic contract validation, and independent Audit. Composer and auditor may share `canonical.py`, but use separate functions, prompts/schemas, and fresh AI invocations. Composer output cannot set audit status.

## 11. Final modules

Iteration 1 has **8 functional modules**, plus a minimal `__init__.py` (`9` source files total):

| Module | Responsibility |
|---|---|
| `models.py` | Nine core Pydantic/domain types and structural validation |
| `workflow.py` | FSM, transitions, guards, and phase orchestration for the explicit persisted state |
| `decisions.py` | Decision Protocol, structural answer acceptance, direct supersession, computed Active Authority payload |
| `analysis.py` | Intake and all MODELING operations: Domain, Capabilities, Architecture, Convergence |
| `canonical.py` | Composition, rendering, validation, independent audit, final file creation, guarded final-path exposure |
| `ai.py` | Narrow provider boundary and concrete local adapter |
| `storage.py` | Concrete filesystem create/load/save with atomic `run.json` replacement |
| `cli.py` | Minimal `start`, `advance`, `answer`, `status`, and `handoff` commands |

`__init__.py` contains package metadata/exports only. Intake and modeling are merged into `analysis.py`; audit and handoff are merged into `canonical.py`; storage has no hypothetical backend interface. Audit independence is behavioral, not file-based.

## 12. Persistence

```text
.prd/runs/<run-id>/
├── source-prd.md
├── run.json
└── canonical-prd.md
```

`run.json` persists the explicit FSM state, pending-decision origin, Decision history and exact answers, current Modeling/Convergence results, current Canonical candidate/Audit result, and concrete diagnostics.

`canonical-prd.md` is written only from the candidate that passed validation and audit, before atomically committing `DONE`. If a crash leaves that file while state remains `CANONICALIZATION`, it is ignored and replaced during the next canonicalization execution. File presence never advances the FSM.

`run.json` uses same-directory temporary write plus atomic replacement. `storage.py` is concrete; there are no repositories, migrations, event logs, artifact stores, transactions, or database abstractions.

## 13. Essential interfaces

```python
class WorkflowService:
    def __init__(self, storage: FileStorage, ai: AIExecutor) -> None: ...
    def start(self, source_path: Path) -> WorkflowRun: ...
    def advance(self, run_id: str) -> WorkflowRun: ...
    def answer(self, run_id: str, decision_id: str, answer: HumanAnswer) -> WorkflowRun: ...
    def status(self, run_id: str) -> WorkflowRun: ...
```

```python
def active_authority(run: WorkflowRun, source_text: str) -> dict[str, object]: ...
def accept_answer(run: WorkflowRun, decision_id: str, answer: HumanAnswer) -> WorkflowRun: ...

def analyze_intake(authority: dict[str, object], ai: AIExecutor) -> Decision | None: ...
def derive_models(authority: dict[str, object], prior_findings: tuple[str, ...], ai: AIExecutor) -> ModelingResult: ...
def review_convergence(authority: dict[str, object], models: ModelingResult, ai: AIExecutor) -> ConvergenceResult: ...

def compose_canonical(authority: dict[str, object], models: ModelingResult, editorial_findings: tuple[str, ...], ai: AIExecutor) -> CanonicalPRD: ...
def render_markdown(document: CanonicalPRD) -> str: ...
def validate_contract(document: CanonicalPRD) -> tuple[str, ...]: ...
def audit_canonical(authority: dict[str, object], models: ModelingResult, document: CanonicalPRD, ai: AIExecutor) -> AuditResult: ...
def final_canonical_path(run: WorkflowRun, run_dir: Path) -> Path: ...
```

`advance()` uses an explicit `match run.state`, executes the complete operation sequence for that state, and applies one guarded transition. It never inspects files to infer the phase.

## 14. Acceptance scenario

An expense-reimbursement PRD defines all required areas except whether an employee may edit a submitted expense awaiting review.

1. Start persists `INTAKE`; usable intake transitions to `MODELING`.
2. Modeling derives all views; Convergence returns `FAIL/HUMAN_DECISION` for the edit rule.
3. `MODELING -> WAITING_HUMAN` exposes one Decision with three material options and recommendation A.
4. The human selects B and clarifies: “Editing is allowed only before the manager records any review action, and an edit resets the submission timestamp.”
5. Structural validation stores B and the exact clarification as equal Authority; the recommendation remains advisory.
6. `WAITING_HUMAN -> MODELING` rebuilds the complete model set.
7. Convergence `PASS` permits `MODELING -> CANONICALIZATION`.
8. The composer produces structured `CanonicalPRD`; rendering and validation pass; the fresh Audit passes.
9. The exact Markdown is written and `CANONICALIZATION -> DONE` occurs.
10. `handoff` returns exactly `canonical-prd.md`, exposing no internal artifact.

## 15. Test strategy

Tests use a scripted fake `AIExecutor`; normal tests require no live provider. They verify:

- the transition table rejects every illegal transition and files never infer state;
- recommendations never enter Active Authority automatically;
- one and only one Material Decision can be pending;
- pending uncertainty prevents progression;
- option plus clarification preserves both exact parts;
- custom answers remain verbatim and are never mapped to options;
- unknown options and empty required text fail structural validation;
- semantic conflict in an accepted answer is detected by Convergence and creates a new Decision;
- late Human Authority returns to `MODELING` and replaces the complete derived model set;
- Convergence `FAIL` cannot enter `CANONICALIZATION`;
- the Composer only runs after Convergence `PASS` and cannot audit or transition itself;
- deterministic validation enforces all ten sections, release/status rules, `PARTIAL` detail, defined roles, and Deferred Decision content;
- a fresh independent Audit is mandatory and each remediation takes only its legal transition;
- only validation `PASS` plus audit `PASS` enters `DONE`;
- only `DONE` exposes one Canonical path;
- `WAITING_HUMAN` survives restart with exact Decision history;
- normal uncertainty never becomes `BLOCKED`;
- unusable input/corrupted state yields concrete diagnostics.

The end-to-end filesystem test executes the acceptance scenario and checks that final Markdown is self-contained, preserves the Human clarification, and omits recommendations/history.

## 16. Implementation slices

### Slice 1 — Core models, storage, and FSM

Add package/test configuration, 9 core types, concrete filesystem storage, and explicit transition guards.

Acceptance: structural tests pass; `run.json` persists explicit state; all legal/illegal transitions are tested; no file infers lifecycle.

### Slice 2 — AI boundary, Intake, and Human Decisions

Add narrow executor/concrete adapter/scripted fake, intake, one-pending-decision behavior, structural answer acceptance, and Active Authority projection.

Acceptance: provider details stay isolated; sufficient intake reaches `MODELING`; material gaps reach `WAITING_HUMAN`; all answer forms persist exactly; recommendation isolation and pause/reload/resume pass; no semantic-answer AI subsystem exists.

### Slice 3 — Modeling and Convergence

Add Domain, Capability, Architecture, and fresh Convergence operations within `MODELING`.

Acceptance: models use only current Active Authority; remediation uses legal transitions; late decisions cause full rebuild; no element provenance/selective invalidation exists; only `PASS` reaches `CANONICALIZATION`.

### Slice 4 — Canonicalization and final exposure

Add constrained composition, deterministic rendering/validation, fresh independent Audit, final-file creation, and guarded path exposure.

Acceptance: `ModelingResult` is not a duplicate Canonical schema; composer cannot create Authority or transition; required contract checks pass; audit is fresh/independent; only both passes write the final artifact and reach `DONE`; only `DONE` exposes it.

### Slice 5 — CLI and walking-skeleton acceptance

Add `start`, `advance`, `answer`, `status`, and `handoff` plus the filesystem-backed scenario.

Acceptance: Source PRD -> pause -> decision -> resume -> convergence -> Canonical PRD -> audit -> `DONE` passes; restart retains authority; handoff contains one artifact; all invariant tests pass without a live AI; no Iteration 2 mechanism appears.

## 17. Removed complexity and freeze

Removed or merged:

- per-element `AuthorityRef` and provenance validation;
- `DecisionPrompt`, Material/Deferred subclasses, and auxiliary result wrappers as core types;
- semantic AI approval of Human Answers;
- deterministic model-to-Canonical compilation and its duplicate schema;
- separate `intake.py`, `modeling.py`, `audit.py`, and `handoff.py`;
- hypothetical storage/repository interfaces;
- eight horizontal implementation slices, reduced to five vertical slices;
- broad `BLOCKED` use for provider failures or analytical uncertainty;
- all implicit phase tracking based on artifacts, flags, timestamps, or file presence.

The only isolated boundaries are `AIExecutor`, required to hide provider mechanics, and concrete filesystem storage, required for pause/resume. No state, persistent flag, module, or core type should be added during Iteration 1 unless a normative contract or failing acceptance test demonstrates the need.

## 18. Quality preservation map

| Simplification | Preserved protection |
|---|---|
| Compute Active Authority directly | Deterministic projection includes only Source PRD and accepted non-superseded answers; recommendations/models are excluded |
| Remove element provenance | Each modeling pass receives only Active Authority; Convergence and Audit detect unsupported semantics |
| Merge Decision types | Conditional validation retains Material packet, Deferred rationale/constraints, statuses, exact answers, and supersession rules |
| Merge DecisionPrompt | One question, 2–4 options, recommendation, and rationale remain mandatory |
| Remove semantic answer reviewer | Exact Human Answer becomes Authority; Modeling/Convergence must ask again if ambiguity remains |
| Full rebuild instead of invalidation | Every late answer returns to `MODELING`; prior derived results are discarded before Convergence |
| AI composition instead of duplicate mapping | Convergence gate, structured schema, deterministic contract validation, and independent Audit prevent unchecked new material meaning |
| Merge Audit into canonical module | Separate function, schema/prompt, and fresh invocation preserve independence; composer cannot set audit status |
| Remove handoff module | Canonical path exposure checks explicit `DONE` and returns one audited file |
| Merge analysis modules | Ordered internal operations remain explicit; FSM semantics are unchanged |
| Remove storage abstraction | Concrete atomic persistence still retains pause/resume and explicit state |
| Remove artifact substates | Six-state FSM and guards remain the only progression mechanism |
| Narrow `BLOCKED` | Product uncertainty must use `WAITING_HUMAN`; remodel/editorial defects retain their contracted paths |
| Reduce to five slices | Every architecture seam and invariant remains covered by acceptance criteria |

Hard gates remain unchanged: Convergence `PASS` before `CANONICALIZATION`; Canonical validation `PASS` plus independent Audit `PASS` before `DONE`; and `DONE` before the sole SpecKit handoff.

## 19. Deferred to Iteration 2+

- fine-grained provenance and traceability;
- freshness, fingerprints, hashes, DAGs, and selective invalidation;
- deeper modeling/materiality/convergence/audit behavior and evaluations;
- automatic retry/backoff and richer recovery;
- grouping/concurrent decisions;
- post-`DONE` revisions and SpecKit impact analysis;
- stronger content-integrity mechanisms if evidence requires them;
- databases, migrations, locking, multi-user/distributed execution;
- UI/API, external integrations, plugins, model routing, parallel agents, telemetry, observability, and SpecKit implementation.
