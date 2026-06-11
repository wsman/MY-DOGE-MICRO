---
name: smoke-check
description: "Run the critical path smoke test gate before QA hand-off. Executes the automated test suite, verifies core functionality, and produces a PASS/FAIL report. Supports both game and product projects. A failed smoke check means the build is not ready for QA."
argument-hint: "[sprint | quick | --platform pc|console|mobile|web|api|cli|all]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, AskUserQuestion
---

## User Guide

- When to use: Run the critical path smoke test gate before QA hand-off. Executes the automated test suite, verifies core functionality, and produces a PASS/FAIL report. Supports both game and product projects. A failed smoke check means the build is not ready for QA.
- Inputs: Command arguments: `/smoke-check [sprint | quick | --platform pc|console|mobile|web|api|cli|all]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: `memory_bank/t3_archive/qa_evidence_index.md`.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

# Smoke Check

This skill is the gate between "implementation done" and "ready for QA
hand-off". It runs the automated test suite, checks for test coverage gaps,
batch-verifies critical paths with the developer, and produces a PASS/FAIL
report.

The rule is simple: **a build that fails smoke check does not go to QA.**
Handing a broken build to QA wastes their time and demoralises the team.

**Output:** `production/qa/smoke-[date].md`

---

## Dual-Domain Parity Contract

| Area | Game branch | Product branch |
|------|-------------|----------------|
| Context reads | Engine from technical preferences, current QA plan, sprint stories, smoke tests, test directories, recent build/test output | Language/framework from technical preferences, current QA plan, API/CLI/workflow/deployment smoke tests, sprint stories, CI/test output, package/deploy config |
| Steps | Run engine tests, verify playable critical path, validate platform/input batches, confirm build ready for QA | Run product test command, verify API/CLI/web/core workflow batches, validate migration/config/deployment/package smoke checks, confirm release candidate ready for QA |
| Outputs | `production/qa/smoke-[date].md` with PASS/FAIL, failed tests, platform batches, manual checks, QA hand-off decision | `production/qa/smoke-[date].md` with PASS/FAIL, contract/CLI/workflow/migration/deployment smoke results, manual checks, QA hand-off decision |
| Next steps | Fix blockers or run `/team-qa`; update regression suite for failures | Fix blockers or run `/team-qa`; run `/test-evidence-review` for contract/migration/package evidence and `/release-checklist` when release-bound |

---

## Parse Arguments

Arguments can be combined: `/smoke-check sprint --platform console`

**Base mode** (first argument, default: `sprint`):
- `sprint` — full smoke check against the current sprint's stories
- `quick` — skip coverage scan (Phase 3) and Batch 3; use for rapid re-checks

**Platform flag** (`--platform`, default: none):

**[游戏专用]** Game platforms:
- `--platform pc` — PC checks (keyboard, mouse, windowed mode)
- `--platform console` — console checks (gamepad, TV safe zones, certification)
- `--platform mobile` — mobile checks (touch, portrait/landscape, battery/thermal)

**[通用产品]** Product platforms:
- `--platform web` — browser checks (page load, navigation, form submission)
- `--platform api` — API checks (health endpoint, auth flow, response schema)
- `--platform cli` — CLI checks (help output, core command, config loading)

**[通用场景]** `--platform all` — all applicable platform variants; per-platform verdict

If `--platform` is provided, Phase 4 adds platform-specific batches and
Phase 5 outputs a per-platform verdict table in addition to the overall verdict.

---

## Phase 1: Detect Test Setup

Before running anything, understand the environment:

1. **Test framework check**: verify `tests/` directory exists.
   If it does not: "No test directory found at `tests/`. Run `/test-setup`
   to scaffold the testing infrastructure, or create the directory manually
   if tests live elsewhere." Then stop.

2. **CI check**: check whether `.github/workflows/` contains a workflow file
   referencing tests. Note in the report whether CI is configured.

3. **Technology detection**: read `standards/technical-preferences.md`.

   **[游戏专用]** Extract `Engine:` value. Store for game-specific test command.

   **[通用产品]** Extract `Language:` and `Framework:` values. Store for product
   test command. Map to test command:
   - Python → `pytest -x --tb=short`
   - TypeScript/JavaScript → `npx vitest run` (or `npx jest` if Jest config found)
   - Rust → `cargo test`
   - Go → `go test ./...`

4. **Smoke test list**: check whether `production/qa/smoke-tests.md` or
   `tests/smoke/` exists. If a smoke test list is found, load it for use in
   Phase 4. If neither exists, smoke tests will be drawn from the current QA
   plan (Phase 4 fallback).

5. **QA plan check**: glob `production/qa/qa-plan-*.md` and take the most
   recently modified file. If found, note the path — it will be used in
   Phase 3 and Phase 4. If not found, note: "No QA plan found. Run
   `/qa-plan sprint` before smoke-checking for best results."

Report findings before proceeding: "Environment: [technology] | Domain: [game/product]. Test directory:
[found / not found]. CI configured: [yes / no]. QA plan: [path / not found]."

---

## Phase 2: Run Automated Tests

Attempt to run the test suite via Bash. Select the command based on the
domain and technology detected in Phase 1.

**[游戏专用] Godot 4:**
```bash
godot --headless --script tests/gdunit4_runner.gd 2>&1
```
If the GDUnit4 runner script does not exist at that path, try:
```bash
godot --headless -s addons/gdunit4/GdUnitRunner.gd 2>&1
```
If neither path exists, note: "GDUnit4 runner not found — confirm the runner
path for your test framework."

**[游戏专用] Unity:**
Unity tests require the editor and cannot be run headlessly via shell in most
environments. Check for recent test result artifacts:
```bash
ls -t test-results/ 2>&1 | head -5
```
If test result files exist (XML or JSON), read the most recent one and parse
PASS/FAIL counts. If no artifacts exist: "Unity tests must be run from the
editor or CI pipeline. Please confirm test status manually before proceeding."

**[游戏专用] Unreal Engine:**
```bash
ls -t Saved/Logs/ 2>&1 | grep -i "test\|automation" | head -5
```
If no matching log found: "UE automation tests must be run via the Session
Frontend or CI pipeline. Please confirm test status manually."

**[通用产品] Python / pytest:**
```bash
pytest -x --tb=short 2>&1
```

**[通用产品] TypeScript / JavaScript:**
If a Vitest config exists (`vitest.config.*`), run:
```bash
npx vitest run 2>&1
```
If a Jest config exists (`jest.config.*` or `package.json` test script clearly
uses Jest), run:
```bash
npx jest 2>&1
```
If neither is clear, run:
```bash
npm test -- --runInBand 2>&1
```

**[通用产品] Rust / cargo test:**
```bash
cargo test 2>&1
```

**[通用产品] Go / go test:**
```bash
go test ./... 2>&1
```

**Unknown technology / not configured:**
"Technology not configured in `standards/technical-preferences.md`. Run
`/setup-engine` to specify the engine or product stack, then re-run
`/smoke-check`."

**If the test runner is not available in this environment** (engine binary not
on PATH, product test command unavailable, runner script not found, etc.),
report clearly:

"Automated tests could not be executed — test runner not found in this
environment.
Status will be recorded as NOT RUN. Confirm test results from your local IDE
or CI pipeline. Unconfirmed NOT RUN is treated as PASS WITH WARNINGS, not
FAIL — the developer must manually confirm results."

Do not treat NOT RUN as an automatic FAIL. Record it as a warning. The
developer's manual confirmation in Phase 4 can resolve it.

Parse runner output and extract:
- Total tests run
- Passing count
- Failing count
- Names of any failing tests (up to 10; if more, note the count)
- Any crash or error output from the runner itself

---

## Phase 3: Check Test Coverage

Draw the story list from, in priority order:
1. The QA plan found in Phase 1 (its Test Summary table lists expected test
   file paths per story)
2. The current sprint plan from `production/sprints/` (most recently modified
   file)
3. If the `quick` argument was passed, skip this phase entirely and note:
   "Coverage scan skipped — run `/smoke-check sprint` for full coverage
   analysis."

For each story in scope:

1. Extract the system slug from the story's file path
   (e.g., `production/epics/combat/story-001.md` → `combat`)
2. Glob `tests/unit/[system]/` and `tests/integration/[system]/` for files
   whose name contains the story slug or a closely related term
3. Check the story file itself for a `Test file:` header field or a
   "Test Evidence" section

Assign a coverage status to each story:

| Status | Meaning |
|--------|---------|
| **COVERED** | A test file was found matching this story's system and scope |
| **MANUAL** | Story type is Visual/Feel or UI; a test evidence document was found |
| **MISSING** | Logic or Integration story with no matching test file |
| **EXPECTED** | Config/Data story — no test file required; spot-check is sufficient |
| **UNKNOWN** | Story file missing or unreadable |

MISSING entries are advisory gaps. They do not cause a FAIL verdict but must
appear prominently in the report and must be resolved before `/story-done` can
fully close those stories.

---

## Phase 4: Run Manual Smoke Check

Domain detection drives which batches to use:
- [Game] detected -> present Game smoke batches (Batch 1-3, platform batches pc/console/mobile)
- [Product] detected -> present Product smoke batches (Batch 1-3, platform batches web/api/cli)
- Unknown -> present generic stability checks (never default to game batches)

Draw the smoke test checklist from, in priority order:
1. The QA plan's "Smoke Test Scope" section (if QA plan was found in Phase 1)
2. `production/qa/smoke-tests.md` (if it exists)
3. `tests/smoke/` directory contents (if it exists)
4. The standard fallback list below (used only when none of the above exist)

Tailor batches 2 and 3 to the actual systems identified from the sprint or QA
plan. Replace bracketed placeholders with real mechanic or workflow names from
the current sprint's stories.

Use `AskUserQuestion` to batch-verify. Keep to at most 3 calls.

**[游戏专用] Game Smoke Batches** *(run when a game engine is detected)*:

**Batch 1 — Core stability (always run):**
```
question: "Smoke check — Batch 1: Core stability. Please verify each:"
options:
  - "Game launches to main menu without crash — PASS"
  - "Game launches to main menu without crash — FAIL"
  - "New game / session starts successfully — PASS"
  - "New game / session starts successfully — FAIL"
  - "Main menu responds to all inputs — PASS"
  - "Main menu responds to all inputs — FAIL"
```

**Batch 2 — Sprint mechanic and regression (always run):**
```
question: "Smoke check — Batch 2: This sprint's changes and regression check:"
options:
  - "[Primary mechanic this sprint] — PASS"
  - "[Primary mechanic this sprint] — FAIL: [describe what broke]"
  - "[Second notable change this sprint, if any] — PASS"
  - "[Second notable change this sprint] — FAIL"
  - "Previous sprint's features still work (no regressions) — PASS"
  - "Previous sprint's features — regression found: [brief description]"
```

**Batch 3 — Data integrity and performance (run unless `quick` argument):**
```
question: "Smoke check — Batch 3: Data integrity and performance:"
options:
  - "Save / load completes without data loss — PASS"
  - "Save / load — FAIL: [describe what broke]"
  - "Save / load — N/A (save system not yet implemented)"
  - "No new frame rate drops or hitches observed — PASS"
  - "Frame rate drops or hitches found — FAIL: [where]"
  - "Performance — not checked in this session"
```

Record each response verbatim for the Phase 5 report.

**Platform Batches** *(run only if `--platform` argument was provided)*:

**PC platform** (`--platform pc` or `--platform all`):
```
question: "Smoke check — PC Platform: Verify platform-specific behaviour:"
options:
  - "Keyboard controls work correctly across all menus and gameplay — PASS"
  - "Keyboard controls — FAIL: [describe issue]"
  - "Mouse input and cursor visibility correct in all states — PASS"
  - "Mouse input — FAIL: [describe issue]"
  - "Windowed and fullscreen modes function without graphical issues — PASS"
  - "Windowed/fullscreen — FAIL: [describe issue]"
  - "Resolution changes apply correctly — PASS"
  - "Resolution changes — FAIL: [describe issue]"
```

**Console platform** (`--platform console` or `--platform all`):
```
question: "Smoke check — Console Platform: Verify platform-specific behaviour:"
options:
  - "Gamepad input works correctly for all actions — PASS"
  - "Gamepad input — FAIL: [describe issue]"
  - "UI fits within TV safe zone margins (no text clipped) — PASS"
  - "TV safe zone — FAIL: [describe what is clipped]"
  - "No keyboard/mouse-only fallbacks shown to gamepad user — PASS"
  - "Input prompt inconsistency — FAIL: [describe]"
  - "Game boots correctly from cold start (no prior save) — PASS"
  - "Cold start — FAIL: [describe issue]"
```

**Mobile platform** (`--platform mobile` or `--platform all`):
```
question: "Smoke check — Mobile Platform: Verify platform-specific behaviour:"
options:
  - "Touch controls work correctly for all primary actions — PASS"
  - "Touch controls — FAIL: [describe issue]"
  - "Game handles orientation change (portrait ↔ landscape) correctly — PASS"
  - "Orientation change — FAIL: [describe what breaks]"
  - "Background / foreground transitions (home button) handled gracefully — PASS"
  - "Background/foreground — FAIL: [describe issue]"
  - "No visible performance issues on target device (no thermal throttling signs) — PASS"
  - "Mobile performance — FAIL: [describe issue]"
```

---

**[通用产品] Product Smoke Batches** *(run when product stack detected)*:

**Batch 1 — Core Workflow (always run):**
```
question: "Smoke check — Batch 1: Core workflow. Please verify each:"
options:
  - "API: Health endpoint returns 200 — PASS"
  - "API: Health endpoint returns 200 — FAIL: [describe response]"
  - "CLI: --help prints usage without error — PASS"
  - "CLI: --help — FAIL: [describe error]"
  - "Web: Homepage loads without console errors — PASS"
  - "Web: Homepage — FAIL: [describe issue]"
```

**Batch 2 — Integration Health (always run):**
```
question: "Smoke check — Batch 2: Integration checks:"
options:
  - "Auth flow works (login → token → authenticated request) — PASS"
  - "Auth flow — FAIL: [describe where it breaks]"
  - "DB migrations run against fresh instance — PASS"
  - "DB migrations — FAIL: [describe error]"
  - "Core POST/command produces expected result — PASS"
  - "Core POST/command — FAIL: [describe mismatch]"
```

**Batch 3 — Data Integrity (run unless `quick` argument):**
```
question: "Smoke check — Batch 3: Data integrity:"
options:
  - "Seed data / fixtures load without constraint errors — PASS"
  - "Seed data — FAIL: [describe constraint error]"
  - "Core query returns expected results within p95 — PASS"
  - "Core query — FAIL: [describe mismatch or timeout]"
```

**Product Platform Batches** *(run only if `--platform` argument was provided)*:

**Web platform** (`--platform web` or `--platform all`):
```
options:
  - "Core navigation works without 404 — PASS"
  - "Core form submission returns success — PASS"
  - "Responsive layout on mobile viewport — PASS"
```

**API platform** (`--platform api` or `--platform all`):
```
options:
  - "Core GET endpoint returns expected schema (200) — PASS"
  - "Core POST endpoint accepts valid payload (201) — PASS"
  - "Auth-protected endpoint rejects unauthenticated request (401) — PASS"
```

**CLI platform** (`--platform cli` or `--platform all`):
```
options:
  - "Core command executes with default flags — PASS"
  - "Config file loads correctly (env vars respected) — PASS"
  - "--version prints the correct version — PASS"
```

## Phase 5: Generate Report

Assemble the full smoke check report:

````markdown
## Smoke Check Report
**Date**: [date]
**Sprint**: [sprint name / number, or "Not identified"]
**Technology**: [engine or stack]
**QA Plan**: [path, or "Not found — run /qa-plan first"]
**Argument**: [sprint | quick | blank]

---

### Automated Tests

**Status**: [PASS ([N] tests, [N] passing) | FAIL ([N] failures) |
NOT RUN ([reason])]

[If FAIL, list failing tests:]
- `[test name]` — [brief failure description from runner output]

[If NOT RUN:]
"Manual confirmation required: did tests pass in your local IDE or CI? This
will determine whether the automated test row contributes to a FAIL verdict."

---

### Test Coverage

| Story | Type | Test File | Coverage Status |
|-------|------|-----------|----------------|
| [title] | Logic | `tests/unit/[system]/[slug]_test.[ext]` | COVERED |
| [title] | Visual/Feel | `production/qa/evidence/manual/[slug]-screenshots.md` | MANUAL |
| [title] | Logic | — | MISSING ⚠ |
| [title] | Config/Data | — | EXPECTED |

**Summary**: [N] covered, [N] manual, [N] missing, [N] expected.

---

### Manual Smoke Checks

Record the checks that were actually presented for the detected domain.

**[游戏专用] Example rows:**
- [x] Game launches without crash — PASS
- [x] New game starts — PASS
- [x] [Core mechanic] — PASS
- [x] Save / load — PASS

**[通用产品] Example rows:**
- [x] API health endpoint returns 200 — PASS
- [x] CLI `--help` prints usage — PASS
- [x] Web homepage loads without console errors — PASS
- [x] Core workflow produces expected result — PASS
- [x] Database migrations run cleanly — PASS

**[通用场景] Failure row format:**
- [ ] [check name] — FAIL: [user's description]

---

### Missing Test Evidence

Stories that must have test evidence before they can be marked COMPLETE via
`/story-done`:

- **[story title]** (`[path]`) — Logic story has no test file.
  Expected location: `tests/unit/[system]/[story-slug]_test.[ext]`

[If none:] "All Logic and Integration stories have test coverage."

---

### Platform-Specific Results *(only if `--platform` was provided)*

| Platform | Checks Run | Passed | Failed | Platform Verdict |
|----------|-----------|--------|--------|-----------------|
| PC | [N] | [N] | [N] | PASS / FAIL |
| Console | [N] | [N] | [N] | PASS / FAIL |
| Mobile | [N] | [N] | [N] | PASS / FAIL |
| Web | [N] | [N] | [N] | PASS / FAIL |
| API | [N] | [N] | [N] | PASS / FAIL |
| CLI | [N] | [N] | [N] | PASS / FAIL |

Omit rows for platforms that were not requested.

**Platform notes**: [any platform-specific observations not captured in pass/fail]

Any platform with one or more FAIL checks contributes to the overall FAIL verdict.

---

### Verdict: [PASS | PASS WITH WARNINGS | FAIL]

[Verdict rules — first matching rule wins:]

**FAIL** if ANY of:
- Automated test suite ran and reported one or more test failures
- Any Batch 1 (core stability) check returned FAIL
- Any Batch 2 (primary sprint change or regression check) returned FAIL

**PASS WITH WARNINGS** if ALL of:
- Automated tests PASS or NOT RUN (developer has not yet confirmed)
- All Batch 1 and Batch 2 smoke checks PASS
- One or more Logic/Integration stories have MISSING test evidence

**PASS** if ALL of:
- Automated tests PASS
- All smoke checks in all batches PASS or N/A
- No MISSING test evidence entries
````

---

## Phase 6: Write and Gate

Present the full report in conversation, then ask:

"May I write this smoke check report to `production/qa/smoke-[date].md`?"

Write only after approval.

When `memory_bank/` exists and the user approves writing the smoke report, also
update `memory_bank/t3_archive/qa_evidence_index.md`.

- Type: `smoke-check`
- Evidence path: `production/qa/smoke-[date].md`
- Verdict: PASS, FAIL, or PASS WITH WARNINGS
- Dedupe by evidence path; update Date, Type, Verdict, and Follow-up Owner for
  an existing path instead of adding a duplicate row.
- If `memory_bank/` does not exist, do not create it from `/smoke-check`; keep
  the existing smoke report behavior and say: "Run `/constitute` to establish
  the memory_bank governance control plane."

After writing, deliver the gate verdict:

**If verdict is FAIL:**

"The smoke check failed. Do not hand off to QA until these failures are
resolved:

[List each failing automated test or smoke check with a one-line description]

Fix the failures and run `/smoke-check` again to re-gate before QA hand-off."

**If verdict is PASS WITH WARNINGS:**

"Smoke check passed with warnings. The build is ready for manual QA.

Advisory items to resolve before running `/story-done` on affected stories:
[list MISSING test evidence entries]

QA hand-off: share `production/qa/qa-plan-[sprint].md` with the qa-tester
agent to begin manual verification."

**If verdict is PASS:**

"Smoke check passed cleanly. The build is ready for manual QA.

QA hand-off: share `production/qa/qa-plan-[sprint].md` with the qa-tester
agent to begin manual verification."

---

## Collaborative Protocol

- **Never treat NOT RUN as automatic FAIL** — record it as NOT RUN and let
  the developer confirm status manually. Unconfirmed NOT RUN contributes to
  PASS WITH WARNINGS, not FAIL.
- **Never auto-fix failures** — report them and state what must be resolved.
  Do not attempt to edit source code or test files.
- **PASS WITH WARNINGS does not block QA hand-off** — it records advisory
  gaps for `/story-done` to follow up on.
- **`quick` argument** skips Phase 3 (coverage scan) and Phase 4 Batch 3.
  Use it for rapid re-checks after fixing a specific failure.
- Use `AskUserQuestion` for all manual smoke check verification.
- **Never write the report without asking** — Phase 6 requires explicit
  approval before any file is created.
