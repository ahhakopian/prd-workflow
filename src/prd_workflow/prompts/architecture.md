# High-Level Architecture Derivation

Perform only the supplied workflow analysis operation. Use only the supplied payload as input. Do not use external information or unstated assumptions. Authority status within the payload is defined below. Return one JSON value matching the output schema.

Derive only:

- major responsibility areas and their responsibilities or material non-responsibilities;
- inside/outside system boundaries and external responsibilities;
- data, decision, and responsibility ownership when established;
- major interactions and material dependency directions;
- required responsibility boundaries;
- high-level architectural constraints and invariants;
- material cross-cutting and non-functional requirements.

Only the supplied Source PRD and accepted, non-superseded Human Decisions are Material Authority. Within their decided scope, supplied Human Decisions outrank conflicting Source PRD meaning. Domain, Capabilities, previous findings, architecture, and deferral classifications are derived artifacts, not Authority. AI recommendations are not Authority.

Support the supplied Capabilities while preserving Domain meaning and all authoritative role, scope, ownership, security, boundary, and material quality constraints. Distinguish displaying, using, or transmitting policy or data from owning that policy, data, decision, or responsibility.

Do not silently resolve ownership, responsibility, system-boundary, permission, security, dependency-direction, or architecture ambiguity. Do not select frameworks, databases, cloud services, deployment technologies, API styles, or implementation structures unless explicitly required by Authority. Do not add implementation detail for completeness, resolve a material unknown, or establish new Material Authority.

If any Deferred Decision drafts are returned alongside the ArchitectureView, the workflow classifies every such draft as DEFERRED. A question is safe to defer only when every reasonable allowed downstream choice preserves product behavior, release scope, actors and permissions, domain semantics, responsibility and feature boundaries, data/decision/responsibility ownership, system boundaries, major dependency direction, high-level architecture invariants, security and privacy, externally visible failure behavior, and material non-functional meaning. It must be independently decidable downstream without invalidating Authority. If any condition is false or unknown, it is a Material Unknown and must not be returned as a Deferred Decision draft. Every Deferred Decision draft must state its question, why it is safe, and constraints downstream must preserve.

If an architectural question is not safe to defer, do not resolve it, do not encode it as a Deferred Decision draft, and do not invent architecture around it. Derive only what current Authority supports. The subsequent Convergence Review is responsible for surfacing the Material Unknown.
