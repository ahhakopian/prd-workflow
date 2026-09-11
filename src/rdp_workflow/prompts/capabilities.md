# Functional Capability Derivation

Perform only the supplied workflow analysis operation. Use only the supplied payload as input. Do not use external information or unstated assumptions. Authority status within the payload is defined below. Return one JSON value matching the output schema.

A Functional Capability is a meaningful user or business ability: what the product must do, not an implementation component, task, or downstream specification Feature.

Every returned Capability requires:

- name;
- purpose;
- release_status = IN | PARTIAL | OUT | FUTURE.

Include actors, behavior, business rules, dependencies, and failures only when supported by Authority.

Only the supplied Source PRD and accepted, non-superseded Human Decisions are Material Authority. Within their decided scope, supplied Human Decisions outrank conflicting Source PRD meaning. The fresh Domain view and previous remodel findings are derived inputs, not Authority. AI recommendations are not Authority.

Derive behavior only when it follows unambiguously from Active Authority and is consistent with the supplied fresh Domain view. Do not invent behavior, rules, actors, permissions, release scope, dependencies, or failure handling to make the model complete. Do not perform downstream Feature decomposition or describe frameworks, databases, APIs, modules, or implementation tasks.

Never guess release scope. If material release scope cannot be determined from Authority, do not resolve it; Convergence must surface the missing material truth.

Do not resolve a material unknown or establish new Material Authority. A question is material when different answers could change behavior, release scope, roles or permissions, business rules, domain meaning, ownership, boundaries, dependency direction, architecture, security or privacy, visible failure behavior, or a material non-functional requirement.
