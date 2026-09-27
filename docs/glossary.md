# Glossary

This glossary defines the normative terminology used by the PRD project.

The same term MUST be used consistently across contracts, prompts, schemas, code, tests, and documentation.

---

## Source PRD

The original Product Requirements Document supplied to the workflow.

It represents the initial product intent.

The Source PRD may be incomplete, ambiguous, inconsistent, or insufficient for downstream specification.

Its material meaning remains authoritative unless explicitly superseded by a later Human Decision.

---

## Canonical PRD

The final self-contained Product & System Contract produced by the PRD Convergence Workflow.

It contains the complete and internally consistent product and system definition required for downstream specification.

A Canonical PRD contains no unresolved Material Decisions.

It is the single normative output of the workflow.

---

## PRD Convergence Workflow

The workflow that transforms a Source PRD into a Canonical PRD.

Its responsibility is to discover missing or inconsistent material information, obtain required Human Decisions, build and reconcile derived models, and establish convergence before canonicalization.

---

## Authority

Information that is allowed to determine material product or system meaning.

Material Authority may originate only from:

- the Source PRD, unless superseded;
- explicit Human Decisions.

AI-generated reasoning, recommendations, models, reviews, and audit findings are not Authority.

---

## Active Authority

The currently applicable set of authoritative statements and Human Decisions after explicit supersession has been applied.

Derived reasoning MUST use Active Authority rather than superseded historical decisions.

---

## Human Decision

An explicit answer provided by a human through the Human Decision Protocol.

A Human Decision may be:

- selection of a proposed option;
- selection of an option with Human Clarification;
- a Custom Decision.

A Human Decision creates new Material Authority.

---

## Human Clarification

Authoritative text added by the human to a selected decision option.

The selected option and Human Clarification form one Human Decision.

Human Clarification has the same authority as the selected option.

---

## Custom Decision

A Human Decision written by the human instead of selecting one of the AI-proposed options.

A Custom Decision MUST NOT be silently mapped to the closest proposed option.

---

## AI Recommendation

The option recommended by the AI when presenting a Material Decision to the human.

An AI Recommendation is advisory only.

It does not become Authority unless explicitly selected by the human.

---

## Material Decision

A decision for which different reasonable answers could materially change the product or system contract.

Material Decisions include decisions that may change:

- product behavior;
- release scope;
- actors, roles, or permissions;
- business rules;
- domain semantics;
- ownership;
- system boundaries;
- responsibility boundaries;
- major dependency direction;
- high-level architecture;
- security or privacy behavior;
- material non-functional requirements.

An unresolved Material Decision MUST block canonicalization.

---

## Material Unknown

A Material Decision for which no unambiguous answer currently exists in Active Authority.

A Material Unknown MUST either be resolved through the Human Decision Protocol or remain blocking.

The AI MUST NOT resolve a Material Unknown by assumption.

---

## Derived Fact

A conclusion that follows unambiguously from Active Authority without introducing new material meaning.

A Derived Fact does not require a new Human Decision.

---

## Deferred Decision

An unresolved decision that has been explicitly classified as safe to decide downstream.

A Deferred Decision is allowed only when every acceptable downstream choice preserves the established product and system contract.

A Material Decision MUST NOT be disguised as a Deferred Decision.

---

## Safe to Defer

A property of a decision whose acceptable outcomes do not change established:

- product behavior;
- release scope;
- role or permission semantics;
- domain semantics;
- ownership;
- system boundaries;
- responsibility boundaries;
- architectural invariants;
- material security or privacy properties;
- material non-functional requirements.

---

## Domain Model

A derived representation of the product's material business and domain semantics.

It may contain:

- domain concepts;
- relationships;
- terminology;
- domain invariants.

The Domain Model is not independently authoritative.

---

## Capability

A meaningful user or business ability of the product.

A Capability describes what the product must be able to do.

A Capability is not an implementation task or technical component.

---

## Capability Model

A derived representation of the product's material Functional Capabilities, actors, required behavior, business rules, release relevance, and material dependencies.

The Capability Model is not independently authoritative.

---

## High-Level Architecture

The material structural definition of the system required to preserve the agreed Product & System Contract.

It may define:

- major responsibility areas;
- ownership;
- system boundaries;
- major interactions;
- dependency directions;
- architectural invariants;
- material architectural constraints.

High-Level Architecture does not include implementation details unless they are explicit upstream constraints.

---

## Architecture Model

The derived representation of the current High-Level Architecture.

The Architecture Model may expose Material Unknowns but MUST NOT resolve them by creating new Authority.

---

## Responsibility Boundary

A normative boundary defining ownership of a material responsibility.

A Responsibility Boundary may define:

- what it owns;
- what it does not own;
- what it may depend on;
- what it must not depend on.

---

## Ownership

The authoritative assignment of responsibility for a material concern.

The workflow distinguishes, where relevant:

- Data Ownership;
- Decision Ownership;
- Responsibility Ownership.

Using or displaying information does not by itself establish Ownership.

---

## System Boundary

The distinction between responsibilities belonging to the system and responsibilities belonging to external actors or systems.

---

## Architectural Invariant

A High-Level Architecture rule that downstream design and implementation MUST preserve.

Changing an Architectural Invariant requires new Material Authority.

---

## Non-Functional Requirement

A requirement describing a material quality, constraint, or cross-cutting property of the system.

Examples include:

- security;
- privacy;
- reliability;
- performance;
- consistency;
- availability;
- auditability;
- data retention.

---

## Convergence

The condition in which Active Authority, Domain Model, Capability Model, High-Level Architecture, release scope, ownership, roles, and responsibility boundaries form one materially consistent system definition.

Convergence requires that no unresolved Material Decision remains.

---

## Convergence Review

An independent evaluation of the current derived product and system understanding.

A Convergence Review determines whether:

- the models are mutually consistent;
- the models are consistent with Active Authority;
- Material Unknowns remain;
- remodelling is required;
- convergence has been reached.

A Convergence Review does not create Authority.

---

## Modeling

The workflow phase that derives and reconciles the Domain Model, Capability Model, and High-Level Architecture.

Modeling MAY reveal new Material Decisions.

Modeling MUST NOT create their authoritative answers.

---

## Canonicalization

The process of compiling a converged product and system definition into the Canonical PRD.

Canonicalization is a synthesis operation.

It MUST NOT introduce new Material Decisions or new Material Authority.

---

## Canonical Audit

The independent validation of a Canonical PRD candidate.

The Canonical Audit verifies:

- compliance with the Canonical PRD Contract;
- preservation of Active Authority;
- internal consistency;
- absence of unresolved Material Decisions;
- safe Deferred Decisions;
- self-containment;
- downstream sufficiency.

The Canonical Audit does not create Authority.

---

## Self-Contained

A property of the Canonical PRD meaning that correct downstream interpretation does not require access to the Source PRD, decision history, AI recommendations, or intermediate workflow artifacts.

---

## Downstream Consumer

Any specification or implementation workflow that receives the Canonical PRD.

Core PRD contracts MUST NOT depend on a particular Downstream Consumer.

Tool-specific integration rules belong in separate integration contracts.

---

## Downstream Sufficiency

The condition in which a Downstream Consumer can continue specification using only the Canonical PRD without making new Material product or system decisions.

---

## Supersession

The explicit replacement of an earlier authoritative statement or Human Decision by a later Human Decision.

Superseded information may remain in historical provenance but MUST NOT affect current Active Authority.

---

## Provenance

Internal information describing where a requirement, decision, or artifact originated.

Provenance may include historical decisions, AI recommendations, findings, and supersession relationships.

Provenance is internal workflow information unless explicitly required by the Canonical PRD Contract.

---

## Target Release

The release whose required implementation scope is defined by the Canonical PRD.

Material Capabilities must be classified for the Target Release as:

- `IN`;
- `PARTIAL`;
- `OUT`;
- `FUTURE`.

---

## Blocking

A condition in which the workflow cannot safely proceed without additional authoritative information or correction.

An unresolved Material Decision is blocking.

AI uncertainty alone is not automatically blocking if existing Authority is sufficient to derive the answer.

---

## Normative Terms

The contracts use the following meanings:

- `MUST` — mandatory;
- `MUST NOT` — prohibited;
- `SHOULD` — recommended unless there is a justified reason to differ;
- `SHOULD NOT` — discouraged unless there is a justified reason;
- `MAY` — optional.