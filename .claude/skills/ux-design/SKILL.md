---
name: ux-design
description: "Guided, section-by-section UX spec authoring for a screen, flow, or HUD. Supports both game projects (player journey, HUD, game screens) and product projects (user flows, CLI interaction, API consumer journey). Reads concept doc and relevant CDDs for context-aware design guidance."
argument-hint: "[screen/flow name] or 'hud' or 'patterns'"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Task
agent: ux-designer
---

## User Guide

- When to use: Guided, section-by-section UX spec authoring for a screen, flow, or HUD. Supports both game projects (player journey, HUD, game screens) and product projects (user flows, CLI interaction, API consumer journey). Reads concept doc and relevant CDDs for context-aware design guidance.
- Inputs: Command arguments: `/ux-design [screen/flow name] or 'hud' or 'patterns`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: None.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

When this skill is invoked:

**Domain detection.** Read the concept document to determine domain:
- `design/cdd/game-concept.md` → **[游戏专用]** Game mode
- `design/cdd/product-concept.md` → **[通用产品]** Product mode

## 1. Parse Arguments & Determine Mode

**[游戏专用]** Game modes:

| Argument | Mode | Output file |
|----------|------|-------------|
| `hud` | HUD design | `design/ux/hud.md` |
| `patterns` | Interaction pattern library | `design/ux/interaction-patterns.md` |
| Any other value | UX spec for a screen or flow | `design/ux/[argument].md` |
| No argument | Ask the user | (see below) |

**[通用产品]** Product modes:

| Argument | Mode | Output file |
|----------|------|-------------|
| `patterns` | Interaction pattern library | `design/ux/interaction-patterns.md` |
| `workflow` or flow name | UX spec for a user workflow | `design/ux/[argument].md` |
| `cli` | CLI interaction design | `design/ux/cli-interaction.md` |
| `api` | API consumer journey | `design/ux/api-consumer-journey.md` |
| Any other value | UX spec for a screen or flow | `design/ux/[argument].md` |
| No argument | Ask the user | (see below) |

**If no argument is provided**, do not fail — ask instead. Use `AskUserQuestion`:
- **[游戏专用]** "What are we designing today?"
  Options: "A specific screen or flow", "The game HUD", "The interaction pattern library", "I'm not sure"
- **[通用产品]** "What are we designing today?"
  Options: "A specific screen or user flow", "CLI interaction design", "API consumer journey", "The interaction pattern library", "I'm not sure"

If the user selects a screen or flow name, normalize it to kebab-case
for the filename (e.g., "Main Menu" becomes `main-menu`).

---

## 2. Gather Context (Read Phase)

Read all relevant context **before** asking the user anything. The skill's value
comes from arriving informed.

### 2a: Required Reads

**[通用场景]** Read the concept document for the detected domain:
- **[游戏专用]** Read `design/cdd/game-concept.md` — if missing, warn and continue
- **[通用产品]** Read `design/cdd/product-concept.md` — if missing, warn and continue

### 2b: User Journey

**[游戏专用]** Read `design/player-journey.md` if it exists. Extract:
- Which journey phase(s) does this screen appear in?
- What is the player's emotional state on arrival?
- What player need is this screen serving?
- What critical moments does this screen deliver?

**[通用产品]** Read the User Journey section of the product concept doc. Extract:
- Which workflow step(s) does this screen/flow belong to?
- What is the user's goal at this point?
- What user need is this screen/flow serving?
- What is the primary JTBD (Job to Be Done) at this interaction point?

If no journey information exists, note the gap and proceed with assumptions.

### 2c: CDD UI Requirements

Glob `design/cdd/*.md` and grep for `UI Requirements` sections. Read any CDD whose
UI Requirements section references this screen by name or category.

These CDD UI Requirements are the **requirements input** to this spec. Collect them
as a list of constraints the spec must satisfy.

If designing the HUD, read ALL CDD UI Requirements sections — the HUD aggregates
requirements from every system.

### 2d: Existing UX Specs

Glob `design/ux/*.md` and note which screens already have specs. For screens that
will link to or from the current screen, read their navigation/flow sections to
find the entry and exit points this spec must match.

### 2e: Interaction Pattern Library

If `design/ux/interaction-patterns.md` exists, read the pattern catalog index
(the list of pattern names and their one-line descriptions). Do not read full
pattern details — just the catalog. This tells you which patterns already exist
so you can reference them rather than reinvent them.

### 2f: Visual / Product Style References

For game projects, check for `design/art/art-bible.md`. If found, read the
visual direction section. UX layout must align with the aesthetic commitments
already made.

For product projects, check for `design/brand/style-guide.md`. If found, read
brand tone, visual standards, docs imagery rules, and accessibility-constrained
color/typography commitments. For UI-heavy products, also check
`design/design-system.md`; if it exists, read component patterns and state
standards before writing screen or workflow specs.

### 2g: Accessibility Requirements

Check for `design/accessibility-requirements.md`. If found, read it. The spec
must satisfy the accessibility tier committed to there.

### 2h: Input Method (from Project Config)

Read `standards/technical-preferences.md` and extract the `## Input & Platform`
section. Store these values for use throughout the skill — they drive the
Interaction Map and inform accessibility requirements:

- **Input Methods** — e.g., Keyboard/Mouse, Gamepad, Touch, Mixed
- **Primary Input** — the dominant input for this game
- **Gamepad Support** — Full / Partial / None
- **Touch Support** — Full / Partial / None
- **Target Platforms** — for safe zone and aspect ratio decisions

If the section is unconfigured (`[TO BE CONFIGURED]`), ask once:
> "Input methods aren't configured yet. What does this game target?"
> Options: "Keyboard/Mouse only", "Gamepad only", "Both (PC + Console)", "Touch (mobile)", "All of the above"
>
> (Run `/setup-engine` to save this permanently so you won't be asked again.)

Store the answer for the rest of this session. Do **not** ask again per section
or per screen.

### 2i: Present Context Summary

Before any design work, present a brief summary to the user:

> **Designing: [Screen/Flow Name]**
> - Mode: [UX Spec / HUD Design / Pattern Library / CLI / API]
> - Journey phase(s) / Workflow step(s): [from concept doc or journey map, or "unknown — no journey map"]
> - CDD requirements feeding this spec: [count and names, or "none found"]
> - Related screens/flows already specced: [list, or "none yet"]
> - Known patterns available: [count, or "no pattern library yet"]
> - Accessibility tier: [from requirements doc, or "not yet defined"]
> - Input methods: [from technical-preferences.md, or "asked above"]

Then ask: "Anything else I should read before we start, or shall we proceed?"

---

## 2b. Retrofit Mode Detection

Before creating a skeleton, check if the target output file already exists.

Glob `design/ux/[filename].md` (where `[filename]` is the resolved output path from Phase 1).

**If the file exists — retrofit mode:**
- Read the file in full
- For each expected section, check whether the body has real content (more than a `[To be designed]` placeholder) or is empty/placeholder
- Present a section status summary to the user:

> "Found existing UX spec at `design/ux/[filename].md`. Here's what's already done:
>
> | Section | Status |
> |---------|--------|
> | Overview & Context | [Complete / Empty / Placeholder] |
> | Purpose & User Need | ... |
> | User Context & Journey Integration | ... |
> | Screen Layout & Information Architecture | ... |
> | Interaction Model | ... |
> | Feedback & State Communication | ... |
> | Accessibility | ... |
> | Edge Cases & Error States | ... |
> | Open Questions | ... |
>
> I'll work on the [N] incomplete sections only — existing content will not be overwritten."

- Skip Section 3 (skeleton creation) — the file already exists
- In Phase 4 (Section Authoring), only work on sections with Status: Empty or Placeholder
- Use `Edit` to fill placeholders in-place rather than creating a new skeleton

**If the file does not exist — fresh authoring mode:**
Proceed to Phase 3 (Create File Skeleton) as normal.

---

## 3. Create File Skeleton

Once the user confirms, **immediately** create the output file with empty section
headers. This ensures incremental writes have a target and work survives interruptions.

Ask: "May I create the skeleton file at `design/ux/[filename].md`?"

---

### Skeleton for UX Spec (screen or flow)

```markdown
# UX Spec: [Screen/Flow Name]

> **Status**: In Design
> **Author**: [user + ux-designer]
> **Last Updated**: [today's date]
> **Journey Phase(s)**: [from context]
> **Template**: UX Spec

---

## Purpose & User Need

[To be designed]

---

## User Context on Arrival

[To be designed]

---

## Navigation / Workflow Position

[To be designed]

---

## Entry & Exit Points

[To be designed]

---

## Layout Specification

### Information Hierarchy

[To be designed]

### Layout Zones

[To be designed]

### Component Inventory

[To be designed]

### ASCII Wireframe

[To be designed]

---

## States & Variants

[To be designed]

---

## Interaction Map

[To be designed]

---

## Events Fired

[To be designed]

---

## Transitions & Animations

[To be designed]

---

## Data Requirements

[To be designed]

---

## Accessibility

[To be designed]

---

## Localization Considerations

[To be designed]

---

## Acceptance Criteria

[To be designed]

---

## Open Questions

[To be designed]
```

---

### Skeleton for HUD Design

```markdown
# HUD Design

> **Status**: In Design
> **Author**: [user + ux-designer]
> **Last Updated**: [today's date]
> **Template**: HUD Design

---

## HUD Philosophy

[To be designed]

---

## Information Architecture

### Full Information Inventory

[To be designed]

### Categorization

[To be designed]

---

## Layout Zones

[To be designed]

---

## HUD Elements

[To be designed]

---

## Dynamic Behaviors

[To be designed]

---

## Platform & Input Variants

[To be designed]

---

## Accessibility

[To be designed]

---

## Open Questions

[To be designed]
```

---

### Skeleton for Interaction Pattern Library

```markdown
# Interaction Pattern Library

> **Status**: In Design
> **Author**: [user + ux-designer]
> **Last Updated**: [today's date]
> **Template**: Interaction Pattern Library

---

## Overview

[To be designed]

---

## Pattern Catalog

[To be designed]

---

## Patterns

[Individual pattern entries added here as they are defined]

---

## Gaps & Patterns Needed

[To be designed]

---

## Open Questions

[To be designed]
```

---

After writing the skeleton, update `production/session-state/active.md` with:
- Task: Designing [screen/flow name] UX spec
- Current section: Starting (skeleton created)
- File: design/ux/[filename].md

---

## 4. Section-by-Section Authoring

Walk through each section in order. For **each section**, follow this cycle:

```
Context  ->  Questions  ->  Options  ->  Decision  ->  Draft  ->  Approval  ->  Write
```

1. **Context**: State what this section needs to contain and surface any relevant
   constraints from context gathered in Phase 2.
2. **Questions**: Ask what is needed to draft this section. Use `AskUserQuestion`
   for constrained choices, conversational text for open-ended exploration.
3. **Options**: Where design choices exist, present 2-4 approaches with pros/cons.
   Explain reasoning in conversation, then use `AskUserQuestion` to capture the decision.
4. **Decision**: User picks an approach or provides custom direction.
5. **Draft**: Write the section content in conversation for review. Flag provisional
   assumptions explicitly.
6. **Approval**: "Does this capture it? Any changes before I write it to the file?"
7. **Write**: Use `Edit` to replace the `[To be designed]` placeholder with approved
   content. Confirm the write.

After writing each section, update `production/session-state/active.md`.

---

### Section Guidance: UX Spec Mode

#### Section A: Purpose & User Need

This section is the foundation. Every other decision flows from it.

**[Game] — Purpose & Player Need**

**Questions to ask**:
- "What player goal does this screen serve? What is the player trying to DO here?"
- "What would go wrong if this screen didn't exist or was hard to use?"
- "Complete this sentence: 'The player arrives at this screen wanting to ___.' "

Cross-reference the player journey context gathered in Phase 2. The stated purpose
must align with the journey phase and emotional state.

**[Product] — Purpose & User Need**

**Questions to ask**:
- "What user goal does this screen, flow, or command serve? What is the user trying to ACCOMPLISH?"
- "What Job to Be Done (JTBD) does this fulfill? Why would the user choose this over an alternative?"
- "What would go wrong if this interaction didn't exist or was hard to use?"
- "Complete this sentence: 'The user interacts with this to ___.' "

Cross-reference the product concept doc gathered in Phase 2. The stated purpose
must align with the product principles and MVP scope.

**For CLI**: focus on the task the user is scripting or automating — "The user runs this command to ___ as part of a pipeline/script."
**For API**: focus on the developer consumer — "The developer calls this endpoint to ___ and expects ___ in return."
**For Web/Admin**: focus on the end-user goal — "The user arrives at this screen to ___ and their primary concern is ___."

---

#### Section B: User Context on Arrival

**[Game] — Player Context**

**Questions to ask**:
- "When in the game does a player first encounter this screen?"
- "What were they just doing immediately before reaching this screen?"
- "What emotional state should the design assume? (calm, stressed, curious, time-pressured)"
- "Do players arrive at this screen voluntarily, or are they sent here by the game?"

Offer to map this against the journey phases if the player journey doc exists.

**[Product] — User Context**

**Questions to ask**:
- "When in the user's workflow does this interaction happen? Is it daily, weekly, or rare one-time?"
- "What was the user doing immediately before reaching this screen or running this command?"
- "What is their state of mind — exploring the product, troubleshooting a problem, completing a routine task, time-pressured by a deadline?"
- "Is the user arriving here voluntarily (exploring, learning) or were they sent here (error recovery, support link, redirect)?"

**For CLI**: "Where in the user's terminal session does this command appear? Are they chaining it with other commands (piping, scripting)?"
**For API**: "Where in the developer's integration workflow does this endpoint sit? Are they building, testing, or debugging?"
**For Web/Admin**: "What task brought the user to this screen? What were they looking at before?"

---

#### Section B2: Navigation / Workflow Position

Where does this screen sit in the navigation or workflow hierarchy? This is a one-paragraph
orientation map — not a full flow diagram.

**[Game] — Navigation Position**

**Questions to ask**:
- "Is this screen accessed from the main menu, from pause, from within gameplay, or from another screen?"
- "Is it a top-level destination (always reachable) or a context-dependent one (only accessible in certain states)?"
- "Can the player reach this screen from more than one place in the game?"

Present as: "This screen lives at: [root] → [parent] → [this screen]" plus any alternate entry paths.

**[Product] — Workflow Position**

**Questions to ask**:
- "Where does this screen, command, or endpoint sit in the overall product interaction tree?"
- "Is it a top-level entry point (landing page, root command, base endpoint) or a child (sub-page, subcommand, nested resource)?"
- "Can the user reach this from more than one place or context?"

**For CLI**: "Where in the command tree? `app command subcommand [action]`" — note parent commands and sibling commands.
**For API**: "Where in the OpenAPI path tree? `GET /api/v1/[resource]/[sub-resource]`" — show relationship to parent and sibling resources.
**For Web/Admin**: "Where in the breadcrumb or site map? Home → [section] → [page] → [this screen]" — note the information architecture position.

---

#### Section B3: Entry & Exit Points

Map every way the user can arrive at and leave this screen, flow, or command.

**[通用场景]**

**Questions to ask**:
- "What are all the ways a user can reach this interaction?" (List each trigger: button press, event, redirect, CLI argument combination, API path, deep link)
- "What can the user do to exit? What happens when they do?" (Back button, confirm action, timeout, event, exit code, redirect, next step in workflow)
- "Are there any exits that are one-way — where the user cannot return to this interaction without starting over?"

Present as two tables:

| Entry Source | Trigger | User carries this context |
|---|---|---|
| [screen/event/command/endpoint] | [how] | [state/data they arrive with] |

| Exit Destination | Trigger | Notes |
|---|---|---|
| [screen/event/command/endpoint] | [how] | [any irreversible state changes] |

**[Product] Additional entry/exit considerations**:
- **CLI**: Exit codes (0=success, non-zero=error types), stdout vs stderr as "exit destinations", pipe output to another command
- **API**: HTTP redirects (301/302), HATEOAS links as guided exits, error responses as exit paths (400/404/500)
- **Web**: Browser back button behavior, form submission redirects, external links, session timeout redirects
- **Admin dashboard**: Bulk action exits, filter-to-detail drill-down exits, export/download as an exit path

---

#### Section C: Layout Specification

This is the largest and most interactive section. Work through it in sub-sections.

### [Game] Game Screen Layout

**Sub-section 1 — Information Hierarchy** (establish this before any layout):
- Ask the user to list every piece of information this screen must communicate.
- Then ask them to rank the items: "What is the single most important thing a player
  needs to see first? What is second? What can be discovered rather than immediately visible?"
- Present the resulting hierarchy for approval before moving to zones.

**Sub-section 2 — Layout Zones**:
- Based on the information hierarchy, propose rough screen zones (header, content
  area, action bar, sidebar, etc.).
- Offer 2-3 zone arrangements with rationale for each. Reference platform and
  input context gathered from game concept.
- Ask: "Do any of these match your mental image, or shall we build a custom arrangement?"

**Sub-section 3 — Component Inventory**:
- For each zone, list the UI components it contains. For each component, note:
  - Component type (button, list, card, stat display, input field, etc.)
  - Content it displays
  - Whether it is interactive
  - If it uses an existing pattern from the library (reference by pattern name)
  - If it introduces a new pattern (flag for later addition to the library)

**Sub-section 4 — ASCII Wireframe**:
- Offer to generate an ASCII wireframe based on the zone layout and component list.
- Use `AskUserQuestion`: "Want an ASCII wireframe as part of this spec?"
  - Options: "Yes, include one", "No, I'll attach a separate file"
- If yes, produce the wireframe in conversation first. Ask for feedback before
  writing it to file.

### [Product] Product Layout — Mode-Specific

#### CLI Output Formatting

**Sub-section 1 — Information Hierarchy**:
- List every piece of information the command must emit (via stdout, stderr, or exit code).
- Rank by importance: "What is the single most important thing the user needs to see first in the output?"
- Consider whether the output is human-readable, machine-parseable (JSON, CSV), or both (e.g., `--json` flag).

**Sub-section 2 — Output Zones**:
- Define the output structure: header section, body/table, summary/footer, error channel (stderr).
- For table-formatted output: define columns, alignment, truncation rules.
- For JSON output: define the response schema (top-level keys, array shapes, nested objects).

**Sub-section 3 — Component Inventory**:
Note which CLI patterns are in play:
- Flags (`--verbose`, `--output json`)
- Positional arguments
- Progress indicators / spinners
- Interactive prompts (confirmations, select menus)
- Color/styling conventions (if applicable)

#### API Response Shape Design

**Sub-section 1 — Information Hierarchy**:
- Define the response envelope: what top-level keys are always present? (e.g., `data`, `meta`, `errors`, `links`)
- For collections: pagination envelope (`items`, `total`, `page`, `pageSize`, `nextCursor`)
- For errors: consistent error format (`code`, `message`, `details`, `requestId`)

**Sub-section 2 — Endpoint Layout**:
- Map the URL structure: base path, resource nesting, query parameters.
- Define HTTP methods per resource and their semantics (GET=read, POST=create, PUT=replace, PATCH=update, DELETE=remove).
- Document rate limit headers and retry-after semantics.

**Sub-section 3 — Component Inventory**:
Note which API patterns are in play:
- Pagination style (offset, cursor, page)
- Filtering and sorting parameters
- Field selection / sparse fieldsets
- Expansion / includes (`?include=author,comments`)
- Versioning strategy (URL path, header, query param)

#### Web / Admin Screen Layout

Follow the same sub-section structure as [Game] Screen Layout above, with these web-specific adjustments:

- **Information Hierarchy**: consider above-the-fold vs scroll-discoverable content.
- **Layout Zones**: propose responsive breakpoints (mobile, tablet, desktop). Consider grid vs flex layout.
- **Component Inventory**: reference standard web components (form fields, data tables, modals, tabs, accordions, toasts, breadcrumbs).
- **ASCII Wireframe**: include responsive variants — "mobile: single column, tablet: 2-column grid, desktop: sidebar + main content".

---

#### Section D: States & Variants

Guide the user to think beyond the happy path.

**[通用场景] Shared core states:**

**Questions to ask** (work through these one at a time):
- "What does this interaction look like the very first time, when there
  is no data yet? (empty state)"
- "What happens when something goes wrong — an error, a failed action, a missing
  resource? (error state)"
- "Is there ever a loading wait on this interaction? If so, what does it show? (loading state)"

**[Game] Additional game-specific states:**
- "Are there any player progression states that change what this screen shows? For
  example, locked content, premium content, or tutorial-mode overlays?"
- "Does this screen behave differently on any supported platform? (platform variant)"

**[Product] Additional product-specific states:**
- **Rate-limited**: What does the user see when they've hit a rate limit? Include retry-after information.
- **Auth-expired**: What happens when the session/token expires mid-interaction? Redirect to login? Inline re-auth?
- **Offline / Connectivity loss**: How does the interaction behave when the network is unavailable? Graceful degradation?
- **Partial data**: What shows when some data loaded but other parts failed? Partial render with error indicators?
- **Maintenance mode**: What does the user see during planned downtime?
- **Permission denied**: Distinct from auth-expired — the user is authenticated but lacks the required role/permission.

Present the collected states as a table for approval:

| State / Variant | Trigger | What Changes |
|-----------------|---------|--------------|
| Default | Normal load | — |
| Empty | No data available | [content area description] |
| [etc.] | [trigger] | [changes] |

---

#### Section E: Interaction Map

For each interactive component identified in the Layout Specification, define:
- The action
- The input(s) that trigger it
- The immediate feedback
- The outcome (navigation target, state change, data write)

### [Game] Game Interaction Map

For each interactive component, define:
- The action (tap, click, press, hold, scroll, drag)
- The platform input(s) that trigger it (mouse click, gamepad A, keyboard Enter)
- The immediate feedback (visual, audio, haptic)
- The outcome (navigation target, state change, data write)

Use the input methods loaded from `technical-preferences.md` in Phase 2h — do
not ask the user again. State them upfront: "Mapping interactions for:
[Input Methods from tech-prefs]. Covering [Gamepad Support] gamepad support."

Work through components one at a time rather than asking for all at once.
For navigation actions (going to another screen), verify the target matches
an existing UX spec or note it as a spec dependency.

### [Product] Product Interaction Map

**For API endpoints:**
- The HTTP method (GET, POST, PUT, PATCH, DELETE) and URL path
- Required and optional parameters (path params, query params, headers, body)
- The success response shape and status code
- The error response shapes and status codes (400, 401, 403, 404, 409, 422, 429, 500)
- Authentication/authorization requirements
- Rate limit and retry semantics

**For CLI commands:**
- The command syntax (flags, positional args, subcommands)
- Flag behaviors (required vs optional, default values, conflicts/mutual exclusion)
- Input sources (stdin, file paths, env vars)
- Output destinations (stdout, file, pipe)
- Exit codes and their meanings
- Interactive prompts (confirmations, select menus, input prompts)

**For Web/Admin screens:**
- Pointer interactions (click, double-click, right-click, drag, hover)
- Keyboard interactions (Tab navigation, Enter to activate, Escape to dismiss, shortcuts)
- Touch interactions (tap, swipe, pinch, long-press)
- Focus order (logical Tab sequence through all interactive elements)
- Form submission and validation feedback

Work through components one at a time rather than asking for all at once.

---

#### Section E2: Events Fired

For every user action in the Interaction Map, document the corresponding event the
system should fire — or explicitly note "no event" if none applies.

**[通用场景]**

**Questions to ask**:
- "For each action, should the system fire an analytics event, trigger a state change, or both?"
- "Are there any actions that should NOT fire an event — and is that a deliberate choice?"

Present as a table alongside the Interaction Map:

| User Action | Event Fired | Payload / Data |
|---|---|---|
| [action] | [EventName] or none | [data passed with event] |

**[Game]** Flag any action that modifies persistent game state (save data, progress, economy) — these need explicit attention from the architecture team.

**[Product]** Flag any action that:
- Modifies persistent data (write, delete, schema change)
- Triggers a billing or metering event
- Accesses or modifies PII (personal data)
- Crosses a service boundary (external API call, message queue publish)
- Has compliance or audit trail implications

---

#### Section E3: Transitions & Animations

Specify how the interaction enters and exits, and how it responds to state changes.

**[Game] — Screen Transitions**

**Questions to ask**:
- "How does this screen appear? (fade in, slide from right, instant pop, scale from button)"
- "How does it dismiss? (fade out, slide back, cut)"
- "Are there any in-screen state transitions that need animation? (loading spinner, success state, error flash)"
- "Is there any animation that could cause motion sickness — and does the game have a reduced-motion option?"

Minimum required:
- Screen enter transition
- Screen exit transition
- At least one state-change animation if the screen has multiple states

**[Product] — Interaction Transitions**

**For API**:
- Request lifecycle states: accepted (202), processing, complete, failed
- Polling/retry behavior: backoff strategy, timeout, max retries
- Idempotency: which operations are safe to retry, which are not
- Long-running operation status: progress indication via `status` field or webhooks

**For CLI**:
- Progress indicators: spinner, progress bar, elapsed time, estimated time remaining
- Verbose vs quiet modes: `--verbose` adds detail, `--quiet` suppresses non-errors
- Signal handling: what happens on SIGINT (Ctrl+C), SIGTERM? Cleanup? Partial output?
- Exit state: "Command completed successfully" vs "Command failed with error code N"

**For Web**:
- Route transitions: page enter/exit animations (fade, slide, instant)
- Loading states: skeleton screens, spinners, progress bars
- Optimistic updates: show success state immediately, revert on server error
- Accessibility: respect `prefers-reduced-motion` media query

---

#### Section F: Data Requirements

Cross-reference the CDD UI Requirements sections gathered in Phase 2.

For each piece of information the interaction displays, ask:
- "Where does this data come from? Which system owns it?"
- "Does this interaction need to write data back, or is it read-only?"
- "Is any of this data time-sensitive or real-time?"

**[通用场景]** Flag any case where the UI would need to own or manage state as an architectural
concern. UX specs define what the UI needs; they do not dictate how the data is
delivered. That is an architecture decision.

Present the data requirements as a table:

| Data | Source System | Read / Write | Update Frequency | Notes |
|------|--------------|--------------|------------------|-------|
| [item] | [system] | Read | Real-time / On load / Polled | — |
| [item] | [system] | Write | On submit / Batched | [concern if any] |

**[Game]** Source systems are typically: game state, save data, player profile, inventory, economy.
**[Product]** Source systems are typically: database, external API, cache, config store, message queue, file system, auth provider.

For each data element, document:
- Null handling: what displays when the data is unavailable?
- Staleness tolerance: how old can the data be before it should be refreshed?
- Caching: can this data be cached? For how long?

---

#### Section G: Accessibility

Cross-reference `design/accessibility-requirements.md` if it exists.

**[通用场景]** Walk through the standard accessibility checklist for this interaction:
- Keyboard-only navigation path through all interactive elements
- Text contrast and minimum readable font sizes
- Color-independent communication (no information conveyed by color alone)
- Screen reader considerations for any non-text elements
- Any motion or animation that needs a reduced-motion alternative

**[Game]** Additional: gamepad navigation order (if applicable)
**[Product]** Additional: WCAG level (A/AA/AAA), ARIA labels for screen readers, focus trapping for modals, skip-to-content links (web)

Use `AskUserQuestion` to surface any open questions on accessibility tier:
- "Has the accessibility tier been committed to for this project?"
  - Options: "Yes, read from requirements doc", "Not yet — let's flag it as a question", "Skip accessibility section for now"

---

#### Section H: Localization Considerations

Document constraints that affect how this interaction behaves when text is translated
or locale changes.

**[通用场景]**

**Questions to ask**:
- "Which text elements in this interaction are the longest? What is the maximum character count that fits the layout?"
- "Are there any elements where text length is layout-critical — e.g., a button label that must stay on one line?"
- "Are there any elements that display numbers, dates, or currencies that need locale-specific formatting?"

Note: aim to flag any element where a 40% text expansion (common in translations from English to German or French) would break the layout. Mark those as HIGH PRIORITY for the localization engineer.

**[Product] Additional considerations**:
- **API**: Are error messages translatable? Document the `Accept-Language` header usage.
- **CLI**: Does the CLI support `LANG` / `LC_ALL` environment variables for locale-aware output? Are help text and error messages in separate message catalogs?
- **Web**: RTL (right-to-left) language support — does the layout accommodate mirrored text flow? Date/time formatting via `Intl` or locale-aware libraries.
- **Admin dashboard**: Multi-tenant localization — do different tenants see different default locales?

---

#### Section I: Acceptance Criteria

Write at least 5 specific, testable criteria that a QA tester can verify without reading any other design document. These become the pass/fail conditions for `/story-done`.

**Format**: Use checkboxes. Each criterion must be verifiable by a human tester.

**[Game] Game criteria examples:**

```
- [ ] Screen opens within [X]ms from [trigger]
- [ ] [Element] displays correctly at [minimum] and [maximum] values
- [ ] [Navigation action] correctly routes to [destination screen]
- [ ] Error state appears when [condition] and shows [specific message or icon]
- [ ] Keyboard/gamepad navigation reaches all interactive elements in logical order
- [ ] [Accessibility requirement] is met — e.g., "all interactive elements have focus indicators"
```

**[Product] Product criteria examples:**

```
- [ ] [API] Endpoint responds within [X]ms p95 under expected load
- [ ] [API] Error response for invalid input includes `code`, `message`, and `details` fields
- [ ] [CLI] Command exits with code 0 on success and non-zero on failure
- [ ] [CLI] Help text (`--help`) is accurate for all flags and subcommands
- [ ] [Web] Screen renders correctly at 320px, 768px, 1024px, and 1440px widths
- [ ] [Web] All interactive elements are reachable and operable via keyboard (Tab/Enter/Escape)
- [ ] [Web] Empty state shows a clear call to action when no data exists
- [ ] [All] Error state displays a user-readable message (no stack traces or internal codes)
- [ ] [All] Authentication-required state redirects to login and returns to original location after sign-in
- [ ] [All] Rate-limited state displays retry-after information
```

**Minimum required** (applies to both domains):
- 1 performance criterion (load/open/response time)
- 1 navigation/workflow criterion (at least one entry or exit path verified)
- 1 error/empty/edge-case state criterion
- 1 accessibility criterion (per committed tier)
- 1 criterion specific to this interaction's core purpose

Ask the user to confirm: "Do these criteria cover what would actually make this interaction 'done' for your QA process?"

---

### Section Guidance: HUD Design Mode

HUD design follows a different order from UX spec mode. Begin with philosophy;
do not touch layout until the information architecture is complete.

#### Section A: HUD Philosophy

Ask the user to describe the game's relationship with on-screen information in
1-2 sentences.

Offer framing examples to help:
- "Nearly HUD-free — atmosphere requires unobstructed immersion (e.g., Hollow Knight, Firewatch)"
- "Minimal but present — only critical information visible, everything else contextual (e.g., Dark Souls)"
- "Information-dense — all decision-relevant data always visible (e.g., Diablo IV, StarCraft II)"
- "Adaptive — HUD density responds to combat state, exploration mode, menus (e.g., God of War)"

This philosophy becomes the design constraint for every subsequent HUD decision.
If a proposed element conflicts with the stated philosophy, surface that conflict.

---

#### Section B: Information Architecture

Complete this before any layout work. Do not skip it.

**Step 1 — Full information inventory**:
Pull all information from CDD UI Requirements sections gathered in Phase 2.
Present the full list: "These are all the things your game systems say they need
to communicate to the player on screen."

**Step 2 — Categorization**:
For each item, ask the user to categorize it:

| Category | Description |
|----------|-------------|
| **Must Show** | Always visible, player needs it for core decisions |
| **Contextual** | Visible only when relevant (in combat, near interactable, etc.) |
| **On Demand** | Player must actively request it (toggle, hold button) |
| **Hidden** | Communicated through world/audio, never on-screen text |

Use `AskUserQuestion` to step through items in groups of 3-4, not all at once.
This is the most consequential design decision in the HUD — do not rush it.

**Conflict check**: If the information philosophy (Section A) says "nearly HUD-free"
but the Must Show list is growing long, surface the conflict explicitly:
> "The current Must Show list has [N] items. That may conflict with the HUD-free
> philosophy. Options: reduce the Must Show list, revise the philosophy, or define
> a hybrid approach where HUD is absent in exploration and present in combat."

---

#### Section C: Layout Zones

Only after the information architecture is approved, design layout zones.

Base layout on:
- Which items are Must Show (they drive the permanent zone decisions)
- Where player attention naturally goes during gameplay (center-screen for action games,
  corners for strategy games)
- Platform and aspect ratio targets

Offer 2-3 zone arrangements. Include rationale based on the HUD philosophy and the
categorization from Section B.

---

#### Section D: HUD Elements

For each element in the layout, specify:
- Element name and category (Must Show / Contextual / On Demand)
- Content displayed
- Visual form (bar, number, icon, counter, map)
- Update behavior (real-time, event-driven, player-queried)
- Contextual trigger (if not always visible)
- Animation behavior (does it pulse when low? Fade in? Slam in?)

Work element by element. Reference the interaction pattern library if relevant patterns
exist for status displays, resource bars, or cooldown indicators.

---

#### Sections E, F, G: Dynamic Behaviors, Platform Variants, Accessibility

These follow the same structure as the UX spec equivalents. See UX Spec section
guidance for D (States/Variants), E (Interactions), and G (Accessibility).

For the HUD specifically, emphasize:
- Dynamic Behaviors: what causes the HUD to change density mid-gameplay?
- Platform Variants: does mobile/console require different element sizes or positions?

---

### Section Guidance: Interaction Pattern Library Mode

Pattern library authoring is additive and catalog-driven, not linear.

#### Phase 1: Catalog Existing Patterns

Glob `design/ux/*.md` (excluding `interaction-patterns.md`) and read the Component
Inventory and Interaction Map sections of each spec. Extract every interaction
pattern used.

Present the extracted list: "Based on existing UX specs, these patterns are already
in use in the game:"
- [Pattern name]: used in [screen], [screen]
- [etc.]

Ask: "Are there patterns you know exist but aren't in existing specs yet? List any
additional ones now."

---

#### Phase 2: Formalize Each Pattern

For each pattern (existing or new), document:

```markdown
### [Pattern Name]

**Category**: Navigation / Input / Feedback / Data Display / Modal / Overlay / [other]
**Used In**: [list of screens]

**Description**: [One paragraph explaining what this pattern is and when to use it]

**Specification**:
- [Component behavior]
- [Input mapping]
- [Visual/audio feedback]
- [Accessibility requirements for this pattern]

**When to Use**: [Conditions where this pattern is appropriate]
**When NOT to Use**: [Conditions where another pattern is more appropriate]

**Reference**: [Screenshot path or ASCII example, if available]
```

Work through patterns in groups. Offer: "Shall I draft the first batch based on what
I've found in the existing specs, or do you want to define them one by one?"

---

#### Phase 3: Identify Gaps

After cataloging known patterns, ask:
- "Are there screens or interactions planned that would need patterns not yet
  in this library?"
- "Are there any patterns in existing specs that feel inconsistent with each
  other and should be consolidated?"

Document gaps in the Gaps section for follow-up.

---

## 5. Cross-Reference Check

Before marking the spec as ready for review, run these checks:

**1. CDD requirement coverage**: Does every CDD UI Requirement that references
this screen have a corresponding element in this spec? Present any gaps.

**2. Pattern library alignment**: Are all interaction patterns used in this spec
referenced by name? If a new pattern was invented during this spec session, flag
it for addition to the pattern library:
> "This spec uses [pattern name], which isn't in the pattern library yet.
> Want to add it now, or flag it as a gap?"

**3. Navigation consistency**: Do the entry/exit points in this spec match the
navigation map in any related specs? Flag mismatches.

**4. Accessibility coverage**: Does the spec address the accessibility tier
committed to in `design/accessibility-requirements.md`? If not, flag open questions.

**5. Empty states**: Does every data-dependent element have an empty state defined?
Flag any that don't.

Present the check results:
> **Cross-Reference Check: [Screen Name]**
> - CDD requirements: [N of M covered / all covered]
> - New patterns to add to library: [list or "none"]
> - Navigation mismatches: [list or "none"]
> - Accessibility gaps: [list or "none"]
> - Missing empty states: [list or "none"]

---

## 6. Handoff

When all sections are approved and written:

### 6a: Update Session State

Update `production/session-state/active.md` with:
- Task: [screen-name] UX spec
- Status: Complete (or In Review)
- File: design/ux/[filename].md
- Sections: All written
- Next: [suggestion]

### 6b: Suggest Next Step

Before presenting options, state clearly:

> "This spec should be validated with `/ux-review` before it enters the
> implementation pipeline. The Pre-Production gate requires all key screen specs
> to have a review verdict."

Then use `AskUserQuestion`:
- "Run `/ux-review [filename]` now, or do something else first?"
  - Options:
    - "Run `/ux-review` now — validate this spec"
    - "Design another screen first, then review all specs together"
    - "Update the interaction pattern library with new patterns from this spec"
    - "Stop here for this session"

If the user picks "Design another screen first", add a note: "Reminder: run
`/ux-review` on all completed specs before running `/gate-check pre-production`."

### 6c: Cross-Link Related Specs

When other UX specs link to or from this screen, note which ones should reference
this spec. Do not edit those files without asking — just name them.

---

## 7. Recovery & Resume

If the session is interrupted (compaction, crash, new session):

1. Read `production/session-state/active.md` — it records the current screen
   and which sections are complete.
2. Read `design/ux/[filename].md` — sections with real content are done;
   sections with `[To be designed]` still need work.
3. Resume from the next incomplete section — no need to re-discuss completed ones.

This is why incremental writing matters: every approved section survives any
disruption.

---

## 8. Specialist Agent Routing

This skill uses `ux-designer` as the primary agent (set in frontmatter). For
specific sub-topics, additional context or coordination may be needed:

| Topic | Coordinate with |
|-------|----------------|
| Visual aesthetics, color, layout feel | `art-director` — UX spec defines zones; art defines how they look |
| Implementation feasibility (engine constraints) | `ui-programmer` — before finalizing component inventory |
| Gameplay data requirements | `game-designer` — when data ownership is unclear |
| Narrative/lore visible in the UI | `narrative-director` — for flavor text, item names, lore panels |
| Accessibility tier decisions | Handled by this session — owned by ux-designer |

When delegating to another agent via the Task tool:
- Provide: screen name, game concept summary, the specific question needing expert input
- The agent returns analysis to this session
- This session presents the agent's output to the user
- The user decides; this session writes to file
- Agents do NOT write to files directly — this session owns all file writes

---

## Collaborative Protocol

This skill follows the collaborative design principle at every step:

1. **Question -> Options -> Decision -> Draft -> Approval** for every section
2. **AskUserQuestion** at every decision point (Explain -> Capture pattern):
   - Phase 2: "Ready to start, or need more context?"
   - Phase 3: "May I create the skeleton?"
   - Phase 4 (each section): design questions, approach options, draft approval
   - Phase 5: "Run cross-reference check? What's next?"
3. **"May I write to [filepath]?"** before the skeleton and before each section write
4. **Incremental writing**: Each section is written to file immediately after approval
5. **Session state updates**: After every section write

**Aesthetic deference**: When layout or visual choices come down to personal taste,
present the options and ask. Do not select a layout because it is "standard" — always
confirm. The user is the creative director.

**Conflict surfacing**: When a CDD requirement and the available screen real estate
conflict, surface the conflict and present resolution options. Never silently drop
a requirement. Never silently expand the layout without flagging it.

**Never** auto-generate the full spec and present it as a fait accompli.
**Never** write a section without user approval.
**Never** contradict an existing approved UX spec without flagging the conflict.
**Always** show where decisions come from (CDD requirements, player journey, user choices).

Verdict: **COMPLETE** — UX spec written and approved section by section.

---

## Recommended Next Steps

- Run `/ux-review [filename]` to validate this spec before it enters the implementation pipeline
- Run `/ux-design [next-screen]` to continue designing remaining screens or flows
- Run `/gate-check pre-production` once all key screens have approved UX specs
