# SpecKit Handoff Contract

## 1. Purpose

This contract defines how the PRD project hands a completed Canonical RDP to SpecKit.

It is an integration contract.

It does not change the Canonical RDP Contract, Materiality Contract, Human Decision Protocol, Workflow Contract, or RDP Convergence Invariants.

The purpose of this contract is to ensure that SpecKit receives one complete and authoritative upstream product and system definition without depending on internal PRD workflow artifacts.

---

## 2. Handoff Artifact

SpecKit MUST receive exactly one normative upstream artifact:

    Canonical RDP

The Canonical RDP MUST have completed the RDP Convergence Workflow and passed the Canonical Audit before handoff.

A draft, intermediate model, or partially converged RDP MUST NOT be handed to SpecKit as authoritative input.

---

## 3. Single-Artifact Rule

The Canonical RDP MUST be sufficient as the sole authoritative input from the PRD project.

SpecKit MUST NOT require access to:

- the Source PRD;
- clarification history;
- Human Decision records;
- AI recommendations;
- Domain Model artifacts;
- Capability Model artifacts;
- Architecture Model artifacts;
- convergence findings;
- Canonical Audit findings;
- previous Canonical RDP drafts;
- internal workflow state.

These artifacts MAY exist for provenance and debugging inside the PRD project, but they are not part of the normative handoff.

---

## 4. Authority Boundary

At handoff time, the Canonical RDP becomes the authoritative representation of upstream product and system intent for SpecKit.

SpecKit SHOULD interpret the Canonical RDP as the current resolved contract.

SpecKit MUST NOT treat earlier PRD artifacts or historical decisions as competing authority.

If historical information conflicts with the Canonical RDP, the Canonical RDP governs the SpecKit workflow.

---

## 5. Decisions Already Made Upstream

SpecKit MUST preserve material decisions already established in the Canonical RDP.

This includes, where applicable:

- product goals and non-goals;
- target release scope;
- included, excluded, partial, and future capabilities;
- actors and roles;
- permissions;
- business rules;
- material domain semantics;
- domain invariants;
- data ownership;
- decision ownership;
- responsibility ownership;
- system boundaries;
- required responsibility boundaries;
- high-level architectural constraints;
- architectural invariants;
- material dependency directions;
- security and privacy constraints;
- material non-functional requirements.

SpecKit MUST NOT silently reopen these decisions during feature specification or implementation planning.

---

## 6. Decisions Allowed Downstream

SpecKit MAY make decisions that are explicitly left open by the Canonical RDP or are otherwise non-material under the Materiality Contract.

Typical downstream decisions may include:

- implementation structure;
- class and function design;
- package and module organization;
- internal APIs;
- repository structure;
- specific library choices;
- specific framework usage;
- database indexing;
- internal refactoring strategy;
- test implementation details;
- local error-handling mechanics;
- other implementation details that preserve the Canonical RDP contract.

A downstream decision MUST remain within all constraints established by the Canonical RDP.

---

## 7. Deferred Decisions

Explicit Deferred Decisions in the Canonical RDP MAY be resolved by SpecKit.

SpecKit MUST preserve any constraints attached to a Deferred Decision.

A Deferred Decision MUST NOT be interpreted as permission to change upstream product or system semantics.

If resolving a Deferred Decision would require changing a material upstream decision, it is no longer a valid downstream-only decision.

---

## 8. Feature Decomposition

SpecKit MAY decompose the Canonical RDP into concrete Features.

Feature decomposition MUST preserve:

- release scope;
- capability semantics;
- domain semantics;
- ownership;
- system boundaries;
- architectural invariants;
- required responsibility boundaries;
- material dependency constraints.

Capabilities and SpecKit Features are not required to have a one-to-one relationship.

A Capability describes what the product must be able to do.

A Feature is a downstream specification and implementation unit.

SpecKit MAY split one Capability across multiple Features or combine related Capabilities where this does not violate established responsibility boundaries.

---

## 9. Feature Boundary Rule

If the Canonical RDP defines a required responsibility boundary, SpecKit MUST preserve it during Feature decomposition.

A downstream Feature MUST NOT:

- take ownership assigned elsewhere;
- move a material responsibility across an established boundary;
- introduce a forbidden dependency;
- collapse two explicitly separated responsibilities;
- create backward ownership that contradicts the Canonical RDP.

SpecKit MAY refine boundaries when the refinement preserves all upstream constraints.

It MUST NOT redefine their material meaning without returning the issue upstream.

---

## 10. No Silent Product Design Rule

SpecKit MUST NOT silently make a new material product or system decision merely because specification cannot continue.

If SpecKit discovers an ambiguity with materially different valid interpretations, it MUST treat this as an upstream contract defect rather than choosing one interpretation automatically.

Examples include uncertainty about:

- whether a capability belongs to the target release;
- who may perform a material action;
- which system owns a decision;
- which responsibility owns material data;
- whether a boundary is internal or external;
- which architecture invariant applies;
- which materially different failure behavior is intended.

Such ambiguity indicates that the Canonical RDP was insufficient for the affected area.

---

## 11. Upstream Escalation Rule

If SpecKit discovers that correct continuation requires a new Material Decision, the issue MUST be returned to the PRD Convergence Workflow.

The expected flow is:

    SpecKit
        ->
    Material issue discovered
        ->
    PRD Convergence Workflow
        ->
    Human Decision if required
        ->
    Modeling / Convergence
        ->
    New Canonical RDP
        ->
    SpecKit

SpecKit MUST NOT create upstream authority itself.

---

## 12. Canonical RDP Revision

A material upstream correction or new Human Decision MUST result in a new Canonical RDP revision.

The revised Canonical RDP becomes the new authoritative handoff artifact.

SpecKit SHOULD evaluate affected Feature specifications against the revised contract.

A Canonical RDP revision MUST NOT require unrelated Features to be redesigned unless the new upstream authority materially affects them.

---

## 13. Forward Evolution Rule

SpecKit SHOULD prefer forward evolution of Features and responsibility boundaries.

Existing earlier Features SHOULD NOT be modified merely because a later Feature can be implemented more conveniently by moving responsibility backward.

Backward modification is acceptable only when required to preserve or restore the authoritative Canonical RDP contract and no reasonable forward-oriented solution exists.

The detailed enforcement of Feature evolution policy belongs to SpecKit governance, not to the PRD project.

---

## 14. Separation of Responsibilities

The PRD project is responsible for determining:

- what product is being built;
- what belongs to the target release;
- who the actors are;
- what material behavior is required;
- what domain semantics apply;
- where material ownership lies;
- which responsibility boundaries are mandatory;
- which high-level architectural constraints must be preserved;
- which material cross-cutting requirements apply.

SpecKit is responsible for:

- decomposing the Canonical RDP into implementable Features;
- specifying Feature behavior in greater detail;
- planning implementation;
- resolving safe downstream decisions;
- producing implementation-oriented artifacts;
- implementing within the established product and system contract.

The boundary is:

> The PRD project determines what product and system must exist. SpecKit determines how to specify and implement it without redefining that product or system.

---

## 15. Handoff Preconditions

The Canonical RDP MUST NOT be handed to SpecKit unless all of the following are true:

1. the RDP Convergence Workflow reached `DONE`;
2. the Canonical RDP Contract is satisfied;
3. no unresolved Material Decision remains;
4. all active Human Decisions are preserved;
5. convergence has passed;
6. the Canonical Audit has passed;
7. all Deferred Decisions are safe to defer;
8. the document is self-contained;
9. downstream sufficiency has been established.

---

## 16. SpecKit Entry Condition

SpecKit SHOULD begin specification from the Canonical RDP as a new authoritative input.

SpecKit SHOULD NOT begin by re-discovering product intent already established upstream.

Clarification inside SpecKit SHOULD focus on downstream specification detail.

If clarification reveals a missing Material Decision, the issue MUST be escalated upstream rather than resolved as an ordinary downstream implementation choice.

---

## 17. Handoff Integrity

The Canonical RDP supplied to SpecKit MUST be the same revision that passed Canonical Audit.

The handoff process SHOULD preserve:

- document identity;
- revision identity;
- content integrity.

Implementation MAY use hashes, version identifiers, or equivalent mechanisms where needed.

The exact integrity mechanism is an implementation detail of the integration.

---

## 18. Integration Invariant

The core integration invariant is:

> SpecKit receives one Canonical RDP, preserves its material product and system decisions, resolves only valid downstream decisions, and returns any newly discovered material ambiguity to the PRD Convergence Workflow instead of silently designing the product itself.