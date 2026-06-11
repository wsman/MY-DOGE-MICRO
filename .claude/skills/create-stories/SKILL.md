---
name: create-stories
description: "Break a single epic into implementable story files. Reads the epic, its CDD, governing ADRs, and control manifest. Each story embeds its CDD requirement TR-ID, ADR guidance, acceptance criteria, story type, and test evidence path. Run after /create-epics for each epic."
argument-hint: "[epic-slug | epic-path] [--review full|lean|solo]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Task, AskUserQuestion
agent: lead-programmer
---

## User Guide

- When to use: Break a single epic into implementable story files. Reads the epic, its CDD, governing ADRs, and control manifest. Each story embeds its CDD requirement TR-ID, ADR guidance, acceptance criteria, story type, and test evidence path. Run after /create-epics for each epic.
- Inputs: Command arguments: `/create-stories [epic-slug | epic-path] [--review full|lean|solo]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: None.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

# Create Stories

A story is a single implementable behaviour — small enough to complete in one
focused session, self-contained, and fully traceable to a CDD requirement and
an ADR decision. Stories are what developers pick up. Epics are what architects
define.

**Run this skill per epic**, not per layer. Run it for Foundation epics first,
then Core, and so on — matching the dependency order.

**Output:** story files under `production/epics/[epic-slug]/`, named `story-NNN-[slug].md`

**Previous step:** `/create-epics [system]`
**Next step after stories exist:** `/story-readiness [story-path]` then `/dev-story [story-path]`

---

## 1. Parse Argument

Extract `--review [full|lean|solo]` if present and store as the review mode
override for this run. If not provided, read `production/review-mode.txt`
(default `full` if missing). This resolved mode applies to all gate spawns
in this skill — apply the check pattern from `standards/director-gates.md`
before every gate invocation.

- `/create-stories [epic-slug]` — e.g. `/create-stories combat`
- `/create-stories production/epics/combat/EPIC.md` — full path also accepted
- No argument — ask: "Which epic would you like to break into stories?"
  Glob `production/epics/*/EPIC.md` and list available epics with their status.

---

## 2. Load Everything for This Epic

Read in full:

- `production/epics/[epic-slug]/EPIC.md` — epic overview, governing ADRs, CDD requirements table
- The epic's CDD (`design/cdd/[filename].md`) — read all 8 sections, especially Acceptance Criteria, Formulas, and Edge Cases
- All governing ADRs listed in the epic — read the Decision, Implementation Guidelines, and Technology Compatibility (Engine Compatibility for game, Technology/Stack Compatibility for product) sections
- `docs/architecture/control-manifest.md` — extract rules for this epic's layer; note the Manifest Version date from the header
- `docs/architecture/tr-registry.yaml` — load all TR-IDs for this system

**ADR existence validation**: After reading the governing ADRs list from the epic, confirm each ADR file exists on disk. If any ADR file cannot be found, **stop immediately** before decomposing any story:

> "Epic references [ADR-NNNN: title] but `docs/architecture/[adr-file].md` was not found.
> Check the filename in the epic's Governing ADRs list, or run `/architecture-decision`
> to create it. Cannot create stories until all referenced ADR files are present."

Do not proceed to Step 3 until all referenced ADR files are confirmed present.

Report: "Loaded epic [name], CDD [filename], [N] governing ADRs (all confirmed present), control manifest v[date]."

---

## 3. Classify Stories by Type

**Story Type Classification** — assign each story a type based on its acceptance criteria:

**[游戏专用]** Game story types:
| Story Type | Assign when criteria reference... |
|---|---|
| Logic | formulas, calculations, state machines, algorithms |
| Integration | cross-system data flow, signals, save/load round-trips between game systems |
| Visual/Feel | animations, VFX, shaders, feel, juice, timing, audio sync |
| UI | menus, HUD, player-facing displays, input handling |
| Config/Data | tuning values, item databases, level data, game constants |

**[通用产品]** Product story types:
| Story Type | Assign when criteria reference... |
|---|---|
| API | endpoint contracts, request/response shapes, status codes |
| CLI | command-line interface, argument parsing, output formatting |
| Data/Migration | schema changes, data transformations, migration scripts |
| Auth/Permission | authentication, authorization, role-based access |
| Workflow | multi-step business logic, state machines, process orchestration |
| UI | screens, components, user-facing interactions |
| Integration | external service calls, webhooks, message queues |
| Ops/Deployment | CI/CD, containerization, infrastructure, monitoring |
| Config | environment variables, feature flags, application settings |

Mixed stories: assign the type that carries the highest implementation risk.
The type determines what test evidence is required before `/story-done` can close the story.

---

## 4. Decompose the CDD into Stories

For each CDD acceptance criterion:

1. Group related criteria that require the same core implementation
2. Each group = one story
3. Order stories: foundational behaviour first, edge cases last, UI last

**Story sizing rule:** one story = one focused session (~2-4 hours). If a
group of criteria would take longer, split into two stories.

For each story, determine:
- **CDD requirement**: which acceptance criterion(ia) does this satisfy?
- **TR-ID**: look up in `tr-registry.yaml`. Use the stable ID. If no match, use `TR-[system]-???` and warn.
- **Governing ADR**: which ADR governs how to implement this?
  - `Status: Accepted` → embed normally
  - `Status: Proposed` → set story `Status: Blocked` with note: "BLOCKED: ADR-NNNN is Proposed — run `/architecture-decision` to advance it"
- **Story Type**: from Step 3 classification
- **Technology risk**: from the ADR's Knowledge Risk field

---

## 4b. QA Lead Story Readiness Gate

**Review mode check** — apply before spawning QL-STORY-READY:
- `solo` → skip. Note: "QL-STORY-READY skipped — Solo mode." Proceed to Step 5 (present stories for review).
- `lean` → skip (not a PHASE-GATE). Note: "QL-STORY-READY skipped — Lean mode." Proceed to Step 5 (present stories for review).
- `full` → spawn as normal.

After decomposing all stories (Step 4 complete) but before presenting them for write approval, spawn `qa-lead` via Task using gate **QL-STORY-READY** (`standards/director-gates.md`).

Pass: the full story list with acceptance criteria, story types, and TR-IDs; the epic's CDD acceptance criteria for reference.

Present the QA lead's assessment. For each story flagged as GAPS or INADEQUATE, revise the acceptance criteria before proceeding — stories with untestable criteria cannot be implemented correctly. Once all stories reach ADEQUATE, proceed.

**After ADEQUATE**: ask the qa-lead to produce concrete test case specifications
for every automated-evidence story type — Game: Logic / Integration; Product:
API / Data/Migration / Auth/Permission / Workflow / Integration. Produce one
test case per acceptance criterion in this format:

```
Test: [criterion text]
  Given: [precondition]
  When: [action]
  Then: [expected result / assertion]
  Edge cases: [boundary values or failure states to test]
```

For manual or smoke-evidence story types — Game: Visual/Feel / UI / Config/Data;
Product: CLI / UI / Ops/Deployment / Config — produce verification steps instead:
```
Manual check: [criterion text]
  Setup: [how to reach the state]
  Verify: [what to look for]
  Pass condition: [unambiguous pass description]
```

These test case specs are embedded directly into each story's `## QA Test Cases` section. The developer implements against these cases. The programmer does not write tests from scratch — QA has already defined what "done" looks like.

---

## 5. Present Stories for Review

Before writing any files, present the full story list:

```
## Stories for Epic: [name]

Story 001: [title] — Logic — ADR-NNNN
  Covers: TR-[system]-001 ([1-line summary of requirement])
  Test required: tests/unit/[system]/[slug]_test.[ext]

Story 002: [title] — Integration — ADR-MMMM
  Covers: TR-[system]-002, TR-[system]-003
  Test required: tests/integration/[system]/[slug]_test.[ext]

Story 003: [title] — Visual/Feel — ADR-NNNN
  Covers: TR-[system]-004
  Evidence required: production/qa/evidence/[slug]-evidence.md

Product example:

Story 001: [title] — API — ADR-NNNN
  Covers: TR-[system]-001 ([1-line summary of requirement])
  Test required: tests/api/[slug]_test.[ext]

Story 002: [title] — Workflow — ADR-MMMM
  Covers: TR-[system]-002
  Test required: tests/integration/[module]/[slug]_test.[ext]

[N stories total, grouped by the domain-appropriate Story Type list]
```

Use `AskUserQuestion`:
- Prompt: "May I write these [N] stories to `production/epics/[epic-slug]/`?"
- Options: `[A] Yes — write all [N] stories` / `[B] Not yet — I want to review or adjust first`

---

## 6. Write Story Files

For each story, write a file under `production/epics/[epic-slug]/` named `story-[NNN]-[slug].md`:

```markdown
# Story [NNN]: [title]

> **Epic**: [epic name]
> **Status**: Ready
> **Layer**: [Foundation / Core / Feature / Presentation]
> **Type**: [one Story Type from the game or product list]
> **Manifest Version**: [date from control-manifest.md header]

## Context

**CDD**: `design/cdd/[filename].md`
**Requirement**: `TR-[system]-NNN`
*(Requirement text lives in `docs/architecture/tr-registry.yaml` — read fresh at review time)*

**ADR Governing Implementation**: [ADR-NNNN: title]
**ADR Decision Summary**: [1-2 sentence summary of what the ADR decided]

**Technology**: [engine or stack name + version] | **Risk**: [LOW / MEDIUM / HIGH]
**Technology Notes**: [from ADR Engine Compatibility or Technology/Stack Compatibility section — post-cutoff APIs, verification required]

**Control Manifest Rules (this layer)**:
- Required: [relevant required pattern]
- Forbidden: [relevant forbidden pattern]
- Guardrail: [relevant performance guardrail]

---

## Acceptance Criteria

*From CDD `design/cdd/[filename].md`, scoped to this story:*

- [ ] [criterion 1 — directly from CDD]
- [ ] [criterion 2]
- [ ] [performance criterion if applicable]

---

## Implementation Notes

*Derived from ADR-NNNN Implementation Guidelines:*

[Specific, actionable guidance from the ADR. Do not paraphrase in ways that
change meaning. This is what the programmer reads instead of the ADR.]

---

## Out of Scope

*Handled by neighbouring stories — do not implement here:*

- [Story NNN+1]: [what it handles]

---

## QA Test Cases

*Written by qa-lead at story creation. The developer implements against these — do not invent new test cases during implementation.*

**[For automated-evidence stories — Game Logic/Integration; Product API/Data-Migration/Auth-Permission/Workflow/Integration]:**

- **AC-1**: [criterion text]
  - Given: [precondition]
  - When: [action]
  - Then: [assertion]
  - Edge cases: [boundary values / failure states]

**[For manual or smoke-evidence stories — Game Visual/Feel/UI/Config/Data; Product CLI/UI/Ops-Deployment/Config]:**

- **AC-1**: [criterion text]
  - Setup: [how to reach the state]
  - Verify: [what to look for]
  - Pass condition: [unambiguous pass description]

---

## Test Evidence

**Story Type**: [type]
**Required evidence**:

**[游戏专用] Game evidence**
- Logic: `tests/unit/[system]/[story-slug]_test.[ext]` — must exist and pass
- Integration: `tests/integration/[system]/[story-slug]_test.[ext]` OR playtest/session log doc
- Visual/Feel: `production/qa/evidence/[story-slug]-evidence.md` + sign-off
- UI: `production/qa/evidence/[story-slug]-evidence.md` or interaction test
- Config/Data: smoke check pass (`production/qa/smoke-*.md`)

**[通用产品] Product evidence**
- API: contract test in `tests/api/[story-slug]_test.[ext]` — must exist and pass
- CLI: command smoke evidence in `production/qa/evidence/smoke/[story-slug].md`
- Data/Migration: migration test in `tests/integration/[story-slug]_test.[ext]` — must exist and pass
- Auth/Permission: permission test in `tests/unit/auth/` or `tests/api/` — must exist and pass
- Workflow: integration test in `tests/integration/[module]/[story-slug]_test.[ext]` — must exist and pass
- UI: walkthrough doc or screenshot in `production/qa/evidence/[story-slug]-evidence.md`
- Integration: integration test or API contract test — must exist and pass
- Ops/Deployment: deployment smoke report in `production/qa/smoke-*.md`
- Config: config validation test or smoke check report

**Status**: [ ] Not yet created

---

## Dependencies

- Depends on: [Story NNN-1 must be DONE, or "None"]
- Unlocks: [Story NNN+1, or "None"]
```

### Also update `production/epics/[epic-slug]/EPIC.md`

Replace the "Stories: Not yet created" line with a populated table:

```markdown
## Stories

| # | Story | Type | Status | ADR |
|---|-------|------|--------|-----|
| 001 | [title] | Logic | Ready | ADR-NNNN |
| 002 | [title] | Integration | Ready | ADR-MMMM |
```

---

## 7. After Writing

Use `AskUserQuestion` to close with context-aware next steps:

Check:
- Are there other epics in `production/epics/` without stories yet? List them.
- Is this the last epic? If so, include `/sprint-plan` as an option.

Widget:
- Prompt: "[N] stories written to `production/epics/[epic-slug]/`. What next?"
- Options (include all that apply):
  - `[A] Start implementing — run /story-readiness [first-story-path]` (Recommended)
  - `[B] Create stories for [next-epic-slug] — run /create-stories [slug]` (only if other epics have no stories yet)
  - `[C] Plan the sprint — run /sprint-plan` (only if all epics have stories)
  - `[D] Stop here for this session`

Note in output: "Work through stories in order — each story's `Depends on:` field tells you what must be DONE before you can start it."

---

## Collaborative Protocol

1. **Read before presenting** — load all inputs silently before showing the story list
2. **Ask once** — present all stories for the epic in one summary, not one at a time
3. **Warn on blocked stories** — flag any story with a Proposed ADR before writing
4. **Ask before writing** — get approval for the full story set before writing files
5. **No invention** — acceptance criteria come from CDDs, implementation notes from ADRs, rules from the manifest
6. **Never start implementation** — this skill stops at the story file level

After writing (or declining):

- **Verdict: COMPLETE** — [N] stories written to `production/epics/[epic-slug]/`. Run `/story-readiness` → `/dev-story` to begin implementation.
- **Verdict: BLOCKED** — user declined. No story files written.
