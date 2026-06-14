# Coding Standards

- All game and product code must include doc comments on public APIs
- Every system must have a corresponding architecture decision record in `docs/architecture/`
- All public methods must be unit-testable (dependency injection over singletons)
- Commits must reference the relevant design document or task ID
- **Game**: gameplay values must be data-driven (external config), never
  hardcoded. Player-facing behavior should trace to CDD acceptance criteria,
  Game pillars, Player Fantasy, and playtest evidence when applicable.
- **Product**: API endpoints, CLI commands, SDK functions, migrations, data
  transforms, integrations, and background jobs must document inputs, outputs,
  errors, compatibility promises, and configuration. Secrets, credentials,
  environment-specific values, feature flags, timeouts, and package versions
  must not be hardcoded in implementation modules.
- **Verification-driven development**: Write tests first when adding gameplay
  systems or product modules with stable contracts. For UI changes, verify with
  screenshots. Compare expected output to actual output before marking work
  complete. Every implementation should have a way to prove it works.

# Design Document Standards

- All design docs use Markdown
- Each game mechanic or product module/workflow has a dedicated document in
  `design/cdd/`
- Game CDDs must include these 8 required sections:
  1. **Overview** -- one-paragraph summary
  2. **Player Fantasy** -- intended feeling and experience
  3. **Detailed Rules** -- unambiguous mechanics
  4. **Formulas** -- all math defined with variables
  5. **Edge Cases** -- unusual situations handled
  6. **Dependencies** -- other systems listed
  7. **Tuning Knobs** -- configurable values identified
  8. **Acceptance Criteria** -- testable success conditions
- Balance values must link to their source formula or rationale
- Product CDDs use equivalent required sections:
  1. **Overview** -- one-paragraph summary of the module or workflow
  2. **User Promise / JTBD** -- what the user is trying to accomplish and what
     the product must reliably do
  3. **Detailed Behavior** -- API, CLI, UI, data, or integration behavior
  4. **Contracts / Data Model** -- schemas, inputs, outputs, errors, exit codes,
     migrations, or state transitions
  5. **Edge Cases** -- invalid input, permissions, retries, partial failure,
     concurrency, data drift, and rollback behavior
  6. **Dependencies** -- upstream/downstream services, packages, docs, and
     operational constraints
  7. **Configuration Knobs** -- environment variables, feature flags, limits,
     defaults, and safe ranges
  8. **Acceptance Criteria** -- contract, workflow, migration, docs, and
     observability checks

# Testing Standards

## Test Evidence by Story Type

All stories must have appropriate test evidence before they can be marked Done:

| Story Type | Required Evidence | Location | Gate Level |
|---|---|---|---|
| **Logic** (formulas, AI, state machines) | Automated unit test — must pass | `tests/unit/[system]/` | BLOCKING |
| **Integration** (multi-system) | Integration test OR documented playtest | `tests/integration/[system]/` | BLOCKING |
| **Visual/Feel** (animation, VFX, feel) | Screenshot + lead sign-off | `production/qa/evidence/` | ADVISORY |
| **UI** (menus, HUD, screens) | Manual walkthrough doc OR interaction test | `production/qa/evidence/` | ADVISORY |
| **Config/Data** (balance tuning) | Smoke check pass | `production/qa/smoke-[date].md` | ADVISORY |
| **API Contract** (endpoints, SDKs) | Contract or integration test + schema diff review | `tests/contract/` or `tests/integration/` | BLOCKING |
| **CLI Workflow** (commands, flags) | Argument, stdout/stderr, and exit-code tests | `tests/cli/` | BLOCKING |
| **Migration/Data Pipeline** | Apply/rollback or dry-run verification with fixtures | `tests/migration/` or `tests/data/` | BLOCKING |
| **Web/App Workflow** (critical user path) | E2E or interaction evidence + accessibility check | `tests/e2e/` or `production/qa/evidence/` | BLOCKING |

## Automated Test Rules

- **Naming**: `[system]_[feature]_test.[ext]` for files; `test_[scenario]_[expected]` for functions
- **Determinism**: Tests must produce the same result every run — no random seeds, no time-dependent assertions
- **Isolation**: Each test sets up and tears down its own state; tests must not depend on execution order
- **No hardcoded data**: Test fixtures use constant files or factory functions, not inline magic numbers
  (exception: boundary value tests where the exact number IS the point)
- **Independence**: Unit tests do not call external APIs, databases, or file I/O — use dependency injection

## What NOT to Automate

- Visual fidelity (shader output, VFX appearance, animation curves)
- "Feel" qualities (input responsiveness, perceived weight, timing)
- Platform-specific rendering (test on target hardware, not headlessly)
- Full gameplay sessions (covered by playtesting, not automation)
- Exploratory user interviews and subjective workflow satisfaction (capture as
  validation notes; do not pretend they are deterministic automated tests)
- Production-only third-party outages (use mocks/contract tests and monitored
  smoke checks instead of depending on live downtime)

## CI/CD Rules

- Automated test suite runs on every push to main and every PR
- No merge if tests fail — tests are a blocking gate in CI
- Never disable or skip failing tests to make CI pass — fix the underlying issue
- Engine-specific CI commands:
  - **Godot**: `godot --headless --script tests/gdunit4_runner.gd`
  - **Unity**: `game-ci/unity-test-runner@v4` (GitHub Actions)
  - **Unreal**: headless runner with `-nullrhi` flag
- Product-specific CI commands should run the configured language/framework
  stack from `docs/reference/<stack>/` and `standards/technical-preferences.md`
  before release:
  - **Python**: unit + contract tests, lint/type checks where configured
  - **TypeScript**: typecheck, unit/component/E2E tests where configured
  - **Rust**: `cargo test`, `cargo clippy`, migration/data tests where relevant
  - **Go**: `go test ./...`, vet/static checks, contract tests where relevant
