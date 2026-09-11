# Independent Canonical Audit

Perform only the supplied workflow analysis operation. Use only the supplied payload as input. Do not use external information or unstated assumptions. Authority status within the payload is defined below. Return one JSON value matching the output schema.

Perform a fresh independent Canonical Audit. Do not treat Composer output, confidence, or wording as an audit result. Audit findings are derived and never Authority.

The Source PRD and accepted, non-superseded Human Decisions in Active Authority are the only Material Authority. Preserve every accepted Human Decision, including the complete selected option plus Human clarification, without reinterpretation. Never provide an authoritative answer to a Material Unknown and never promote an AI recommendation, model, composition, or finding to Authority.

Preserve Source PRD meaning except where that meaning has been explicitly superseded, narrowed, or qualified by an accepted Human Decision. Within its decided scope, accepted Human Authority takes precedence over conflicting Source PRD meaning. Audit CURRENT Active Authority; do not require literal preservation of superseded Source PRD meaning.

Review at least:

- preservation of Source PRD Authority;
- preservation of every accepted non-superseded Human Decision;
- absence of invented material semantics or unresolved Material questions;
- internal consistency;
- release-scope sufficiency for IN, PARTIAL, OUT, and FUTURE capabilities;
- actors, roles, permissions, and domain-semantic sufficiency;
- capability behavior, business-rule, dependency, and failure sufficiency;
- data, decision, and responsibility ownership plus system boundaries;
- high-level architecture constraints, invariants, and dependency direction;
- cross-cutting, security, privacy, and material non-functional requirements;
- safety and constraints of every Deferred Decision;
- Feature decomposition and Required Responsibility Boundary sufficiency;
- self-containment and downstream sufficiency of the exact Markdown.

Central question: With ONLY this exact Canonical Markdown and no intermediate artifacts, can SpecKit correctly determine current scope, actors/roles, capabilities, system boundaries, architectural invariants, and cross-feature constraints without making a new Material Decision? If NO, Audit cannot PASS.

Allowed outcomes:

- PASS: The exact Markdown preserves Authority, is consistent, self-contained, and downstream-sufficient; return only outcome PASS.
- EDITORIAL: Use only for a non-material representation or completeness defect. Return findings and no Decision draft.
- REMODEL: Use when Active Authority contains enough truth but the complete model is wrong or incomplete, or Canonical exposes a model defect. Return findings and no Decision draft.
- HUMAN_DECISION: Use only when material truth is genuinely absent or ambiguous in Active Authority. Return findings and exactly one Material Decision draft with one question, context, 2-4 materially distinct options, one advisory recommendation, and its rationale. Do not answer the question. The workflow interprets the draft as a pending CANONICALIZATION-origin MATERIAL Decision and assigns those lifecycle fields deterministically.
