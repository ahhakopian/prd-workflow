# PRD Convergence Invariants

## 1. Purpose

This contract defines the non-negotiable invariants of the PRD Convergence Workflow.

An implementation MAY change its internal architecture, orchestration, storage, prompts, or agent structure, but it MUST preserve every invariant defined here.

These invariants are the primary acceptance criteria for the workflow.

---

## 2. Source Authority Invariant

The Source PRD is initial authority.

A later explicit human decision MAY supersede Source PRD meaning.

AI-generated artifacts MUST NOT independently create new material authority.

The following are not authority by themselves:

- AI recommendations;
- reviews;
- domain models;
- capability models;
- architecture models;
- convergence findings;
- canonical drafts;
- audit findings.

---

## 3. Human Authority Invariant

A new material product or system decision MUST originate from an explicit human answer.

The AI MAY:

- identify the need for a decision;
- formulate the question;
- propose options;
- recommend an option;
- explain its recommendation.

The AI MUST NOT select the authoritative answer on behalf of the human.

---

## 4. Recommendation Isolation Invariant

An AI recommendation MUST remain advisory until explicitly selected by the human.

The workflow MUST NOT infer human consent from:

- absence of an answer;
- continuation of the workflow;
- previous similar choices;
- common practice;
- implementation convenience;
- the AI's confidence.

No default recommendation may silently become authority.

---

## 5. Human Clarification Preservation Invariant

When the human selects an option and provides additional clarification:

    Authoritative Decision =
    Selected Option
    +
    Human Clarification

Both parts MUST be preserved.

The clarification MUST have the same authority as the option itself.

The workflow MUST NOT:

- discard the clarification;
- weaken it;
- summarize away material meaning;
- map it back to the unqualified option;
- replace it with AI interpretation.

---

## 6. Custom Decision Invariant

A custom human decision is authoritative as written.

The workflow MUST NOT silently convert a custom answer into the closest AI-proposed option.

If the custom decision is materially ambiguous, the workflow MUST request clarification instead of choosing an interpretation.

---

## 7. Material Unknown Invariant

A material unresolved question MUST block Canonical PRD completion.

A material unknown MUST be resolved by either:

- existing authority that determines the answer unambiguously; or
- an explicit human decision.

AI inference alone MUST NOT resolve a material unknown.

---

## 8. Deferred Decision Invariant

A decision MAY be deferred only when it satisfies the Materiality Contract.

A deferred decision MUST NOT change any established:

- product behavior;
- release scope;
- actor or permission model;
- domain semantics;
- ownership;
- system boundary;
- required responsibility boundary;
- architectural invariant;
- material security or privacy property;
- material non-functional requirement.

If safe deferral cannot be demonstrated, the decision MUST be treated as material.

---

## 9. No Hidden Decision Invariant

No material decision may enter the Canonical PRD solely through:

- synthesis wording;
- architecture assumptions;
- domain interpretation;
- capability decomposition;
- audit correction;
- model recommendation.

Every material statement in the Canonical PRD MUST be traceable to existing authority or be an unambiguous derivation from that authority.

---

## 10. One Meaning Invariant

A material concept MUST have one active meaning throughout the converged model and Canonical PRD.

The workflow MUST detect materially conflicting meanings across:

- Source PRD;
- active human decisions;
- domain model;
- capability model;
- architecture model;
- Canonical PRD.

Such conflicts MUST be resolved before completion.

---

## 11. Scope Consistency Invariant

Every material capability MUST have an explicit target-release status.

Allowed statuses are:

    IN
    PARTIAL
    OUT
    FUTURE

The same capability MUST NOT have contradictory release status in different parts of the Canonical PRD.

For `PARTIAL`, included and excluded behavior MUST both be explicit.

---

## 12. Role Consistency Invariant

Every material actor or role referenced by a requirement or capability MUST be defined.

Material permissions MUST NOT depend on downstream inference.

Two sections MUST NOT assign contradictory permissions or responsibilities to the same role.

---

## 13. Ownership Consistency Invariant

Material data, decisions, and responsibilities MUST NOT have conflicting authoritative owners.

The workflow MUST distinguish between:

- data ownership;
- decision ownership;
- responsibility ownership;
- consumption or display of information.

Using information MUST NOT automatically imply ownership.

---

## 14. Boundary Consistency Invariant

Required responsibility boundaries MUST be mutually compatible.

Two boundaries MUST NOT simultaneously claim exclusive ownership of the same material responsibility.

A responsibility MUST NOT be assigned outside the established system boundary without an explicit authoritative decision.

---

## 15. Architecture Consistency Invariant

High-level architecture MUST support all `IN` and applicable `PARTIAL` capabilities without violating:

- role constraints;
- ownership;
- domain invariants;
- responsibility boundaries;
- material non-functional requirements.

Architecture MUST NOT introduce new material product behavior merely to make the design convenient.

---

## 16. Derived Model Non-Authority Invariant

Domain, capability, and architecture models are derived reasoning artifacts.

They MAY:

- expose contradictions;
- expose missing information;
- reveal material decisions;
- organize existing authority;
- derive consequences of existing authority.

They MUST NOT independently create new material authority.

---

## 17. Reconsideration Invariant

A new material human decision MAY invalidate previously derived reasoning.

After such a decision, affected conclusions MUST be reconsidered before canonicalization.

The workflow MUST NOT assume that previously generated domain, capability, architecture, or convergence results remain valid merely because they were valid before the decision.

---

## 18. Convergence Invariant

The workflow MUST NOT enter successful canonicalization until the current product and system model has converged.

Convergence requires:

- no unresolved material decision;
- no material contradiction;
- consistent domain semantics;
- consistent release scope;
- consistent actors and permissions;
- consistent ownership;
- consistent responsibility boundaries;
- architecture compatible with required capabilities;
- remaining undecided matters classified as safely deferred.

---

## 19. Canonicalization Purity Invariant

Canonicalization is a compilation/synthesis operation.

It MUST NOT:

- make a new material decision;
- choose between unresolved alternatives;
- invent missing requirements;
- reinterpret human authority;
- introduce unsupported architectural constraints.

If canonicalization appears to require a new material decision, the workflow MUST return to convergence.

---

## 20. Canonical Self-Containment Invariant

The Canonical PRD MUST contain all information required for correct downstream specification.

A downstream consumer MUST NOT require access to:

- Source PRD;
- human decision history;
- intermediate reviews;
- domain-model artifacts;
- capability-model artifacts;
- architecture-model artifacts;
- AI recommendations;
- convergence findings.

These MAY remain internal workflow artifacts.

---

## 21. Canonical Sufficiency Invariant

Using only the Canonical PRD, downstream work MUST be able to determine:

- what product is being built;
- who it is for;
- what the target release includes and excludes;
- what capabilities are required;
- what actors and permissions exist;
- what domain semantics apply;
- who owns material data, decisions, and responsibilities;
- where system and responsibility boundaries lie;
- which high-level architectural constraints are mandatory;
- which material cross-cutting requirements apply;
- which decisions remain intentionally deferred.

If any of these requires a new material product or system decision, the Canonical PRD is not complete.

---

## 22. Canonical Audit Invariant

A Canonical PRD MUST pass an independent audit before the workflow reaches `DONE`.

The audit MUST verify at least:

- contract completeness;
- authority preservation;
- internal consistency;
- absence of unsupported material semantics;
- absence of unresolved material questions;
- safe deferred decisions;
- self-containment;
- downstream sufficiency.

The synthesis operation MUST NOT audit itself as the sole quality gate.

---

## 23. Audit Repair Invariant

A non-material representational defect MAY be repaired directly during canonicalization.

A material defect MUST NOT be repaired only by editing Canonical PRD wording.

If a finding exposes missing or conflicting material authority:

    Canonicalization
        ->
    Human Decision / Modeling
        ->
    Convergence
        ->
    Canonicalization

The underlying model MUST be corrected before the final document.

---

## 24. Human Decision Re-entry Invariant

Any new material human decision discovered after modeling has begun MUST cause the workflow to re-enter modeling/convergence.

The workflow MUST NOT proceed directly from a new material decision to final Canonical PRD output using stale derived models.

---

## 25. Sequential Decision Invariant

When material decisions may influence each other, they SHOULD be resolved sequentially.

After each material decision, remaining unanswered questions SHOULD be reconsidered.

The workflow MUST NOT continue asking questions that have become obsolete or materially changed because of an earlier answer.

---

## 26. No Unnecessary HITL Invariant

The workflow MUST NOT ask the human to decide a question that existing authority already resolves unambiguously.

AI reasoning SHOULD derive such consequences directly.

Human interaction is required for new material authority, not for deterministic derivation.

---

## 27. Failure Transparency Invariant

If the workflow cannot progress safely, it MUST expose a concrete blocking reason.

It MUST NOT:

- silently guess;
- silently skip a required decision;
- mark an incomplete result as Canonical;
- hide an invariant violation behind generic model failure.

---

## 28. Single Decision Mechanism Invariant

The product SHOULD use one Human Decision Protocol for all material questions regardless of where they are discovered.

Separate decision semantics for intake, modeling, architecture, or canonical audit SHOULD NOT exist.

The origin of a question MAY differ; the authority semantics MUST remain the same.

---

## 29. Single Canonical Output Invariant

The workflow produces one normative downstream artifact:

    Canonical PRD

Intermediate artifacts MAY exist internally.

They MUST NOT be required as additional normative inputs to correctly interpret the Canonical PRD.

---

## 30. Implementation Independence Invariant

The invariants in this contract define behavior, not implementation architecture.

The implementation MAY use:

- a finite-state machine;
- agents;
- deterministic functions;
- persisted artifacts;
- in-memory state;
- other internal mechanisms.

No particular implementation mechanism is required unless necessary to preserve these invariants.

---

## 31. Simplicity Invariant

Implementation complexity MUST be justified by a demonstrated requirement.

The system SHOULD prefer:

- explicit rules over implicit behavior;
- one mechanism over parallel mechanisms;
- full safe reconsideration over complex selective invalidation when practical;
- deterministic validation where deterministic validation is sufficient;
- small workflow states over states that merely mirror internal steps.

Complexity MUST NOT be added solely for anticipated future flexibility.

---

## 32. Completion Invariant

The workflow MAY enter `DONE` only if all of the following are true:

1. the Canonical PRD exists;
2. the Canonical PRD Contract is satisfied;
3. no material unresolved decision remains;
4. all active human authority is preserved;
5. domain semantics are internally consistent;
6. target-release scope is internally consistent;
7. role and permission semantics are internally consistent;
8. ownership is internally consistent;
9. required responsibility boundaries are internally consistent;
10. high-level architecture is compatible with required capabilities;
11. all remaining undecided matters are safely deferred;
12. canonicalization introduced no unsupported material authority;
13. Canonical Audit passes;
14. the Canonical PRD is self-contained;
15. the Canonical PRD is sufficient for downstream specification.

The final invariant is:

> The workflow is complete only when downstream work may decide how to implement the system without being forced to decide what product or system it is supposed to build.