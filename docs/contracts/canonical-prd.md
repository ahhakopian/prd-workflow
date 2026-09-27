# Canonical PRD Contract

## 1. Purpose

The Canonical PRD is the final, self-contained Product & System Contract produced from a source PRD.

It defines the product and system sufficiently for a downstream specification workflow to continue without making new material product or system decisions.

The Canonical PRD is the definition of done for the PRD Convergence Workflow.

It MUST describe the current intended system, not the history of how decisions were reached.

---

## 2. Canonicality Rule

A Canonical PRD is ready only when:

- all material product and system questions are resolved;
- its sections are mutually consistent;
- no material decision is based only on an AI assumption or recommendation;
- any remaining undecided matters are explicitly safe to defer downstream;
- the document is sufficient as the sole upstream input for further specification.

A material unresolved question MUST block canonicalization.

---

## 3. Material Decision Rule

A decision is material if different reasonable answers could change any of the following:

- product behavior;
- release scope;
- actors, roles, or permissions;
- business rules;
- domain semantics;
- data, decision, or responsibility ownership;
- system boundaries;
- responsibility boundaries;
- major dependency direction;
- high-level architecture;
- security or privacy behavior;
- a material non-functional requirement.

A decision MAY be deferred only when all acceptable downstream choices preserve these properties.

AI MUST NOT resolve a material unknown on behalf of the human.

---

## 4. Human Decision Rule

When a material question cannot be resolved from existing authoritative information, the workflow MUST ask a human.

The AI MUST provide:

- one concrete decision question;
- 2–4 materially distinct options;
- one recommended option;
- a concise rationale for the recommendation.

The human MAY:

- select one option;
- select an option and add a clarification;
- provide a custom decision.

A selected option plus human clarification forms one authoritative decision.

The clarification has the same authority as the selected option and MUST NOT be discarded, weakened, or silently reinterpreted.

An AI recommendation is advisory only and MUST NOT become authority without an explicit human answer.

---

## 5. Required Structure

A Canonical PRD MUST contain the following sections:

1. Product Definition
2. Scope & Release Boundary
3. Actors & Roles
4. Domain Model
5. Functional Capabilities
6. System Boundaries & Ownership
7. High-Level Architecture
8. Cross-Cutting & Non-Functional Requirements
9. Required Responsibility Boundaries
10. Deferred Decisions & Handoff Constraints

A section MUST NOT be omitted merely because no additional requirements were found. In that case, the document MUST state that no additional constraints apply.

---

## 6. Product Definition

This section MUST define:

- the problem being solved;
- target users;
- intended product outcome;
- product goals;
- explicit non-goals.

Goals and non-goals SHOULD use stable identifiers.

This section defines what the product is and why it exists. It MUST NOT prescribe implementation details.

---

## 7. Scope & Release Boundary

This section MUST identify the target release.

Every material capability MUST have an explicit release status:

- `IN` — required in the target release;
- `PARTIAL` — only explicitly listed parts are included;
- `OUT` — explicitly excluded from the target release;
- `FUTURE` — known but deferred to a later release.

For `PARTIAL`, both included and excluded behavior MUST be stated.

Priority labels alone MUST NOT be used as a substitute for release scope.

---

## 8. Actors & Roles

This section MUST define all material human, system, and external actors.

For every material role, it MUST be possible to determine:

- its purpose or responsibility;
- what it may do;
- what it must do, where applicable;
- what it must not do, where applicable;
- material permission boundaries.

Role and permission semantics MUST NOT be left for downstream inference.

---

## 9. Domain Model

This section MUST define the shared business/domain semantics required for consistent downstream specification.

It SHOULD contain:

- material domain concepts;
- material relationships;
- domain invariants;
- canonical terminology where ambiguity would matter.

It MUST describe domain meaning, not implementation structure.

Technical concepts such as repositories, controllers, databases, queues, or APIs MUST NOT appear as domain concepts unless they are genuinely part of the product domain.

---

## 10. Functional Capabilities

This section MUST describe the product's material user or business capabilities.

Each capability SHOULD define:

- name and purpose;
- release status;
- applicable actors;
- required behavior;
- material business rules;
- material dependencies;
- material failure or rejection conditions.

Capabilities describe what the product must do.

They MUST NOT be decomposed into technical implementation tasks.

---

## 11. System Boundaries & Ownership

This section MUST make the system boundary explicit.

It MUST identify, where material:

- responsibilities inside the system;
- responsibilities outside the system;
- external dependencies;
- data ownership;
- decision ownership;
- responsibility ownership;
- authoritative systems of record.

Using, displaying, or transmitting information MUST NOT be treated as ownership unless ownership is explicitly established.

---

## 12. High-Level Architecture

This section MUST define only architectural decisions that downstream work is required to preserve.

It SHOULD describe:

- major responsibility areas or components;
- their responsibilities;
- explicit non-responsibilities where material;
- major interactions;
- architectural constraints;
- architectural invariants;
- material dependency directions.

It MUST NOT prescribe implementation details unless they are explicit upstream constraints.

Frameworks, libraries, database engines, API styles, class structures, repository patterns, and similar choices SHOULD remain downstream decisions unless they are materially required.

---

## 13. Cross-Cutting & Non-Functional Requirements

This section MUST contain all material requirements that apply across multiple capabilities or materially constrain implementation.

Applicable categories may include:

- security;
- privacy;
- reliability;
- performance;
- consistency;
- auditability;
- observability;
- availability;
- compatibility;
- data retention.

Only applicable categories need to be included.

Material non-functional requirements MUST be specific enough that downstream work is not forced to invent the intended requirement level.

---

## 14. Required Responsibility Boundaries

This section MUST define any responsibility boundaries that downstream decomposition is not allowed to violate.

Where material, a boundary SHOULD state:

- what it owns;
- what it does not own;
- what it may depend on;
- what it must not depend on;
- which capabilities it supports.

This section constrains decomposition without performing detailed downstream feature specification.

---

## 15. Deferred Decisions & Handoff Constraints

A remaining decision MAY be listed as deferred only when it is proven safe to decide downstream.

Each deferred decision MUST state:

- what remains undecided;
- why it is safe to defer;
- any constraints that downstream choices must preserve.

The section MUST also make clear which decisions are already fixed upstream and MUST NOT be reopened downstream.

At minimum, downstream work MUST preserve established:

- release scope;
- actors and roles;
- material domain semantics;
- ownership rules;
- system boundaries;
- architectural invariants;
- required responsibility boundaries;
- material cross-cutting requirements.

A material unresolved question MUST NOT be disguised as a deferred decision.

---

## 16. Consistency Requirements

Before the document can be Canonical, all of the following MUST hold:

- capability scope is consistent with the release boundary;
- every referenced material role is defined;
- material domain terms have one consistent meaning;
- ownership assignments do not contradict each other;
- capabilities are compatible with architectural invariants;
- required responsibility boundaries do not claim conflicting ownership;
- every material capability has an explicit release status;
- no material decision exists only because the AI inferred or recommended it;
- no material unresolved assumption remains;
- every deferred decision satisfies the safe-to-defer rule.

---

## 17. Downstream Sufficiency

The Canonical PRD MUST be understandable and usable without access to:

- the source PRD;
- clarification history;
- AI recommendations;
- intermediate domain, capability, or architecture artifacts;
- decision history;
- previous drafts.

A downstream specification workflow, using only the Canonical PRD, MUST be able to determine:

- what product is being built;
- what is in and out of the target release;
- who the actors and roles are;
- what behavior is required;
- what domain semantics must be preserved;
- where ownership and system boundaries lie;
- which high-level architectural constraints are mandatory;
- which cross-cutting requirements apply;
- which responsibility boundaries must be preserved;
- which decisions remain intentionally open downstream.

If a new material product or system decision is still required to continue correctly, the PRD is not Canonical.

---

## 18. Provenance Policy

The Canonical PRD represents current authoritative meaning.

It SHOULD NOT contain:

- superseded decisions;
- rejected alternatives;
- AI recommendations;
- internal audit findings;
- intermediate reasoning;
- workflow history.

Such information MAY be retained internally by the workflow but is not part of the Canonical PRD contract.

Stable identifiers SHOULD be used where downstream traceability is valuable.

---

## 19. Definition of Done

A Canonical PRD is complete when:

1. all required sections are present;
2. the target release is explicit;
3. all material capabilities have explicit release scope;
4. all material actors, roles, and permissions are defined;
5. material domain semantics are unambiguous;
6. material ownership and system boundaries are explicit;
7. required high-level architectural decisions are resolved;
8. material cross-cutting and non-functional requirements are defined;
9. required responsibility boundaries are consistent;
10. every material unknown has authoritative resolution;
11. no AI recommendation has silently become authority;
12. all remaining undecided matters are demonstrably safe to defer;
13. the document is internally consistent;
14. the document is self-contained;
15. no additional upstream artifact is required for correct downstream interpretation.

The core completion criterion is:

> Downstream work may decide how to implement the system, but it must not be forced to redefine what product or system it has been asked to build.