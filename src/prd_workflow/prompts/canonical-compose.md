# Canonical PRD Composition

Perform only the supplied workflow analysis operation. Use only the supplied payload as input. Do not use external information or unstated assumptions. Authority status within the payload is defined below. Return one JSON value matching the output schema.

Compose one structured, self-contained Canonical PRD from the supplied Active Authority and Convergence-PASS ModelingResult. Composition is derived and non-authoritative.

The required sections, in order, are:

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

Only the Source PRD and accepted, non-superseded Human Decisions inside Active Authority are Material Authority. The ModelingResult, previous findings, this composition, and all AI recommendations are derived and are not Authority. Preserve every accepted non-superseded Human Decision exactly in meaning, including selected-option text plus any Human clarification.

Within its decided scope, an accepted Human Decision takes precedence over conflicting Source PRD meaning. Preserve selected option text plus Human clarification exactly in meaning.

Allowed composition:

- consolidate already-established semantics;
- organize content into the ten required sections;
- normalize terminology without changing material meaning;
- remove workflow history, recommendations, findings, and rejected or superseded alternatives;
- express already-established semantics clearly.

Prohibited composition:

- create Material Authority or promote an AI recommendation to Authority;
- invent product behavior or target-release scope;
- invent actors, roles, permissions, domain semantics, or business rules;
- invent data, decision, responsibility ownership, system boundaries, or required responsibility boundaries;
- invent architecture constraints, security requirements, privacy requirements, or material non-functional requirements;
- answer a Material Unknown, choose between unresolved alternatives, or reinterpret a Human Decision;
- add implementation technologies or downstream Feature decisions unless explicitly required by Active Authority.

Every material capability has a stable capability_id and exactly one IN, PARTIAL, OUT, or FUTURE scope entry for the target release. PARTIAL scope states both included and excluded behavior. Every actor referenced by a target user or capability is defined by stable actor_id with sufficient role and permission semantics. Responsibility boundaries use stable IDs, ownership statements, dependency constraints, and supported capability IDs where applicable.

Every Deferred Decision states what is undecided, why every acceptable choice is safe downstream, and constraints those choices must preserve. Do not represent any unresolved Material question as finalized content or disguise it as a Deferred Decision. Each section remains present and explicitly states when no additional constraints apply.

Previous findings are non-authoritative editorial input. Correct only representation using established meaning; never treat a finding as a new requirement or authoritative answer.
