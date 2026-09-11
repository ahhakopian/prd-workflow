# Human Decision Protocol

## 1. Purpose

This contract defines how the RDP Convergence Workflow obtains authoritative human decisions when a material question cannot be resolved from existing authority.

The protocol ensures that:

- AI does not make material product or system decisions on behalf of the human;
- the human receives concrete decision options rather than an unstructured question;
- AI recommendations remain advisory;
- human clarifications are preserved as authority;
- downstream reasoning uses the complete human decision without reinterpretation.

---

## 2. Invocation Rule

The Human Decision Protocol MUST be invoked when:

- a decision is classified as `MATERIAL`;
- existing authoritative information does not determine the answer unambiguously.

The protocol MUST NOT be invoked merely because the AI prefers additional confirmation.

If existing authority already determines the answer, the workflow MUST derive the result instead of asking the human again.

If a question is safely deferred under the Materiality Contract, it MUST NOT block the workflow.

---

## 3. AI Responsibilities

For each material unresolved decision, the AI MUST prepare:

- one concrete decision question;
- sufficient context to understand why the decision matters;
- 2–4 materially distinct options;
- one recommended option;
- a concise rationale for the recommendation.

The AI MUST NOT:

- answer the question on behalf of the human;
- treat the recommended option as selected;
- create multiple questions for the same underlying decision;
- combine independent material decisions into one compound question;
- hide a preferred answer by making alternatives obviously unreasonable;
- invent requirements merely to eliminate uncertainty.

---

## 4. Decision Question

Each question MUST:

- address exactly one underlying material decision;
- be understandable without requiring hidden AI reasoning;
- describe the decision at the level relevant to the Canonical RDP;
- avoid unnecessary implementation detail;
- make the material consequence of the decision clear.

A question SHOULD be asked before dependent questions whose meaning may change based on its answer.

---

## 5. Decision Options

The AI MUST provide between 2 and 4 options.

Each option MUST:

- represent a materially distinct answer;
- be internally coherent;
- be plausible in the current product or system context;
- describe the consequence relevant to the decision;
- avoid substantial overlap with another option.

Options MUST NOT include a synthetic `Other` option.

The human always has the separate ability to provide a custom decision.

If only one valid answer exists under current authority, the matter is not a human decision and SHOULD be derived instead.

---

## 6. AI Recommendation

The AI MUST identify one option as its recommendation and provide a concise rationale.

The recommendation SHOULD consider:

- the source PRD;
- current authoritative decisions;
- the Canonical RDP Contract;
- simplicity;
- consistency;
- current release scope;
- avoidance of unnecessary complexity.

The recommendation is advisory only.

It MUST NOT become authority unless explicitly selected by the human.

---

## 7. Allowed Human Answers

The human MAY answer in one of three forms.

### 7.1 Option Selection

The human selects one proposed option.

Example:

    "A"

The selected option becomes authoritative.

### 7.2 Option Selection with Clarification

The human selects one proposed option and adds authoritative clarification.

Example:

    {
      "kind": "option_with_clarification",
      "option_id": "A",
      "clarification": "Only organization administrators may perform this action."
    }

The selected option and clarification together form one authoritative decision.

The clarification has the same authority as the selected option.

It MAY:

- narrow the option;
- qualify the option;
- add a condition;
- add a constraint;
- make the decision more specific.

The workflow MUST preserve both parts.

It MUST NOT reduce the decision back to the original option text alone.

### 7.3 Custom Decision

The human MAY reject all proposed options and provide a custom decision.

Example:

    {
      "kind": "custom",
      "text": "The action requires approval from both the account owner and an administrator."
    }

The custom text becomes the authoritative decision.

The AI MUST NOT silently map a custom decision to the closest proposed option.

---

## 8. Authority Rule

Only an explicit human answer creates new material authority.

The following do NOT create authority:

- AI recommendations;
- AI assumptions;
- common industry practice;
- inferred user preference;
- implementation convenience;
- intermediate domain, capability, or architecture models;
- audit findings.

Derived conclusions MAY use existing authority but MUST NOT extend it with new material meaning.

---

## 9. Clarification Preservation

For an `option_with_clarification` answer:

    Authoritative Decision =
    Selected Option
    +
    Human Clarification

The clarification MUST NOT be treated as:

- optional metadata;
- a lower-priority note;
- commentary that may be ignored;
- an AI-interpretable suggestion.

Downstream stages MUST preserve the combined meaning.

---

## 10. Conflicting Human Answer

If the selected option and human clarification are materially inconsistent and the resulting meaning cannot be determined unambiguously, the AI MUST NOT choose which part to prioritize.

The workflow MUST ask the human a follow-up clarification question.

Example:

    Option A:
    Only administrators may delete accounts.

    Human clarification:
    Regular users must also be able to delete any account.

If the intended final rule is ambiguous, a new human decision is required.

---

## 11. Decision Supersession

A later human decision MAY supersede an earlier human decision.

Supersession MUST be explicit or unambiguous from the decision context.

The AI MUST NOT silently assume that a newer answer replaces an earlier one merely because they are different.

When a decision is superseded:

- the new decision becomes active authority;
- the superseded decision remains historical provenance;
- downstream reasoning MUST use the active decision.

---

## 12. Decision Dependency

A human decision MAY invalidate conclusions produced earlier in the workflow.

After a new material decision:

- affected domain conclusions MUST be reconsidered;
- affected capability conclusions MUST be reconsidered;
- affected architectural conclusions MUST be reconsidered;
- convergence MUST be re-evaluated before canonicalization.

The workflow MUST NOT assume that previously generated downstream reasoning remains valid.

---

## 13. One-Decision-at-a-Time Rule

When material decisions may influence one another, the workflow SHOULD resolve them sequentially.

After each material human decision, the workflow SHOULD reconsider the remaining unresolved questions before asking the next one.

This prevents questions from being asked based on assumptions invalidated by an earlier answer.

Independent decisions MAY be grouped only when resolving one cannot materially change the meaning or relevance of the others.

---

## 14. Decision Record

Each human decision SHOULD be stored with at least:

    Decision ID
    Source / Origin
    Question
    Context
    Options
    Recommended Option
    Recommendation Rationale
    Human Answer
    Supersedes
    Status

The record MAY contain additional provenance required by the implementation.

Decision history is internal workflow state and SHOULD NOT be copied into the Canonical RDP unless needed to understand the current authoritative requirement.

---

## 15. Decision Status

A decision record MUST have one of the following states:

    PENDING
    RESOLVED
    SUPERSEDED

`PENDING` means no authoritative answer exists.

`RESOLVED` means an authoritative human answer exists and is active.

`SUPERSEDED` means a later authoritative decision has explicitly replaced it.

A `PENDING` material decision MUST block Canonical RDP completion.

---

## 16. Failure Rules

The workflow MUST NOT proceed as if a material decision were resolved when:

- the human has not answered;
- the answer cannot be interpreted unambiguously;
- the selected option does not exist;
- the clarification materially contradicts the selected option without a clear final meaning;
- a custom answer is empty or materially unclear.

In such cases, the workflow MUST remain blocked on human input.

---

## 17. Completion Rule

A Human Decision Protocol cycle is complete only when:

- the human has provided an explicit answer;
- the answer is internally understandable;
- the authoritative meaning is preserved exactly;
- any superseded authority is identified when necessary;
- affected downstream reasoning can be reconsidered.

The central rule is:

> AI may frame the decision, propose options, and recommend a choice, but only the human may create new material authority.