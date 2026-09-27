# Product Requirements Document — Personalizer UI MVP

**Document type:** Source PRD for PRD State Machine  
**Product:** Personalizer UI  
**Release:** MVP  
**Target platform:** Google Chrome Desktop, Manifest V3  
**Primary application class:** Supported top-level single-page web applications (SPA)  
**Status:** Revised source PRD for canonicalization

---

## 1. Product Definition

Personalizer MVP is a personal UI projection over an existing live SPA. The user changes the presentation and layout of supported source UI elements and semantic regions while the source application remains the functional application and continues to own its business logic, data, authentication, permissions, application state, and framework lifecycle.

The Personalizer stores user intent as declarative Desired UI State and reconciles that intent against the current source UI. A deterministic extension runtime performs validated transformations. Bounded Pi reasoning is used only where deterministic processing is insufficient: ambiguous natural-language intent, binding repair, and bounded analysis of layout conflicts caused by source-application changes.

The MVP architecture must also be shaped so that later mixed ownership of the effective UI can be added without replacing the core model. The MVP itself does not add third-party business capabilities or external application buttons, but its domain model must not assume that all future effective UI nodes and functionality are owned by the source application.

### Problem

Users of third-party SPAs must generally accept a common UI or rely on technical CSS, scripts, extensions, or custom code for fragile changes. These approaches usually encode low-level implementation details and tend to break when the source application changes.

The product must let a nontechnical user express and persist a desired personal presentation while preserving supported source behavior and recovering conservatively when the source UI evolves.

### Target actor

- `A-01` — End User

### Intended outcome

A user can:

- activate Personalization Mode on a supported SPA;
- select existing semantic elements and semantic regions directly on the live page;
- perform supported direct manipulations or provide bounded natural-language intent;
- preview a proposed change;
- save the personalization with explicit notice that saving enables automatic application on future visits to that site;
- return later and receive the saved personalization automatically;
- continue using supported original source actions;
- survive supported SPA navigation, rerenders, and source-UI changes through deterministic reconciliation, bounded repair, or explicit user re-selection/confirmation where required.

### Goals

- `G-01` Let nontechnical users select and change supported live UI elements and semantic regions through direct gestures or local text intent.
- `G-02` Persist scoped declarative Desired UI State and automatically reapply every enabled saved personalization on later visits to its site without normal-path AI.
- `G-03` Make the meaning of Save explicit: a successful Save persists the personalization and enables automatic future reapplication for that site.
- `G-04` Preserve original interactive behavior for supported transformations and recover changed target bindings conservatively.
- `G-05` Reconcile saved user intent with source-application UI changes, including changes to previously unpersonalized elements that alter the effective layout or conflict with personalized regions.
- `G-06` Support safe layout management of large semantic containers as indivisible units in MVP.
- `G-07` Keep AI outside deterministic execution and steady-state reapplication.
- `G-08` Minimize permissions and page context shared for bounded reasoning while retaining safe failure and recovery.
- `G-09` Make the MVP domain model extensible to future mixed UI ownership without requiring a replacement of the Desired UI model, runtime, persistence, or reconciliation architecture.

### Explicit non-goals

- `NG-01` No full functional application clone.
- `NG-02` No arbitrary model-generated executable JavaScript, React code, or userscript.
- `NG-03` No general website coding agent.
- `NG-04` No source-application backend modification.
- `NG-05` No automatic source API reverse engineering.
- `NG-06` No new source-application business capabilities in MVP.
- `NG-07` No third-party capability integrations, OAuth/provider adapters, or external application actions in MVP.
- `NG-08` No user-facing creation of Personalizer-owned third-party buttons/widgets as an MVP capability.
- `NG-09` No universal Semantic UI AST in MVP.
- `NG-10` No UI or feature marketplace.
- `NG-11` No cross-application UX profile.
- `NG-12` No mobile browser support.
- `NG-13` No native application support.
- `NG-14` No guaranteed cross-origin iframe editing.
- `NG-15` No guaranteed closed Shadow DOM personalization.
- `NG-16` No arbitrary cross-container movement of internal elements or arbitrary source subtrees.
- `NG-17` No arbitrary rebuilding of the source application's layout.
- `NG-18` No PRD-level mandate for a specific visual-transformation mechanism such as CSS Grid, Flexbox order, absolute positioning, DOM reparenting, portals, or another implementation technique.

---

## 2. Core Product Principles

### `P-01` — Live application, not cloned application

The Personalizer operates over the original live SPA. It does not create a separate functional copy of the application or recreate the source framework runtime.

### `P-02` — Desired state, not patch history

The authoritative personalization artifact is declarative Desired UI State, not an accumulated sequence of imperative DOM patches.

Conceptually:

```text
Library.visible = false
Sidebar.width = 220
Sidebar.dock = left
PropertiesPanel.dock = bottom
```

rather than:

```text
remove(...)
move(...)
patch(...)
patch(...)
```

### `P-03` — Desired state describes the Effective UI

Desired UI State must be modeled as the user's desired state of the **Effective UI relative to the Source Semantic UI**, rather than as a data structure that is intrinsically limited to changing CSS properties of an existing DOM node.

For MVP, supported operations primarily modify existing source-owned elements and source-owned semantic regions. The model must nevertheless leave extension points for future Personalizer-owned nodes, insertion points, and capability bindings.

### `P-04` — Deterministic execution

Only the trusted extension runtime executes page transformations. Valid model output is data. It is validated before any deterministic runtime action.

### `P-05` — AI-free deterministic path

Unambiguous direct manipulations and normal successful reapplication do not require an LLM call.

### `P-06` — Preserve user intent across source changes

A source-application change may change how the current Desired UI State must be realized, but it does not automatically change what the user wants.

The system may automatically change RuntimeBinding or another derived runtime realization when the same Desired UI State can still be satisfied safely. If preserving the user's intent requires changing Desired UI State itself, the system must not silently do so.

### `P-07` — Source changes do not create new user preferences

A newly added, removed, or changed source-owned element does not by itself authorize the Personalizer to invent a new personalization rule for that element.

### `P-08` — Semantic regions are first-class MVP targets

Large semantic containers/regions such as Sidebar, MainContent, Toolbar, PropertiesPanel, or equivalent application-specific regions may be manipulated as indivisible semantic units when the runtime recognizes them as supported regions.

The MVP does not require arbitrary extraction or relocation of their internal source-owned subtrees.

### `P-09` — Transformation contract before transformation mechanism

The PRD defines supported user-visible transformations, behavioral preservation constraints, validation requirements, and failure behavior.

The concrete technical mechanism used to realize a supported transformation is a downstream architecture decision and may differ by transformation class.

### `P-10` — Mixed-ownership readiness without MVP integrations

The domain model must be able to evolve from:

```text
Source UI + modify existing source nodes
```

to:

```text
Source UI
+ Personalizer-owned UI nodes
+ capability bindings
= Effective UI
```

without replacing the core Desired UI, reconciliation, persistence, or runtime contracts.

Actual third-party capability integration remains outside MVP.

---

## 3. Scope & Release Boundary

Target is Chrome Desktop Manifest V3 over supported top-level SPAs and normal DOM.

All explicitly included capabilities below are MVP requirements. Unsupported operations are rejected or narrowed; they are never implemented by falling back to arbitrary model-generated code.

### Capability `CAP-01` — Activation, access, save semantics — IN

**Included:**

- Activate Personalization Mode from extension UI.
- Provide a user-facing control surface, preferably Chrome Side Panel.
- Request only the access needed for editing the current page.
- When the user saves a personalization, explicitly warn that the saved personalization will automatically apply on subsequent visits to that site.
- If persistent site permission required for future automatic application is not already available, request it as part of the Save flow.
- A Save is successful only when the state can be persisted and the required site permission for automatic reapplication is available.
- Allow the user later to disable site personalization without necessarily deleting the saved profile.

**Excluded:**

- A successful saved-but-not-auto-applied state created by ordinary Save.
- Silent persistent permission expansion to unrelated origins.

### Capability `CAP-02` — Live element and region inspection — IN

**Included:**

- Highlight hovered candidates and selected targets.
- Suppress the source action on selection when needed for safe editing.
- Capture multi-signal `ElementRef`.
- Identify supported large semantic regions and region relationships where available.
- Capture necessary local semantic, structural, geometric, and layout context.
- Show only transformations allowed for the selected target/region.

**Excluded:**

- Treating a raw selector as target identity.
- Assuming every DOM subtree is a movable semantic region.

### Capability `CAP-03` — Direct supported element changes — IN

**Included:**

- Hide/restore.
- Safe resize.
- Spacing.
- Density.
- Limited typography.
- Limited appearance.
- Supported ordering inside an existing supported container.
- Alignment.
- Supported collapse/expand behavior.
- Supported sticky/fixed intent where the downstream runtime can preserve required behavior.
- Compile direct unambiguous gestures directly to declarative Desired UI Rules without LLM reasoning.

**Supported property classes include:**

- width;
- safe height;
- min/max width;
- margin;
- padding;
- gap;
- compact/default/expanded density where representable;
- font size;
- font weight;
- line height;
- foreground color;
- background;
- border;
- radius;
- opacity;
- same-container ordering and supported alignment.

**Excluded:**

- Arbitrary source-subtree relocation.
- Arbitrary cross-container movement of internal elements.
- Arbitrary page reconstruction.

### Capability `CAP-04` — Semantic container layout — IN

The MVP supports controlled layout changes to recognized large semantic regions as indivisible units.

**Included:**

- `Hide(region)`
- `Show(region)`
- `Resize(region)`
- `ReorderSiblingRegions(...)`
- `Dock(region, left|right|top|bottom)` where the target layout supports a safe realization
- `ChangeSplitRatio(...)` for supported region relationships

A semantic region may carry conceptual properties such as:

```text
semanticType
layoutRole
parentRegion
movableAsUnit
resizable
```

**Material constraint:**

Moving a recognized region as one semantic unit is different from extracting arbitrary descendants from it. For example, moving a `Sidebar` region as a unit may be supported while moving `Search` from inside that Sidebar to an unrelated Header remains outside guaranteed MVP behavior.

**Excluded:**

- `Move(arbitraryChild, unrelatedContainer)`
- arbitrary DOM subtree detachment;
- arbitrary form restructuring;
- arbitrary layout rebuild.

### Capability `CAP-05` — Local text intent compilation — IN

**Included:**

- Accept text instructions concerning a selected target, semantic region, or bounded local UI area.
- Send only task-necessary structured context and allowed operations to the remote Personalizer/Pi service.
- Obtain schema-constrained Desired UI DSL data for local validation and preview.
- Permit the Personalizer service to use a distinct LLM provider only with task-minimum context.

**Excluded:**

- Full DOM/HTML as normal model input.
- Arbitrary executable model output.
- AI invocation for ordinary deterministic gestures.

### Capability `CAP-06` — Preview, confirmation, and Save — IN

**Included:**

- Preview every proposed new personalization change before persistence.
- Accept or cancel preview.
- Undo the latest unconfirmed change.
- On Save, always show explicit user notice that saving will cause automatic reapplication on later visits to the site.
- Obtain explicit Save confirmation.
- If required persistent site permission is missing, request it during Save.
- Complete Save only after required permission is granted.
- Persist only confirmed state.

**Excluded:**

- Silent Save.
- Silent enablement of future reapplication without the Save warning.
- Persisting an ordinary Save as successfully active while required persistent site permission remains unavailable.

### Capability `CAP-07` — Persistent Desired UI management — IN

**Included:**

- Persist confirmed Desired UI State for origin and relevant route/context scope across tabs and browser restart.
- A successful ordinary Save produces a saved and enabled personalization.
- View, override, disable, re-enable, and remove rules or entire site personalization.
- Delete the entire saved site personalization.
- Restore source presentation as far as the supported runtime allows when a rule is removed or personalization is disabled.

**Business rule:**

`Saved` and `Enabled for automatic reapplication` are coupled at initial successful Save. The user may later explicitly disable an already saved personalization.

### Capability `CAP-08` — Automatic reapplication — IN

**Included:**

- On later visits to a site with enabled saved personalization, automatically find applicable scope, reconcile targets/regions, and apply Desired UI State.
- Reapply after supported SPA navigation and rerender events.
- Preserve supported original controls and source actions.

**Business rules:**

- Successful saved personalization is automatically re-applied on future matching visits unless the user later explicitly disables it.
- Normal successful reapplication does not require AI.
- One failed independent rule does not block other valid independent rules.

### Capability `CAP-09` — Source-UI change detection and continuity — IN

The system must treat source UI evolution as broader than loss of a personalized target.

**Included:**

- Detect relevant route/context changes.
- Detect replacement or material change of bound elements.
- Detect relevant addition, removal, or material change of previously unpersonalized source-owned elements/regions when those changes may affect personalized presentation.
- Trigger selective reconciliation of affected rules/regions.
- Re-evaluate the effective layout after relevant source changes.

**Examples of material impact include:**

- overlap with a personalized region;
- overflow or clipping;
- loss of usable viewport space;
- a new sibling region changing layout constraints;
- changed parent layout relationships;
- changed region ordering;
- source changes that make a previously satisfiable desired layout unsafe or impossible.

**Excluded:**

- Generating new personalization preferences merely because the source application added a new element.

### Capability `CAP-10` — Conservative target resolution — IN

**Included:**

- Use multiple semantic, accessible, attribute, structural, neighbor, geometry, and other relevant signals.
- Return `resolved`, `ambiguous`, or `unresolved` with confidence and evidence.
- Auto-rebind only sufficiently unambiguous targets.
- Provide evidence sufficient to decide between automatic rebind, Pi-assisted binding repair, and human re-selection.

**Excluded:**

- Canonical identity based on one CSS selector.
- Automatic modification of a low-confidence candidate.

### Capability `CAP-11` — Bounded binding repair — IN

Binding Repair answers:

> Which current live source element/region corresponds to a previously intended semantic target?

**Included:**

- When deterministic matching is insufficient, send old `ElementRef`/region reference plus bounded candidates/context to remote Pi.
- Obtain a structured `BindingRepairResult`.
- Auto-update `RuntimeBinding` only when the result is sufficiently unambiguous.
- Ask the user to reselect when ambiguity remains.

**Invariant:**

Binding repair may change derived runtime binding but may not silently change Desired UI State.

### Capability `CAP-12` — Layout reconciliation and layout repair — IN

Layout Reconciliation answers:

> Can the existing Desired UI State still be realized safely against the current Source Semantic UI and current source layout?

**Included:**

- Re-evaluate personalized regions after relevant source UI changes, including changes to previously unpersonalized source elements/regions.
- Verify the resulting Effective UI against supported layout/behavior constraints.
- Automatically choose a different safe runtime realization when the same Desired UI State can still be satisfied without changing user intent.
- Escalate bounded conflicts to Pi when deterministic reconciliation cannot determine a safe realization.
- Obtain structured layout-conflict analysis or repair proposals.
- If the existing Desired UI State cannot be preserved and a preference change is required, show proposed alternatives through Preview and require explicit user confirmation before changing Desired UI State.

**Examples of verification concerns include:**

- relevant region overlap;
- clipping;
- overflow;
- unusable occlusion;
- invalid supported region relationship;
- loss of source interaction required by the supported behavior contract.

**Excluded:**

- Automatically changing user preferences merely to make a new source layout fit.
- Hiding or moving a newly introduced source element by inventing a personalization rule without user intent.

### Capability `CAP-13` — Safe deterministic runtime and recovery — IN

**Included:**

- Validate Desired UI DSL before application.
- Apply supported transformations deterministically.
- Verify supported postconditions.
- Revert/cancel unconfirmed preview.
- Keep source site usable when extension or remote reasoning fails.
- Provide development/test diagnostics.
- Allow disabling personalization and removing problematic rules.

**Transformation-mechanism rule:**

This capability specifies behavior, safety, validation, and recovery. It does not choose the concrete mechanism used for a transformation class. Mechanisms are decided downstream.

---

## 4. Actors & Roles

### `A-01` — End User (HUMAN)

**Purpose:** Create and control personal presentation of a supported source application.

**May do:**

- Activate Personalization Mode.
- Select supported source elements and semantic regions.
- Use supported direct manipulations.
- Provide bounded local text intent.
- Preview, accept, cancel, and undo changes.
- Save personalization.
- Disable, re-enable, override, or delete saved personalization.
- Reselect a target after unresolved binding ambiguity.
- Approve or reject any proposal that would change Desired UI State during preference conflict resolution.

**Must do:**

- Explicitly confirm each Save after seeing the warning that saved personalization will automatically apply on future visits to that site.
- Grant required persistent site permission for Save to complete when that permission is not already available.
- Explicitly confirm any repair proposal that changes user intent/Desired UI State.

### `A-02` — Personalizer Runtime / Chrome Extension (SYSTEM)

**Purpose:** Own the personal UI layer, local Desired UI State, reconciliation, and deterministic execution over the live source SPA.

**May do:**

- Inspect permitted live UI.
- Capture `ElementRef` and semantic-region references.
- Derive current source/effective layout context.
- Persist scoped rules.
- Resolve targets.
- Reconcile Desired UI State against current source UI.
- Apply supported deterministic transformations.
- Change derived RuntimeBinding/runtime realization without user confirmation when this preserves the same Desired UI State and passes safety/verification gates.
- Send bounded reasoning context to the remote Personalizer service.

**Must do:**

- Validate model-produced DSL/results before use.
- Use confidence and safety gates.
- Keep extension/editor controls isolated where practical.
- Request minimal site access.
- Warn on every Save about automatic future reapplication.
- Treat an ordinary successful Save as saved+enabled.
- Reconcile relevant source changes without inventing user preferences.
- Require user confirmation before a repair changes Desired UI State itself.

**Must not do:**

- Clone the functional SPA.
- Invent new business capabilities.
- Execute arbitrary model code.
- Modify uncertain targets.
- Silently alter user intent.
- Treat newly introduced source elements as automatically personalized.
- Own source business data, authentication, permissions, or framework state.

### `A-03` — Pi UI Reasoning Agent / Remote Personalizer Service (SYSTEM)

**Purpose:** Perform bounded semantic reasoning and return structured data.

**May do:**

- Interpret ambiguous local UI intent.
- Compare bounded binding candidates.
- Analyze bounded layout conflicts.
- Return structured Desired UI DSL, BindingRepairResult, or LayoutRepairResult/proposals.
- Forward only minimum task-specific context to an optional separate LLM provider.

**Must do:**

- Preserve context minimization and sensitive-input exclusion.
- Return data subject to extension validation.
- Distinguish a runtime/binding repair that preserves Desired UI State from a proposal that would change user preference.

**Must not do:**

- Execute page code.
- Run shell commands.
- Edit user files.
- Grant browser/site permissions.
- Reverse engineer arbitrary source APIs.
- Bypass extension validation.
- Silently modify persisted Desired UI State.
- Own source business state, live DOM truth, applied rules, or local personalization storage.

### `A-04` — Source Web Application (EXTERNAL)

**Purpose:** Remain the original functional application.

It retains ownership of:

- source data;
- business logic;
- authentication;
- permissions;
- application state;
- source actions;
- source framework lifecycle.

It may independently add, remove, move, rerender, or redesign source-owned UI. The Personalizer must reconcile its own saved presentation against such changes within the supported MVP contract.

### `A-05` — Separate LLM Provider (optional) (EXTERNAL)

**Purpose:** If selected downstream, process a bounded Pi reasoning task.

**May do:**

- Receive only task-minimum context forwarded by the Personalizer service.
- Return a model result to the Personalizer service.

**Must not do:**

- Receive full DOM/HTML, arbitrary page data, credentials, authentication material, unrelated form values, or unrelated context.
- Execute page transformations.
- Own Desired UI State.
- Grant permissions.
- Bypass deterministic validation.

Its use is permitted but not required; self-hosted or more private inference remains valid.

---

## 5. Domain Model

### 5.1 Core concepts

#### Source Application

The live SPA that remains authoritative for its business functionality.

#### Source Semantic UI

The bounded semantic representation of source-owned UI relevant to Personalizer operation.

MVP does not require a universal semantic AST. It must nevertheless represent enough semantic identity and region/layout relationships to support element personalization, region management, target resolution, and reconciliation.

#### Effective UI

The UI presented to the user after the Personalizer reconciles Source Semantic UI with Desired UI State.

For MVP, Effective UI is primarily source-owned UI with supported personalization applied. The concept must be broad enough to later compose Personalizer-owned nodes without changing the core model.

#### Personalization Mode

Explicit user-activated editing context.

#### SiteProfile

Personalization state for an origin/application scope.

#### UIScope

Origin plus applicable route/context constraints.

#### ElementRef

Multi-signal persistent semantic identity/context for an intended element target.

Possible signals include:

- semantic role;
- accessible name;
- visible text;
- stable attributes;
- structural context;
- neighboring context;
- geometry;
- auxiliary technical locator candidates.

A locator is not identity.

#### SemanticRegion

A recognized large layout/container unit that may be managed as an indivisible semantic target.

Conceptual attributes may include:

```text
semanticType
layoutRole
parentRegion
movableAsUnit
resizable
```

Examples may include application-specific equivalents of:

- RootLayout;
- Sidebar;
- MainContent;
- Toolbar;
- PropertiesPanel.

The exact region-discovery and representation mechanism is deferred.

#### RegionRef

Persistent semantic identity/context for a SemanticRegion.

The exact representation may reuse/generalize ElementRef or use a related type; this is a downstream design choice.

#### DesiredUIRule

A scoped declarative statement of desired presentation/layout relative to a semantic target or region.

#### DesiredUIState

The authoritative collection of active user preferences defining desired Effective UI relative to Source Semantic UI.

Desired UI State is not patch history and is not RuntimeBinding.

#### RuntimeBinding

Replaceable mapping from an intended semantic target/region reference to its current live source representation.

#### RuntimeRealization

Derived runtime choice of how a valid Desired UI rule is currently realized against the current source UI.

Changing RuntimeRealization while preserving the same user intent does not itself change Desired UI State.

#### Transformation

A restricted supported visual/layout change.

#### BindingRepairResult

Structured outcome of target repair:

- resolved;
- ambiguous;
- unresolved.

#### LayoutConflict

A detected incompatibility or unsafe interaction between current source layout and saved Desired UI State.

#### LayoutRepairResult

Structured result of bounded layout-repair reasoning.

It must distinguish at least:

- same Desired UI State can be safely realized through another runtime realization;
- user-preference change is required;
- ambiguous/unresolved.

#### Reconciliation

The process of deriving a safe Effective UI from current Source Semantic UI plus current Desired UI State.

#### SaveState

For ordinary successful Save:

```text
persisted = true
enabledForAutomaticReapplication = true
```

A later explicit Disable may produce:

```text
persisted = true
enabledForAutomaticReapplication = false
```

### 5.2 Mixed-ownership extension concepts

The following concepts are part of the architectural domain shape but are **not user-facing MVP integration capabilities**.

#### NodeOwnership

Conceptually distinguishes ownership such as:

- `source-application`;
- `personalizer`.

The exact representation is deferred.

#### ContainerOwnership

Conceptually identifies who owns the host/layout container.

#### FunctionalOwnership

Conceptually allows future functionality ownership such as:

- source application;
- Personalizer;
- external provider.

#### PersonalNode

Future Personalizer-created semantic UI node.

MVP does not require user-facing creation of third-party nodes, but Desired UI/Effective UI must not be modeled in a way that makes PersonalNode impossible without replacing the architecture.

#### InsertionPoint

Future semantic slot/placement contract within a region/container.

Example concept:

```text
Sidebar
  insertionPoints:
    header
    body
    footer
```

MVP need not expose or populate a complete insertion-point system, but region architecture must not preclude it.

#### CapabilityBinding

Future declarative association between a PersonalNode and a functional capability/provider.

The MVP does not implement external provider capabilities.

### 5.3 Material relationships

- SiteProfile contains Desired UI rules scoped to UIScopes.
- DesiredUIRule addresses a semantic element/region or future effective-UI construct.
- Active rules form DesiredUIState.
- DesiredUIState plus Source Semantic UI are reconciled into Effective UI.
- RuntimeBinding maps semantic target identity to the current live source representation.
- RuntimeRealization describes how current Desired UI is realized and may change after source UI evolution without changing user intent.
- SemanticRegions form supported layout relationships, including parent/sibling relations.
- Binding recovery proceeds from deterministic resolution to bounded Pi reasoning to human re-selection.
- Layout recovery proceeds from deterministic reconciliation to bounded Pi conflict analysis; if a preference change is required, explicit user Preview+confirmation is mandatory.
- Mixed-ownership extension points allow future PersonalNodes to be placed in semantic InsertionPoints and bound to capabilities without redefining DesiredUIState as a different architectural concept.

### 5.4 Domain invariants

- `INV-01` DesiredUIState, not patch history, RuntimeBinding, or RuntimeRealization, is authoritative user intent.
- `INV-02` A technical selector alone is never canonical target identity.
- `INV-03` Ambiguous target mapping is never modified automatically.
- `INV-04` Binding repair may change RuntimeBinding but not user intent.
- `INV-05` Layout reconciliation may change runtime realization automatically only when the same Desired UI State remains satisfied.
- `INV-06` Any change to Desired UI State caused by a source-layout conflict requires Preview and explicit user confirmation.
- `INV-07` A source-owned element becoming new, changed, or inconvenient does not create a new personalization preference automatically.
- `INV-08` Only validated supported transformations affect live presentation.
- `INV-09` Deterministic gestures and normal successful reapplication do not require AI.
- `INV-10` The source application owns business and framework runtime; the Personalizer does not clone it.
- `INV-11` Semantic regions may be managed as supported indivisible units; arbitrary descendant reparenting is not implied.
- `INV-12` Successful ordinary Save means persisted and enabled for automatic future reapplication.
- `INV-13` The user is warned about that future automatic application on every Save.
- `INV-14` Concrete transformation mechanisms are architecture decisions, not product requirements.
- `INV-15` Mixed-ownership readiness is required, but external capability integration is not an MVP feature.

---

## 6. Core Workflows

### 6.1 First personalization

```text
Open supported SPA
  -> Activate Personalization Mode
  -> Select element or semantic region
  -> Capture semantic target/context
  -> Determine allowed transformations
  -> Direct gesture OR bounded text intent
  -> Produce restricted Desired UI proposal
  -> Validate
  -> Preview
  -> User chooses Save
  -> Always warn: future visits will auto-apply personalization
  -> User confirms
  -> Ensure persistent site permission
  -> Persist Desired UI State
  -> Mark personalization enabled
```

If the permission needed for future automatic reapplication is denied, ordinary Save does not complete successfully.

### 6.2 Returning visit

```text
Open matching site
  -> Load enabled SiteProfile
  -> Determine matching UIScope
  -> Reconcile Desired UI State with current Source Semantic UI
  -> Resolve current targets/regions
  -> Apply valid deterministic realization
  -> Verify
```

Normal success path has no model call.

### 6.3 Deterministic source update

When the source SPA changes:

```text
Source UI change
  -> Detect affected semantic elements/regions/layout
  -> Reconcile existing Desired UI State
  -> Re-resolve bindings
  -> Recompute safe runtime realization
  -> Verify Effective UI
```

If user intent can still be preserved safely, the runtime may adapt automatically.

### 6.4 Binding repair

```text
Target no longer resolves confidently
  -> deterministic candidate resolution
  -> if sufficient: rebind
  -> else bounded Pi Binding Repair
  -> if sufficient: rebind
  -> else user re-selection
```

Desired UI State is unchanged.

### 6.5 Layout reconciliation

```text
Source UI/layout changed
  -> existing binding may still be valid
  -> evaluate personalized region in new environment
  -> verify overlap/clipping/region constraints/behavior
  -> if same intent can be safely realized:
         change derived runtime realization
     else:
         create LayoutConflict
```

### 6.6 Preference conflict resolution

If the source UI has changed such that current user preference cannot be preserved safely:

```text
LayoutConflict
  -> deterministic alternatives if available
  -> bounded Pi analysis/proposals if needed
  -> Preview proposed preference change(s)
  -> explicit user decision
  -> only then update Desired UI State
```

The Personalizer must not silently choose a new preference.

---

## 7. Functional Requirements

### Save and permission requirements

- `FR-001` Editing starts only after explicit user activation.
- `FR-002` The extension requests minimal page access for editing.
- `FR-003` Every Save shows an explicit warning that the saved personalization will automatically apply during later visits to that site.
- `FR-004` Every Save requires explicit user confirmation after the warning.
- `FR-005` If required persistent site permission is absent, the Save flow requests it.
- `FR-006` Ordinary Save does not complete successfully if required persistent permission is denied.
- `FR-007` Successful ordinary Save persists Desired UI State and enables automatic reapplication.
- `FR-008` The user may later explicitly disable a saved personalization without necessarily deleting it.

### Selection and inspection requirements

- `FR-010` Hover identifies selectable candidates visually.
- `FR-011` Selection clearly identifies the current target.
- `FR-012` Source action may be suppressed during selection when necessary.
- `FR-013` Selection produces a multi-signal semantic reference.
- `FR-014` Supported semantic regions are distinguishable from arbitrary DOM subtrees.
- `FR-015` Allowed transformations are derived from the target/region context.

### Direct transformation requirements

- `FR-020` Supported unambiguous gestures compile without LLM.
- `FR-021` MVP supports the element-level transformation classes defined in `CAP-03`.
- `FR-022` MVP supports semantic-region operations defined in `CAP-04`.
- `FR-023` Unsupported transformations are rejected or narrowed.
- `FR-024` Unsupported requests never fall back to arbitrary model-generated page code.
- `FR-025` The runtime must preserve required source behavior for a supported transformation.
- `FR-026` The PRD does not prescribe one implementation mechanism for all transformation classes.

### Text-intent requirements

- `FR-030` The user may provide text intent for a selected target, region, or bounded local UI area.
- `FR-031` Only task-necessary structured context and allowed operations are sent remotely.
- `FR-032` Model results must conform to schema.
- `FR-033` Invalid model results are not applied.
- `FR-034` Pi/model results do not directly execute page transformations.

### Persistence and reapplication requirements

- `FR-040` Confirmed rules persist across tabs and browser restarts.
- `FR-041` Rules are scoped to origin and applicable route/context.
- `FR-042` Enabled saved personalization automatically reapplies on matching future visits.
- `FR-043` Normal valid reapplication requires no LLM.
- `FR-044` A coincidental locator match on an unrelated screen is insufficient for rule application.

### Semantic region requirements

- `FR-050` The system may recognize large semantic containers as first-class targets.
- `FR-051` A supported semantic region may be resized as a unit.
- `FR-052` A supported semantic region may be hidden/restored as a unit.
- `FR-053` Supported sibling regions may be reordered.
- `FR-054` Supported regions may be docked to supported layout positions.
- `FR-055` Supported split relationships may expose split-ratio personalization.
- `FR-056` Region manipulation does not imply arbitrary movement of internal descendants.

### Target resolution requirements

- `FR-060` Resolver uses multiple relevant signals.
- `FR-061` Resolver distinguishes resolved, ambiguous, and unresolved.
- `FR-062` Automatic bind/rebind occurs only when sufficiently unambiguous.
- `FR-063` Insufficient confidence prevents speculative modification.

### Binding repair requirements

- `FR-070` Binding repair starts only when deterministic resolution is insufficient.
- `FR-071` Pi receives bounded old-reference/candidate context.
- `FR-072` Repair result is structured.
- `FR-073` Successful binding repair may update RuntimeBinding.
- `FR-074` Binding repair does not modify Desired UI State.
- `FR-075` Remaining ambiguity triggers human re-selection.

### Source-change and layout reconciliation requirements

- `FR-080` Runtime detects relevant changes to source-owned personalized and unpersonalized UI.
- `FR-081` Source changes that may affect personalized layout trigger selective reconciliation.
- `FR-082` Reconciliation verifies supported layout/behavior postconditions.
- `FR-083` Runtime may automatically change derived realization if the same Desired UI State remains safely satisfied.
- `FR-084` Runtime must not invent personalization for a newly introduced source-owned element.
- `FR-085` If preserving current Desired UI State is impossible or unsafe, the conflict becomes explicit.
- `FR-086` Pi may analyze a bounded layout conflict and propose structured alternatives.
- `FR-087` Any proposal that changes Desired UI State must be previewed and explicitly confirmed by the user before persistence.
- `FR-088` Failure to resolve a layout conflict must leave the source site usable.

### Mixed-ownership readiness requirements

- `FR-090` Desired UI/Effective UI domain contracts must not assume that every future effective UI node is source-owned.
- `FR-091` The architecture must allow future ownership metadata for UI nodes, containers, and functionality.
- `FR-092` The architecture must leave a compatible extension path for PersonalNode, InsertionPoint, and CapabilityBinding.
- `FR-093` MVP does not require creating external-service nodes or executing external-provider business capabilities.
- `FR-094` Adding future `create personal node + bind capability` should be an extension of the DSL/runtime model rather than a replacement of Desired UI architecture.

---

## 8. System Boundaries & Ownership

### Inside the MVP system

- Chrome Manifest V3 extension shell.
- Isolated editor/inspector UI.
- Live content runtime.
- Local SiteProfile and Desired UI State persistence.
- Source Semantic UI extraction sufficient for MVP targets/regions.
- Element/region target resolver.
- Semantic-region layout handling.
- Reconciliation and RuntimeBinding/RuntimeRealization management.
- Deterministic transformation runtime.
- SPA/source-change lifecycle observation.
- Remote Personalizer/Pi service for bounded intent, binding repair, and layout-conflict reasoning.
- Optional separate LLM-provider boundary limited to task-minimum context.

### Outside the MVP system

- Source backend.
- Source business data and state.
- Source authentication and permissions.
- Source business logic.
- Source framework lifecycle ownership.
- Full functional clone.
- Universal semantic application model.
- Native/mobile applications.
- Cloud account/sync requirement.
- UI/feature marketplace.
- External capability integrations.
- OAuth/provider-adapter system for third-party actions.
- User-facing creation of third-party application buttons/widgets.

### Data ownership

- Source application owns its business data, state, authentication, and permissions.
- Personalizer owns local personalization artifacts: SiteProfile, Desired UI State, semantic references, derived bindings/realizations, and relevant reconciliation metadata.
- Remote Pi service and optional LLM provider may process only bounded task-specific context and do not become authoritative owners of source data or user preferences.

### Decision ownership

- User owns persisted personalization intent.
- Runtime owns deterministic validation, confidence gates, supported-operation enforcement, reconciliation, and safe derived realization.
- Pi/model may return structured proposals/evidence but does not have authority to silently change Desired UI State.
- Source application owns source business and authentication/permission decisions.

### Future mixed ownership

The model must distinguish conceptually between:

```text
UI/container ownership
functional ownership
```

A future mixed-ownership scenario may look like:

```text
Host container ownership: source application
UI node ownership: Personalizer
Context ownership: source application
Functional capability ownership: external provider
```

This is an architectural extension target, not an MVP feature.

---

## 9. High-Level Architecture

### Primary path

```text
User direct manipulation
        or
bounded natural-language intent
        |
        v
Semantic target/region + Desired UI proposal
        |
        v
Schema / policy validation
        |
        v
Reconciliation + target resolution
        |
        v
Deterministic runtime realization
        |
        v
Effective UI over original live SPA
```

### Steady-state path

```text
Saved enabled Desired UI State
        |
        v
Current Source Semantic UI
        |
        v
Reconcile
        |
        v
Resolve bindings/regions
        |
        v
Apply deterministic realization
        |
        v
Verify
```

No AI is required on the normal successful path.

### Repair path

```text
Current source UI changed
        |
        v
Selective reconciliation
        |
        +--> target identity problem
        |       |
        |       v
        |   Binding Repair
        |
        +--> layout/environment problem
                |
                v
          Layout Reconciliation
                |
        +-------+--------+
        |                |
same intent         preference change
still satisfiable   required
        |                |
automatic derived     Preview
realization change      |
                        v
                      User
```

### Responsibility areas

#### Chrome Extension Shell

- explicit activation;
- site-limited permissions;
- Save permission flow;
- Side Panel coordination;
- local persistence coordination;
- navigation/source-change lifecycle coordination;
- bounded reasoning requests.

#### Editor / Inspector

- hover/selection;
- semantic target and region selection;
- direct manipulation;
- text instruction input;
- preview;
- Save warning/confirmation;
- undo;
- rule management;
- target re-selection;
- preference-repair confirmation.

#### Source Semantic UI / Reconciliation

- relevant semantic target representation;
- semantic regions and relationships;
- current source/effective layout context;
- reconciliation of Desired UI State against current source UI;
- layout conflict detection.

#### Deterministic Runtime

- DSL/schema validation;
- supported transformation application;
- derived RuntimeBinding and RuntimeRealization;
- verification;
- safe recovery/revert.

#### Remote Personalizer/Pi

- bounded intent compilation;
- bounded binding repair;
- bounded layout-conflict analysis/proposals.

#### Optional LLM Provider

- model inference only on forwarded task-minimum context.

### Architectural invariants

- `D-01` Operate on the original live SPA, never a functional clone.
- `D-02` Persist declarative Desired UI State, not patch history.
- `D-03` Desired UI State describes desired Effective UI relative to Source Semantic UI.
- `D-04` Deterministic runtime executes validated transformations.
- `D-05` Model output is restricted data, never arbitrary executable page code.
- `D-06` Pi is a bounded UI intent/repair agent, not an unrestricted coding agent.
- `D-07` AI is not required for deterministic gestures or successful steady-state reapplication.
- `D-08` Element/region semantic identity and RuntimeBinding remain distinct.
- `D-09` Multi-signal target identity; a CSS selector alone is not canonical.
- `D-10` Ambiguous targets are not modified automatically.
- `D-11` Successful ordinary Save means persisted+enabled automatic future reapplication and requires explicit warning/confirmation.
- `D-12` Source changes may trigger automatic binding/runtime-realization repair, but not silent changes to Desired UI State.
- `D-13` Newly introduced source elements do not automatically receive personalization rules.
- `D-14` Large supported semantic containers are first-class MVP targets and may be managed as indivisible units.
- `D-15` Arbitrary movement of internal elements between unrelated containers remains outside MVP.
- `D-16` Mixed-ownership compatibility is an architectural requirement; external capability integration is not an MVP capability.
- `D-17` The PRD fixes transformation behavior and safety contracts, not concrete transformation mechanisms.

---

## 10. Privacy, Security, Permissions & Failure

### Remote context

Bounded page context may be sent to a remote Personalizer service for Pi reasoning.

The Personalizer service may, but need not, forward only minimum task-specific context to a distinct LLM provider.

Neither permitted remote boundary authorizes:

- full DOM/HTML;
- arbitrary page content;
- credentials;
- passwords;
- tokens;
- cookies;
- authentication material;
- hidden secrets;
- unrelated form values;
- unrelated page context.

### Model authority

Model/provider output:

- is schema-constrained;
- is locally validated;
- does not execute page transformations directly;
- cannot grant permissions;
- cannot silently modify Desired UI State.

### Permission rules

- Editing requires explicit user activation.
- Permissions are site-limited.
- Save always warns about future automatic reapplication.
- If the persistent site permission needed to honor Save semantics is absent, it is requested in the Save flow.
- Save is not successfully completed if required permission is denied.
- Permissions do not silently expand to unrelated origins.

### Graceful failure

Remote service/provider failure must not block:

- source site loading;
- original site behavior;
- deterministic direct gestures;
- valid saved deterministic rules that can still be resolved/reconciled locally.

An unresolved or unsafe rule may fail independently without blocking unrelated valid rules.

---

## 11. Non-Functional Requirements

- `NFR-01` Direct deterministic manipulations should feel interactive and must not depend on AI latency. Numeric SLA is deferred until prototype measurement.
- `NFR-02` Reopening a personalized site with successfully reconciled targets/regions requires no model call.
- `NFR-03` One failed independent rule does not block independent valid rules.
- `NFR-04` Uncertain targets remain unresolved rather than being guessed.
- `NFR-05` User can disable personalization, remove a rule, or delete the site profile.
- `NFR-06` Development/test diagnostics identify relevant rule, semantic target/region, binding/resolution path, reconciliation path, repair trigger, validation outcome, and verification outcome.
- `NFR-07` Production telemetry or external diagnostic sending requires a separate product/privacy decision.
- `NFR-08` Source UI changes should trigger selective rather than unnecessary global AI processing where practical.
- `NFR-09` Mixed-ownership extension readiness must not impose third-party integration runtime cost on normal MVP operation.

---

## 12. Quality Gates & MVP Validation

### Quality gates

- `QG-01` Every supported MVP transformation has a deterministic execution contract and automated regression coverage.
- `QG-02` Main first-personalization journey has browser E2E coverage.
- `QG-03` Save warning, permission grant, permission denial, successful save+auto-reapply, later Disable, and re-enable behavior are tested.
- `QG-04` Supported SPA navigation and rerender scenarios have browser verification.
- `QG-05` Source changes to previously unpersonalized elements are tested where they materially affect a personalized region.
- `QG-06` Binding repair path is tested for auto-rebind, Pi-assisted repair, and human re-selection.
- `QG-07` Layout reconciliation is tested for:
  - automatic same-intent runtime adaptation;
  - irreconcilable layout conflict;
  - user-confirmed preference change;
  - refusal to invent a new preference for a new source element.
- `QG-08` Invalid model output cannot bypass schema validation.
- `QG-09` AI unavailable path leaves source site and valid deterministic functionality usable.
- `QG-10` Original supported source action remains functional after supported personalization.
- `QG-11` Semantic container operations are verified on the selected reference SPA.
- `QG-12` Architecture review confirms that future PersonalNode/InsertionPoint/CapabilityBinding can extend the model without replacing the core Desired UI architecture.

### Validation objectives

- `VO-01` A nontechnical user can create supported personalization without CSS/JavaScript.
- `VO-02` Supported original source actions remain functional.
- `VO-03` Saved personalization automatically reappears after return to the site.
- `VO-04` The user understands from every Save warning that future visits will automatically apply the personalization.
- `VO-05` Personalization survives supported SPA navigation/rerender.
- `VO-06` Personalization can survive relevant source UI evolution through reconciliation and bounded repair.
- `VO-07` Large semantic regions can be personalized as coherent layout units.
- `VO-08` Most normal runtime interactions after creation of personalization require no model call.
- `VO-09` The architectural model can later support mixed ownership without a foundational migration.

---

## 13. Required Responsibility Boundaries

### `RB-01` — Extension Shell and Permissions

**Owns:**

- activation;
- site access;
- Save warning/permission flow;
- Side Panel coordination;
- extension lifecycle;
- local persistence coordination;
- navigation/source-change coordination;
- AI gateway coordination.

**Does not own:**

- source authentication;
- source business permissions;
- source business logic.

### `RB-02` — Editor and Live Inspection

**Owns:**

- selection/highlight;
- local instruction input;
- semantic element/region selection;
- preview controls;
- Save confirmation UX;
- user re-selection and preference-conflict confirmation.

**Does not own:**

- source business actions;
- deterministic execution semantics;
- provider inference.

### `RB-03` — Desired State and Persistence

**Owns:**

- restricted Desired UI DSL;
- SiteProfile;
- scoped Desired UI State;
- enabled/disabled saved status;
- rule management.

**Must not depend on:**

- remote Pi service;
- optional LLM provider for ordinary read/write of persisted preferences.

### `RB-04` — Semantic UI & Region Model

**Owns:**

- bounded source semantic representation needed by MVP;
- semantic target/region identity;
- region relationships needed for container management;
- mixed-ownership extension contracts at the domain boundary.

**Does not own:**

- universal application semantic AST;
- external capabilities.

### `RB-05` — Target Resolution & Binding Repair Orchestration

**Owns:**

- multi-signal matching;
- confidence decisions;
- RuntimeBinding lifecycle;
- binding-repair escalation.

**Does not own:**

- user preference.

### `RB-06` — Reconciliation & Layout Conflict Management

**Owns:**

- reconciliation of Desired UI State against current Source Semantic UI;
- RuntimeRealization lifecycle;
- relevant layout postcondition checks;
- LayoutConflict detection;
- layout-repair escalation;
- distinction between automatic same-intent repair and preference-changing proposals.

**Does not own:**

- authority to silently rewrite user Desired UI State.

### `RB-07` — Deterministic Transformation Runtime

**Owns:**

- DSL validation;
- supported preview/application/revert;
- runtime realization;
- visual/behavior verification.

**Does not own:**

- Pi semantic interpretation;
- source framework/business state.

### `RB-08` — SPA / Source-Change Lifecycle Coordination

**Owns:**

- detection of relevant route/rerender/source-UI changes;
- selective re-evaluation triggers.

**Does not own:**

- source framework lifecycle itself;
- user preference.

### `RB-09` — Remote Personalizer and Pi Reasoning

**Owns:**

- bounded intent compilation;
- bounded binding repair reasoning;
- bounded layout-conflict analysis and structured proposals.

**Does not own:**

- deterministic page execution;
- extension permissions;
- saved rules;
- source business state;
- authority to silently change Desired UI State.

### `RB-10` — Optional Separate LLM Processing

**Owns:**

- optional inference on task-minimum forwarded context.

**Does not own:**

- source state;
- page execution;
- permissions;
- rule persistence;
- binding authority;
- user preference authority.

---

## 14. Deferred Decisions & Handoff Constraints

### `DD-01` — Desired UI DSL serialization

Which exact serialization is used: JSON, YAML, TypeScript-native representation, or another schema-compatible format?

**Constraint:** declarative, restricted, versioned, inspectable, model-independent, schema-validatable, never executable page code.

### `DD-02` — Schema-validation implementation

Which validation library/representation is used?

**Constraint:** invalid DSL/results must be rejected before application.

### `DD-03` — Weak LLM/provider selection

Which exact model/provider is used?

**Constraint:** both self-hosted and permitted external-provider routes remain valid under the fixed bounded-context/privacy contract.

### `DD-04` — Visual transformation mechanisms

Which concrete mechanism is used for each supported transformation class?

Candidate mechanism families may include, but are not selected by this PRD:

- existing layout properties;
- CSS Grid/Flex mechanisms;
- visual repositioning;
- controlled DOM movement/reparenting;
- portals/projection;
- another architecture-approved technique.

**Constraints downstream must preserve:**

- source behavior preservation required by the supported capability;
- deterministic execution;
- validation;
- recoverability;
- no arbitrary model-generated code;
- semantic-region indivisibility where required;
- unsupported transformations remain rejectable.

No single mechanism is mandated globally.

### `DD-05` — Cloud account/sync

Cloud account or sync is not required for local MVP.

### `DD-06` — Target confidence algorithm

Exact scoring/matching implementation is deferred.

**Constraint:** resolved/ambiguous/unresolved remain distinct and auto-bind requires sufficient confidence.

### `DD-07` — Semantic region discovery/model

How are supported semantic regions detected and represented?

**Constraints:**

- regions must be distinguishable from arbitrary DOM subtrees;
- region identity must support reconciliation;
- container operations must remain restricted to supported semantic units.

### `DD-08` — Layout postcondition/constraint model

What exact constraint representation determines overlap, clipping, supported docking, valid split relationships, and other layout-safety conditions?

**Constraint:** architecture must support deterministic verification and explicit unresolved/conflict states.

### `DD-09` — Full semantic application model

Universal Semantic UI AST is post-MVP.

**Constraint:** MVP representation must leave an evolutionary path.

### `DD-10` — Mixed-ownership extension representation

What exact schema represents:

- NodeOwnership;
- ContainerOwnership;
- FunctionalOwnership;
- PersonalNode;
- InsertionPoint;
- CapabilityBinding?

**Constraint:** this must extend, not replace, the core Desired UI / Effective UI / reconciliation model.

### `DD-11` — External feature integrations

Actual external provider integrations, OAuth/adapters, and business capabilities are post-MVP.

### `DD-12` — UI marketplace

Post-MVP.

### `DD-13` — Cross-application UX profile

Post-MVP.

### `DD-14` — Reference SPA

Which real supported SPA is used for MVP quality-gate verification?

**Constraint:** reference choice must not broaden product scope.

### `DD-15` — Exact typed Pi tool API

What exact typed tools are exposed to Pi?

**Constraints:**

- UI-specific and bounded;
- no shell;
- no arbitrary page code;
- no user-file edits;
- no permission grants;
- no validation bypass;
- separate structured result types for intent, binding repair, and layout-conflict reasoning where appropriate.

---

## 15. Fixed Upstream Decisions That Must Not Be Reopened Without Blocking Evidence

- Operate on the original live SPA, never a functional clone.
- Persist declarative Desired UI State rather than patch history.
- Desired UI State describes desired Effective UI relative to Source Semantic UI.
- Deterministic runtime executes validated transformations.
- Model output is restricted data, never arbitrary executable page code.
- Pi is a bounded UI intent/repair agent, not an unrestricted coding agent.
- AI is not required for deterministic gestures or successful steady-state reapplication.
- Semantic target identity and RuntimeBinding are distinct.
- A lone CSS selector is not canonical target identity.
- Ambiguous targets are not modified automatically.
- Every successful ordinary Save means persisted+enabled automatic future reapplication.
- Every Save explicitly warns the user about that future automatic reapplication.
- Missing required persistent site permission is resolved in the Save flow; denial prevents successful ordinary Save.
- Source changes may automatically change derived binding/runtime realization only when user intent remains unchanged.
- Any repair that changes Desired UI State requires Preview and explicit user confirmation.
- Newly added or changed source elements do not automatically receive newly invented personalization rules.
- Large supported semantic containers are first-class MVP targets and may be managed as indivisible units.
- Arbitrary movement of internal elements between unrelated containers remains outside MVP.
- Mixed-ownership readiness is required in the architecture, but external provider capabilities and user-facing third-party UI nodes are not MVP features.
- The PRD specifies transformation contracts, not concrete visual-transformation mechanisms.
- Bounded page context may be sent to a remote Personalizer service for Pi reasoning.
- The remote service may, but need not, forward only minimum task-specific context to a distinct LLM provider.
- Both remote boundaries preserve context minimization, sensitive-input exclusion, schema-constrained output, deterministic validation/execution, and graceful failure.
- Chrome Desktop Manifest V3 and local MVP persistence are fixed.
- WXT/TypeScript, Side Panel, isolated extension UI, local storage, SPA navigation/source-change observation, and Playwright remain implementation baselines/preferences unless downstream architecture establishes a justified alternative consistent with product constraints.

---

## 16. Product Definition of Done

The MVP has validated its main product hypothesis when, on a selected real supported SPA, a user can:

```text
open the source application
  -> activate Personalizer
  -> select an existing element or recognized semantic region
  -> make a supported direct change or bounded text request
  -> preview the result
  -> save it after an explicit automatic-reapplication warning
  -> grant site permission if needed
  -> continue using supported original source functionality
  -> return later and receive the saved personalization automatically
  -> navigate/rerender within supported SPA behavior
  -> survive supported source-UI evolution through:
       deterministic reconciliation,
       binding repair,
       layout repair,
       or safe human confirmation/re-selection
```

The MVP must also demonstrate controlled semantic-container layout management and confirm through architecture review that future mixed ownership can be added as an extension of the existing Effective UI/Desired UI model rather than as a replacement architecture.

The MVP does not require:

- arbitrary UI reconstruction;
- arbitrary cross-container subtree movement;
- external provider actions;
- third-party buttons/widgets;
- OAuth integration;
- marketplace functionality;
- universal semantic application modeling.
