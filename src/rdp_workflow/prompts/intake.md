# Intake Analysis

Perform only the supplied workflow analysis operation. Use only the supplied payload as input. Do not use external information or unstated assumptions. Authority status within the payload is defined below. Return one JSON value matching the output schema.

Review Active Authority for:

- material ambiguity;
- material contradiction;
- missing material information or constraints.

Material dimensions are:

- product behavior;
- release scope;
- actors and permissions;
- domain semantics;
- feature and responsibility boundaries;
- ownership;
- high-level architecture;
- security;
- material non-functional requirements.

Only the Source PRD and accepted, non-superseded Human Decisions are Material Authority. Accepted Human Decisions take precedence over conflicting Source PRD meaning within their decided scope. AI recommendations are never Authority.

Do not answer a Material Unknown. If a Material Unknown remains, return exactly one earliest consequential Human Decision. Otherwise, return no blocking Decision.

A returned Material Decision draft must ask exactly one concrete non-compound question, provide sufficient context, contain 2-4 plausible materially distinct options with a material consequence for each, and identify exactly one advisory recommended option with a recommendation rationale. It must contain no Human Answer or deferral fields. The workflow interprets the draft as a pending INTAKE-origin MATERIAL Decision and assigns those lifecycle fields deterministically.
