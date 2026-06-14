# Constitution Driven Development -- Complete Workflow Guide

> **How to go from zero to a shipped game or product using Constitution Driven Development.**
>
> This guide walks you through every phase of game or product development using the
> 53-agent system, 74 slash commands, and 12 automated hooks. It assumes you
> have Claude Code installed and are working from the project root.
>
> The pipeline has 7 phases. Each phase has a formal gate (`/gate-check`)
> that must run before normal advancement. A FAIL verdict requires an explicit
> user override with a risk note before advancing. The authoritative phase
> sequence and gate policy are defined in `workflow/workflow-catalog.yaml`
> and read by `/help`.
>
> For a saved project progress dashboard, run `/cdd-status`. For the practical
> user manual, read `docs/USER-MANUAL.md`. For a generated artifact map by
> phase, read `docs/PHASE-CHECKLISTS.md`.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Phase 1: Concept](#phase-1-concept)
3. [Phase 2: Systems Design](#phase-2-systems-design)
4. [Phase 3: Technical Setup](#phase-3-technical-setup)
5. [Phase 4: Pre-Production](#phase-4-pre-production)
6. [Phase 5: Production](#phase-5-production)
7. [Phase 6: Polish](#phase-6-polish)
8. [Phase 7: Release](#phase-7-release)
9. [Cross-Cutting Concerns](#cross-cutting-concerns)
10. [Appendix A: Agent Quick-Reference](#appendix-a-agent-quick-reference)
11. [Appendix B: Slash Command Quick-Reference](#appendix-b-slash-command-quick-reference)
12. [Appendix C: Common Workflows](#appendix-c-common-workflows)

---

## Quick Start

### What You Need

Before you start, make sure you have:

- **Claude Code** installed and working
- **Git** with Git Bash (Windows) or standard terminal (Mac/Linux)
- **jq** (optional but recommended -- hooks fall back to `grep` if missing)
- **Python 3** (optional -- some hooks use it for JSON validation)

### Step 1: Clone and Open

```bash
git clone https://github.com/Negentropy-Laby/Constitution-Driven-Development.git my-project
cd my-project
```

### Step 2: Run /constitute

If this is your first session:

```
/constitute
```

This guided onboarding asks where you are and routes you to the right phase:

- **Path A** -- No idea yet: routes to `/brainstorm`
- **Path B** -- Vague idea: routes to `/brainstorm` with seed
- **Path C** -- Clear spec: either formalizes a constitution first and then
  routes to `/brainstorm [your spec]`, or writes a minimal concept and routes
  into the domain workflow
- **Path D1** -- Existing project, few artifacts: detects what exists and routes
  to the next missing step
- **Path D2** -- Existing project, CDDs/ADRs/source exist: offers audit,
  revision, `/project-stage-detect`, or `/constitute-check` as appropriate

### Step 3: Verify Hooks Are Working

Start a new Claude Code session. You should see output from the
`session-start.sh` hook:

```
=== Constitution Driven Development -- Session Context ===
Branch: main
Recent commits:
  abc1234 Initial commit
===================================
```

If you see this, hooks are working. If not, check `.claude/settings.json` to
make sure the hook paths are correct for your OS.

### Step 4: Ask for Help Anytime

At any point, run:

```
/help
```

This reads your current phase from `production/stage.txt`, checks which
artifacts exist, and tells you exactly what to do next. It distinguishes
between REQUIRED next steps and OPTIONAL opportunities.

### Step 5: Create Your Directory Structure

Directories are created as needed. The system expects this layout:

```
src/                  # Game source code or product source code
  core/               # Engine/framework code
  gameplay/           # Gameplay systems
  ai/                 # AI systems
  networking/         # Multiplayer code
  ui/                 # UI code
  api/                # Product API endpoints and schemas
  cli/                # Product CLI commands and terminal UX
  services/           # Product services, jobs, integrations
  app/ or web/        # Product UI surface
  data/               # Product data pipelines and transforms
  tools/              # Dev tools
assets/               # Game assets or product-facing assets/artifacts
  art/                # Sprites, models, textures
  audio/              # Music, SFX
  vfx/                # Particle effects
  shaders/            # Shader files
  data/               # JSON config/balance data
design/               # Design documents
  cdd/                # CDD design documents
  narrative/          # Story, lore, dialogue
  levels/             # Level design documents
  balance/            # Balance spreadsheets and data
  ux/                 # UX specifications
docs/                 # Technical documentation
  architecture/       # Architecture Decision Records
  api/                # API documentation
  engine-reference/   # Game engine reference snapshots
  reference/<stack>/  # Product stack/framework reference snapshots
  postmortems/        # Post-mortems
tests/                # Unit, integration, performance, playtest, contract, CLI, E2E, migration
prototypes/           # Throwaway prototypes
production/           # Sprint plans, milestones, releases
  sprints/
  milestones/
  releases/
  epics/              # Epic and story files (from /create-epics + /create-stories)
  playtests/          # Playtest reports
  session-state/      # Ephemeral session state (gitignored)
  session-logs/       # Session audit trail (gitignored)
```

> **Tip:** You do not need all of these on day one. Create directories as you
> reach the phase that needs them. The important thing is to follow this
> structure when you do create them, because the **rules system** and imported
> directory guidance apply standards based on file paths. Code in
> `src/gameplay/` gets gameplay rules, `src/api/` gets contract/API guidance,
> `src/cli/` gets command/exit-code guidance, and so on.

---

## Phase 1: Concept

### What Happens in This Phase

You go from "no idea" or "vague idea" to a structured concept document.
For games, that means Game pillars, Player Fantasy, and player journey. For
products, that means Product principles, user promise, JTBD, user journey, and
MVP workflow. This is where you figure out **what** you are making and **why**.

### Phase 1 Pipeline

```
/brainstorm  -->  game-concept.md or product-concept.md  -->  /constitute
     |                              |                              |
     v                              v                              v
  10 concepts              Structured concept doc          Constitution + review mode
  MDA/JTBD analysis        with pillars/principles         derived from the concept
  motivation mapping                  |                              |
                                      v                              v
                              /design-review  -->  /gate-check concept
                                      |                 |
                                      v                 v
                              reviewed concept     ready for Systems Design
```

### Step 1.1: Brainstorm With /brainstorm

This is your starting point. Run the brainstorm skill:

```
/brainstorm
```

Or with a genre hint:

```
/brainstorm roguelike deckbuilder
```

**What happens:** The brainstorm skill guides you through a collaborative 6-phase
ideation process using professional studio techniques:

1. Asks about your interests, themes, and constraints
2. Generates 10 concept seeds with MDA (Mechanics, Dynamics, Aesthetics) analysis
3. You pick 2-3 favorites for deep analysis
4. Performs player motivation mapping and audience targeting
5. You choose the winning concept
6. Formalizes it into `design/cdd/game-concept.md` for game projects or
   `design/cdd/product-concept.md` for product projects

The concept document includes:

- Elevator pitch (one sentence)
- Core fantasy (what the player imagines themselves doing)
- MDA breakdown
- Target audience (Bartle types, demographics)
- Core loop diagram
- Unique selling proposition
- Comparable titles and differentiation
- Game pillars (3-5 non-negotiable design values)
- Anti-pillars (things the game intentionally avoids)

For product projects, the product concept uses equivalent sections such as core
promise, product principles, JTBD/user journey, personas, and MVP scope.

### Step 1.2: Return to /constitute

```
/constitute
```

After `/brainstorm` writes the concept document, return to `/constitute`.
It derives the project constitution from the concept, sets review mode if
needed, and hands off to the next stage-aware workflow step.

### Step 1.3: Review the Concept

```
/design-review design/cdd/game-concept.md
```

For product projects, use:

```
/design-review design/cdd/product-concept.md
```

Validates structure and completeness before you decompose the concept into
systems or modules.

Technology setup and module mapping are deliberately not Concept gate
requirements. `/setup-engine` is required in Technical Setup. `/map-systems` is
the first required Systems Design / Specification step.

### Phase 1 Gate

```
/gate-check concept
```

**Requirements to pass:**

- Constitution exists in `memory_bank/t0_core/basic_law_index.md`
- `design/cdd/game-concept.md` or `design/cdd/product-concept.md` exists
- Pillars/principles are defined in the concept document or companion file
- Concept review has been run and is not `MAJOR REVISION NEEDED`

**Verdict:** PASS / CONCERNS / FAIL. CONCERNS is passable with acknowledged
risks. FAIL leaves `production/stage.txt` unchanged unless the user records an
explicit override and risk note.

---

## Phase 2: Systems Design

### What Happens in This Phase

You create all the design documents that define how your game systems or
product modules work. Nothing gets coded yet -- this is pure design. Each
system/module identified in the module index gets its own CDD, authored section
by section, reviewed individually, and then all CDDs are cross-checked for
consistency.

### Phase 2 Pipeline

```
/map-systems  -->  module-index.md  -->  /map-systems next  -->  /design-system  -->  /design-review
      |                  |                     |                     |                     |
      v                  v                     v                     v                     v
 system/module      dependencies,         Picks next system    Section-by-section     Validates required
 decomposition      priorities, order     from module-index    CDD authoring          sections
                                                           (repeat for each MVP system)
                                                                 |
                                                                 v
/review-all-gdds
       |
       v
  Cross-CDD consistency + design theory review
  PASS / CONCERNS / FAIL
```

### Step 2.1: Map Systems or Modules

Before writing individual CDDs, enumerate all the systems or modules your
project needs:

```
/map-systems
```

This creates `design/cdd/module-index.md` -- a master tracking document that:

- **Game**: lists every system your game needs (combat, movement, UI, AI,
  economy, levels, narrative, audio, etc.)
- **Product**: lists every module or workflow your product needs (API surface,
  CLI commands, web/app screens, services, data pipelines, migrations,
  permissions, docs, observability, release workflow, etc.)
- Maps dependencies between systems
- Assigns priority tiers:
  - **Game**: MVP, Vertical Slice, Alpha, Full Vision
  - **Product**: MVP Workflow, Internal Beta, Public Beta, GA, Full Vision
- Determines design order (Foundation > Core > Feature > Presentation > Polish)

### Step 2.2: Author System CDDs

Design each system or module in dependency order using the guided workflow:

```
/map-systems next
```

This picks the highest-priority undesigned system/module and hands off to
`/design-system`, which guides you through creating its CDD section by section.

You can also design a specific system or module directly:

```
/design-system combat-system
/design-system payments-api
```

**What /design-system does:**

1. Reads your concept, module index, and any upstream/downstream CDDs
   - **Game**: reads Game concept, Game pillars, Player Fantasy, systems index,
     and upstream/downstream game CDDs
   - **Product**: reads Product concept, Product principles, user promise, JTBD,
     workflow map, module index, stack reference, and upstream/downstream
     product CDDs
2. Runs a Technical Feasibility Pre-Check (domain mapping + feasibility brief)
3. Walks you through each required CDD section one at a time
4. Each section follows: Context > Questions > Options > Decision > Draft > Approval > Write
5. Each section is written to file immediately after approval (survives crashes)
6. Flags conflicts with existing approved CDDs
7. Routes to specialist agents per category (systems-designer for math,
   economy-designer for economy, narrative-director for story systems,
   lead-programmer and language specialists for product contracts/modules)

**The 8 required Game CDD sections:**

| # | Section | What Goes Here |
|---|---------|---------------|
| 1 | **Overview** | One-paragraph summary of the system |
| 2 | **Player Fantasy** | What the player imagines/feels when using this system |
| 3 | **Detailed Rules** | Unambiguous mechanical rules |
| 4 | **Formulas** | Every calculation, with variable definitions and ranges |
| 5 | **Edge Cases** | What happens in weird situations? Explicitly resolved. |
| 6 | **Dependencies** | What other systems this connects to (bidirectional) |
| 7 | **Tuning Knobs** | Which values designers can safely change, with safe ranges |
| 8 | **Acceptance Criteria** | How do you test that this works? Specific, measurable. |

Plus a **Game Feel** section: feel reference, input responsiveness (ms/frames),
animation feel targets (startup/active/recovery), impact moments, weight profile.

**The equivalent Product CDD sections:**

| # | Section | What Goes Here |
|---|---------|---------------|
| 1 | **Overview** | One-paragraph summary of the module, workflow, or capability |
| 2 | **User Promise / JTBD** | What the user is trying to accomplish and what the product must reliably do |
| 3 | **Detailed Behavior** | API, CLI, web/app, library, data, or integration behavior in precise terms |
| 4 | **Contracts / Data Model** | Schemas, inputs, outputs, errors, exit codes, state transitions, migrations |
| 5 | **Edge Cases** | Invalid input, permissions, retries, partial failure, concurrency, data drift, rollback |
| 6 | **Dependencies** | Upstream/downstream modules, services, packages, docs, and operational constraints |
| 7 | **Configuration Knobs** | Environment variables, feature flags, limits, defaults, and safe ranges |
| 8 | **Acceptance Criteria** | Contract tests, workflow checks, migration safety, docs, observability, release checks |

Plus a **Workflow Validation** section: primary user path, alternate paths,
known failure states, recovery behavior, support burden, and evidence required
before implementation.

### Step 2.2: Review Each CDD

Before the next system starts, validate the current one:

```
/design-review design/cdd/combat-system.md
```

Checks all required sections for completeness, formula/contract clarity, edge
case resolution, bidirectional dependencies, and testable acceptance criteria.
For games, it checks Player Fantasy, Game Feel, formulas, tuning knobs, and
playtestable criteria. For products, it checks user promise, JTBD alignment,
API/CLI/web/data contracts, permissions, configuration, migration behavior,
observability, documentation, and workflow validation.

**Verdict:** APPROVED / NEEDS REVISION / MAJOR REVISION. Only APPROVED CDDs
should proceed.

### Step 2.3: Small Changes Without Full CDDs

For tuning changes, small additions, or tweaks that do not warrant a full CDD:

```
/quick-design "add 10% damage bonus for flanking attacks"
/quick-design "add --json output mode to the import CLI"
```

This creates a lightweight spec in `design/quick-specs/` instead of a full
CDD. Use it for game tuning, number changes, and small additions, or for
product-scoped changes such as CLI flag behavior, API response shape tweaks,
small workflow copy changes, config defaults, docs-only feature notes, or
single-table migration adjustments.

### Step 2.4: Cross-CDD Consistency Review

After all MVP system CDDs are approved individually:

```
/review-all-gdds
```

This reads ALL CDDs simultaneously and runs two analysis phases:

**Phase 1 -- Cross-CDD Consistency:**
- Dependency bidirectionality (A references B, does B reference A?)
- Rule contradictions between systems
- Stale references to renamed or removed systems
- Ownership conflicts (two systems claiming the same responsibility)
- Formula range compatibility (does System A's output fit System B's input?)
- Acceptance criteria cross-check

**Phase 2 -- Design Theory (Game Design Holism):**
- Competing progression loops (do two systems fight for the same reward space?)
- Cognitive load (more than 4 active systems at once?)
- Dominant strategies (one approach that makes all others irrelevant)
- Economic loop analysis (sources and sinks balanced?)
- Difficulty curve consistency across systems
- Pillar alignment and anti-pillar violations
- Player fantasy coherence

**Product Phase 2 -- Product Coherence and Contract Review:**
- Product principle and user promise alignment
- JTBD and workflow continuity across modules
- API, CLI, UI, data, and migration contract compatibility
- Permission, privacy, security, and error-state coverage
- Configuration and environment boundary clarity
- Documentation, observability, rollback, and support readiness
- MVP workflow scope vs. implementation/story scope

**Output:** `design/cdd/cross-review-[date].md` with a verdict.

### Step 2.5: Narrative Design (If Applicable)

If your game has story, lore, or dialogue, this is when you build it:

1. **World-building** -- Use `world-builder` to define factions, history,
   geography, and rules of your world
2. **Story structure** -- Use `narrative-director` to design story arcs,
   character arcs, and narrative beats
3. **Character sheets** -- Use the `narrative-character-sheet.md` template

### Phase 2 Gate

```
/gate-check systems-design
```

**Requirements to pass:**

- All MVP systems/modules in `module-index.md` have `Status: Approved`
- Each MVP system/module has a reviewed CDD
- Cross-CDD review report exists (`design/cdd/cross-review-*.md`)
  with verdict of PASS or CONCERNS (not FAIL)

---

## Phase 3: Technical Setup

### What Happens in This Phase

You make key technical decisions, document them as Architecture Decision Records
(ADRs), validate them through review, produce a control manifest that gives
programmers flat, actionable rules, and establish the test baseline. You also
establish UX foundations.

### Phase 3 Pipeline

```
 /setup-engine  -->  /create-architecture  -->  /architecture-decision (x N)  -->  /architecture-review
       |                    |                          |                                   |
       v                    v                          v                                   v
 technical prefs      Master architecture       Per-decision ADRs              Validates completeness,
 engine/stack refs    document covering         in docs/architecture/          dependency ordering,
                      all systems/modules       adr-*.md                       engine/stack compatibility
                                                                                         |
                                                                                         v
                                                                            /create-control-manifest
                                                                                         |
                                                                                         v
                                                                            Flat programmer rules
                                                                            docs/architecture/
                                                                            control-manifest.md
        Also in this phase:
        -------------------
        Accessibility requirements doc
        /test-setup baseline
```

### Step 3.1: Choose Your Engine or Stack

```
/setup-engine
```

Or with a specific engine:

```
/setup-engine godot 4.6
```

Or with a specific product stack:

```
/setup-engine python 3.13 flask
```

`/setup-engine` populates `standards/technical-preferences.md`, pins the
engine or stack version, routes specialist agents, records naming conventions
and performance budgets, and creates version reference docs when the selected
technology is knowledge-risky.

### Step 3.2: Master Architecture Document

```
/create-architecture
```

Creates the overarching architecture document in `docs/architecture/architecture.md`
covering system boundaries, data flow, and integration points. For games, this
includes engine architecture, scene/entity ownership, asset loading, runtime
performance budgets, and platform constraints. For products, this includes API
or CLI boundaries, service/module ownership, data model, persistence,
integration points, deployment topology, observability, and rollback strategy.

### Step 3.2: Architecture Decision Records (ADRs)

For each significant technical decision:

```
/architecture-decision "State Machine vs Behavior Tree for NPC AI"
/architecture-decision "REST endpoint vs background job for CSV imports"
```

**What happens:** The skill guides you through creating an ADR with:
- Context and decision drivers
- All options with pros/cons and engine or stack compatibility
- Chosen option with rationale
- Consequences (positive, negative, risks)
- Dependencies (Depends On, Enables, Blocks, Ordering Note)
- CDD Requirements Addressed (linked by TR-ID)

ADRs go through a lifecycle: Proposed > Accepted > Superseded/Deprecated.

**Minimum 3 Foundation-layer ADRs are required** before the gate check.

**Retrofitting existing ADRs:** If you already have ADRs from a brownfield
project:

```
/architecture-decision retrofit docs/architecture/adr-005.md
```

This detects which template sections are missing and adds only those, never
overwriting existing content.

### Step 3.3: Architecture Review

```
/architecture-review
```

Validates all ADRs together:
- Topological sort of ADR dependencies (detects cycles)
- Engine or stack compatibility verification
- CDD Revision Flags (flags CDD sections that need updates based on ADR choices)
- TR-ID registry maintenance (`docs/architecture/tr-registry.yaml`)

### Step 3.4: Control Manifest

```
/create-control-manifest
```

Takes all Accepted ADRs and produces a flat programmer rules sheet:

```
docs/architecture/control-manifest.md
```

This contains Required patterns, Forbidden patterns, and Guardrails organized
by code layer. Game manifests cover gameplay, engine, AI, networking, UI, asset,
and platform rules. Product manifests cover API/CLI/web/data/service boundaries,
schema and error contracts, migration rules, config, observability, deployment,
and security constraints. Stories created later embed the manifest version date
so staleness can be detected.

### Step 3.5: Accessibility Requirements

Create `design/accessibility-requirements.md` using the template. Commit to a
tier (Basic / Standard / Comprehensive / Exemplary) and fill the 4-axis feature
matrix (visual, motor, cognitive, auditory). Game projects cover controls,
HUD/menu readability, subtitles/audio cues, difficulty assists, and platform
input methods. Product projects cover keyboard navigation, screen reader
behavior, form/API/CLI error clarity, reduced motion, docs accessibility,
workflow recovery, and supported device/browser/terminal contexts.

This document is required in Phase 3 because UX specs (written in Phase 4)
reference this tier — it is a design prerequisite, not a UX deliverable.

### Step 3.6: Test Framework Baseline

```
/test-setup
```

Scaffolds the minimum test baseline before Pre-Production:

- `tests/unit/`
- `tests/integration/`
- `.github/workflows/tests.yml`
- At least one example test file proving the selected runner works

This baseline is required at the Technical Setup gate. `/test-helpers` remains
optional and should not be treated as a blocker; use it later for fixtures,
factories, mocks, engine-specific helpers, or stack-specific helper libraries.

### Phase 3 Gate

```
/gate-check technical-setup
```

**Requirements to pass:**

- `docs/architecture/architecture.md` exists
- At least 3 ADRs exist and are Accepted
- Architecture review report exists
- `docs/architecture/control-manifest.md` exists
- `design/accessibility-requirements.md` exists
- Test baseline exists: `tests/unit/`, `tests/integration/`,
  `.github/workflows/tests.yml`, and at least one example test file
- Game projects have current `docs/engine-reference/<engine>/` references when
  engine APIs are used; Product projects have current `docs/reference/<stack>/`
  references when framework, package, SDK, database, or cloud APIs are used

---

## Phase 4: Pre-Production

### What Happens in This Phase

You create UX specs for key screens/workflows, prototype risky mechanics or
technical approaches, turn design documents into implementable stories, plan
your first sprint, and validate the first end-to-end slice. For games, that is
a Vertical Slice that proves the core loop is fun. For products, that is an MVP
workflow validation that proves the user can complete the core job with the
intended API/CLI/web/data path.

### Phase 4 Pipeline

```
/ux-design  -->  /prototype  -->  /create-epics  -->  /create-stories  -->  /sprint-plan
    |                |                  |                   |                       |
    v                v                  v                   v                       v
  UX specs       Throwaway       Epic files in       Story files in          First sprint with
  design/ux/     prototypes      production/         production/             prioritized stories
                 in prototypes/  epics/*/EPIC.md     epics/*/story-*.md      production/sprints/
                                 (one per module)    (one per behaviour)     sprint-*.md
    |                                                      |
    v                                                      v
 /ux-review                                          /story-readiness
 (validates specs                                    (validates each story
  before epics)                                       before pickup)
                         |
                         v
                    Vertical Slice or MVP Workflow Validation
                    (Game: playable build, 1 unguided session)
                    (Product: end-to-end workflow, contract/docs evidence)
                         |
                         v
                    /gate-check pre-production
                    (normal advancement before implementation)
```

### Step 4.1: UX Specs for Key Screens

Before writing epics, create UX specs so that story authors know what screens,
flows, commands, endpoints, or user interactions exist and what they must
support.

**UX Specs:**

```
/ux-design main-menu
/ux-design core-gameplay-hud
/ux-design onboarding-workflow
/ux-design import-cli-flow
/ux-design api-consumer-journey
```

Three modes: screen/flow, HUD, and interaction patterns. Output goes to
`design/ux/`. Game specs include player need, layout zones, HUD/screen states,
interaction map, data requirements, events fired, accessibility, localization.
Product specs include user need/JTBD, workflow steps, API/CLI/web states,
input/output contracts, error and recovery paths, docs/help text, accessibility,
localization, observability, and support handoff.

Reads your `accessibility-requirements.md` (written in Phase 3) and your
input method config from `technical-preferences.md` to drive accessibility
and input coverage checks — no need to re-specify them per screen.

> **Tip:** `/design-system` emits a 📌 UX Flag for every system with UI
> requirements. Use those flags as a checklist for which screens need specs.

**Interaction Pattern Library:**

```
/ux-design interaction-patterns
```

Create `design/ux/interaction-patterns.md` — 16 standard controls plus
game-specific patterns (inventory slot, ability icon, HUD bar, dialogue box,
etc.) and product-specific patterns (forms, tables, command help, API error
payloads, empty states, import/export flows, auth prompts, destructive actions)
with animation, sound, copy, accessibility, and feedback standards.

For product projects, design artifacts are split by surface:
- `design/brand/style-guide.md` is optional for brand tone, docs imagery,
  screenshots, diagrams, and public release material standards.
- `design/ux/interaction-patterns.md` is required when the product has an API,
  CLI, SDK/library, web UI, admin console, docs-driven consumer journey, or other
  user/integrator-facing surface.
- `design/design-system.md` is required only for UI-heavy products such as web
  apps, desktop/mobile apps, admin consoles, and component-heavy docs sites.

**UX Review:**

```
/ux-review all
```

Validates UX specs for CDD alignment and accessibility tier compliance.
For games, it checks player journey, HUD/menu clarity, input mapping, and Game
Feel implications. For products, it checks user workflow continuity, API/CLI
consumer expectations, copy/error clarity, docs handoff, and stack/UI
constraints. Produces APPROVED / NEEDS REVISION / MAJOR REVISION NEEDED verdict.

### Step 4.2: Prototype Risky Mechanics

Not everything needs a prototype. Prototype when:
- **Game**: a mechanic is novel and you are not sure it is fun
- **Game**: two design options both seem viable and you need to feel the difference
- **Product**: a workflow, API shape, CLI interaction, data import, migration,
  or integration is risky and you need evidence before committing
- **Either**: a technical approach is risky and you are not sure it is feasible

```
/prototype "grappling hook movement with momentum"
/prototype "CSV import dry-run workflow with invalid row recovery"
```

**What happens:** The skill collaborates with you to define a hypothesis,
success criteria, and minimal scope. The `prototyper` agent works in an
isolated git worktree (`isolation: worktree`) so throwaway code never
pollutes `src/`.

**Key rule:** The `prototype-code` rule intentionally relaxes coding standards --
hardcoded values OK, no tests required -- but a README with hypothesis and
findings is mandatory.

### Step 4.3: Create Epics and Stories From Design Artifacts

```
/create-epics layer: foundation
/create-stories [epic-slug]   # repeat for each epic
/create-epics layer: core
/create-stories [epic-slug]   # repeat for each core epic
```

`/create-epics` reads your CDDs, ADRs, and architecture to define epic scope —
one epic per architectural module. Then `/create-stories` breaks each epic into
implementable story files in `production/epics/[slug]/`. Each story embeds:
- CDD requirement references (TR-IDs, not quoted text -- stays fresh)
- ADR references (only from Accepted ADRs; Proposed ADRs cause `Status: Blocked`)
- Control manifest version date (for staleness detection)
- Engine- or stack-specific implementation notes
- Acceptance criteria from the CDD

Once stories exist, do not implement them in Phase 4. Run `/story-readiness`
first, validate the Vertical Slice or MVP workflow, then run
`/gate-check pre-production`. Formal story implementation begins in Phase 5
after the gate passes or the user records an explicit override with risk note.

### Step 4.4: Validate Stories Before Pickup

```
/story-readiness production/epics/combat/story-001-damage-calc.md
```

Checks: Design completeness, Architecture coverage, Scope clarity, Definition
of Done. Verdict: READY / NEEDS WORK / BLOCKED.

### Step 4.5: Effort Estimation

```
/estimate production/epics/combat/story-001-damage-calc.md
```

Provides effort estimates with risk assessment.

### Step 4.6: Plan Your First Sprint

```
/sprint-plan new
```

**What happens:** The `producer` agent collaborates on sprint planning:
- Asks for sprint goal and available time
- Breaks the goal into Must Have / Should Have / Nice to Have tasks
- Identifies risks and blockers
- Creates `production/sprints/sprint-01.md`
- Populates `production/sprint-status.yaml` (machine-readable story tracking)

### Step 4.7: Vertical Slice or MVP Workflow Validation

Before normal advancement to Production/Implementation, build and validate the
first end-to-end slice:

**Game vertical slice:**

- One complete end-to-end core loop, playable from start to finish
- Representative quality (not placeholder everything)
- Played unguided in at least 1 session
- Playtest report written (`/playtest-report`)
- Cumulative 3-session validation is required later in Polish / Verification

**Product MVP workflow validation:**

- One complete core user job from start to finish (API/CLI/web/app/data path)
- At least 1 unguided core-workflow session
- Contract evidence for public APIs, CLI flags/output, schemas, or migrations
- Failure-state evidence for invalid input, auth/permission, partial failure,
  rollback/dry-run, retry, or data recovery paths
- Docs/help evidence for the path a real user or integrator would follow
- Validation report written in `production/qa/evidence/user-tests/` or QA
  evidence captured in the matching `production/qa/evidence/` subdirectory

This is a governed advisory gate condition: `/gate-check` returns FAIL if a game
has not been played unguided or a product has not completed an end-to-end
workflow validation with evidence. FAIL does not update `production/stage.txt`
unless the user records an explicit override and risk note.

### Phase 4 Gate

```
/gate-check pre-production
```

**Requirements to pass:**

- At least 1 UX spec reviewed in `design/ux/`
- UX review completed (APPROVED or NEEDS REVISION with documented risks)
- At least 1 prototype with README
- Story files exist in `production/epics/[epic-slug]/story-NNN-[slug].md`
- At least 1 sprint plan exists
- Game: at least 1 playtest report exists with at least 1 unguided
  vertical-slice session
- Product: at least 1 workflow validation report or QA evidence bundle exists
  for the MVP path, including at least 1 unguided core-workflow session plus
  contract/docs/error-state evidence

---

## Phase 5: Production

### What Happens in This Phase

This is the core production/implementation loop. You work in sprints (typically
1-2 weeks), implementing features story by story, tracking progress, and
closing stories through a structured completion review. This phase repeats
until your game is content-complete or your product MVP/GA scope is
implementation-complete.

### Phase 5 Pipeline (Per Sprint)

```
/sprint-plan new  -->  /story-readiness  -->  /dev-story  -->  /story-done
       |                     |                    |                |
       v                     v                    v                v
  Sprint created       Story validated      Code written     8-phase review:
  sprint-status.yaml   READY verdict        Tests pass       verify criteria,
  populated                                                  check deviations,
                                                             update story status
       |
       |  (repeat per story until sprint complete)
       v
  /sprint-status  (quick 30-line snapshot anytime)
  /scope-check    (if scope is growing)
  /retrospective  (at sprint end)
```

### Step 5.1: The Story Lifecycle

The production phase centers on the **story lifecycle**:

```
/story-readiness  -->  /dev-story  -->  /story-done  -->  next story
```

**1. Story Readiness:** Before picking up a story, validate it:

```
/story-readiness production/epics/combat/story-001-damage-calc.md
```

This checks design completeness, architecture coverage, ADR status (blocks
if ADR is still Proposed), control manifest version (warns if stale), and
scope clarity. For games, it confirms CDD/player-facing behavior and playtest
criteria. For products, it confirms API/CLI/web/data contracts, config,
migration, docs, observability, and rollback criteria. Verdict: READY / NEEDS
WORK / BLOCKED.

**2. Implementation:** Work with the appropriate agents.

```
/dev-story production/epics/combat/story-001-damage-calc.md
```

`/dev-story [story-path]` implements one READY story and routes automatically
to the correct programmer or specialist agent for the project domain.

**Game implementation routing:**

- `gameplay-programmer` for gameplay systems
- `engine-programmer` for core engine work
- `ai-programmer` for AI behavior
- `network-programmer` for multiplayer
- `ui-programmer` for UI code
- `tools-programmer` for dev tools

**Product implementation routing:**

- `lead-programmer` for module ownership, architecture fit, and code review
- `python-specialist`, `typescript-specialist`, `rust-specialist`, or
  `go-specialist` for stack-specific implementation
- `ux-designer` for web/app workflows, CLI interaction, API consumer journeys,
  copy/error states, and docs handoff
- `security-engineer` for auth, permissions, secrets, input validation, and
  dependency risk
- `devops-engineer` for CI/CD, deployment, migrations, rollback, and monitoring
- `analytics-engineer` for events, telemetry, data pipelines, and observability

All agents follow the collaborative protocol: they read the design doc, ask
clarifying questions, present architectural options, get your approval, then
implement.

**3. Story Completion:** When a story is done:

```
/story-done production/epics/combat/story-001-damage-calc.md
```

This runs an 8-phase completion review:
1. Find and read the story file
2. Load referenced CDD, ADRs, and control manifest
3. Verify acceptance criteria (auto-checkable, manual, deferred)
4. Check for CDD/ADR deviations (BLOCKING / ADVISORY / OUT OF SCOPE)
5. Prompt for code review
6. Generate completion report (COMPLETE / COMPLETE WITH NOTES / BLOCKED)
7. Update story `Status: Complete` with completion notes
8. Surface the next ready story

Tech debt discovered during review is logged to `docs/tech-debt-register.md`.

### Step 5.2: Sprint Tracking

Check progress anytime:

```
/sprint-status
```

Quick 30-line snapshot reading from `production/sprint-status.yaml`.

If scope is growing:

```
/scope-check production/sprints/sprint-03.md
```

This compares current scope against the original plan and flags scope increase,
recommends cuts.

### Step 5.3: Content Tracking

```
/content-audit
```

Compares CDD-specified content against what has been implemented. Catches
content gaps early. Game audits compare assets, levels, narrative, systems, and
balance data. Product audits compare API endpoints, CLI commands, schemas,
docs/help text, migrations, config, package/build artifacts, and workflow
coverage against Product CDDs.

### Step 5.4: Design Change Propagation

When a CDD changes after stories have been created:

```
/propagate-design-change design/cdd/combat-system.md
```

Git-diffs the CDD, finds affected ADRs, generates an impact report, and
walks you through Superseded/update/keep decisions.

### Step 5.5: Multi-System Features (Team Orchestration)

For features spanning multiple domains, use team skills:

```
/team-combat "healing ability with HoT and cleanse"
/team-narrative "Act 2 story content"
/team-ui "inventory screen redesign"
/team-level "forest dungeon level"
/team-audio "combat audio pass"
/team-ui "admin dashboard import workflow"
/team-qa "release candidate API contract sweep"
```

Each team skill coordinates a 6-phase collaborative workflow:
1. **Design** -- Game: game-designer asks mechanic/player questions. Product:
   ux-designer/lead-programmer asks workflow, contract, and user promise questions.
2. **Architecture** -- lead-programmer proposes code structure and integration boundaries.
3. **Parallel Implementation** -- Game specialists or Product language/UX/security/devops specialists work simultaneously.
4. **Integration** -- Game: gameplay/engine/UI programmer wires systems together. Product: lead-programmer/language specialist wires API/CLI/web/data contracts and deployment paths.
5. **Validation** -- qa-tester runs against acceptance criteria, playtest evidence, contract tests, CLI tests, E2E workflow checks, or migration evidence.
6. **Report** -- coordinator summarizes status, risks, deviations, and next steps.

The orchestration is automated, but **decision points stay with you**.

### Step 5.6: Sprint Review and Next Sprint

At the end of a sprint:

```
/retrospective
```

Analyzes planned vs. completed, velocity, blockers, and actionable improvements.

Then plan the next sprint:

```
/sprint-plan new
```

### Step 5.7: Milestone Reviews

At milestone checkpoints:

```
/milestone-review "alpha"
```

Produces feature completeness, quality metrics, risk assessment, and go/no-go
recommendation.

### Phase 5 Gate

```
/gate-check production
```

**Requirements to pass:**

- All MVP stories complete
- Sprint and story implementation evidence is complete for the current core scope
- Story completion evidence covers acceptance criteria, CDD/ADR deviations, and review status
- Game: at least one vertical-slice playtest confirms the core loop is understandable and not blocked by confusion loops
- Product: MVP workflow validation evidence covers primary path, errors,
  permissions, docs/help, contracts, and operational readiness
- Product: no blocking contract, migration, security, deployment, or support gaps

Cumulative multi-session game playtest or product validation evidence belongs
to Phase 6 Polish / Verification.

---

## Phase 6: Polish

### What Happens in This Phase

Your game is feature-complete or your product scope is implementation-complete.
Now you make it release-ready. For games, this phase focuses on performance,
balance, accessibility, audio, visual polish, and playtesting. For products, it
focuses on performance, API/CLI ergonomics, workflow clarity, docs accuracy,
observability, reliability, accessibility, migration safety, and support
readiness.

### Phase 6 Pipeline

```
/perf-profile  -->  /balance-check  -->  /asset-audit  -->  /playtest-report or validation evidence
       |                  |                    |                    |
       v                  v                    v                    v
  Profile CPU/GPU,   Analyze formulas,    Verify naming,      Game: new player,
  runtime, memory,   contracts, config,   formats, sizes,     mid-game, difficulty
  database, network  and data for         schemas, docs       Product: workflow,
  bottlenecks        broken paths                             contract, docs evidence

  /tech-debt  -->  /team-polish
       |                |
       v                v
  Track and        Coordinated pass:
  prioritize       performance + art +
  debt items       audio + UX + QA
```

### Step 6.1: Performance Profiling

```
/perf-profile
```

Guides you through structured performance profiling:
- Establish targets (FPS/memory/platform for games; latency/throughput/memory,
  DB/query cost, startup time, binary size, or job duration for products)
- Identify bottlenecks ranked by impact
- Generate actionable optimization tasks with code locations and expected gains

### Step 6.2: Balance Analysis

```
/balance-check assets/data/combat_damage.json
```

Analyzes balance data for statistical outliers, broken progression curves,
degenerate strategies, and economy imbalances. For products, use the same
command to analyze pricing/usage limits, quotas, ranking/score formulas,
recommendation thresholds, risk scores, migration batch sizes, retry budgets,
or other product parameters for outliers, unsafe defaults, and evidence gaps.

### Step 6.3: Asset Audit

```
/asset-audit
```

Verifies naming conventions, file format standards, and size budgets across
all assets. For products, the audit includes API schemas, OpenAPI/SDK artifacts,
CLI help snapshots, docs assets, package/build output, migration files,
config examples, generated clients, release bundles, and data fixtures.

### Step 6.4: Playtesting or Product Validation Evidence

```
/playtest-report
```

Generates structured playtest reports. Three sessions are required, covering:
- New player experience
- Mid-game systems
- Difficulty curve

For product projects, capture equivalent validation evidence instead of game
playtests:
- New user / first-run workflow
- Power-user or mid-complexity workflow
- Failure/recovery path such as invalid input, permission error, migration
  rollback, API timeout, CLI misuse, or partial data failure

Store product validation reports in `production/qa/evidence/user-tests/` and
link contract, CLI, E2E, migration, docs, and
observability evidence.

### Step 6.5: Technical Debt Assessment

```
/tech-debt
```

Scans for TODO/FIXME/HACK comments, code duplication, overly complex functions,
missing tests, and outdated dependencies. Each item categorized and prioritized.

### Step 6.6: Coordinated Polish Pass

```
/team-polish "combat system"
```

Coordinates specialists in parallel:
1. Performance optimization (performance-analyst)
2. Game visual polish (technical-artist) or Product UI/docs polish (ux-designer)
3. Game audio polish (sound-designer) or Product notification/copy/error polish (ux-designer + localization-lead)
4. Game feel/juice (gameplay-programmer + technical-artist) or Product ergonomics/reliability polish (lead-programmer + language specialist + devops-engineer)

You set priorities; the team executes with your approval at each step.

### Step 6.7: Localization and Accessibility

```
/localize src/
```

Scans for hardcoded strings, concatenation that breaks translation, text that
does not account for expansion, and missing locale files.

Accessibility is audited against the tier committed in Phase 3's accessibility
requirements document.

### Phase 6 Gate

```
/gate-check polish
```

**Requirements to pass:**

- At least 3 playtest reports exist
- Coordinated polish pass completed (`/team-polish`)
- No blocking performance issues
- Accessibility tier requirements met
- Product projects may satisfy the validation evidence requirement with 3
  product workflow evidence reports covering first-run, core workflow, and
  failure/recovery path instead of game playtest reports
- Product projects have no blocking API/CLI contract, migration, docs,
  observability, reliability, security, or deployment-readiness issues

---

## Phase 7: Release

### What Happens in This Phase

Your game or product is polished, tested, and ready. Now you ship it.

### Phase 7 Pipeline

```
/release-checklist  -->  /launch-checklist  -->  /team-release
        |                       |                      |
        v                       v                      v
  Pre-release             Full cross-department    Coordinate:
  validation across       validation (Go/No-Go     build, QA sign-off,
  code, content,          per department)           deployment, launch
  store/legal or
  product ops/legal
                    Also: /changelog, /patch-notes, /hotfix
```

### Step 7.1: Release Checklist

```
/release-checklist v1.0.0
```

Generates a comprehensive pre-release checklist covering:
- Build verification (all platforms compile and run)
- Game certification requirements (platform-specific)
- Game store metadata (descriptions, screenshots, trailers)
- Product deployment target, package/release artifact, migration readiness,
  API/CLI compatibility, docs/help accuracy, monitoring, rollback, and support
  handoff
- Legal compliance (EULA, privacy policy, ratings)
- Save game compatibility or product data/migration compatibility
- Analytics verification

### Step 7.2: Launch Readiness (Full Validation)

```
/launch-checklist
```

Complete cross-department validation:

| Department | What Is Checked |
|-----------|---------------|
| **Engineering** | Build stability, crash rates, memory leaks, load times |
| **Design** | Game: feature completeness, tutorial flow, difficulty curve. Product: workflow completeness, user promise, JTBD, failure recovery |
| **Art** | Game: asset quality, missing textures, LOD levels. Product: UI visual quality, brand/style guide, docs images |
| **Audio** | Game: missing sounds, mixing levels, spatial audio. Product: notifications, audio cues if applicable |
| **QA** | Open bug count by severity, regression suite pass rate |
| **Narrative** | Game: dialogue completeness, lore consistency, typos. Product: help text, release messaging, docs voice |
| **Localization** | All strings translated, no truncation, locale testing |
| **Accessibility** | Compliance checklist, assistive feature testing |
| **Store / Distribution** | Game: store metadata complete, screenshots approved, pricing set. Product: package registry, app store, deployment channel, installer, or API docs published |
| **Marketing** | Game: press kit ready, launch trailer, social media scheduled. Product: release announcement, changelog, migration guide, customer comms |
| **Community / Support** | Patch notes draft, FAQ prepared, support channels ready |
| **Infrastructure** | Servers scaled, CDN configured, monitoring active, rollout/rollback verified |
| **Legal** | EULA finalized, privacy policy, COPPA/GDPR compliance |

Each item gets a **Go / No-Go** status. All must be Go to ship.

### Step 7.3: Generate Player-Facing Content

```
/patch-notes v1.0.0
```

Generates player- or user-friendly patch notes from git history and sprint
data. For games, it translates developer language into player language. For
products, it translates implementation details into user-visible changes,
migration notes, API/CLI compatibility notes, deprecations, and operational
impact.

```
/changelog v1.0.0
```

Generates an internal changelog (more technical, for the team).

### Step 7.4: Coordinate the Release

```
/team-release
```

Coordinates release-manager, QA, and DevOps through:
1. Pre-release validation
2. Build management
3. Final QA sign-off
4. Deployment preparation, migration/rollback checks, and monitoring readiness
5. Go/No-Go decision

### Step 7.5: Ship

The `validate-push` hook will warn you when pushing to `main` or `develop`.
This is intentional -- release pushes should be deliberate:

```bash
git tag v1.0.0
git push origin main --tags
```

For product projects, also execute the release path defined by your stack:
package publish, deployment, migration apply, feature flag rollout, canary,
monitoring checks, and rollback plan verification.

### Step 7.6: Post-Launch

**Hotfix workflow** for critical production bugs:

```
/hotfix "Players losing save data when inventory exceeds 99 items"
/hotfix "API import endpoint returns 500 for malformed CSV rows"
```

Bypasses normal sprint processes with a full audit trail:
1. Creates a hotfix branch
2. Implements the fix
3. Ensures backport to development branch
4. Documents the incident, affected users, validation evidence, and rollback or
   mitigation status

**Post-mortem** after launch stabilizes:

```
Ask Claude to create a post-mortem using the template at
templates/post-mortem.md
```

---

## Cross-Cutting Concerns

These topics apply across all phases.

### Director Review Modes

Director gates are specialist agents that review your work at key workflow steps.
By default they run at every checkpoint. You can control how much review you get.

**Set your review intensity once during `/constitute`.** Saved to `production/review-mode.txt`.

| Mode | What runs | Best for |
|------|-----------|----------|
| `full` | All director gates at every step | New projects, learning the system |
| `lean` | Directors only at phase transitions (`/gate-check`) | Experienced devs |
| `solo` | No director reviews | Game jams, prototypes, maximum speed |

**Override for a single run** without changing your global setting:

```
/brainstorm space horror --review full
/architecture-decision --review solo
```

The `--review` flag works on all gate-using skills. Change the global mode at any
time by editing `production/review-mode.txt` directly or re-running `/constitute`.

Full gate definitions and check pattern: `standards/director-gates.md`

---

### The Collaboration Protocol

This system is **user-driven collaborative**, not autonomous.

**Pattern:** Question > Options > Decision > Draft > Approval

Every agent interaction follows this pattern:
1. Agent asks clarifying questions
2. Agent presents 2-4 options with trade-offs and reasoning
3. You decide
4. Agent drafts based on your decision
5. You review and refine
6. Agent asks "May I write this to [filepath]?" before writing

See `docs/COLLABORATIVE-DESIGN-PRINCIPLE.md` for the full protocol with
examples.

### The AskUserQuestion Tool

Agents use the `AskUserQuestion` tool for structured option presentation.
The pattern is Explain then Capture: full analysis in conversation text first,
then a clean UI picker for the decision. Use it for design choices,
architecture decisions, and strategic questions. Do not use it for open-ended
discovery questions or simple yes/no confirmations.

### Agent Coordination (3-Tier Hierarchy)

```
Tier 1 (Directors):    creative-director, technical-director, producer
                                          |
Tier 2 (Leads):        game-designer, lead-programmer, art-director,
                       audio-director, narrative-director, qa-lead,
                       release-manager, localization-lead
                                          |
Tier 3 (Specialists):  gameplay-programmer, engine-programmer,
                       ai-programmer, network-programmer, ui-programmer,
                       tools-programmer, systems-designer, level-designer,
                       economy-designer, world-builder, writer,
                       technical-artist, sound-designer, ux-designer,
                       qa-tester, performance-analyst, devops-engineer,
                       analytics-engineer, accessibility-specialist,
                       live-ops-designer, prototyper, security-engineer,
                       community-manager, python-specialist,
                       typescript-specialist, rust-specialist, go-specialist,
                       godot-specialist, godot-gdscript-specialist,
                       godot-csharp-specialist, godot-gdextension-specialist,
                       godot-shader-specialist, unity-specialist,
                       unity-dots-specialist, unity-shader-specialist,
                       unity-addressables-specialist, unity-ui-specialist,
                       unreal-specialist, ue-blueprint-specialist,
                       ue-gas-specialist, ue-replication-specialist,
                       ue-umg-specialist
```

**Coordination rules:**
- Vertical delegation: Directors > Leads > Specialists. Never skip tiers for
  complex decisions.
- Horizontal consultation: Agents at the same tier may consult each other but
  must not make binding decisions outside their domain.
- Conflict resolution: Design conflicts go to `creative-director`. Technical
  conflicts go to `technical-director`. Scope conflicts go to `producer`.
- No unilateral cross-domain changes.

### Automated Hooks (Safety Net)

The system has 12 hooks that run automatically:

| Hook | Trigger | What It Does |
|------|---------|-------------|
| `session-start.sh` | Session start | Shows branch, recent commits, detects active.md for recovery |
| `detect-gaps.sh` | Session start | Detects fresh projects (no engine, no concept) and suggests `/constitute` |
| `pre-compact.sh` | Before compaction | Dumps session state into conversation for auto-recovery |
| `post-compact.sh` | After compaction | Reminds Claude to restore session state from `active.md` |
| `notify.sh` | Notification event | Shows Windows toast notification via PowerShell |
| `validate-commit.sh` | Before commit | Checks for design doc references, valid JSON, no hardcoded values |
| `validate-push.sh` | Before push | Warns on pushes to main/develop |
| `validate-assets.sh` | Before commit | Checks asset naming and size |
| `validate-skill-change.sh` | Skill file written | Advises running `/skill-test` after `.claude/skills/` changes |
| `log-agent.sh` | Agent start | Logs agent invocations for audit trail |
| `log-agent-stop.sh` | Agent stop | Completes agent audit trail (start + stop) |
| `session-stop.sh` | Session end | Final session logging |

### Context Resilience

**Session state file:** `production/session-state/active.md` is a living
checkpoint. Update it after each significant milestone. After any disruption
(compaction, crash, `/clear`), read this file first.

**Incremental writing:** When creating multi-section documents, write each
section to file immediately after approval. This means completed sections
survive crashes and context compactions. Previous discussion about written
sections can be safely compacted.

**Automatic recovery:** The `session-start.sh` hook detects and previews
`active.md` automatically. The `pre-compact.sh` hook dumps state into the
conversation before compaction.

**Sprint status tracking:** `production/sprint-status.yaml` is the
machine-readable story tracker. Written by `/sprint-plan` (init) and
`/story-done` (status updates). Read by `/sprint-status`, `/help`, and
`/story-done` (next story). Eliminates fragile markdown scanning.

### Brownfield Adoption

For existing projects that already have some artifacts:

```
/adopt
```

Or targeted:

```
/adopt cdds
/adopt adrs
/adopt stories
/adopt infra
```

This audits existing artifacts for **format** (not existence), classifies gaps
as BLOCKING/HIGH/MEDIUM/LOW, builds an ordered migration plan, and writes
`docs/adoption-plan-[date].md`. Core principle: MIGRATION not REPLACEMENT --
it never regenerates existing work, only fills gaps.

Individual skills also support retrofit mode:

```
/design-system retrofit design/cdd/combat-system.md
/architecture-decision retrofit docs/architecture/adr-005.md
```

These detect which sections are present vs. missing and fill only the gaps.

### Gate System

Phase gates are formal checkpoints. Run `/gate-check` with the transition name:

```
/gate-check concept              # Concept -> Systems Design
/gate-check systems-design       # Systems Design -> Technical Setup
/gate-check technical-setup      # Technical Setup -> Pre-Production
/gate-check pre-production       # Pre-Production -> Production
/gate-check production           # Production -> Polish
/gate-check polish               # Polish -> Release
```

**Verdicts under governed advisory gate policy:**
- **PASS** -- all required artifacts and checks are satisfied; normal stage update is allowed after user confirmation.
- **CONCERNS** -- advancement is allowed only with an explicit risk note attached to the gate report.
- **FAIL** -- default behavior is no `production/stage.txt` update; advancement requires a user override and risk note.

When a gate allows advancement, `production/stage.txt` is updated after user
confirmation. The stage file controls the status line and `/help` behavior.

### Reverse Documentation

For code that exists without design docs (common after brownfield adoption):

```
/reverse-document src/gameplay/combat/
/reverse-document src/api/imports/
/reverse-document src/cli/
```

Reads existing code and generates CDD-format design documentation from it. Game
reverse-documentation captures mechanics, Player Fantasy implications,
formulas, tuning knobs, and playtest criteria. Product reverse-documentation
captures user promise, contracts, schemas, config, error states, migration
behavior, docs gaps, and verification evidence.

---

## Appendix A: Agent Quick-Reference

### "I need to do X -- which agent do I use?"

| I need to... | Agent | Tier |
|-------------|-------|------|
| Come up with a game idea | `/brainstorm` skill | -- |
| Come up with a product idea | `/brainstorm` skill | -- |
| Design a game mechanic | `game-designer` | 2 |
| Design a product workflow | `ux-designer` + `lead-programmer` | 2-3 |
| Design specific formulas/numbers | `systems-designer` | 3 |
| Design product limits, quotas, scoring, or pricing logic | `systems-designer` + `lead-programmer` | 2-3 |
| Design a game level | `level-designer` | 3 |
| Design loot tables / economy | `economy-designer` | 3 |
| Design a product data model or API contract | `lead-programmer` + language specialist | 2-3 |
| Build world lore | `world-builder` | 3 |
| Write dialogue | `writer` | 3 |
| Write product onboarding/docs/release copy | `writer` + `ux-designer` | 3 |
| Plan the story | `narrative-director` | 2 |
| Plan a sprint | `producer` | 1 |
| Make a creative decision | `creative-director` | 1 |
| Make a technical decision | `technical-director` | 1 |
| Implement gameplay code | `gameplay-programmer` | 3 |
| Implement core engine systems | `engine-programmer` | 3 |
| Implement API/backend code | `lead-programmer` + language specialist | 2-3 |
| Implement CLI code | `lead-programmer` + language specialist | 2-3 |
| Implement web/app product UI | `ui-programmer` or language specialist + `ux-designer` | 3 |
| Implement migrations or data pipelines | `lead-programmer` + language specialist + `devops-engineer` | 2-3 |
| Implement AI behavior | `ai-programmer` | 3 |
| Implement multiplayer | `network-programmer` | 3 |
| Implement UI | `ui-programmer` | 3 |
| Build dev tools | `tools-programmer` | 3 |
| Review code architecture | `lead-programmer` | 2 |
| Create shaders / VFX | `technical-artist` | 3 |
| Define visual style | `art-director` | 2 |
| Define audio style | `audio-director` | 2 |
| Design sound effects | `sound-designer` | 3 |
| Design UX flows | `ux-designer` | 3 |
| Write test cases | `qa-tester` | 3 |
| Plan test strategy | `qa-lead` | 2 |
| Profile performance | `performance-analyst` | 3 |
| Set up CI/CD | `devops-engineer` | 3 |
| Design analytics | `analytics-engineer` | 3 |
| Check accessibility | `accessibility-specialist` | 3 |
| Plan live operations | `live-ops-designer` | 3 |
| Manage a release | `release-manager` | 2 |
| Manage localization | `localization-lead` | 2 |
| Prototype quickly | `prototyper` | 3 |
| Audit security | `security-engineer` | 3 |
| Communicate with players or product users | `community-manager` | 3 |
| Python stack help | `python-specialist` | 3 |
| TypeScript stack help | `typescript-specialist` | 3 |
| Rust stack help | `rust-specialist` | 3 |
| Go stack help | `go-specialist` | 3 |
| Godot-specific help | `godot-specialist` | 3 |
| GDScript-specific help | `godot-gdscript-specialist` | 3 |
| Godot shader help | `godot-shader-specialist` | 3 |
| GDExtension modules | `godot-gdextension-specialist` | 3 |
| Unity-specific help | `unity-specialist` | 3 |
| Unity DOTS/ECS | `unity-dots-specialist` | 3 |
| Unity shaders/VFX | `unity-shader-specialist` | 3 |
| Unity Addressables | `unity-addressables-specialist` | 3 |
| Unity UI Toolkit | `unity-ui-specialist` | 3 |
| Unreal-specific help | `unreal-specialist` | 3 |
| Unreal GAS | `ue-gas-specialist` | 3 |
| Unreal Blueprints | `ue-blueprint-specialist` | 3 |
| Unreal replication | `ue-replication-specialist` | 3 |
| Unreal UMG/CommonUI | `ue-umg-specialist` | 3 |

### Agent Hierarchy

```
                    creative-director / technical-director / producer
                                         |
          ---------------------------------------------------------------
          |            |           |           |          |        |       |
    game-designer  lead-prog  art-dir  audio-dir  narr-dir  qa-lead  release-mgr
          |            |           |           |          |        |        |
     specialists  programmers  tech-art  snd-design  writer   qa-tester  devops
     (systems,    (gameplay,             (sound)     (world-  (perf,     (analytics,
      economy,     engine,                           builder)  access.)   security)
      level)       ai, net,
                   ui, tools)
```

**Escalation rule:** If two agents disagree, go up. Design conflicts go to
`creative-director`. Technical conflicts go to `technical-director`. Scope
conflicts go to `producer`.

---

## Appendix B: Slash Command Quick-Reference

### All 74 Commands by Category

#### Onboarding and Navigation (7)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/constitute` | CDD onboarding, routes to the right game or product workflow | Any (first session) |
| `/constitute-check` | Constitutional health audit for principles, active context, and project artifacts | Any |
| `/help` | Context-aware "what do I do next?" | Any |
| `/cdd-status` | Saved catalog-driven project dashboard and next-command roadmap | Any |
| `/project-stage-detect` | Full project audit to determine current phase | Any |
| `/setup-engine` | Configure game engine or product language/framework stack, pin version, set preferences | 3 |
| `/adopt` | Brownfield audit and migration plan | Any (existing projects) |

#### Concept and Systems Design (6)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/brainstorm` | Collaborative ideation with Game MDA/SDT or Product JTBD/user workflow analysis | 1 |
| `/map-systems` | Decompose concept into game systems or product modules index | 1-2 |
| `/design-system` | Guided section-by-section CDD authoring for a system or module | 2 |
| `/quick-design` | Lightweight Game tuning spec or Product API/CLI/web/workflow spec | 2+ |
| `/review-all-gdds` | Cross-CDD consistency and design theory/workflow-value review | 2 |
| `/propagate-design-change` | Find ADRs/stories affected by CDD changes | 5 |

#### Art, Assets, and Product Artifacts (3)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/art-bible` | Game art bible or Product brand style guide at `design/brand/style-guide.md` | 1-3 |
| `/asset-spec` | Game visual/audio/VFX asset specs or Product API/CLI/docs/config/migration/package artifact specs | 4 |
| `/asset-audit` | Game asset compliance or Product schema/build/docs/migration/config/package artifact audit | 6 |

#### UX and Interface (2)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/ux-design` | Author UX specs for game screens/HUD or product web/API/CLI workflows | 4 |
| `/ux-review` | Validate UX specs for accessibility and CDD alignment | 4 |

#### Architecture (4)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/create-architecture` | Master architecture document | 3 |
| `/architecture-decision` | Create or retrofit an ADR | 3 |
| `/architecture-review` | Validate all ADRs, dependency ordering | 3 |
| `/create-control-manifest` | Flat programmer rules from Accepted ADRs | 3 |

#### Stories and Sprints (8)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/create-epics` | Translate CDDs + ADRs into epics (one per module) | 4 |
| `/create-stories` | Break a single epic into story files | 4 |
| `/dev-story` | Implement a story and route to the correct programmer or language specialist | 5 |
| `/sprint-plan` | Create or manage sprint plans | 4-5 |
| `/sprint-status` | Quick 30-line sprint snapshot | 5 |
| `/story-readiness` | Validate story is implementation-ready | 4-5 |
| `/story-done` | 8-phase story completion review | 5 |
| `/estimate` | Effort estimation with risk assessment | 4-5 |

#### Reviews and Analysis (10)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/design-review` | Validate CDD against domain-appropriate section standard | 1-2 |
| `/code-review` | Architectural code review | 5+ |
| `/balance-check` | Game balance formula analysis or Product quotas/rate/pricing/permissions/workflow friction analysis | 5-6 |
| `/content-audit` | CDD-specified game content or Product API/CLI/web/data/docs surfaces vs. implementation | 5 |
| `/scope-check` | Scope creep detection | 5 |
| `/perf-profile` | Performance profiling workflow | 6 |
| `/tech-debt` | Tech debt scanning and prioritization | 6 |
| `/gate-check` | Formal phase gate with PASS/CONCERNS/FAIL | All transitions |
| `/consistency-check` | Cross-document consistency scan | 2+ |
| `/security-audit` | Game security surfaces or Product auth/API/secrets/dependency/data/deployment review | 5+ |

#### QA and Testing (10)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/qa-plan` | Generate QA test plan for a sprint or feature | 5 |
| `/smoke-check` | Critical path smoke test gate before QA hand-off | 5-6 |
| `/soak-test` | Game extended play-session soak or Product endurance/load/reliability soak protocol | 6 |
| `/regression-suite` | Map test coverage, identify fixed bugs lacking regression tests | 5-6 |
| `/test-setup` | Scaffold required test baseline and CI/CD pipeline for the game engine or product stack | 3 |
| `/test-helpers` | Optional engine- or language/stack-specific fixtures, factories, mocks, and helper libraries | 4-5 |
| `/test-evidence-review` | Quality review of test files and manual evidence | 5 |
| `/test-flakiness` | Detect non-deterministic tests from CI logs | 5-6 |
| `/skill-test` | Validate skill files for structural and behavioral correctness | Any |
| `/skill-improve` | Improve skill files while preserving Game content and adding Product parity | Any |

#### Production Management (6)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/milestone-review` | Milestone progress and go/no-go | 5 |
| `/retrospective` | Sprint retrospective analysis | 5 |
| `/bug-report` | Structured bug report creation | 5+ |
| `/bug-triage` | Re-evaluate open bugs for priority, severity, and owner | 5+ |
| `/reverse-document` | Generate design or architecture docs from existing implementation | Any |
| `/playtest-report` | Game playtest report or Product user/workflow validation report | 4-6 |

#### Release (6)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/release-checklist` | Pre-release validation | 7 |
| `/launch-checklist` | Full cross-department launch readiness | 7 |
| `/changelog` | Auto-generate internal changelog | 7 |
| `/patch-notes` | Player-facing patch notes or Product developer/user-facing release notes | 7 |
| `/hotfix` | Emergency fix workflow | 7+ |
| `/day-one-patch` | Post-launch first patch planning for Game or Product critical issues | 7+ |

#### Creative and Content (3)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/prototype` | Throwaway prototype in isolated worktree | 4 |
| `/onboard` | Onboard a new contributor, role, or agent | Any |
| `/localize` | String extraction and validation | 6-7 |

#### Team Orchestration (9)

| Command | Purpose | Phase |
|---------|---------|-------|
| `/team-combat` | Game combat squad or Product critical-workflow/API/CLI feature squad | 5 |
| `/team-narrative` | Game narrative/worldbuilding squad or Product content/onboarding/docs narrative squad | 5 |
| `/team-ui` | Game UI/HUD squad or Product web UI, CLI interaction, or API consumer journey squad | 5 |
| `/team-level` | Game level/area squad or Product workflow/module area squad | 5 |
| `/team-audio` | Game audio squad or Product notification/status feedback and accessibility signal squad | 5-6 |
| `/team-polish` | Game polish pass or Product UX/API/CLI/docs/reliability polish pass | 6 |
| `/team-release` | Game release/certification squad or Product deployment/release squad | 7 |
| `/team-live-ops` | Game live-ops squad or Product lifecycle/feature flag/analytics operations squad | 7+ |
| `/team-qa` | Game QA/playtest squad or Product contract/integration/migration/user-test QA squad | 6-7 |

---

## Appendix C: Common Workflows

### Workflow 1: "I just started and have no game or product idea"

```
1. /constitute (routes you based on where you are and what kind of project)
2. /brainstorm (collaborative ideation, pick a concept)
3. /design-review on concept doc
4. /gate-check concept (verify you're ready for Systems Design / Specification)
5. /map-systems (decompose concept into systems/modules with deps and priorities)
6. /design-system per system/module (guided CDD authoring)
7. /review-all-gdds, then /gate-check systems-design
8. /setup-engine + architecture + ADRs + test baseline
```

### Workflow 2: "I have designs and want to start coding"

```
1. /design-review on each CDD (make sure they're solid)
2. /review-all-gdds (cross-CDD consistency)
3. /gate-check systems-design
4. /create-architecture + /architecture-decision (per major decision)
5. /architecture-review
6. /create-control-manifest
7. /gate-check technical-setup
8. /create-epics layer: foundation + /create-stories [slug] (define epics, break into stories)
9. /sprint-plan new
10. /story-readiness -> implement -> /story-done (story lifecycle)
```

### Workflow 3: "I need to add a complex feature mid-production"

```
1. /design-system or /quick-design (depending on scope)
2. /design-review to validate
3. /propagate-design-change if modifying existing CDDs
4. /estimate for effort and risk
5. /team-combat, /team-narrative, /team-ui, /team-qa, etc. (appropriate team skill)
6. /story-done when complete
7. /balance-check if it affects game balance, product limits, quotas, pricing,
   ranking, workflow friction, or other tunable product behavior
```

### Workflow 4: "Something broke in production"

```
1. /hotfix "description of the issue"
2. Fix is implemented on hotfix branch
3. /code-review the fix
4. Run tests
5. /release-checklist for hotfix build
6. Deploy and backport
```

### Workflow 5: "I have an existing project and want to use this system"

```
1. /constitute (choose Path D -- existing work)
2. /project-stage-detect (determines current phase)
3. /adopt (audits existing artifacts, builds migration plan)
4. /design-system retrofit [path] (fill CDD gaps)
5. /architecture-decision retrofit [path] (fill ADR gaps)
6. /gate-check at appropriate transition
```

### Workflow 6: "Starting a new sprint"

```
1. /retrospective (review last sprint)
2. /sprint-plan new (create next sprint)
3. /scope-check (ensure scope is manageable)
4. /story-readiness per story before pickup
5. Implement stories
6. /story-done per completed story
7. /sprint-status for quick progress checks
```

### Workflow 7: "Shipping the game or product"

```
1. /gate-check polish (verify Polish phase is complete)
2. /tech-debt (decide what's acceptable at launch)
3. /localize (final localization pass)
4. /release-checklist v1.0.0
5. /launch-checklist (full cross-department validation)
6. /team-release (coordinate the release)
7. /patch-notes and /changelog
8. Game: ship store/platform build; Product: deploy/publish package, apply
   migrations or feature flags, verify monitoring and rollback path
9. /hotfix if anything breaks post-launch
10. Post-mortem after launch stabilizes
```

### Workflow 8: "I'm lost / don't know what to do next"

```
1. /help (reads your phase, checks artifacts, tells you what's next)
2. If /help doesn't help: /project-stage-detect (full audit)
3. If stage seems wrong: /gate-check at the transition you think you're at
```

---

## Tips for Getting the Most Out of the System

1. **Always start with design, then implement.** The agent system is built
   around the assumption that a design document exists before code is written.
   Agents reference CDDs constantly.

2. **Use team skills for cross-cutting features.** Do not try to manually
   coordinate 4 agents yourself -- let `/team-combat`, `/team-narrative`,
   etc. handle the orchestration.

3. **Trust the rules system.** When a rule flags something in your code, fix
   it. The rules encode hard-won game development wisdom (data-driven values,
   delta time, accessibility, etc.).

4. **Compact proactively.** At ~65-70% context usage, compact or `/clear`.
   The pre-compact hook saves your progress. Do not wait until you are at the
   limit.

5. **Use the right tier of agent.** Do not ask `creative-director` to write a
   shader. Do not ask `qa-tester` to make design decisions. The hierarchy
   exists for a reason.

6. **Run /help when uncertain.** It reads your actual project state and tells
   you the single most important next step.

7. **Run `/design-review` before handing designs to programmers.** This
   catches incomplete specs early, saving rework.

8. **Run `/code-review` after every major feature.** Catch architectural
   issues before they propagate.

9. **Prototype risky mechanics first.** A day of prototyping can save a week
   of production on a mechanic that does not work.

10. **Keep your sprint plans honest.** Use `/scope-check` regularly. Scope
    creep is the number one killer of indie games.

11. **Document decisions with ADRs.** Future-you will thank present-you for
    recording *why* things were built the way they were.

12. **Use the story lifecycle religiously.** `/story-readiness` before pickup,
    `/story-done` after completion. This catches deviations early and keeps
    the pipeline honest.

13. **Write to files early and often.** Incremental section writing means your
    design decisions survive crashes and compactions. The file is the memory,
    not the conversation.
