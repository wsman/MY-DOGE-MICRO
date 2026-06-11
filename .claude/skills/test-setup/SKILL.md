---
name: test-setup
description: "Scaffold the test framework and CI/CD pipeline. Supports game engines (Godot/GUT, Unity/NUnit, Unreal/UE Automation) and product stacks (Python/pytest, Node/Vitest, Rust/cargo test, Go/go test). Run once during Technical Setup phase before the first sprint begins."
argument-hint: "[force]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write
---

## User Guide

- When to use: Scaffold the test framework and CI/CD pipeline. Supports game engines (Godot/GUT, Unity/NUnit, Unreal/UE Automation) and product stacks (Python/pytest, Node/Vitest, Rust/cargo test, Go/go test). Run once during Technical Setup phase before the first sprint begins.
- Inputs: Command arguments: `/test-setup [force]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: None.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

# Test Setup

This skill scaffolds the automated testing infrastructure for the project.
It detects the configured engine (game) or technology stack (product),
generates the appropriate test runner configuration, creates the standard
directory layout, and wires up CI/CD so tests run on every push.

Run this once during the Technical Setup phase, before any implementation
begins. A test framework installed at sprint start costs 30 minutes.
A test framework installed at sprint four costs 3 sprints.

**Output:** `tests/` directory structure + `.github/workflows/tests.yml` + one runnable example test file

---

## Phase 1: Detect Technology and Existing State

**[通用场景]** 1. **Detect domain and technology**:
   - Read `standards/technical-preferences.md`.
   - **[游戏专用]** Extract `Engine:` value. If not configured, stop: "Engine not configured."
   - **[通用产品]** Extract `Language:` and `Framework:` values. If not configured, stop: "Stack not configured."
   - If neither is configured, stop: "Technology not configured. Run `/setup-engine` first."

**[通用场景]** 2. **Check for existing test infrastructure**:
   - Glob `tests/` — does the directory exist?
   - Glob `tests/unit/` and `tests/integration/` — do subdirectories exist?
   - Glob `.github/workflows/` — does a CI workflow file exist?
   - **[游戏专用]** Glob `tests/gdunit4_runner.gd` (Godot), `tests/EditMode/` (Unity), `Source/Tests/` (Unreal).
   - **[通用产品]** Glob `tests/conftest.py` (Python), `vitest.config.*` (Node), `Cargo.toml` with test profile (Rust), `*_test.go` (Go).

**[通用场景]** 3. **Report findings**:
   - "Technology: [engine or stack]. Test directory: [found / not found]. CI workflow: [found / not found]."
   - If everything already exists AND `force` argument was not passed:
     "Test infrastructure appears to be in place. Re-run with `/test-setup force`
     to regenerate. Proceeding will not overwrite existing test files."

If the `force` argument is passed, skip the "already exists" early-exit and
proceed — but still do not overwrite files that already exist at a given path.
Only create files that are missing.

---

## Phase 2: Present Plan

Based on the technology detected and the existing state, present a plan:

```
## Test Setup Plan — [Engine or Stack]

I will create the following (skipping any that already exist):

tests/
  unit/           — Isolated unit tests
  integration/    — Cross-module and end-to-end tests
  api/            — Product API contract tests (product projects)
  smoke/          — Critical path test list (15-minute manual gate)
  README.md       — Test framework documentation

[Technology-specific files — see per-technology details below]

.github/workflows/tests.yml  — CI: run tests on every push to main
[Technology-specific example test — created so the baseline is runnable]
production/qa/evidence/      — Canonical manual/automated evidence schema

Estimated time: ~5 minutes to create all files.
```

Ask: "May I create these files? I will not overwrite any test files that
already exist at these paths."

Do not proceed without approval.

---

## Phase 3: Create Directory Structure

After approval, create the following files:

### `tests/README.md`

```markdown
# Test Infrastructure

**Technology**: [engine or stack name + version]
**Test Framework**: [Game: GdUnit4 / Unity / UE Automation | Product: pytest / Vitest / cargo / go]
**CI**: `.github/workflows/tests.yml`
**Setup date**: [date]

## Directory Layout

    tests/
      unit/           # Isolated unit tests
      integration/    # Cross-system and save/load tests
      api/            # Product API contract tests (product projects)
      smoke/          # Critical path test list for /smoke-check gate
      # Manual and release evidence lives in production/qa/evidence/

## Running Tests

[Technology-specific command — see below]

## Test Naming

[Game] Game naming: **Files**: `[system]_[feature]_test.[ext]`, **Functions**: `test_[scenario]_[expected]`, **Example**: `combat_damage_test.gd`
[Product] Product naming: **Files**: `test_[module]_[feature].py` / `[feature].test.ts` / `[feature]_test.rs`, **Example**: `test_user_service.py`

## Story Type → Test Evidence

[Game] Game evidence:

| Story Type | Required Evidence | Location |
|---|---|---|
| Logic | Automated unit test — must pass | `tests/unit/[system]/` |
| Integration | Integration test OR playtest doc | `tests/integration/[system]/` |
| Visual/Feel | Screenshot + lead sign-off | `production/qa/evidence/manual/` |
| UI | Manual walkthrough OR interaction test | `production/qa/evidence/manual/` |
| Config/Data | Smoke check pass | `production/qa/smoke-*.md` |

[Product] Product evidence:
| Story Type | Required Evidence | Location |
|---|---|---|
| Logic | Automated unit test | `tests/unit/[module]/` |
| Integration | Integration test OR API contract test | `tests/integration/[module]/` |
| UI | Screenshot OR interaction test | `production/qa/evidence/manual/` |
| CLI | Smoke command output | `production/qa/evidence/smoke/` |
| API | Contract test | `tests/api/` |
| Config/Data | Migration test OR smoke check | `production/qa/smoke-*.md` |

## CI

Tests run automatically on every push to `main` and on every pull request.
A failed test suite blocks merging.
```

### Technology-specific template selection

Select exactly one scaffold family from the detected domain and technology.
Do not write multiple competing CI templates to `.github/workflows/tests.yml`.

- **[游戏专用]** If an engine is detected, create only the engine scaffold and
  game smoke seed for that engine.
- **[通用产品]** If a product stack is detected, create only the stack scaffold
  and product smoke seed for the detected language/framework.
- **Unknown**: stop and ask the user to run `/setup-engine`; do not guess.

### Engine-specific files

#### Godot 4 (`Engine: Godot`)

Create `tests/gdunit4_runner.gd`:

```gdscript
# GdUnit4 test runner — invoked by CI and /smoke-check
# Usage: godot --headless --script tests/gdunit4_runner.gd
extends SceneTree

func _init() -> void:
    var runner := load("res://" + "addons/gdunit4/GdUnitRunner.gd")
    if runner == null:
        push_error("GdUnit4 not found. Install via AssetLib or addons/.")
        quit(1)
        return
    var instance = runner.new()
    instance.run_tests()
    quit(0)
```

Create `tests/unit/.gdignore_placeholder` with content:
`# Unit tests go here — one subdirectory per system (e.g., tests/unit/combat/)`

Create `tests/integration/.gdignore_placeholder` with content:
`# Integration tests go here — one subdirectory per system`

Create `tests/unit/example_movement_test.gd`:
```gdscript
extends GdUnitTestSuite

func test_example_vector_length() -> void:
    assert_float(Vector2(3, 4).length()).is_equal_approx(5.0, 0.001)
```

Note in the README: **Installing GdUnit4**
```
1. Open Godot → AssetLib → search "GdUnit4" → Download & Install
2. Enable the plugin: Project → Project Settings → Plugins → GdUnit4 ✓
3. Restart the editor
4. Verify that the Godot addons directory contains `gdunit4/`
```

#### Unity (`Engine: Unity`)

Create `tests/EditMode/` placeholder file `tests/EditMode/README.md`:
```markdown
# Edit Mode Tests
Unit tests that run without entering Play Mode.
Use for pure logic: formulas, state machines, data validation.
Assembly definition required: `tests/EditMode/EditModeTests.asmdef`
```

Create `tests/PlayMode/README.md`:
```markdown
# Play Mode Tests
Integration tests that run in a real game scene.
Use for cross-system interactions, physics, and coroutines.
Assembly definition required: `tests/PlayMode/PlayModeTests.asmdef`
```

Create `tests/EditMode/ExampleTests.cs`:
```csharp
using NUnit.Framework;

public class ExampleTests
{
    [Test]
    public void Example_Addition_Works()
    {
        Assert.AreEqual(4, 2 + 2);
    }
}
```

Note in the README: **Enabling Unity Test Framework**
```
Window → General → Test Runner
(Unity Test Framework is included by default in Unity 2019+)
```

#### Unreal Engine (`Engine: Unreal` or `Engine: UE5`)

Create `Source/Tests/README.md`:
```markdown
# Unreal Automation Tests
Tests use the UE Automation Testing Framework.
Run via: Session Frontend → Automation → select "MyGame." tests
Or headlessly: UnrealEditor -nullrhi -ExecCmds="Automation RunTests MyGame.; Quit"

Test class naming: F[SystemName]Test
Test category naming: "MyGame.[System].[Feature]"
```

Create `Source/Tests/ExampleAutomationTest.cpp`:
```cpp
 #include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FExampleAutomationTest,
    "MyGame.Example.Baseline",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)

bool FExampleAutomationTest::RunTest(const FString& Parameters)
{
    TestEqual(TEXT("Example arithmetic baseline"), 2 + 2, 4);
    return true;
}
```

---

## Phase 4: Create CI/CD Workflow

### Godot 4

Create `.github/workflows/tests.yml`:

```yaml
name: Automated Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Run GdUnit4 Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          lfs: true

      - name: Run GdUnit4 Tests
        uses: MikeSchulze/gdUnit4-action@v1
        with:
          godot-version: '[VERSION FROM docs/engine-reference/godot/VERSION.md]'
          paths: |
            tests/unit
            tests/integration
          report-name: test-results

      - name: Upload Test Results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: reports/
```

### Unity

Create `.github/workflows/tests.yml`:

```yaml
name: Automated Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Run Unity Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          lfs: true

      - name: Run Edit Mode Tests
        uses: game-ci/unity-test-runner@v4
        env:
          UNITY_LICENSE: ${{ secrets.UNITY_LICENSE }}
        with:
          testMode: editmode
          artifactsPath: test-results/editmode

      - name: Run Play Mode Tests
        uses: game-ci/unity-test-runner@v4
        env:
          UNITY_LICENSE: ${{ secrets.UNITY_LICENSE }}
        with:
          testMode: playmode
          artifactsPath: test-results/playmode

      - name: Upload Test Results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: test-results/
```

Note: Unity CI requires a `UNITY_LICENSE` secret. Add to GitHub repository
secrets before the first CI run.

### Unreal Engine

Create `.github/workflows/tests.yml`:

```yaml
name: Automated Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Run UE Automation Tests
    runs-on: self-hosted  # UE requires a local runner with the editor installed

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          lfs: true

      - name: Run Automation Tests
        run: |
          "$UE_EDITOR_PATH" "${{ github.workspace }}/[ProjectName].uproject" \
            -nullrhi -nosound \
            -ExecCmds="Automation RunTests MyGame.; Quit" \
            -log -unattended
        shell: bash

      - name: Upload Logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-logs
          path: Saved/Logs/
```

Note: UE CI requires a self-hosted runner with Unreal Editor installed.
Set the `UE_EDITOR_PATH` environment variable on the runner.

---

### Product-specific files

**[通用产品]** Product stack scaffold blocks. Create files appropriate to the
detected stack.

#### Python / pytest (`Language: Python`)

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests (deselect with -m "not slow")
    api: API contract tests
timeout = 30
```

Create `tests/conftest.py`:
```python
# Shared fixtures for all tests
import pytest
import tempfile
import os

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d

@pytest.fixture
def test_env():
    os.environ["TESTING"] = "1"
    yield
    os.environ.pop("TESTING", None)
```

Create `tests/unit/test_example.py`:
```python
def test_example_baseline():
    assert 2 + 2 == 4
```

CI template (`Language: Python`):
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: pytest -x --tb=short
```

#### Node / Vitest / Jest (`Language: TypeScript` or `Language: JavaScript`)

Create `vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config'
export default defineConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    environment: 'node',
    globals: true,
  },
})
```

Create `tests/unit/example.test.ts`:
```typescript
import { describe, expect, it } from 'vitest'

describe('example baseline', () => {
  it('runs the test harness', () => {
    expect(2 + 2).toBe(4)
  })
})
```

CI template (`Language: TypeScript`):
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "22" }
      - run: npm ci
      - run: npx vitest run
```

#### Rust / cargo test (`Language: Rust`)

Create `tests/unit/example_test.rs`:
```rust
 #[test]
fn example_baseline() {
    assert_eq!(2 + 2, 4);
}
```

Create `tests/unit.rs` so `cargo test` discovers the nested baseline file:
```rust
 #[path = "unit/example_test.rs"]
mod example_test;
```

CI template:
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - run: cargo test
```

#### Go / go test (`Language: Go`)

Create `tests/unit/example_test.go`:
```go
package unit

import "testing"

func TestExampleBaseline(t *testing.T) {
	if 2+2 != 4 {
		t.Fatal("example baseline failed")
	}
}
```

CI template:
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version: "1.22" }
      - run: go test ./...
```

## Phase 5: Create Smoke Test Seed

Create `tests/smoke/critical-paths.md`. Write only the variant matching the
detected domain — never write both game and product smoke seeds to the same file.

**[游戏专用] Game smoke seed:**

```markdown
# Smoke Test: Critical Paths

**Purpose**: Run these 10-15 checks in under 15 minutes before any QA hand-off.
**Run via**: `/smoke-check` (which reads this file)
**Update**: Add new entries when new core systems are implemented.

## Core Stability (always run)

1. Game launches to main menu without crash
2. New game / session can be started from the main menu
3. Main menu responds to all inputs without freezing

## Core Mechanic (update per sprint)

<!-- Add the primary mechanic for each sprint here as it is implemented -->
<!-- Example: "Player can move, jump, and the camera follows correctly" -->
4. [Primary mechanic — update when first core system is implemented]

## Data Integrity

5. Save game completes without error (once save system is implemented)
6. Load game restores correct state (once load system is implemented)

## Performance

7. No visible frame rate drops on target hardware (60fps target)
8. No memory growth over 5 minutes of play (once core loop is implemented)
```

**[通用产品]** Product smoke seed:

Create `tests/smoke/critical-paths.md` with product-appropriate entries:

```markdown
# Smoke Test: Critical Paths

**Purpose**: Run these 10-15 checks in under 15 minutes before any QA hand-off.
**Run via**: `/smoke-check` (which reads this file)

## Core Stability (always run)

**API:**
1. Health endpoint returns 200
2. Auth endpoint accepts valid credentials and returns token
3. Core GET endpoint returns expected schema (200)

**CLI:**
1. `--help` prints usage without error
2. Core command executes with default flags
3. `--version` prints the correct version

**Web:**
1. Homepage loads (200) without console errors
2. Core navigation works (no 404)
3. Core form submits successfully

## Core Workflow (update per sprint)

4. [Primary workflow — update when first core module is implemented]

## Data Integrity

5. Database migrations run cleanly against fresh instance
6. Seed data / fixtures load without constraint errors

## Performance

7. API response <500ms p95 on core endpoint
8. No unbounded memory growth over 5 minutes of sustained load (once core workflow is implemented)
```

---

## Phase 6: Post-Setup Summary

After writing all files, report:

```
Test infrastructure created for [technology].

Files created:
- tests/README.md
- tests/unit/ (directory)
- tests/integration/ (directory)
- tests/api/ (directory, for product API contract tests)
- tests/smoke/critical-paths.md
- production/qa/evidence/ (canonical evidence schema)
[technology-specific files]
- [technology-specific example test file]
- .github/workflows/tests.yml

Next steps:
1. [Technology-specific setup step: Game — install/configure engine test plugin; Product — run the stack test command locally]
2. Run the generated example test locally to confirm the harness works.
3. Replace or extend the example with your first module test when implementation starts: `tests/unit/[first-module]/[module]_test.[ext]`
4. Run `/qa-plan sprint` before your first sprint to classify stories and set
   test evidence requirements
5. `/smoke-check` before every QA hand-off

Gate note: /gate-check Technical Setup → Pre-Production now requires:
- tests/ directory with unit/ and integration/ subdirectories
- .github/workflows/tests.yml
- At least one example test file
This `/test-setup` baseline creates the example test; no separate hand-written
test is required for the setup gate.
`/test-helpers` is an optional enhancement for fixtures, factories, mocks, and
engine/stack helper libraries after this baseline exists; missing helpers are
not a gate blocker.

Verdict: **COMPLETE** — test framework scaffolded and CI/CD wired up.
```

---

## Collaborative Protocol

- **Never overwrite existing test files** — only create files that are missing.
  If a test runner file exists, leave it as-is.
- **Always ask before creating files** — Phase 2 requires explicit approval.
- **Technology detection is non-negotiable** — game projects require `Engine:`;
  product projects require `Language:` and should use `Framework:` when available.
  If the relevant technology is not configured, stop and redirect to
  `/setup-engine`. Do not guess.
- **`force` flag skips the "already exists" early-exit but never overwrites.**
  It means "create any missing files even if the directory already exists."
- **[游戏专用]** For Unity CI, note that the `UNITY_LICENSE` secret must be configured
  manually. Do not attempt to automate license management.
