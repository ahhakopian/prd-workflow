# Personalizer UI — MVP Smoke Test PRD

## Product

Personalizer UI is a Chrome extension for personalizing the interface of third-party single-page web applications.

The extension works over the live source application rather than creating a separate functional copy of it.

## MVP Goal

Allow a user to modify selected parts of an existing SPA without writing CSS or JavaScript, while preserving the original behavior of retained interactive elements.

## Primary User Flow

1. The user opens a supported SPA.
2. The user activates Personalizer UI.
3. The user selects an existing UI element on the page.
4. The user changes it through a supported direct manipulation or a natural-language instruction.
5. The system shows a preview.
6. The user confirms the change.
7. The personalization is saved and reapplied on later visits.

## Functional Requirements

### FR-1 — Element selection

The user must be able to enter a personalization mode and select an existing element from the live page.

### FR-2 — Supported transformations

The MVP must support at least:

- hide/show;
- width adjustment;
- spacing adjustment;
- ordering within a supported layout container.

### FR-3 — Desired state

Confirmed personalization must be stored as declarative desired UI state rather than as arbitrary executable JavaScript or a history of DOM patches.

### FR-4 — Original behavior

Where a personalized element represents an existing source-application action, the implementation should preserve the original interactive element and its behavior whenever the supported transformation allows it.

### FR-5 — Natural-language intent

When a user's intent cannot be derived deterministically from direct manipulation, the system may use an AI model to translate the instruction into a restricted, schema-valid UI transformation.

The AI model must not generate executable page JavaScript.

### FR-6 — Reapplication

Saved personalization must be reapplied on later visits without requiring an AI call when the target elements can be resolved deterministically.

### FR-7 — Target recovery

If a saved target can no longer be resolved after the source application's UI changes, the system should first attempt deterministic re-resolution and may use AI-assisted repair when necessary.

It must not automatically modify an ambiguous target.

### FR-8 — Persistence scope

Each saved rule must belong to the current site and an applicable route/context scope.

**Open product decision:** when a new rule is saved, should it apply only to the current route/context by default, or should the user explicitly choose its scope?

## Privacy

Only the minimum page context required for an AI operation may be sent to an external AI service.

Full-page HTML, credentials, authentication tokens, and unrelated form values must not be sent by default.

## MVP Platform Boundary

The MVP targets:

- Google Chrome Desktop;
- Manifest V3;
- top-level SPAs.

One selected reference SPA is sufficient for the MVP validation guarantee. Other compatible SPAs may work on a best-effort basis.

## Non-Goals

The MVP does not include:

- creating a complete replacement application UI;
- arbitrary JavaScript generation or execution by the AI model;
- backend modification;
- reverse engineering source-application APIs;
- new business functionality absent from the source application;
- mobile browsers;
- native desktop applications;
- a UI-extension marketplace.

## MVP Success Condition

The MVP is successful when, on the reference SPA, a user can:

1. select an existing element;
2. make and preview a supported UI change;
3. save the change;
4. continue using the original application behavior;
5. revisit the application and receive the saved personalization automatically;
6. survive a normal SPA rerender or safely fail to rebind when the target becomes ambiguous.