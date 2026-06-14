---
name: create-architecture
description: "Guided, section-by-section authoring of the master architecture document. Reads all CDDs, the module index, existing ADRs, and the reference library to produce a complete architecture blueprint before any code is written. Supports both game and general product domains."
argument-hint: "[focus-area: full | layers | data-flow | api-boundaries | adr-audit] [--review full|lean|solo]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Bash, AskUserQuestion, Task
agent: technical-director
---

## User Guide

- When to use: Guided, section-by-section authoring of the master architecture document. Reads all CDDs, the module index, existing ADRs, and the reference library to produce a complete architecture blueprint before any code is written. Supports both game and general product domains.
- Inputs: Command arguments: `/create-architecture [focus-area: full | layers | data-flow | api-boundaries | adr-audit] [--review full|lean|solo]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: None.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

# Create Architecture

This skill produces `docs/architecture/architecture.md` — the master architecture
document that translates all approved CDDs into a concrete technical blueprint.
It sits between design and implementation, and must exist before sprint planning begins.

**Distinct from `/architecture-decision`**: ADRs record individual point decisions.
This skill creates the whole-system blueprint that gives ADRs their context.

Resolve the review mode (once, store for all gate spawns this run):
1. If `--review [full|lean|solo]` was passed → use that
2. Else read `production/review-mode.txt` → use that value
3. Else → default to `lean`

See `standards/director-gates.md` for the full check pattern.

**Domain detection.** The concept document at `design/cdd/` reveals the domain:
- **游戏专用**: `game-concept.md` exists — use game architecture layers and engine reference docs
- **通用产品**: `product-concept.md` exists — use product architecture layers and stack reference docs

Sections below are marked **[通用场景]** (both domains), **[游戏专用]** (game-domain), or **[通用产品]** (product-domain).

**Argument modes:**
- **No argument / `full`**: Full guided walkthrough — all sections, start to finish
- **`layers`**: Focus on the module layer diagram only
- **`data-flow`**: Focus on data flow between modules only
- **`api-boundaries`**: Focus on API boundary definitions only
- **`adr-audit`**: Audit existing ADRs for compatibility gaps only

---

## Phase 0: Load All Context

Before anything else, load the full project context in this order:

### 0a. Technology Context (Critical)

**[游戏专用]** Read the engine reference library completely:

1. `docs/engine-reference/[engine]/VERSION.md`
   → Extract: engine name, version, LLM cutoff, post-cutoff risk levels
2. `docs/engine-reference/[engine]/breaking-changes.md`
   → Extract: all HIGH and MEDIUM risk changes
3. `docs/engine-reference/[engine]/deprecated-apis.md`
   → Extract: APIs to avoid
4. `docs/engine-reference/[engine]/current-best-practices.md`
   → Extract: post-cutoff best practices that differ from training data
5. All files in `docs/engine-reference/[engine]/modules/`
   → Extract: current API patterns per domain

If no engine is configured, stop and prompt:
> "No engine is configured. Run `/setup-engine` first. Architecture cannot be
> written without knowing which engine and version you are targeting."

**[通用产品]** Read the stack reference library completely:

1. `docs/reference/[stack]/VERSION.md`
   → Extract: stack name, version, LLM cutoff, post-cutoff risk levels
2. `docs/reference/[stack]/breaking-changes.md`
   → Extract: all HIGH and MEDIUM risk changes
3. `docs/reference/[stack]/deprecated-apis.md`
   → Extract: APIs to avoid
4. `docs/reference/[stack]/current-best-practices.md`
   → Extract: post-cutoff best practices that differ from training data
5. All files in `docs/reference/[stack]/modules/`
   → Extract: current API patterns per domain

If no stack is configured, stop and prompt:
> "No technology stack is configured. Run `/setup-engine` first. Architecture cannot be
> written without knowing which stack and version you are targeting."

### 0b. Design Context + Technical Requirements Extraction

Read all approved design documents and extract technical requirements from each:

1. **游戏专用**: `design/cdd/game-concept.md` — game pillars, genre, core loop
   **通用产品**: `design/cdd/product-concept.md` — product principles, user journey, MVP
2. `design/cdd/module-index.md` — all modules, dependencies, priority tiers
3. `standards/technical-preferences.md` — naming conventions, performance budgets,
   allowed libraries, forbidden patterns
4. **Every CDD in `design/cdd/`** — for each, extract technical requirements:
   - Data structures implied by the game rules
   - Performance constraints stated or implied
   - Engine capabilities the system requires
   - Cross-system communication patterns (what talks to what, how)
   - State that must persist (save/load implications)
   - Threading or timing requirements

Build a **Technical Requirements Baseline** — a flat list of all extracted
requirements across all CDDs, numbered `TR-[gdd-slug]-[NNN]`. This is the
complete set of what the architecture must cover. Present it as:

```
## Technical Requirements Baseline
Extracted from [N] CDDs | [X] total requirements

| Req ID | CDD | System | Requirement | Domain |
|--------|-----|--------|-------------|--------|
| TR-combat-001 | combat.md | Combat | Hitbox detection per-frame | Physics |
| TR-combat-002 | combat.md | Combat | Combo state machine | Core |
| TR-inventory-001 | inventory.md | Inventory | Item persistence | Save/Load |
```

This baseline feeds into every subsequent phase. No CDD requirement should be
left without an architectural decision to support it by the end of this session.

### 0c. Existing Architecture Decisions

Read all files in `docs/architecture/` to understand what has already been decided.
List any ADRs found and their domains.

### 0d. Generate Knowledge Gap Inventory

Before proceeding, display a structured summary:

```
## Technology Knowledge Gap Inventory
Technology: [name + version]
LLM Training Covers: up to approximately [version]
Post-Cutoff Versions: [list]

### HIGH RISK Domains (must verify against reference docs before deciding)
- [Domain]: [Key changes]

### MEDIUM RISK Domains (verify key APIs)
- [Domain]: [Key changes]

### LOW RISK Domains (in training data, likely reliable)
- [Domain]: [no significant post-cutoff changes]

### Modules from CDD that touch HIGH/MEDIUM risk domains:
- [CDD module name] → [domain] → [risk level]
```

Ask: "This inventory identifies [N] modules in HIGH RISK technology domains. Shall I
continue building the architecture with these warnings flagged throughout?"

---

## Phase 1: Module Layer Mapping

Map every module from `module-index.md` into an architecture layer.

**[游戏专用]** The standard game architecture layers are:

```
┌─────────────────────────────────────────────┐
│  PRESENTATION LAYER                         │  ← UI, HUD, menus, VFX, audio
├─────────────────────────────────────────────┤
│  FEATURE LAYER                              │  ← gameplay systems, AI, quests
├─────────────────────────────────────────────┤
│  CORE LAYER                                 │  ← physics, input, combat, movement
├─────────────────────────────────────────────┤
│  FOUNDATION LAYER                           │  ← engine integration, save/load,
│                                             │    scene management, event bus
├─────────────────────────────────────────────┤
│  PLATFORM LAYER                             │  ← OS, hardware, engine API surface
└─────────────────────────────────────────────┘
```

**[通用产品]** The standard product architecture layers are:

```
┌─────────────────────────────────────────────┐
│  PRESENTATION LAYER                         │  ← UI components, API endpoints, CLI commands
├─────────────────────────────────────────────┤
│  FEATURE LAYER                              │  ← business logic, integrations, user-facing features
├─────────────────────────────────────────────┤
│  CORE LAYER                                 │  ← auth, data access, config, logging
├─────────────────────────────────────────────┤
│  FOUNDATION LAYER                           │  ← framework integration, ORM/database,
│                                             │    message queue, storage abstraction
├─────────────────────────────────────────────┤
│  INFRASTRUCTURE LAYER                       │  ← OS, cloud services, container runtime
└─────────────────────────────────────────────┘
```

**[通用场景]** For each module, ask:
- Which layer does it belong to?
- What are its module boundaries?
- What does it own exclusively? (data, state, behaviour)

Present the proposed layer assignment and ask for approval before proceeding to
the next section. Write the approved layer map immediately to the skeleton file.

**[游戏专用]** **Engine awareness check**: For each module assigned to the Core and Foundation
layers, flag if it touches a HIGH or MEDIUM risk engine domain. Show the relevant
engine reference excerpt inline.

**[通用产品]** **Stack awareness check**: For each module assigned to the Core and Foundation
layers, flag if it touches a HIGH or MEDIUM risk stack domain. Show the relevant
stack reference excerpt inline.

---

## Phase 2: Module Ownership Map

For each module defined in Phase 1, define ownership:

- **Owns**: what data and state this module is solely responsible for
- **Exposes**: what other modules may read or call
- **Consumes**: what it reads from other modules
- **Technology APIs used**: **[游戏专用]** which specific engine classes/nodes/signals this module
  calls directly (with version and risk level noted). **[通用产品]** which specific framework
  classes/decorators/middleware this module uses directly (with version and risk level noted).

Format as a table per layer, then as an ASCII dependency diagram.

**[游戏专用]** **Engine awareness check**: For every engine API listed, verify against the
relevant module reference doc. If an API is post-cutoff, flag it:

```
⚠️  [ClassName.method()] — Godot 4.6 (post-cutoff, HIGH risk)
    Verified against: docs/engine-reference/godot/modules/[domain].md
    Behaviour confirmed: [yes / NEEDS VERIFICATION]
```

**[通用产品]** **Stack awareness check**: For every framework API listed, verify against the
relevant module reference doc. If an API is post-cutoff, flag it:

```
⚠️  [ClassName.method()] — Django 5.2 (post-cutoff, HIGH risk)
    Verified against: docs/reference/django/modules/[domain].md
    Behaviour confirmed: [yes / NEEDS VERIFICATION]
```

Get user approval on the ownership map before writing.

---

## Phase 3: Data Flow

Define how data moves between modules during key scenarios.

**[游戏专用]** Cover at minimum these game data flows:

1. **Frame update path**: Input → Core systems → State → Rendering
2. **Event/signal path**: How systems communicate without tight coupling
3. **Save/load path**: What state is serialised, which module owns serialisation
4. **Initialisation order**: Which modules must boot before others

**[通用产品]** Cover at minimum these product data flows:

1. **Request/response path**: Request → Middleware → Business logic → Response
2. **Message queue/event path**: How modules communicate asynchronously without tight coupling
3. **Persistence path**: Unit of work → Repository → Database (what state is persisted, which module owns the schema)
4. **Startup order**: Config load → Database connection → Route registration → Server listen

**[通用场景]** Use ASCII sequence diagrams where helpful. For each data flow:
- Name the data being transferred
- Identify the producer and consumer
- State whether this is synchronous call, signal/event/message, or shared state
- Flag any data flows that cross thread/process boundaries

Get user approval per scenario before writing.

---

## Phase 4: API Boundaries

Define the public contracts between modules. For each boundary:

- What is the interface a module exposes to the rest of the system?
- What are the entry points (functions/signals/properties)?
- What invariants must callers respect?
- What must the module guarantee to callers?

Write in pseudocode or the project's actual language (from technical preferences).
These become the contracts programmers implement against.

**[游戏专用]** **Engine awareness check**: If any interface uses engine-specific types (e.g.
`Node`, `Resource`, `Signal` in Godot), flag the version and verify the type
exists and has not changed signature in the target engine version.

**[通用产品]** **Stack awareness check**: If any interface uses framework-specific types (e.g.
`Request`, `Response`, `Middleware` in FastAPI/Django), flag the version and verify the type
exists and has not changed signature in the target stack version.

---

## Phase 5: ADR Audit + Traceability Check

Review all existing ADRs from Phase 0c against both the architecture built in
Phases 1-4 AND the Technical Requirements Baseline from Phase 0b.

### ADR Quality Check

For each ADR:
- [ ] **[游戏专用]** Does it have an Engine Compatibility section? **[通用产品]** Does it have a Stack Compatibility section?
- [ ] Is the technology version recorded?
- [ ] Are post-cutoff APIs flagged?
- [ ] Does it have a "CDD Requirements Addressed" section?
- [ ] Does it conflict with the layer/ownership decisions made in this session?
- [ ] Is it still valid for the pinned version?

| ADR | Technology Compat | Version | CDD Linkage | Conflicts | Valid |
|-----|-------------------|---------|-------------|-----------|-------|
| ADR-0001: [title] | ✅/❌ | ✅/❌ | ✅/❌ | None/[conflict] | ✅/⚠️ |

### Traceability Coverage Check

Map every requirement from the Technical Requirements Baseline to existing ADRs.
For each requirement, check if any ADR's "CDD Requirements Addressed" section
or decision text covers it:

| Req ID | Requirement | ADR Coverage | Status |
|--------|-------------|--------------|--------|
| TR-combat-001 | Hitbox detection per-frame | ADR-0003 | ✅ |
| TR-combat-002 | Combo state machine | — | ❌ GAP |

Count: X covered, Y gaps. For each gap, it becomes a **Required New ADR**.

### Required New ADRs

List all decisions made during this architecture session (Phases 1-4) that do
not yet have a corresponding ADR, PLUS all uncovered Technical Requirements.
Group by layer — Foundation first:

**Foundation Layer (must create before any coding):**
- `/architecture-decision [title]` → covers: TR-[id], TR-[id]

**Core Layer:**
- `/architecture-decision [title]` → covers: TR-[id]

---

## Phase 6: Missing ADR List

Based on the full architecture, produce a complete list of ADRs that should exist
but don't yet. Group by priority:

**Must have before coding starts (Foundation & Core decisions):**
- [e.g. "Scene management and scene loading strategy"]
- [e.g. "Event bus vs direct signal architecture"]

**Should have before the relevant system is built:**
- [e.g. "Inventory serialisation format"]

**Can defer to implementation:**
- [e.g. "Specific shader technique for water"]

---

## Phase 7: Write the Master Architecture Document

Once all sections are approved, write the complete document to
`docs/architecture/architecture.md`.

Ask: "May I write the master architecture document to `docs/architecture/architecture.md`?"

The document structure:

```markdown
# [Project Name] — Master Architecture

## Document Status
- Version: [N]
- Last Updated: [date]
- **[游戏专用]** Engine: [name + version]
- **[通用产品]** Stack: [language] + [framework] [version]
- CDDs Covered: [list]
- ADRs Referenced: [list]

## Technology Knowledge Gap Summary
[Condensed from Phase 0d inventory — HIGH/MEDIUM risk domains and their implications]

## Module Layer Map
[From Phase 1]

## Module Ownership
[From Phase 2]

## Data Flow
[From Phase 3]

## API Boundaries
[From Phase 4]

## ADR Audit
[From Phase 5]

## Required ADRs
[From Phase 6]

## Architecture Principles
[3-5 key principles that govern all technical decisions for this project,
derived from the concept document, CDDs, and technical preferences]

## Open Questions
[Decisions deferred — must be resolved before the relevant layer is built]
```

---

## Phase 7b: Technical Director Sign-Off + Lead Programmer Feasibility Review

After writing the master architecture document, perform an explicit sign-off before handoff.

**Step 1 — Technical Director self-review** (this skill runs as technical-director):

Apply gate **TD-ARCHITECTURE** (`standards/director-gates.md`) as a self-review. Check all four criteria from that gate definition against the completed document.

**Review mode check** — apply before spawning LP-FEASIBILITY:
- `solo` → skip. Note: "LP-FEASIBILITY skipped — Solo mode." Proceed to Phase 8 handoff.
- `lean` → skip (not a PHASE-GATE). Note: "LP-FEASIBILITY skipped — Lean mode." Proceed to Phase 8 handoff.
- `full` → spawn as normal.

**Step 2 — Spawn `lead-programmer` via Task using gate LP-FEASIBILITY (`standards/director-gates.md`):**

Pass: architecture document path, technical requirements baseline summary, ADR list.

**Step 3 — Present both assessments to the user:**

Show the Technical Director assessment and Lead Programmer verdict side by side.

Use `AskUserQuestion` — "Technical Director and Lead Programmer have reviewed the architecture. How would you like to proceed?"
Options: `Accept — proceed to handoff` / `Revise flagged items first` / `Discuss specific concerns`

**Step 4 — Record sign-off in the architecture document:**

Update the Document Status section:
```
- Technical Director Sign-Off: [date] — APPROVED / APPROVED WITH CONDITIONS
- Lead Programmer Feasibility: FEASIBLE / CONCERNS ACCEPTED / REVISED
```

Ask: "May I update the Document Status section in `docs/architecture/architecture.md` with the sign-off?"

---

## Phase 8: Handoff

After writing the document, provide a clear handoff:

1. **Run these ADRs next** (from Phase 6, prioritised): list the top 3
2. **Gate check**: "The master architecture document is complete. Run `/gate-check pre-production` when all required ADRs are also written."
3. **Update session state**: Write a summary to `production/session-state/active.md`

---

## Collaborative Protocol

This skill follows the collaborative design principle at every phase:

1. **Load context silently** — do not narrate file reads
2. **Present findings** — show the knowledge gap inventory and layer proposals
3. **Ask before deciding** — present options for each architectural choice
4. **Get approval before writing** — each phase section is written only after
   user approves the content
5. **Incremental writing** — write each approved section immediately; do not
   accumulate everything and write at the end. This survives session crashes.

Never make a binding architectural decision without user input. If the user is
unsure, present 2-4 options with pros/cons before asking them to decide.

---

## Recommended Next Steps

- Run `/architecture-decision [title]` for each required ADR listed in Phase 6 — Foundation layer ADRs first
- Run `/create-control-manifest` once the required ADRs are written to produce the layer rules manifest
- Run `/gate-check pre-production` when all required ADRs are written and the architecture is signed off
