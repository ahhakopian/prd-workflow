# Domain Derivation

Perform only the supplied workflow analysis operation. Use only the supplied payload as input. Do not use external information or unstated assumptions. Authority status within the payload is defined below. Return one JSON value matching the output schema.

Derive only:

- product problem, intended outcome, target users, goals, and explicit non-goals when established;
- downstream-significant domain concepts and relationships;
- canonical business terminology where ambiguity matters;
- domain invariants that follow from the supplied authority.

Only the supplied Source PRD and accepted, non-superseded Human Decisions are Material Authority. Within their decided scope, supplied Human Decisions outrank conflicting Source PRD meaning. Previous remodel findings are corrective feedback, not Authority. AI recommendations and all derived artifacts are not Authority.

Use business language and include only semantics that can affect downstream product or system interpretation. Do not invent technical entities or select implementation technologies. Do not add product behavior, scope, roles, ownership, domain meaning, architecture, security, or material quality requirements that do not follow unambiguously from Authority.

Do not resolve a material unknown. Different reasonable answers are material when they could change product behavior, release scope, actors or permissions, domain meaning, ownership, system or responsibility boundaries, major dependency direction, high-level architecture, security or privacy, externally visible failure behavior, or a material non-functional requirement.

Do not manufacture content merely to make the result look complete.
