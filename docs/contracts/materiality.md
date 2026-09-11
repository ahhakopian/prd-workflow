# Materiality Contract

## 1. Purpose

This contract defines how the RDP Convergence Workflow classifies unresolved decisions.

Every unresolved decision MUST be classified as either:

- `MATERIAL` — must be resolved before the Canonical RDP can be completed;
- `DEFERRED` — may be safely decided downstream.

An unresolved decision MUST NOT remain unclassified.

---

## 2. Core Rule

A decision is `MATERIAL` if two reasonable answers could produce materially different product or system outcomes.

A decision is `DEFERRED` only if every acceptable downstream choice preserves the already established product and system contract.

When uncertain whether a decision is material, the workflow MUST treat it as `MATERIAL`.

---

## 3. Materiality Test

A decision MUST be classified as `MATERIAL` if changing its answer could change any of the following:

1. product behavior;
2. target release scope;
3. actors, roles, or permissions;
4. business rules;
5. domain meaning or invariants;
6. data ownership;
7. decision ownership;
8. responsibility ownership;
9. system boundaries;
10. required responsibility boundaries;
11. major dependency direction;
12. high-level architecture;
13. security or privacy behavior;
14. externally observable failure behavior;
15. a material non-functional requirement;
16. the meaning of another already established requirement.

If none of these can change, the decision MAY be considered for deferral.

---

## 4. Safe-to-Defer Test

A decision MAY be classified as `DEFERRED` only if all of the following are true:

- the product behavior remains unchanged;
- the target release scope remains unchanged;
- actors and permissions remain unchanged;
- domain semantics remain unchanged;
- ownership remains unchanged;
- system and responsibility boundaries remain unchanged;
- architectural invariants remain unchanged;
- material security and privacy properties remain unchanged;
- material non-functional requirements remain satisfied;
- the decision can be made independently during downstream specification or implementation;
- choosing one valid option does not invalidate another established upstream decision.

If any condition is false or unknown, the decision is `MATERIAL`.

---

## 5. Material Decisions Require Human Authority

A `MATERIAL` decision MUST NOT be resolved solely by:

- AI inference;
- AI recommendation;
- common practice;
- implementation convenience;
- assumed industry convention;
- an unstated interpretation of the source PRD.

If existing authoritative information determines the answer unambiguously, the workflow MAY derive the answer from that authority.

Otherwise, the workflow MUST invoke the Human Decision Protocol.

---

## 6. Derived Facts vs Decisions

The workflow MUST distinguish between:

### Derived fact

A conclusion that follows unambiguously from existing authoritative information.

Example:

> Authority states that only administrators may deactivate accounts.

Therefore:

> An ordinary user cannot deactivate another user's account.

No new human decision is required.

### Material decision

A choice between multiple valid interpretations or designs that existing authority does not determine.

Example:

> The PRD requires account deactivation but does not establish whether users may deactivate their own accounts.

If the alternatives change product behavior or permissions, a human decision is required.

The AI MUST NOT convert a material decision into a derived fact merely because one option appears preferable.

---

## 7. Materiality Is About Consequences, Not Technicality

A technical-looking decision MAY be material.

Example:

> Is authorization enforced by the client or by the server?

This is `MATERIAL` because it changes the security model and responsibility ownership.

A product-looking decision MAY be safely deferred.

Example:

> What exact wording should a non-material informational tooltip use?

This MAY be `DEFERRED` if no business, legal, usability, or acceptance requirement depends on the wording.

Classification MUST be based on consequences, not on whether the question appears "product" or "technical".

---

## 8. Examples of Material Decisions

The following are normally `MATERIAL` when not already determined by authority:

- whether a capability is included in the target release;
- whether one role may perform an action;
- which component or responsibility area owns a business decision;
- which system is authoritative for a material piece of data;
- whether user data may be shared with an external service;
- whether a workflow is synchronous or asynchronous when this changes observable behavior or guarantees;
- whether an operation must be strongly consistent;
- whether a failure is retried automatically or surfaced to the user when this changes product behavior;
- whether one responsibility may depend on another;
- whether a capability belongs to one responsibility boundary or another;
- whether a material action requires approval;
- whether data is retained, deleted, or recoverable;
- whether a security-sensitive operation is enforced client-side or server-side.

These examples are illustrative, not exhaustive.

---

## 9. Examples of Safe Deferred Decisions

The following are normally safe to defer when no upstream constraint makes them material:

- internal class names;
- module or package layout;
- helper function structure;
- choice between equivalent implementation libraries;
- internal refactoring strategy;
- exact database index design;
- internal logging format;
- exact API route naming;
- exact method names;
- local code organization;
- test helper structure.

A normally deferred decision becomes `MATERIAL` if, in the actual context, it affects one of the materiality criteria defined above.

---

## 10. Partial Materiality

A question MAY contain both material and non-material parts.

The workflow MUST separate them.

Example:

> Which database should be used, and must data remain within a specific jurisdiction?

The database product may be deferred.

The data residency requirement is material.

The AI MUST NOT force a single classification onto a compound question when its parts have different materiality.

---

## 11. Cascading Decisions

A decision is `MATERIAL` if resolving it can materially change which other questions need to be asked.

Such decisions SHOULD be resolved before dependent questions.

After a material human decision is made, previously derived product, domain, capability, or architecture conclusions that depend on it MUST be reconsidered.

The workflow MUST NOT assume that previously generated downstream conclusions remain valid.

---

## 12. Conflicting Authority

If existing authoritative statements appear materially inconsistent, the AI MUST NOT choose one silently.

The conflict itself is a `MATERIAL` question unless an explicit precedence rule already resolves it.

If clarification is required, the Human Decision Protocol MUST be invoked.

---

## 13. Ambiguous Human Answers

A human answer is authoritative.

However, if a selected option and its accompanying clarification are materially inconsistent with each other and the resulting meaning cannot be determined unambiguously, the workflow MUST ask the human to clarify.

The AI MUST NOT choose which part of the human answer takes precedence unless an explicit rule already defines that precedence.

---

## 14. Deferred Decision Requirements

Every deferred decision recorded in the Canonical RDP MUST include:

- the undecided question;
- why it is safe to defer;
- any constraints that downstream choices must preserve.

A deferred decision MUST NOT be used as a container for unresolved material uncertainty.

If the workflow cannot explain why a decision is safe to defer, it MUST classify it as `MATERIAL`.

---

## 15. Classification Output

When the workflow evaluates an unresolved question, the classification SHOULD be expressible as:

```text
Decision:
Classification: MATERIAL | DEFERRED
Reason:
Affected contract areas:
Required action:

For a material decision:
Required action: HUMAN_DECISION
unless the answer follows unambiguously from existing authority.

For a deferred decision:
Required action: DEFER


16. Completion Rule

The Canonical RDP MUST NOT be completed while any unresolved MATERIAL decision remains.
Canonicalization is allowed only when every discovered unresolved decision is either:
- resolved by existing authority;
- resolved through an explicit human decision; or
- classified as DEFERRED under this contract.

The central rule is:
If choosing differently could change what product or system is being built, the decision must be resolved upstream.