# PRD Convergence Workflow Contract

## 1. Purpose

This contract defines the normative workflow that transforms a Source PRD into a Canonical PRD.

The workflow exists to:

- detect missing, ambiguous, contradictory, or insufficiently specified material information;
- obtain authoritative human decisions where required;
- derive a coherent domain, capability, responsibility, and high-level architecture model;
- converge those views into one internally consistent product and system definition;
- produce a self-contained Canonical PRD.

The workflow MUST follow the Canonical PRD Contract, Materiality Contract, and Human Decision Protocol.

---

## 2. Input

The workflow accepts one primary input:

    Source PRD

The Source PRD represents the initial product intent.

It MAY be incomplete, ambiguous, inconsistent, or insufficient for downstream specification.

The Source PRD is authoritative only for statements that have not been explicitly superseded by later human decisions.

---

## 3. Output

The successful output is:

    Canonical PRD

The Canonical PRD MUST satisfy the Canonical PRD Contract and its Definition of Done.

Intermediate artifacts are internal workflow state.

They MUST NOT be required to correctly interpret the final Canonical PRD.

---

## 4. Workflow Principle

The workflow MUST continue until the Canonical PRD can be produced without making any new material product or system decision during canonicalization.

The workflow MUST NOT use canonicalization itself to resolve uncertainty.

Material uncertainty MUST be resolved before canonicalization.

The central convergence rule is:

> Discover uncertainty, resolve material decisions, rebuild the affected understanding, and repeat until the product and system definition is complete and internally consistent.

---

## 5. Workflow States

The workflow uses the following coarse-grained states:

    INTAKE
    MODELING
    WAITING_HUMAN
    CANONICALIZATION
    DONE
    BLOCKED

The workflow SHOULD NOT introduce additional lifecycle states for individual modeling steps unless implementation evidence demonstrates that they are necessary.

Domain modeling, capability modeling, architecture modeling, and convergence review are internal operations of `MODELING`, not independent top-level workflow states.

---

## 6. INTAKE

### Purpose

Determine whether the Source PRD contains enough authoritative information to begin coherent product and system modeling.

### Responsibilities

INTAKE MUST:

- review the Source PRD for material ambiguity;
- detect material contradictions;
- detect missing requirements or constraints;
- detect unresolved product decisions;
- detect undefined actors, roles, terminology, ownership, scope, security, or material non-functional requirements where visible from the Source PRD;
- classify unresolved questions using the Materiality Contract.

### Outcomes

If no unresolved material decision blocks modeling:

    INTAKE -> MODELING

If a material decision requires human authority:

    INTAKE -> WAITING_HUMAN

If the Source PRD is too incomplete to meaningfully continue even through structured clarification:

    INTAKE -> BLOCKED

INTAKE MUST NOT silently invent missing material requirements.

---

## 7. WAITING_HUMAN

### Purpose

Obtain authoritative human resolution for one or more material questions.

### Rules

Every question MUST follow the Human Decision Protocol.

The AI MUST:

- ask one concrete material question;
- provide 2–4 materially distinct options;
- provide a recommendation;
- explain the recommendation.

The human MAY:

- select an option;
- select an option and add authoritative clarification;
- provide a custom decision.

AI recommendations MUST NOT become authority without an explicit human answer.

### Sequential Resolution

Material decisions that may affect one another SHOULD be resolved one at a time.

After each material decision, the workflow MUST reconsider whether remaining pending questions are still valid.

### Return Rule

After a human decision obtained during INTAKE:

    WAITING_HUMAN -> INTAKE or MODELING

depending on whether intake completeness must be re-evaluated.

After a human decision obtained during MODELING or CANONICALIZATION:

    WAITING_HUMAN -> MODELING

A new material decision discovered after modeling has begun MUST trigger a fresh convergence cycle.

The workflow MUST NOT return directly from such a decision to final canonicalization.

---

## 8. MODELING

### Purpose

Build and converge the product and system understanding required by the Canonical PRD Contract.

### Internal Modeling Sequence

A modeling iteration SHOULD derive, at minimum:

    Domain Model
        ->
    Functional Capabilities
        ->
    High-Level Architecture
        ->
    Convergence Review

The exact implementation MAY use additional internal analyses, but they MUST NOT create independent material authority.

### 8.1 Domain Model

Domain modeling MUST derive:

- material domain concepts;
- relationships;
- terminology;
- domain invariants.

It MUST NOT introduce technical implementation concepts as domain facts unless they are authoritative product concepts.

### 8.2 Functional Capabilities

Capability modeling MUST derive:

- meaningful user or business capabilities;
- applicable actors;
- required behavior;
- business rules;
- release relevance;
- material capability dependencies.

It MUST NOT replace capabilities with implementation tasks.

### 8.3 High-Level Architecture

Architecture modeling MUST derive only architecture needed to establish:

- responsibility areas;
- ownership;
- major interactions;
- system boundaries;
- responsibility boundaries;
- material dependency directions;
- architectural invariants;
- material technical constraints.

It MUST NOT resolve material uncertainty by assumption.

If architecture exposes a material unknown, that unknown MUST enter convergence review.

---

## 9. Convergence Review

### Purpose

Determine whether the current product, domain, capability, ownership, scope, and architecture views form one coherent system definition.

### Required Checks

The review MUST detect:

- contradictions between authoritative decisions and derived models;
- conflicting domain meanings;
- conflicting capability definitions;
- inconsistent release scope;
- ambiguous role or permission boundaries;
- conflicting ownership;
- overlapping responsibility boundaries;
- inconsistent architecture and capability decomposition;
- unsupported architectural assumptions;
- unresolved material questions;
- material requirements implied by one model but absent from authority;
- material decisions invented by AI reasoning.

### Review Outcomes

The convergence review has two primary outcomes:

    PASS
    FAIL

A `FAIL` finding MUST identify the required remediation.

Allowed remediation classes SHOULD include:

    HUMAN_DECISION
    REMODEL

### HUMAN_DECISION

Use when existing authority cannot determine a material answer.

The workflow MUST transition:

    MODELING -> WAITING_HUMAN

### REMODEL

Use when existing authority is sufficient but the derived models are incomplete, inconsistent, or incorrect.

The workflow MUST repeat the modeling cycle.

The AI MUST NOT ask the human to decide something already determined by existing authority.

---

## 10. Modeling Retry Rule

A modeling retry MUST use:

- current authoritative decisions;
- the Source PRD;
- relevant previous convergence findings.

The workflow SHOULD prefer rebuilding a coherent model set over maintaining complex partial invalidation logic.

A new material human decision SHOULD normally cause the current domain, capability, architecture, and convergence results to be reconsidered together.

The workflow MUST NOT preserve an older derived conclusion merely because it was generated before the new decision.

---

## 11. Convergence Gate

The workflow MAY leave MODELING only when convergence review is `PASS`.

A `PASS` requires that:

- no unresolved material decision remains;
- derived models are mutually consistent;
- derived models are consistent with active human authority;
- release scope is explicit;
- actors and roles are sufficiently defined;
- material domain semantics are explicit;
- capabilities are sufficiently defined;
- ownership and system boundaries are explicit;
- required responsibility boundaries are explicit;
- required high-level architecture constraints are explicit;
- material cross-cutting requirements are known;
- any remaining undecided matters are safe to defer under the Materiality Contract.

When these conditions hold:

    MODELING -> CANONICALIZATION

---

## 12. CANONICALIZATION

### Purpose

Compile the converged product and system definition into the Canonical PRD.

Canonicalization is a synthesis step, not a decision-making step.

### Canonical Synthesis Rules

Canonical synthesis MUST:

- preserve active human authority;
- preserve material product semantics;
- preserve release scope;
- preserve roles and permissions;
- preserve domain semantics;
- preserve capabilities and business rules;
- preserve ownership and responsibility boundaries;
- preserve required architectural invariants;
- preserve material cross-cutting requirements;
- preserve explicit safe-to-defer decisions;
- produce the structure required by the Canonical PRD Contract.

Canonical synthesis MUST NOT:

- create new material product behavior;
- resolve an unresolved material question;
- silently select an AI recommendation;
- weaken a human clarification;
- convert a derived assumption into authority;
- introduce implementation constraints not supported by existing authority.

---

## 13. Canonical Audit

Every synthesized Canonical PRD MUST pass an independent audit before completion.

The audit MUST verify:

- compliance with the Canonical PRD Contract;
- internal consistency;
- preservation of active human authority;
- absence of unsupported material semantics;
- absence of unresolved material questions;
- correct release scope;
- sufficient role and permission definition;
- sufficient domain definition;
- sufficient capability definition;
- ownership consistency;
- architecture consistency;
- responsibility-boundary consistency;
- material non-functional completeness;
- safe classification of deferred decisions;
- downstream sufficiency;
- self-containedness.

### Audit Outcomes

If the audit passes:

    CANONICALIZATION -> DONE

If the audit detects a material question requiring new authority:

    CANONICALIZATION -> WAITING_HUMAN
    WAITING_HUMAN -> MODELING

If the audit detects only a non-material representational or editorial defect:

    repair the Canonical PRD
    ->
    audit again

A material audit finding MUST NOT be repaired solely by rewriting Canonical PRD text if the underlying product or system model is unresolved.

---

## 14. DONE

`DONE` means:

- the Canonical PRD exists;
- all required sections are complete;
- all material questions are resolved;
- remaining deferred decisions are safe to defer;
- internal consistency checks pass;
- the Canonical Audit passes;
- the Canonical PRD is self-contained.

`DONE` is the only successful terminal state.

---

## 15. BLOCKED

`BLOCKED` is used when the workflow cannot make valid progress.

Invalid Source PRD input detected before a run is created is a command/input
error, not a workflow state. Missing, unreadable, truncated, or invalid
`run.json` is an out-of-band storage error because no trusted aggregate exists
to transition. Structural corruption detected after a parseable run has been
created, including failure of the immutable Source PRD integrity check, MAY
transition that trusted active run to `BLOCKED`.

Examples include:

- the Source PRD is fundamentally insufficient to determine even the intended product;
- required human input is unavailable and the workflow cannot continue without it;
- authoritative human decisions remain materially contradictory after clarification;
- required input is corrupted or structurally unusable;
- an invariant failure prevents safe continuation.

The workflow MUST provide a concrete blocking reason.

`BLOCKED` MUST NOT be used merely because the AI is uncertain.

Material uncertainty with available human authority MUST use the Human Decision Protocol instead.

---

## 16. Authority Rule

Only the following may establish material product or system authority:

- the Source PRD, unless superseded;
- explicit human decisions produced through the Human Decision Protocol.

The following are derived artifacts and MUST NOT independently create material authority:

- reviews;
- domain models;
- capability models;
- architecture models;
- convergence findings;
- AI recommendations;
- canonical audit findings;
- intermediate drafts.

Derived artifacts MAY expose the need for a decision but MUST NOT make that decision themselves.

---

## 17. Supersession Rule

A later human decision MAY explicitly supersede earlier authority.

When authority changes:

- the newer active decision MUST be used;
- superseded authority MUST NOT influence current canonical meaning;
- affected derived understanding MUST be reconsidered;
- convergence MUST be established again.

Historical decisions MAY be retained internally for provenance.

They SHOULD NOT appear in the Canonical PRD unless needed to understand current authoritative meaning.

---

## 18. Deferred Decision Rule

A decision MUST NOT be deferred merely to avoid human interaction.

Deferral is allowed only when the Materiality Contract classifies the decision as safe to defer.

Every deferred decision included in the Canonical PRD MUST state:

- what remains undecided;
- why it is safe to defer;
- what constraints downstream choices must preserve.

An unresolved material question MUST always block canonicalization.

---

## 19. Simplicity Rule

The workflow SHOULD use the smallest orchestration model that preserves the required quality invariants.

It SHOULD NOT introduce:

- per-artifact lifecycle states unless required;
- complex dependency graphs unless required by demonstrated behavior;
- selective invalidation machinery when full remodelling is sufficiently cheap and safer;
- parallel authority systems;
- multiple human decision mechanisms;
- workflow states that merely restate which internal operation runs next.

Complexity MUST be justified by an observed requirement, not anticipated future flexibility.

---

## 20. Core Transition Model

The normative high-level transition model is:

    INTAKE
      |
      | sufficient
      v
    MODELING
      |
      | convergence PASS
      v
    CANONICALIZATION
      |
      | audit PASS
      v
    DONE

At any point where a material unresolved decision requires human authority:

    INTAKE / MODELING / CANONICALIZATION
      ->
    WAITING_HUMAN

After a material human decision made after modeling has begun:

    WAITING_HUMAN
      ->
    MODELING

If modeling is internally inconsistent but no new human decision is required:

    MODELING
      ->
    MODELING

If canonical audit finds only non-material representational defects:

    CANONICALIZATION
      ->
    CANONICALIZATION

If valid progress is impossible:

    any active state
      ->
    BLOCKED

---

## 21. Definition of Workflow Completion

The workflow is complete only when:

1. Source PRD material gaps have been identified;
2. all required material human decisions have been obtained;
3. domain semantics have converged;
4. functional capabilities have converged;
5. release scope is explicit;
6. actors, roles, and permissions are sufficiently defined;
7. ownership and system boundaries have converged;
8. required high-level architecture has converged;
9. required responsibility boundaries have converged;
10. material cross-cutting requirements are defined;
11. remaining undecided matters are safely deferred;
12. Canonical PRD synthesis introduces no new material decisions;
13. Canonical Audit passes;
14. the final Canonical PRD satisfies its own Definition of Done.

The central workflow invariant is:

> The workflow is not finished when every processing step has run. It is finished when the Canonical PRD is complete, internally consistent, authoritative, and sufficient for downstream specification without new material product or system decisions.
