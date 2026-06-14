---
name: test-evidence-review
description: "Quality review of test files and manual evidence documents. Goes beyond existence checks — evaluates assertion coverage, edge case handling, naming conventions, and evidence completeness. Produces ADEQUATE/INCOMPLETE/MISSING verdict per story. Run before QA sign-off or on demand."
argument-hint: "[story-path | sprint | system-name]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write
---

## User Guide

- When to use: Quality review of test files and manual evidence documents. Goes beyond existence checks — evaluates assertion coverage, edge case handling, naming conventions, and evidence completeness. Produces ADEQUATE/INCOMPLETE/MISSING verdict per story. Run before QA sign-off or on demand.
- Inputs: Command arguments: `/test-evidence-review [story-path | sprint | system-name]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: `memory_bank/t3_archive/qa_evidence_index.md`, `memory_bank/t3_archive/reviews/review-index.md`.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

## Phase 0: Domain Routing

Detect the project domain before reviewing evidence:
- `design/cdd/game-concept.md` -> **[Game]** review unit/integration tests, smoke checks, manual playtest records, session logs, screenshots, input/platform evidence, and CDD acceptance coverage.
- `design/cdd/product-concept.md` -> **[Product]** review contract tests, CLI smoke output, migration evidence, auth/permission checks, integration traces, deployment smoke logs, screenshots, user-test notes, and CDD acceptance coverage.
- If unclear, ask whether evidence should prove game playability or product workflow/API/CLI correctness.

Preserve playtest evidence lookup. Product evidence lookup is a parallel branch.

## Dual-Domain Parity Contract

| Area | Game branch | Product branch |
|------|-------------|----------------|
| Context reads | Story files, CDD acceptance, unit/integration tests, playtest/session logs, screenshots, smoke reports | Story files, CDD acceptance/contracts, contract/API tests, CLI smoke output, migration dry-run logs, auth/permission evidence, integration traces, deployment smoke, user-test notes |
| Steps | Locate evidence by story type, read tests/docs, assess assertions, edge cases, naming, manual evidence completeness, sign-off | Locate evidence by product story type, read tests/logs/docs, assess contract coverage, CLI outputs, migration safety, permission matrix, observability/deployment evidence, sign-off |
| Outputs | In-conversation verdicts and optional `production/qa/evidence-review-[date].md` with ADEQUATE/INCOMPLETE/MISSING per story | Same report path with product-specific ADEQUATE/INCOMPLETE/MISSING verdicts and evidence gaps by contract/workflow/ops category |
| Next steps | Add missing tests/evidence, rerun `/smoke-check`, coordinate `/team-qa` | Add missing contract/CLI/migration/auth/deployment/user-test evidence, rerun `/smoke-check`, coordinate `/team-qa` |

# Test Evidence Review

`/smoke-check` verifies that test files **exist** and **pass**. This skill
goes further — it reviews the **quality** of those tests and evidence documents.
A test file that exists and passes may still leave critical behaviour uncovered.
A manual evidence doc that exists may lack the sign-offs required for closure.

**Output:** Summary report (in conversation) + optional `production/qa/evidence-review-[date].md`

**When to run:**
- Before QA hand-off sign-off (`/team-qa` Phase 5)
- On any story where test quality is in question
- As part of milestone review for Logic and Integration story quality audit

---

## 1. Parse Arguments

**Modes:**
- `/test-evidence-review [story-path]` — review a single story's evidence
- `/test-evidence-review sprint` — review all stories in the current sprint
- `/test-evidence-review [system-name]` — review all stories in an epic/system
- No argument — ask which scope: "Single story", "Current sprint", "A system"

---

## 2. Load Stories in Scope

Based on the argument:

**Single story**: Read the story file directly. Extract: Story Type, Test
Evidence section, story slug, system name.

**Sprint**: Read the most recently modified file in `production/sprints/`.
Extract the list of story file paths from the sprint plan. Read each story file.

**System**: Glob story files under the matching system directory in `production/epics/`. Read each.

For each story, collect:
- `Type:` field (Logic / Integration / Visual/Feel / UI / Config/Data)
- `## Test Evidence` section — the stated expected test file path or evidence doc
- Story slug (from file name)
- System name (from directory path)
- Acceptance Criteria list (all checkbox items)

---

## 3. Locate Evidence Files

For each story, find the evidence:

**Logic stories**: Glob `tests/unit/[system]/[story-slug]_test.*`
  - If not found, also try: Grep in `tests/unit/[system]/` for files
    containing the story slug

**Integration stories**: Glob `tests/integration/[system]/[story-slug]_test.*`
  - Also check `production/session-logs/` for playtest records mentioning the story

**Visual/Feel and UI stories**: Glob `production/qa/evidence/[story-slug]-evidence.*`

**Config/Data stories**: Glob `production/qa/smoke-*.md` (any smoke check report)

Note what was found (path) or not found (gap) for each story.

---

## 4. Review Automated Test Quality (Logic / Integration)

For each test file found, read it and evaluate:

### Assertion coverage

Count the number of distinct assertions (lines containing assert, expect,
check, verify, or engine-specific assertion patterns). Low assertion count is
a quality signal — a test that makes only 1 assertion per test function may
not cover the range of expected behaviour.

Thresholds:
- **3+ assertions per test function** → normal
- **1-2 assertions per test function** → note as potentially thin
- **0 assertions** (test exists but no asserts) → flag as BLOCKING — the
  test passes vacuously and proves nothing

### Edge case coverage

For each acceptance criterion in the story that contains a number, threshold,
or "when X happens" conditional: check whether a test function name or
test body references that specific case.

Heuristics:
- Grep test file for "zero", "max", "null", "empty", "min", "invalid",
  "boundary", "edge" — presence of any is a positive signal
- If the story has a Formulas section with specific bounds: check whether
  tests exercise at minimum/maximum values

### Naming quality

Test function names should describe: the scenario + the expected result.
Pattern: `test_[scenario]_[expected_outcome]`

Flag functions named generically (`test_1`, `test_run`, `testBasic`) as
**naming issues** — they make failures harder to diagnose.

### Formula traceability

For Logic stories where the CDD has a Formulas section: check that the test
file contains at least one test whose name or comment references the formula
name or a formula value. A test that exercises a formula without mentioning
it by name is harder to maintain when the formula changes.

---

## 5. Review Manual Evidence Quality (Visual/Feel / UI)

For each evidence document found, read it and evaluate:

### Criterion linkage

The evidence doc should reference each acceptance criterion from the story.
Check: does the evidence doc contain each criterion (or a clear rephrasing)?
Missing criteria mean a criterion was never verified.

### Sign-off completeness

Check for three sign-off lines (or equivalent fields):
- Developer sign-off
- Designer / art-lead sign-off (for Visual/Feel)
- QA lead sign-off

If any are missing or blank: flag as INCOMPLETE — the story cannot be fully
closed without all required sign-offs.

### Screenshot / artefact completeness

For Visual/Feel stories: check whether screenshot file paths are referenced
in the evidence doc. If referenced, Glob for them to confirm they exist.

For UI stories: check whether a walkthrough sequence (step-by-step interaction
log) is present.

### Date coverage

Evidence doc should have a date. If the date is earlier than the story's
last major change (heuristic: compare against sprint start date from the sprint
plan), flag as POTENTIALLY STALE — the evidence may not cover the final
implementation.

---

## 6. Build the Review Report

For each story, assign a verdict:

| Verdict | Meaning |
|---------|---------|
| **ADEQUATE** | Test/evidence exists, passes quality checks, all criteria covered |
| **INCOMPLETE** | Test/evidence exists but has quality gaps (thin assertions, missing sign-offs) |
| **MISSING** | No test or evidence found for a story type that requires it |

The overall sprint/system verdict is the worst story verdict present.

```markdown
## Test Evidence Review

> **Date**: [date]
> **Scope**: [single story path | Sprint [N] | [system name]]
> **Stories reviewed**: [N]
> **Overall verdict**: ADEQUATE / INCOMPLETE / MISSING

---

### Story-by-Story Results

#### [Story Title] — [Type] — [ADEQUATE/INCOMPLETE/MISSING]

**Test/evidence path**: `[path]` (found) / (not found)

**Automated test quality** *(Logic/Integration only)*:
- Assertion coverage: [N per function on average] — [adequate / thin / none]
- Edge cases: [covered / partial / not found]
- Naming: [consistent / [N] generic names flagged]
- Formula traceability: [yes / no — formula names not referenced in tests]

**Manual evidence quality** *(Visual/Feel/UI only)*:
- Criterion linkage: [N/M criteria referenced]
- Sign-offs: [Developer ✓ | Designer ✗ | QA Lead ✗]
- Artefacts: [screenshots present / missing / N/A]
- Freshness: [dated [date] — current / potentially stale]

**Issues**:
- BLOCKING: [description] *(prevents story-done)*
- ADVISORY: [description] *(should fix before release)*

---

### Summary

| Story | Type | Verdict | Issues |
|-------|------|---------|--------|
| [title] | Logic | ADEQUATE | None |
| [title] | Integration | INCOMPLETE | Thin assertions (avg 1.2/function) |
| [title] | Visual/Feel | INCOMPLETE | QA lead sign-off missing |
| [title] | Logic | MISSING | No test file found |

**BLOCKING items** (must resolve before story can be closed): [N]
**ADVISORY items** (should address before release): [N]
```

---

## 7. Write Output (Optional)

Present the report in conversation.

Ask: "May I write this test evidence review to
`production/qa/evidence-review-[date].md`?"

This is optional — the report is useful standalone. Write only if the user
wants a persistent record.

When `memory_bank/` exists and the user approves writing the evidence review,
also update:

- `memory_bank/t3_archive/reviews/review-index.md`
- `memory_bank/t3_archive/qa_evidence_index.md`

For the review index, use Review Type `test-evidence-review` and Source Artifact
`production/qa/evidence-review-[date].md`. For the QA evidence index, use Type
`test-evidence-review`. Dedupe both indexes by source or evidence path; update
Date, Verdict, and Follow-up Owner for an existing path instead of adding a
duplicate row.

If `memory_bank/` does not exist, do not create it from `/test-evidence-review`;
keep the existing report behavior and say: "Run `/constitute` to establish the
memory_bank governance control plane."

After the report:

- For BLOCKING items: "These must be resolved before `/story-done` can mark the
  story Complete. Would you like to address any of them now?"
- For thin assertions: "Consider running `/test-helpers [system]` to see
  scaffolded assertion patterns for common cases."
- For missing sign-offs: "Manual sign-off is required from [role]. Share
  `[evidence-path]` with them to complete sign-off."

Verdict: **COMPLETE** — evidence review finished. Use CONCERNS if BLOCKING items were found.

---

## Collaborative Protocol

- **Report quality issues, do not fix them** — this skill reads and evaluates;
  it does not modify test files or evidence documents
- **ADEQUATE means adequate for shipping, not perfect** — avoid nitpicking
  tests that are functioning and comprehensive enough to give confidence
- **BLOCKING vs. ADVISORY distinction is important** — only flag BLOCKING when
  the gap leaves a story criterion genuinely unverified
- **Ask before writing** — the report file is optional; always confirm before writing
