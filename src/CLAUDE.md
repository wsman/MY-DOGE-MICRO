# Source Directory

When writing or editing code in this directory, first identify whether the work
is for a **Game** project or a **Product** project, then apply the matching
standards below.

## Domain Detection

- **Game**: `design/cdd/game-concept.md`, gameplay systems, engine code,
  playable loops, HUD, assets, player-facing mechanics.
- **Product**: `design/cdd/product-concept.md`, API/CLI/web/library/data
  modules, business workflows, user journeys, migrations, integrations.
- **Unknown**: read both concept paths if present and ask before making
  domain-specific assumptions.

## Version Reference Warning

The LLM's training data may predate the pinned engine, framework, language, or
library version.

- **Game**: always check `docs/engine-reference/` before using any engine API.
- **Product**: always check `docs/reference/<stack>/` before using any
  framework, package, SDK, database, cloud, or language-version-specific API.

Do not guess at post-cutoff API signatures -- look them up first.

## Coding Standards

- All public APIs require doc comments
- Prefer dependency injection over singletons for testability
- Every new system needs a corresponding ADR in `docs/architecture/`
- Commits must reference the relevant story ID or design document

**Game-specific standards:**

- Gameplay values must be **data-driven** (external config files), never
  hardcoded.
- Game code should preserve the separation between gameplay, engine, AI,
  networking, UI, tools, and assets.
- Player-facing behavior must trace back to CDD acceptance criteria, Game
  pillars, Player Fantasy, and playtest evidence where applicable.

**Product-specific standards:**

- Public API endpoints, CLI commands, SDK functions, migrations, and data
  contracts must document inputs, outputs, errors, and compatibility promises.
- Configuration, credentials, feature flags, package versions, timeouts, and
  environment-specific values must not be hardcoded in implementation modules.
- Error behavior must be stable and testable: HTTP status codes, CLI exit codes,
  typed exceptions, retry semantics, and migration rollback/dry-run behavior
  should be explicit when relevant.
- Product behavior must trace back to Product principles, user promise, JTBD,
  workflow validation, or acceptance criteria in `design/cdd/`.

## File Routing

Match the specialist agent to the file type being written.

- **Game**: use the engine-specialist agent configured in `CLAUDE.md`.
  See `CLAUDE.md` -> Technical Preferences -> Engine Specialists -> File
  Extension Routing. When in doubt, use the primary engine specialist.
- **Product**: use `lead-programmer` plus the language specialist configured
  for the stack (`python-specialist`, `typescript-specialist`,
  `rust-specialist`, or `go-specialist`). Use `devops-engineer`,
  `security-engineer`, `analytics-engineer`, or `ux-designer` when the changed
  file is primarily infrastructure, security, analytics, UI, CLI, or API
  consumer workflow.

## Tests

Tests live in `tests/` — not in `src/`.
Run `/test-setup` to scaffold the test framework if it doesn't exist yet.

- **Game**: every gameplay system should have unit tests covering its formulas
  and edge cases; UI/HUD changes need screenshots or interaction evidence;
  engine integration should be verified against engine-reference docs.
- **Product**: API changes need contract or integration tests; CLI changes need
  argument, stdout/stderr, and exit-code tests; web changes need interaction or
  E2E evidence; migrations need apply/rollback or dry-run verification; data
  pipeline changes need fixture-based and edge-case tests.

## Verification-Driven Development

Write tests first when adding gameplay systems or product modules with stable
contracts.
For UI changes, verify with screenshots.
Compare expected output to actual output before marking work complete.
