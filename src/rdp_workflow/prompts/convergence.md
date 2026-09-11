# Convergence Review

Perform only the supplied workflow analysis operation. Use only the supplied payload as input. Do not use external information or unstated assumptions. Authority status within the payload is defined below. Return one JSON value matching the output schema.

Only the supplied Source PRD and accepted, non-superseded Human Decisions are Material Authority. Within their decided scope, supplied Human Decisions outrank conflicting Source PRD meaning. Domain, Capabilities, Architecture, Deferred Decisions, findings, and other model outputs are derived and never create Authority. AI recommendations are advisory and are not Authority. Never select or fabricate a Human Answer; only an explicit later human answer can create new Material Authority.

Review at least:

- unresolved Material Unknowns;
- contradictions with Active Authority;
- unsupported assumptions or invented material meaning;
- Domain-to-Capability inconsistency;
- Capability-to-Architecture inconsistency;
- actor or permission conflicts;
- target-release scope conflicts or missing scope;
- data, decision, or responsibility ownership conflicts;
- system or responsibility-boundary conflicts;
- major dependency-direction conflicts;
- architecture drift or unsupported implementation constraints;
- unsafe Deferred Decisions;
- material authoritative requirements lost from the model;
- material security, privacy, failure-behavior, or non-functional gaps.

An unresolved question is MATERIAL when different reasonable answers could change product behavior, release scope, actors or permissions, business rules, domain meaning, ownership, system or responsibility boundaries, major dependency direction, high-level architecture, security or privacy, externally visible failure behavior, material non-functional meaning, or another established requirement. When uncertain, treat it as MATERIAL.

If multiple Material Unknowns exist, return exactly one: the earliest consequential blocking question whose resolution most directly enables the next complete remodeling pass.

A question is DEFERRED only when every reasonable allowed downstream choice preserves product behavior, release scope, actors and permissions, domain semantics, responsibility and feature boundaries, data/decision/responsibility ownership, system boundaries, major dependency direction, high-level architecture invariants, security and privacy, externally visible failure behavior, and material non-functional meaning; is independently decidable downstream; and cannot invalidate established Authority. Otherwise it is MATERIAL.

Return outcome PASS only when no unresolved Material Decision or material contradiction remains; all views are mutually consistent and complete for material scope, actors, permissions, domain meaning, ownership, boundaries, architecture, cross-cutting requirements, and release scope; and every remaining open question is safely DEFERRED. PASS contains only its outcome.

Return outcome REMODEL when Active Authority already contains enough information and the derived model is wrong, incomplete, contradictory, or overreaching. Include corrective findings and no Decision draft.

Return outcome HUMAN_DECISION only when required material truth is not unambiguously present in Active Authority. Never ask the human to repair a modeling error that Authority can correct.

HUMAN_DECISION must contain findings and exactly one Material Decision draft with one concrete non-compound question, sufficient context, 2-4 plausible and materially distinct options with their consequences, exactly one advisory recommended option, and a concise recommendation rationale. It must contain no Human Answer or deferral fields. The workflow interprets the draft as a pending MODELING-origin MATERIAL Decision and assigns those lifecycle fields deterministically. The recommendation is advisory and must not be treated as selected Authority.
