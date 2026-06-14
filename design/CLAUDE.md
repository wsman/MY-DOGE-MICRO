# Design Directory

When authoring or editing files in this directory, follow these standards.

## CDD Files (`design/cdd/`)

First identify the CDD domain:
- **Game** CDDs usually sit beside `design/cdd/game-concept.md` and describe
  mechanics, systems, levels, economy, narrative, UI/HUD, or player-facing
  behavior.
- **Product** CDDs usually sit beside `design/cdd/product-concept.md` and
  describe API, CLI, web/app, library, data, migration, service, or operational
  workflows.

Every **Game** CDD must include all **8 required sections** in this order:
1. Overview — one-paragraph summary
2. Player Fantasy — intended feeling and experience
3. Detailed Rules — unambiguous mechanics
4. Formulas — all math defined with variables
5. Edge Cases — unusual situations handled
6. Dependencies — other systems listed
7. Tuning Knobs — configurable values identified
8. Acceptance Criteria — testable success conditions

Every **Product** CDD must include the equivalent **8 required sections**:
1. Overview — one-paragraph summary of the module or workflow
2. User Promise / JTBD — what the user is trying to accomplish
3. Detailed Behavior — API, CLI, UI, data, library, or integration behavior
4. Contracts / Data Model — schemas, inputs, outputs, errors, exit codes, migrations
5. Edge Cases — invalid input, permissions, retries, partial failure, rollback
6. Dependencies — upstream/downstream modules, services, packages, docs
7. Configuration Knobs — environment variables, feature flags, limits, defaults
8. Acceptance Criteria — contract, workflow, migration, docs, observability checks

**File naming:** `[system-or-module-slug].md` (e.g. `movement-system.md`,
`combat-system.md`, `imports-api.md`, `reporting-cli.md`)

**Module index:** `design/cdd/module-index.md` — update when adding a new Game
system or Product module CDD.

**Design order:** Foundation → Core → Feature → Presentation → Polish

**Validation:** Run `/design-review [path]` after authoring any CDD.
Run `/review-all-gdds` after completing a set of related CDDs.

## Quick Specs (`design/quick-specs/`)

Lightweight specs for tuning changes, minor mechanics, or balance adjustments.
For Product projects, also use quick specs for small API response changes, CLI
flag behavior, config defaults, copy/help text, docs-only updates, or isolated
workflow adjustments. Use `/quick-design` to author.

## UX Specs (`design/ux/`)

- Per-screen specs: `design/ux/[screen-name].md`
- HUD design: `design/ux/hud.md`
- Interaction pattern library: `design/ux/interaction-patterns.md`
- Accessibility requirements: `design/ux/accessibility-requirements.md`
- Product workflow specs: `design/ux/[workflow-name].md`
- Product API/CLI consumer journey specs: `design/ux/[surface]-journey.md`

Use `/ux-design` to author. Validate with `/ux-review` before passing Game
UI/HUD work or Product web/API/CLI workflow work to `/team-ui`.
