---
name: story-done
description: "End-of-story completion review. Reads the story file, verifies each acceptance criterion against the implementation, checks for CDD/ADR deviations, prompts code review, updates story status to Complete, and surfaces the next ready story from the sprint."
argument-hint: "[story-file-path] [--review full|lean|solo]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion, Task
---

## User Guide

- When to use: End-of-story completion review. Reads the story file, verifies each acceptance criterion against the implementation, checks for CDD/ADR deviations, prompts code review, updates story status to Complete, and surfaces the next ready story from the sprint.
- Inputs: Command arguments: `/story-done [story-file-path] [--review full|lean|solo]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: `memory_bank/t3_archive/sprint_snapshots/story-closure-index.md`.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

# Story Done

This skill closes the loop between design and implementation. Run it at the end
of implementing any story. It ensures every acceptance criterion is verified
before the story is marked done, CDD and ADR deviations are explicitly
documented rather than silently introduced, code review is prompted rather than
forgotten, and the story file reflects actual completion status.

**Output:** Updated story file (Status: Complete) + surfaced next story.

---

## Phase 1: Find the Story

Resolve the review mode (once, store for all gate spawns this run):
1. If `--review [full|lean|solo]` was passed → use that
2. Else read `production/review-mode.txt` → use that value
3. Else → default to `lean`

See `standards/director-gates.md` for the full check pattern.

**If a file path is provided** (e.g., `/story-done production/epics/core/story-damage-calculator.md`):
read that file directly.

**If no argument is provided:**

1. Check `production/session-state/active.md` for the currently active story.
2. If not found there, read the most recent file in `production/sprints/` and
   look for stories marked IN PROGRESS.
3. If multiple in-progress stories are found, use `AskUserQuestion`:
   - "Which story are we completing?"
   - Options: list the in-progress story file names.
4. If no story can be found, ask the user to provide the path.

---

## Phase 2: Read the Story

Read the full story file. Extract and hold in context:

- **Story name and ID**
- **CDD Requirement TR-ID(s)** referenced (e.g., `TR-combat-001`)
- **Manifest Version** embedded in the story header (e.g., `2026-03-10`)
- **ADR reference(s)** referenced
- **Acceptance Criteria** — the complete list (every checkbox item)
- **Implementation files** — files listed under "files to create/modify"
- **Story Type** — the `Type:` field from the story header.
  - Game types: Logic / Integration / Visual/Feel / UI / Config/Data
  - Product types: API / CLI / Data/Migration / Auth/Permission / Workflow / UI / Integration / Ops/Deployment / Config
- **Technology notes** — any technology-specific constraints noted (engine compatibility for game, stack compatibility for product)
- **Definition of Done** — if present, the story-level DoD
- **Estimated vs actual scope** — if an estimate was noted

Also read:
- `docs/architecture/tr-registry.yaml` — look up each TR-ID in the story.
  Read the *current* `requirement` text from the registry entry. This is the
  source of truth for what the CDD required — do not use any requirement text
  that may be quoted inline in the story (it may be stale).
- The referenced CDD section — just the acceptance criteria and key rules, not
  the full document. Use this to cross-check the registry text is still accurate.
- The referenced ADR(s) — just the Decision and Consequences sections
- `docs/architecture/control-manifest.md` header — extract the current
  `Manifest Version:` date (used in Phase 4 staleness check)

---

## Phase 3: Verify Acceptance Criteria

For each acceptance criterion in the story, attempt verification using one of
three methods:

### Automatic verification (run without asking)

- **File existence check**: `Glob` for files the story said would be created.
- **Test pass check**: if a test file path is mentioned, run it via `Bash`.
- **No hardcoded values check**: `Grep` for numeric literals in implementation code
  paths that should be in config files.
- **No hardcoded strings check**: `Grep` for user-facing strings in `src/`
  that should be in localization files.
- **Dependency check**: if a criterion says "depends on X", check that X exists.

### Manual verification with confirmation (use `AskUserQuestion`)

- Criteria about subjective qualities ("feels responsive", "animations play correctly")
- Criteria about gameplay behaviour ("player takes damage when...", "enemy responds to...")
- Criteria about product workflow behaviour ("user can approve invoice", "CLI prints the expected table")
- Performance criteria ("completes within Xms") — ask if profiled or accept as assumed

Batch up to 4 manual verification questions into a single `AskUserQuestion` call:

```
question: "Does [criterion]?"
options: "Yes — passes", "No — fails", "Not tested yet"
```

### Unverifiable (flag without blocking)

- Criteria that require a full build, deployment, or end-to-end user session to test
- Mark as:
  - **[游戏专用]** `DEFERRED — requires playtest session`
  - **[通用产品]** `DEFERRED — requires user test, deployment, or end-to-end session`

### Test-Criterion Traceability

After completing the pass/fail/deferred check above, map each acceptance
criterion to the test that covers it:

For each acceptance criterion in the story:

1. Ask: is there a test — unit, integration, confirmed manual playtest, or
   confirmed manual user test — that
   directly verifies this criterion?
   - **Unit test**: check `tests/unit/` for a test file or function name that
     matches the criterion's subject (use `Glob` and `Grep`)
   - **Integration test**: check `tests/integration/` similarly
   - **Manual confirmation**: if the criterion was verified via `AskUserQuestion`
     above with a "Yes — passes" answer, count that as a manual test

2. Produce a traceability table:

```
| Criterion | Test | Status |
|-----------|------|--------|
| AC-1: [criterion text] | tests/unit/test_foo.gd::test_bar | COVERED |
| AC-2: [criterion text] | Manual playtest/user-test confirmation | COVERED |
| AC-3: [criterion text] | — | UNTESTED |
```

3. Apply these escalation rules:

   - If **>50% of criteria are UNTESTED**: escalate to **BLOCKING** — test
     coverage is insufficient to confirm the story is actually done. The verdict
     in Phase 6 cannot be COMPLETE until coverage improves.
   - If **some (≤50%) criteria are UNTESTED**: remain ADVISORY — does not block
     completion, but must appear in Completion Notes.
   - If **all criteria are COVERED**: no action needed beyond including the
     table in the report.

4. For any ADVISORY untested criteria, add to the Completion Notes in Phase 7:
   `"Untested criteria: [AC-N list]. Recommend adding tests in a follow-up story."`

### Test Evidence Requirement

Based on the Story Type extracted in Phase 2, check for required evidence:

First determine the project domain from the story's CDD path or nearby concept
document (`game-concept.md` vs `product-concept.md`). Use the game table for game
stories and the product table for product stories. If domain is unknown and the
type exists in both domains (`UI`, `Integration`), use the stricter product rule
when the story references API/CLI/data/workflow/service terms; otherwise ask the
user which domain applies.

**[游戏专用]** Game evidence table:
| Story Type | Required Evidence | Gate Level |
|---|---|---|
| **Logic** | Automated unit test in `tests/unit/[system]/` — must exist and pass | BLOCKING |
| **Integration** | Integration test in `tests/integration/[system]/` OR playtest/session log doc | BLOCKING |
| **Visual/Feel** | Screenshot + sign-off in `production/qa/evidence/` | ADVISORY |
| **UI** | Manual walkthrough doc OR interaction test in `production/qa/evidence/` | ADVISORY |
| **Config/Data** | Smoke check pass report in `production/qa/smoke-*.md` | ADVISORY |

**[通用产品]** Product evidence table:
| Story Type | Required Evidence | Gate Level |
|---|---|---|
| **API** | Contract test (pytest/Vitest/cargo/go) in `tests/api/` — must pass | BLOCKING |
| **CLI** | Smoke command output in `production/qa/evidence/smoke/` — `--help` + core command | ADVISORY |
| **Data/Migration** | Migration test against fresh instance in `tests/integration/` | BLOCKING |
| **Auth/Permission** | Permission test in `tests/unit/auth/` or `tests/api/` — must pass | BLOCKING |
| **Workflow** | Integration test in `tests/integration/[module]/` — must pass | BLOCKING |
| **UI** | Walkthrough doc OR screenshot in `production/qa/evidence/` | ADVISORY |
| **Integration** | Integration test OR API contract test | BLOCKING |
| **Ops/Deployment** | Deployment smoke in `production/qa/smoke-*.md` | BLOCKING |
| **Config** | Config validation test OR smoke check | ADVISORY |

**Product evidence checks:**

- **API**: read the story's Test Evidence path first. If absent or missing,
  search `tests/api/` for a contract test referencing the story slug, endpoint,
  or TR-ID. If none found, flag **BLOCKING**.
- **CLI**: check `production/qa/evidence/smoke/`, `production/qa/evidence/manual/`, or
  `production/qa/smoke-*.md` for command output covering `--help` and the core
  command path. If none found, flag **ADVISORY**.
- **Data/Migration**: read the exact Test Evidence path first, then search
  `tests/integration/` for migration or fresh-instance tests. If none found,
  flag **BLOCKING**.
- **Auth/Permission**: search `tests/unit/auth/` and `tests/api/` for permission
  tests covering the role, token, or access boundary named by the story. If none
  found, flag **BLOCKING**.
- **Workflow**: read the exact Test Evidence path first, then search
  `tests/integration/[module]/` and `tests/integration/` for workflow coverage.
  If none found, flag **BLOCKING**.
- **UI**: check `production/qa/evidence/` for walkthrough or screenshot evidence,
  or an interaction test named in the story. If none found, flag **ADVISORY**.
- **Integration**: read the exact Test Evidence path first, then search
  `tests/integration/` and `tests/api/` for service, webhook, queue, or contract
  coverage. If none found, flag **BLOCKING**.
- **Ops/Deployment**: check for `production/qa/smoke-*.md`, CI evidence, or a
  deployment smoke artifact named in the story. If none found, flag **BLOCKING**.
- **Config**: check for a config validation test, smoke report, or evidence doc
  covering the changed environment variable, feature flag, or setting. If none
  found, flag **ADVISORY**.

**For game Logic stories**: first read the story's **Test Evidence** section to extract the
exact required file path. Use `Glob` to check that exact path. If the exact path is not
found, also search `tests/unit/[system]/` broadly (the file may have been placed at a
slightly different location). If no test file is found at either location:
- Flag as **BLOCKING**: "Logic story has no unit test file. Story requires it at
  `[exact-path-from-Test-Evidence-section]`. Create and run the test before marking
  this story Complete."

**For game Integration stories**: read the story's **Test Evidence** section for the exact
required path. Use `Glob` to check that exact path first, then search
`tests/integration/[system]/` broadly, then check `production/session-logs/`,
`production/qa/evidence/playtests/`, and `production/qa/evidence/` for a playtest or session
log record referencing this story.
If none found: flag as **BLOCKING** (same rule as Logic).

**For game Visual/Feel and game UI stories**: glob `production/qa/evidence/` for a file
referencing this story. If none: flag as **ADVISORY** —
"No manual test evidence found. Create `production/qa/evidence/[story-slug]-evidence.md`
using the test-evidence template and obtain sign-off before final closure."

**For game Config/Data stories**: check for any `production/qa/smoke-*.md` file.
If none: flag as **ADVISORY** — "No smoke check report found. Run `/smoke-check`."

**If no Story Type is set**: flag as **ADVISORY** —
"Story Type not declared. Add one domain-appropriate value: Game
`Logic|Integration|Visual/Feel|UI|Config/Data`, or Product
`API|CLI|Data/Migration|Auth/Permission|Workflow|UI|Integration|Ops/Deployment|Config`."

Any BLOCKING test evidence gap prevents the COMPLETE verdict in Phase 6.

---

## Phase 4: Check for Deviations

Compare the implementation against the design documents.

Run these checks automatically:

1. **CDD rules check**: Using the current requirement text from `tr-registry.yaml`
   (looked up by the story's TR-ID), check that the implementation reflects what
   the CDD actually requires now — not what it required when the story was written.
   `Grep` the implemented files for key function names, data structures, or class
   names mentioned in the current CDD section.

2. **Manifest version staleness check**: Compare the `Manifest Version:` date
   embedded in the story header against the `Manifest Version:` date in the
   current `docs/architecture/control-manifest.md` header.
   - If they match → pass silently.
   - If the story's version is older → flag as ADVISORY:
     "ADVISORY: Story was written against manifest v[story-date]; current manifest
     is v[current-date]. New rules may apply. Run /story-readiness to check."
   - If control-manifest.md does not exist → skip this check.

3. **ADR constraints check**: Read the referenced ADR's Decision section. Check
   for forbidden patterns from `docs/architecture/control-manifest.md` (if it
   exists). `Grep` for patterns explicitly forbidden in the ADR.

4. **Hardcoded values check**: `Grep` the implemented files for numeric literals
   in module logic that should be in data files.

5. **Scope check**: Did the implementation touch files outside the story's stated
   scope? (files not listed in "files to create/modify")

For each deviation found, categorize:

- **BLOCKING** — implementation contradicts the CDD or ADR (must fix before
  marking complete)
- **ADVISORY** — implementation drifts slightly from spec but is functionally
  equivalent (document, user decides)
- **OUT OF SCOPE** — additional files were touched beyond the story's stated
  boundary (flag for awareness — may be valid or scope creep)

---

## Phase 4b: QA Coverage Gate

**Review mode check** — apply before spawning QL-TEST-COVERAGE:
- `solo` → skip. Note: "QL-TEST-COVERAGE skipped — Solo mode." Proceed to Phase 5.
- `lean` → skip (not a PHASE-GATE). Note: "QL-TEST-COVERAGE skipped — Lean mode." Proceed to Phase 5.
- `full` → spawn as normal.

After completing the deviation checks in Phase 4, spawn `qa-lead` via Task using gate **QL-TEST-COVERAGE** (`standards/director-gates.md`).

Pass:
- The story file path and story type
- Test file paths found during Phase 3 (exact paths, or "none found")
- The story's `## QA Test Cases` section (the pre-written test specs from story creation)
- The story's `## Acceptance Criteria` list

The qa-lead reviews whether the tests actually cover what was specified — not just whether files exist.

Apply the verdict:
- **ADEQUATE** → proceed to Phase 5
- **GAPS** → flag as **ADVISORY**: "QA lead identified coverage gaps: [list]. Story can complete but gaps should be addressed in a follow-up story."
- **INADEQUATE** → flag as **BLOCKING**: "QA lead: critical logic is untested. Verdict cannot be COMPLETE until coverage improves. Specific gaps: [list]."

Skip this phase for advisory-only evidence story types when no code test is
required by the story: Game Config/Data; Product CLI / UI / Config. Do not skip
for Product API, Data/Migration, Auth/Permission, Workflow, Integration, or
Ops/Deployment stories.

---

## Phase 5: Lead Programmer Code Review Gate

**Review mode check** — apply before spawning LP-CODE-REVIEW:
- `solo` → skip. Note: "LP-CODE-REVIEW skipped — Solo mode." Proceed to Phase 6 (completion report).
- `lean` → skip (not a PHASE-GATE). Note: "LP-CODE-REVIEW skipped — Lean mode." Proceed to Phase 6 (completion report).
- `full` → spawn as normal.

Spawn `lead-programmer` via Task using gate **LP-CODE-REVIEW** (`standards/director-gates.md`).

Pass: implementation file paths, story file path, relevant CDD section, governing ADR.

Present the verdict to the user. If CONCERNS, surface them via `AskUserQuestion`:
- Options: `Revise flagged issues` / `Accept and proceed` / `Discuss further`
If REJECT, do not proceed to Phase 6 verdict until the issues are resolved.

If the story has no implementation files yet (verdict is being run before coding is done), skip this phase and note: "LP-CODE-REVIEW skipped — no implementation files found. Run after implementation is complete."

---

## Phase 6: Present the Completion Report

Before updating any files, present the full report:

```markdown
## Story Done: [Story Name]
**Story**: [file path]
**Date**: [today]

### Acceptance Criteria: [X/Y passing]
- [x] [Criterion 1] — auto-verified (test passes)
- [x] [Criterion 2] — confirmed
- [ ] [Criterion 3] — FAILS: [reason]
- [?] [Criterion 4] — DEFERRED: requires playtest/user test/deployment session

### Test-Criterion Traceability
| Criterion | Test | Status |
|-----------|------|--------|
| AC-1: [text] | [test file::test name] | COVERED |
| AC-2: [text] | Manual confirmation | COVERED |
| AC-3: [text] | — | UNTESTED |

### Test Evidence
**Story Type**: [Game: Logic | Integration | Visual/Feel | UI | Config/Data] OR [Product: API | CLI | Data/Migration | Auth/Permission | Workflow | UI | Integration | Ops/Deployment | Config] OR [Not declared]
**Required evidence**: [domain-specific required evidence from the game/product table]
**Evidence found**: [YES — `[path]` | NO — BLOCKING | NO — ADVISORY]

### Deviations
[NONE] OR:
- BLOCKING: [description] — [CDD/ADR reference]
- ADVISORY: [description] — user accepted / flagged for tech debt

### Scope
[All changes within stated scope] OR:
- Extra files touched: [list] — [note whether valid or scope creep]

### Verdict: COMPLETE / COMPLETE WITH NOTES / BLOCKED
```

**Verdict definitions:**
- **COMPLETE**: all criteria pass, no blocking deviations
- **COMPLETE WITH NOTES**: all criteria pass, advisory deviations documented
- **BLOCKED**: failing criteria or blocking deviations must be resolved first

If the verdict is **BLOCKED**: do not proceed to Phase 7. List what must be
fixed. Offer to help fix the blocking items.

---

## Phase 7: Update Story Status

Ask before writing: "May I update the story file to mark it Complete and log
the completion notes?"

If yes, edit the story file:

1. Update the status field: `Status: Complete`
2. Add a `## Completion Notes` section at the bottom:

```markdown
## Completion Notes
**Completed**: [date]
**Criteria**: [X/Y passing] ([any deferred items listed])
**Deviations**: [None] or [list of advisory deviations]
**Test Evidence**: [story type: test/smoke/evidence path, or manual evidence deferred]
**Code Review**: [Pending / Complete / Skipped]
```

3. If advisory deviations exist, ask: "Should I log these as tech debt in
   `docs/tech-debt-register.md`?"

4. **Update `production/sprint-status.yaml`** (if it exists):
   - Find the entry matching this story's file path or ID
   - Set `status: done` and `completed: [today's date]`
   - Update the top-level `updated` field
   - This is a silent update — no extra approval needed (already approved in step above)

### Session State Update

After updating the story file, silently append to
`production/session-state/active.md`:

    ## Session Extract — /story-done [date]
    - Verdict: [COMPLETE / COMPLETE WITH NOTES / BLOCKED]
    - Story: [story file path] — [story title]
    - Tech debt logged: [N items, or "None"]
    - Next recommended: [next ready story title and path, or "None identified"]

If `active.md` does not exist, create it with this block as the initial content.
Confirm in conversation: "Session state updated."

### Memory Bank Story Closure Index

When `memory_bank/` exists and the story is marked Complete, also update
`memory_bank/t3_archive/sprint_snapshots/story-closure-index.md`.

- Completion Verdict: COMPLETE, COMPLETE WITH RISKS, or BLOCKED
- Use `Story Path` as the dedupe key.
- If the same story path already exists, update Date, Completion Verdict,
  Evidence Paths, Review Path, and Remaining Risks instead of adding a duplicate
  row.
- If `memory_bank/` does not exist, do not create it from `/story-done`; keep
  the existing story, sprint-status, and session-state behavior and say:
  "Run `/constitute` to establish the memory_bank governance control plane."

---

## Phase 8: Surface the Next Story

After completion, help the developer keep momentum:

1. Read the current sprint plan from `production/sprints/`.
2. Find stories that are:
   - Status: READY or NOT STARTED
   - Not blocked by other incomplete stories
   - In the Must Have or Should Have tier

Present:

```
### Next Up
The following stories are ready to pick up:
1. [Story name] — [1-line description] — Est: [X hrs]
2. [Story name] — [1-line description] — Est: [X hrs]

Run `/story-readiness [path]` to confirm a story is implementation-ready
before starting.
```

If no more Must Have stories remain in this sprint (all are Complete or Blocked):

```
### Sprint Close-Out Sequence

All Must Have stories are complete. QA sign-off is required before advancing.
Run these in order:

1. `/smoke-check sprint` — verify the critical path still works end-to-end
2. `/team-qa sprint` — full QA cycle: test case execution, bug triage, sign-off report
3. `/gate-check` — advance to the next phase once QA approves

Do not run `/gate-check` until `/team-qa` returns APPROVED or APPROVED WITH CONDITIONS.
```

If there are Should Have stories still unstarted, surface them alongside the close-out sequence so the user can choose: close the sprint now, or pull in more work first.

If no more stories are ready but Must Have stories are still In Progress (not Complete):
"No more stories ready to start — [N] Must Have stories still in progress. Continue implementing those before sprint close-out."

---

## Collaborative Protocol

- **Never mark a story complete without user approval** — Phase 7 requires an
  explicit "yes" before any file is edited.
- **Never auto-fix failing criteria** — report them and ask what to do.
- **Deviations are facts, not judgments** — present them neutrally; the user
  decides if they are acceptable.
- **BLOCKED verdict is advisory** — the user can override and mark complete
  anyway; document the risk explicitly if they do.
- Use `AskUserQuestion` for the code review prompt and for batching manual
  criteria confirmations.

---

## Recommended Next Steps

- Run `/story-readiness [next-story-path]` to validate the next story before starting implementation
- If all Must Have stories are complete: run `/smoke-check sprint` → `/team-qa sprint` → `/gate-check`
- If tech debt was logged: track it via `/tech-debt` to keep the register current
