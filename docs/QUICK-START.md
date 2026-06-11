# Constitution Driven Development — Quick Start Guide

## What Is This?

This is a complete Claude Code agent architecture supporting both **game development**
and **general product development** (web apps, CLI tools, APIs, data pipelines).

It organizes 53 specialized AI agents into a studio hierarchy that mirrors
real development teams, with defined responsibilities, delegation rules, and
coordination protocols.

**Game projects**: engine-specialist agents for Godot, Unity, and Unreal — each with
dedicated sub-specialists for major engine subsystems. Design agents and templates are
grounded in established game design theory (MDA Framework, Self-Determination Theory,
Flow State, Bartle Player Types).

**Product projects**: language-specialist agents (Python, TypeScript, Rust, Go) with
stack-aware architecture, testing, and deployment workflows. Design agents and
templates are grounded in product development theory (JTBD, user psychology,
action-first design).

Use whichever agent set matches your project.

## The Project Brain

`/constitute` creates or refreshes `memory_bank/`, the project brain and
governance control plane for the workspace.

| Layer | What it answers |
|-------|-----------------|
| **T0 Core** | What is legally true now? Current laws, phase, release state, and amendments. |
| **T1 Axioms** | What context supports those laws? Technical, architecture, UX, QA, behavior, and module context. |
| **T2 Execution** | What should happen next? Workflow contract, generated mirrors, and current roadmap. |
| **T3 Archive** | What evidence proves past decisions? Gate, review, QA, story, sprint, milestone, and release indexes. |

Agents and slash commands do not replace this memory. They maintain it while
detailed work stays in `design/`, `docs/`, `workflow/`, `templates/`,
`standards/`, and `production/`.
When approved artifacts record `PASS/FAIL`, `APPROVED/REJECTED`, `GO/NO-GO`,
`PROCEED/PIVOT/KILL`, `CUT/KEEP/DEFER`, or `RELEASE/HOLD` decisions, the owning
workflow also updates T1, T0, or a T3 index.

Every slash command includes a local `User Guide` block for when to use it,
inputs, outputs, memory-bank writes, and recommended next steps. Recommended
next steps are not automatic execution; run the next command only after the
user chooses to proceed.

CDD's own cross-project skill testing standards live in `skill_testing/`.
The memory-bank T2 mount is documented at
`memory_bank/t2_execution/skill_testing/README.md`. Approved `/skill-test`
reports and `/skill-improve` records live in
`memory_bank/t3_archive/skill_testing/`.

## How to Use

### 1. Understand the Hierarchy

There are three tiers of agents:

- **Tier 1 (Opus)**: Directors who make high-level decisions
  - `creative-director` -- vision and creative conflict resolution
  - `technical-director` -- architecture and technology decisions
  - `producer` -- scheduling, coordination, and risk management

- **Tier 2 (Sonnet)**: Department leads who own their domain
  - `game-designer`, `lead-programmer`, `art-director`, `audio-director`,
    `narrative-director`, `qa-lead`, `release-manager`, `localization-lead`

- **Tier 3 (Sonnet/Haiku)**: Specialists who execute within their domain
  - Designers, programmers, artists, writers, testers, engineers

### 2. Pick the Right Agent for the Job

Ask yourself: "What department would handle this in a real studio?"

| I need to... | Use this agent |
|-------------|---------------|
| Design a new mechanic | `game-designer` |
| Design an API endpoint or CLI command | `lead-programmer` or `ux-designer` |
| Write combat code | `gameplay-programmer` |
| Write API/backend code | `lead-programmer` + language specialist |
| Create a shader | `technical-artist` |
| Architect a database schema | `lead-programmer` |
| Design a user workflow | `ux-designer` |
| Review code quality | `lead-programmer` (via `/code-review`) |
| Write dialogue | `writer` |
| Plan the next sprint | `producer` |
| Review code quality | `lead-programmer` |
| Write test cases | `qa-tester` |
| Design a level | `level-designer` |
| Fix a performance problem | `performance-analyst` |
| Set up CI/CD | `devops-engineer` |
| Design a loot table | `economy-designer` |
| Resolve a creative conflict | `creative-director` |
| Make an architecture decision | `technical-director` |
| Manage a release | `release-manager` |
| Prepare strings for translation | `localization-lead` |
| Test a mechanic idea quickly | `prototyper` |
| Review code for security issues | `security-engineer` |
| Check accessibility compliance | `accessibility-specialist` |
| Get Unreal Engine advice | `unreal-specialist` |
| Get Unity advice | `unity-specialist` |
| Get Godot advice | `godot-specialist` |
| Design GAS abilities/effects | `ue-gas-specialist` |
| Define BP/C++ boundaries | `ue-blueprint-specialist` |
| Implement UE replication | `ue-replication-specialist` |
| Build UMG/CommonUI widgets | `ue-umg-specialist` |
| Design DOTS/ECS architecture | `unity-dots-specialist` |
| Write Unity shaders/VFX | `unity-shader-specialist` |
| Manage Addressable assets | `unity-addressables-specialist` |
| Build UI Toolkit/UGUI screens | `unity-ui-specialist` |
| Write idiomatic GDScript | `godot-gdscript-specialist` |
| Create Godot shaders | `godot-shader-specialist` |
| Build GDExtension modules | `godot-gdextension-specialist` |
| Plan live events and seasons | `live-ops-designer` |
| Write patch notes for players | `community-manager` |
| Brainstorm a new game idea | Use `/brainstorm` skill |

### 3. Use Slash Commands for Common Tasks

| Command | What it does |
|---------|-------------|
| `/constitute` | Creates or refreshes `memory_bank/` T0-T3 governance, establishes governing principles, and routes to the right workflow |
| `/constitute-check` | Audits T0-T3 memory health and recommends migration steps for older projects |
| `/help` | Context-aware "what do I do next?" — reads your current phase and artifacts |
| `/cdd-status` | Generate `production/project-roadmap.md` and update the T2 roadmap mirror when `memory_bank/` exists |
| `/project-stage-detect` | Analyze project state, detect stage, identify gaps |
| `/setup-engine` | Configure engine + version for games, or language/framework stack for products; populate reference docs |
| `/adopt` | Brownfield audit and migration plan for existing projects |
| `/brainstorm` | Guided concept ideation from scratch: game concepts or product concepts |
| `/map-systems` | Decompose concept into systems, map dependencies, guide per-system CDDs |
| `/design-system` | Guided, section-by-section CDD authoring for a game system or product module |
| `/quick-design` | Lightweight spec for small changes — tuning, tweaks, minor additions |
| `/review-all-gdds` | Cross-CDD consistency review; game design theory for games, workflow/value coherence for products |
| `/propagate-design-change` | Find ADRs and stories affected by a CDD change |
| `/ux-design` | Author UX specs (screen/flow, HUD, interaction patterns) |
| `/ux-review` | Validate UX specs for accessibility and CDD alignment |
| `/create-architecture` | Master architecture document for game systems and product modules |
| `/architecture-decision` | Creates an ADR |
| `/architecture-review` | Validate all ADRs, dependency ordering, CDD traceability |
| `/create-control-manifest` | Flat programmer rules sheet from Accepted ADRs |
| `/create-epics` | Translate CDDs + ADRs into epics (one per architectural module) |
| `/create-stories` | Break a single epic into implementable story files |
| `/dev-story` | Read a story and implement it — routes to the correct programmer agent |
| `/sprint-plan` | Creates or updates sprint plans |
| `/sprint-status` | Quick 30-line sprint snapshot |
| `/story-readiness` | Validate a story is implementation-ready before pickup |
| `/story-done` | End-of-story completion review — verifies acceptance criteria |
| `/estimate` | Produces structured effort estimates |
| `/design-review` | Reviews a design document |
| `/code-review` | Reviews code for quality and architecture |
| `/balance-check` | Game balance formulas/economy; product quotas, rate limits, pricing tiers, permissions, and workflow friction |
| `/asset-audit` | Game asset compliance; product build artifacts, API schemas, docs assets, release bundles |
| `/content-audit` | CDD-specified content vs. implemented — find gaps |
| `/scope-check` | Detect scope creep against plan |
| `/perf-profile` | Performance profiling and bottleneck ID |
| `/tech-debt` | Scan, track, and prioritize tech debt |
| `/gate-check` | Validate phase readiness under governed advisory policy: PASS, CONCERNS with risk note, or FAIL with explicit override |
| `/consistency-check` | Scan all CDDs for cross-document inconsistencies (conflicting stats, names, rules) |
| `/reverse-document` | Generate design/architecture docs from existing code |
| `/milestone-review` | Reviews milestone progress |
| `/retrospective` | Runs sprint/milestone retrospective |
| `/bug-report` | Structured bug report creation |
| `/playtest-report` | Game playtest report; product user-test / workflow validation report |
| `/onboard` | Generates onboarding docs for a role |
| `/release-checklist` | Validates pre-release checklist |
| `/launch-checklist` | Complete launch readiness validation |
| `/changelog` | Generates changelog from git history |
| `/patch-notes` | Generate game player-facing patch notes or product developer/user-facing release notes |
| `/hotfix` | Emergency fix with audit trail |
| `/prototype` | Scaffolds a throwaway prototype |
| `/localize` | Localization scan, extract, validate |
| `/team-combat` | Game combat feature squad; product critical-workflow/API/CLI feature squad |
| `/team-narrative` | Game narrative/worldbuilding squad; product content/onboarding/docs narrative squad |
| `/team-ui` | Game UI/HUD squad; product web UI, CLI interaction, or API consumer journey squad |
| `/team-release` | Game release squad; product deployment/release squad |
| `/team-polish` | Game polish pass; product UX/API/CLI/docs/reliability polish pass |
| `/team-audio` | Game audio squad; product notification/status feedback and accessibility signal squad |
| `/team-level` | Game level/area squad; product workflow/module area squad |
| `/team-live-ops` | Game live-ops squad; product lifecycle/feature flag/analytics operations squad |
| `/team-qa` | Game QA/playtest squad; product contract/integration/migration/user-test QA squad |
| `/qa-plan` | Generate a QA test plan for a sprint or feature |
| `/bug-triage` | Re-prioritize open bugs, assign to sprints, surface systemic trends |
| `/smoke-check` | Run critical path smoke test gate before QA hand-off (PASS/FAIL) |
| `/soak-test` | Game extended play-session soak test; product endurance/load/reliability soak protocol |
| `/regression-suite` | Map coverage to CDD critical paths, flag gaps, maintain regression suite |
| `/test-setup` | Scaffold the required Technical Setup test baseline: `tests/unit/`, `tests/integration/`, `.github/workflows/tests.yml`, and one runnable example test |
| `/test-helpers` | Optional enhancement after the baseline: game engine-specific or product language/stack-specific fixtures, factories, mocks, and helper libraries |
| `/test-flakiness` | Detect flaky tests from CI history, flag for quarantine or fix |
| `/test-evidence-review` | Quality review of test files and manual evidence — ADEQUATE/INCOMPLETE/MISSING |
| `/skill-test` | Validate skill files with the T2 spec catalog and write approved T3 evidence (static / spec / category / audit) |

### 4. Use Templates for New Documents

Templates are in `templates/`:

- `constitution-design-document.md` -- game-specific CDD reference for mechanics and systems, including Player Fantasy, Game Feel, and playtest acceptance
- `product-concept.md` -- for initial general product concepts, user journeys, MVP scope, and adoption risks
- `game-design-document.md` -- historical GDD / game-specific reference template
- `architecture-decision-record.md` -- for technical decisions
- `architecture-traceability.md` -- maps CDD requirements to ADRs to story IDs
- `risk-register-entry.md` -- for new risks
- `surface-profile.md` -- for product surface and N/A applicability decisions
- `narrative-character-sheet.md` -- for new characters
- `test-plan.md` -- for feature test plans
- `sprint-plan.md` -- for sprint planning
- `milestone-definition.md` -- for new milestones
- `level-design-document.md` -- for new levels
- `game-pillars.md` -- game-specific core design pillars
- `art-bible.md` -- for visual style reference
- `style-guide.md` -- for product brand, docs imagery, screenshots, diagrams, and release material standards
- `design-system.md` -- for UI-heavy product component rules and implementation handoff
- `technical-design-document.md` -- for per-system technical designs
- `post-mortem.md` -- for project/milestone retrospectives
- `sound-bible.md` -- for audio style reference
- `release-checklist-template.md` -- for platform release checklists
- `changelog-template.md` -- for game player-facing patch notes and product changelog/release categories
- `release-notes.md` -- for player-facing release notes
- `incident-response.md` -- for live incident response playbooks
- `game-concept.md` -- for initial game concepts (MDA, SDT, Flow, Bartle)
- `pitch-document.md` -- for pitching the game to stakeholders
- `economy-model.md` -- for virtual economy design (sink/faucet model)
- `faction-design.md` -- for faction identity, lore, and gameplay role
- `module-index.md` -- for systems/modules decomposition and dependency mapping
- `t0/` -- legacy T0 constitutional memory bank templates
- `t1/` -- legacy T1 context and pattern memory bank templates
- `memory-bank/` -- T0-T3 governance control-plane templates for new projects, including cross-project skill testing assets
- `project-stage-report.md` -- for project stage detection output
- `design-doc-from-implementation.md` -- for reverse-documenting existing code into CDDs
- `architecture-doc-from-code.md` -- for reverse-documenting code into architecture docs
- `concept-doc-from-prototype.md` -- for reverse-documenting prototypes into concept docs
- `ux-spec.md` -- for per-screen UX specifications (layout zones, states, events)
- `hud-design.md` -- for whole-game HUD philosophy, zones, and element specs
- `accessibility-requirements.md` -- for project-wide accessibility tier and feature matrix
- `interaction-pattern-library.md` -- for standard UI controls and game-specific patterns
- `player-journey.md` -- for 6-phase emotional arc and retention hooks by time scale
- `difficulty-curve.md` -- for difficulty axes, onboarding ramp, and cross-system interactions
- `test-evidence.md` -- template for recording manual test evidence (screenshots, walkthrough notes)

Also in `templates/collaborative-protocols/` (used by agents, not typically edited directly):

- `design-agent-protocol.md` -- question-options-draft-approval cycle for design agents
- `implementation-agent-protocol.md` -- story pickup through /story-done cycle for programming agents
- `leadership-agent-protocol.md` -- cross-department delegation and escalation for director-tier agents

### 5. Follow the Coordination Rules

1. Work flows down the hierarchy: Directors -> Leads -> Specialists
2. Conflicts escalate up the hierarchy
3. Cross-department work is coordinated by the `producer`
4. Agents do not modify files outside their domain without delegation
5. All decisions are documented

## First Steps for a New Project

**Don't know where to begin?** Run `/constitute`. It asks where you are, what kind of project you're building, and routes you to the right workflow. No assumptions about your domain or experience level.

If you already know what you need, jump directly to the relevant path:

### Path A: "I have no idea what to build"

1. **Run `/constitute`** (or `/brainstorm open`) — guided onboarding:
   what you want to build, your constraints, your governing principles
   - Establishes your project constitution, then routes to concept exploration
   - For games: produces a game concept document and recommends an engine
2. **Validate the concept** — Run `/design-review` on your concept document
3. **Run the Concept gate** — `/gate-check concept`
4. **Decompose into systems** — Run `/map-systems` to map all systems and dependencies
5. **Design each system** — Run `/design-system [system-name]` (or `/map-systems next`)
   to write CDDs in dependency order
6. **Run the Systems Design gate** — `/review-all-gdds`, then `/gate-check systems-design`
7. **Create technology and architecture** — Run `/setup-engine`,
   `/create-architecture`, core ADRs, `/architecture-review`, and
   `/create-control-manifest`
8. **Commit accessibility and tests** — Create `design/accessibility-requirements.md`
   from `templates/accessibility-requirements.md`, run `/test-setup`,
   then run `/gate-check technical-setup`
9. **Design the core UX** — After the Technical Setup gate, run
   `/ux-design [core-screen-or-hud]`, then `/ux-review`
10. **Test the core loop** — Run `/prototype [core-mechanic]`
11. **Playtest it** — Run `/playtest-report` to validate the hypothesis
12. **Create epics and stories** — Run `/create-epics layer: foundation`, then
   `/create-stories [epic-slug]` for the first implementation epic
13. **Plan the first sprint** — Run `/sprint-plan new`, then `/story-readiness`
14. **Run the Pre-Production gate** — `/gate-check pre-production`
15. **Build sprint stories** — `/sprint-plan` -> `/story-readiness` ->
    `/dev-story` -> `/story-done`, then `/gate-check production`
16. **Polish and validate** — Run `/playtest-report` until 3 playtest reports
    exist, then `/team-polish` and `/gate-check polish`
17. **Release** — `/release-checklist` -> `/launch-checklist` -> `/team-release`

### Path B: "I know what I want to build"

If you already have a game concept and engine choice, you may record the engine
early, but normal gate order is still Concept → Systems Design → Technical
Setup:

1. **Validate the concept** — Run `/design-review` on your concept document
2. **Run the Concept gate** — `/gate-check concept`
3. **Decompose into systems** — Run `/map-systems` to enumerate systems and dependencies
4. **Design each system** — Run `/design-system [system-name]` for CDDs in dependency order
5. **Run the Systems Design gate** — `/review-all-gdds`, then `/gate-check systems-design`
6. **Set up the engine** — Run `/setup-engine [engine] [version]`
   (e.g., `/setup-engine godot 4.6`) — also creates technical preferences
7. **Create architecture and ADRs** — Run `/create-architecture`,
   `/architecture-decision`, `/architecture-review`, and `/create-control-manifest`
8. **Commit accessibility and tests** — Create `design/accessibility-requirements.md`
   from `templates/accessibility-requirements.md`, run `/test-setup`,
   then run `/gate-check technical-setup`
9. **Design and review the core UX** — After the Technical Setup gate, run
   `/ux-design [core-screen-or-hud]`, then `/ux-review`
10. **Prototype and playtest the core loop** — Run `/prototype [core-mechanic]`,
    then `/playtest-report`
11. **Create epics and stories** — Run `/create-epics layer: foundation`, then
   `/create-stories [epic-slug]`
12. **Plan the first sprint** — Run `/sprint-plan new`, then `/story-readiness`
13. **Run the Pre-Production gate** — `/gate-check pre-production`
14. **Build sprint stories** — `/sprint-plan` -> `/story-readiness` ->
    `/dev-story` -> `/story-done`, then `/gate-check production`
15. **Polish and validate** — Run `/playtest-report` until 3 playtest reports
    exist, then `/team-polish` and `/gate-check polish`
16. **Release** — `/release-checklist` -> `/launch-checklist` -> `/team-release`

### Path C: "I know the game but not the engine"

If you have a concept but don't know which engine fits:

1. **Run `/setup-engine`** with no arguments — it will ask about your game's
   needs (2D/3D, platforms, team size, language preferences) and recommend
   an engine based on your answers. This records the Technical Setup decision
   early; return to the Concept or Systems Design gate if those are not done.
2. Follow Path B from the current missing gate onward

### Path D: "I have an existing project"

If you have design docs, prototypes, or code already:

1. **Run `/constitute`** (or `/project-stage-detect`) — analyzes what exists,
   identifies gaps, establishes governance, and recommends next steps
2. **Run `/adopt`** if you have existing CDDs, ADRs, or stories — audits
   internal format compliance and builds a numbered migration plan to fill gaps
   without overwriting your existing work
3. **Configure engine/stack if needed** — Run `/setup-engine` if not yet configured
4. **Validate phase readiness** — Run `/gate-check` to see where you stand
5. **Plan the next sprint** — Run `/sprint-plan new`

---

## Product Quick-Start Paths `[通用产品]`

The paths above cover game projects. For product projects, use these equivalents:

### Product Path A: "I have no idea what to build"

1. **Run `/constitute`** (or `/brainstorm open`) — guided onboarding:
   choose product domain (API, CLI, web, data pipeline), establish principles
   - Produces a product concept document (JTBD, user psychology, MVP scope)
2. **Validate the concept** — Run `/design-review` on your product concept
3. **Run the Concept gate** — `/gate-check concept`
4. **Decompose into modules** — Run `/map-systems` to map all modules and dependencies
5. **Design each module** — Run `/design-system [module-name]` to write CDDs in dependency order
6. **Run the Specification gate** — `/review-all-gdds`, then `/gate-check systems-design`
7. **Create technology and architecture** — Run `/setup-engine`,
   `/create-architecture`, core ADRs, `/architecture-review`, and
   `/create-control-manifest`
8. **Commit accessibility and tests** — Create `design/accessibility-requirements.md`
   from `templates/accessibility-requirements.md`, run `/test-setup`,
   then run `/gate-check technical-setup`
9. **Design and review the core UX** — After the Technical Setup gate, run
   `/ux-design [core-workflow]`, then `/ux-review`
10. **Prototype the riskiest assumption** — Run `/prototype [core-workflow]`
    (API spike, CLI spike, data pipeline spike, or workflow prototype)
11. **Validate the workflow** — Run `/playtest-report` for product user-test or
    workflow validation evidence
12. **Create epics and stories** — Run `/create-epics layer: foundation`, then
    `/create-stories [epic-slug]`
13. **Plan the first sprint** — Run `/sprint-plan new`, then `/story-readiness`
14. **Run the Pre-Implementation gate** — `/gate-check pre-production`
15. **Build sprint stories** — `/sprint-plan` -> `/story-readiness` ->
    `/dev-story` -> `/story-done`, then `/gate-check production`
16. **Polish and validate** — Run `/playtest-report` for product validation
    until 3 user/workflow validation reports exist, then `/team-polish` and
    `/gate-check polish`
17. **Release** — `/release-checklist` -> `/launch-checklist` -> `/team-release`

### Product Path B: "I know what I want to build"

If you already have a product concept and stack choice, you may record the stack
early, but normal gate order is still Concept → Specification → Architecture:

1. **Validate the concept** — Run `/design-review` on your product concept
2. **Run the Concept gate** — `/gate-check concept`
3. **Decompose into modules** — Run `/map-systems` to enumerate modules and dependencies
4. **Design each module** — Run `/design-system [module-name]` for CDDs in dependency order
5. **Run the Specification gate** — `/review-all-gdds`, then `/gate-check systems-design`
6. **Set up the stack** — Run `/setup-engine [lang] [framework]`
   (e.g., `/setup-engine python 3.13 flask`) — also creates technical preferences
7. **Create architecture and ADRs** — Run `/create-architecture`,
   `/architecture-decision`, `/architecture-review`, and `/create-control-manifest`
8. **Commit accessibility and tests** — Create `design/accessibility-requirements.md`
   from `templates/accessibility-requirements.md`, run `/test-setup`,
   then run `/gate-check technical-setup`
9. **Design and review the core UX** — After the Technical Setup gate, run
   `/ux-design [core-workflow]`, then `/ux-review`
10. **Prototype and validate the core workflow** — Run `/prototype [core-workflow]`,
    then `/playtest-report` for product user-test or workflow validation evidence
11. **Create epics and stories** — Run `/create-epics layer: foundation`, then
    `/create-stories [epic-slug]`
12. **Plan the first sprint** — Run `/sprint-plan new`, then `/story-readiness`
13. **Run the Pre-Implementation gate** — `/gate-check pre-production`
14. **Build sprint stories** — `/sprint-plan` -> `/story-readiness` ->
    `/dev-story` -> `/story-done`, then `/gate-check production`
15. **Polish and validate** — Run `/playtest-report` for product validation
    until 3 user/workflow validation reports exist, then `/team-polish` and
    `/gate-check polish`
16. **Release** — `/release-checklist` -> `/launch-checklist` -> `/team-release`

### Product Path C: "I know the product but not the stack"

If you have a concept but don't know which stack fits:

1. **Run `/setup-engine`** with no arguments — it will ask about your product's
   needs (API/CLI/web, scale expectations, team language preferences) and recommend
   a stack based on your answers. This records the Architecture decision early;
   return to the Concept or Specification gate if those are not done.
2. Follow Product Path B from the current missing gate onward

### Product Path D: Shared

Product Path D is identical to the shared Path D above — `/constitute` or
`/project-stage-detect` handles both game and product projects.

## File Structure Reference

```
CLAUDE.md                          -- Master config (read this first, ~60 lines)
AGENTS.md                          -- Codex/agent adapter config
workflow/
  workflow-catalog.yaml            -- 7-phase pipeline definition (read by /help)
  generated/                       -- Generated gate and workflow views
templates/                         -- 80 document templates (canonical document and memory-bank templates)
standards/                         -- Shared technical, coding, coordination, and context standards
skill_testing/                     -- Cross-project skill/agent testing catalog, specs, rubric
docs/
  QUICK-START.md                   -- This file
  USER-MANUAL.md                   -- Practical operating manual
  reference/                       -- Shared reference docs for agents, skills, hooks, rules
.claude/
  settings.json                    -- Claude Code hooks and project settings
  agents/                          -- 53 Claude adapter agent definitions
  skills/                          -- 74 slash command definitions (Claude adapter copy)
  hooks/                           -- 12 hook scripts wired by settings.json
  rules/                           -- 16 path-specific rule files
  docs/quick-start.md              -- Claude adapter pointer to docs/QUICK-START.md
.agents/
  skills/                          -- Codex/agent adapter copy of slash commands
```

For the full user manual, see `docs/USER-MANUAL.md`. For the generated artifact
checklist by phase, see `docs/PHASE-CHECKLISTS.md`. For delivery validation, see
`docs/CUSTOMER-ACCEPTANCE.md`.
