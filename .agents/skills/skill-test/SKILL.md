---
name: skill-test
description: "Validate skill files for structural compliance and behavioral correctness. Three modes: static (linter), spec (behavioral), audit (coverage report)."
argument-hint: "static [skill-name | all] | spec [skill-name] | category [skill-name | all] | audit"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write
---

## User Guide

- When to use: Validate skill files for structural compliance and behavioral correctness. Three modes: static (linter), spec (behavioral), audit (coverage report).
- Inputs: Command arguments: `/skill-test static [skill-name | all] | spec [skill-name] | category [skill-name | all] | audit`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Static/spec/category/audit reports. Approved writes go to `memory_bank/t3_archive/skill_testing/results/` and update `memory_bank/t3_archive/skill_testing/coverage-index.yaml`.
- Memory-bank writes: Reads canonical test assets from `skill_testing/`; with approval writes T3 test evidence under `memory_bank/t3_archive/skill_testing/`.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

## Phase 0: Domain Routing

Detect the skill domain before testing:
- **[Game]** verify game examples, player/gameplay/engine language, playtest references, and game CDD paths remain valid.
- **[Product]** verify product examples, API/CLI/web/data language, product-concept paths, stack references, and product evidence paths remain valid.
- **[Both]** check that dual-domain skills preserve both branches and do not hide game-only content from game workflows.

A passing skill test must not require deleting game-specific examples.
# Skill Test

Validates `.agents/skills/*/SKILL.md` files for structural compliance and
behavioral correctness. No external dependencies — runs entirely within the
existing skill/hook/template architecture.

**Four modes:**

| Mode | Command | Purpose | Token Cost |
|------|---------|---------|------------|
| `static` | `/skill-test static [name\|all]` | Structural linter — 7 compliance checks per skill | Low (~1k/skill) |
| `spec` | `/skill-test spec [name]` | Behavioral verifier — evaluates assertions in test spec | Medium (~5k/skill) |
| `category` | `/skill-test category [name\|all]` | Category rubric — checks skill against its category-specific metrics | Low (~2k/skill) |
| `audit` | `/skill-test audit` | Coverage report — skills, agent specs, last test dates | Low (~3k total) |

---

## Phase 1: Parse Arguments

Determine mode from the first argument:

- `static [name]` → run 8 structural/parity checks on one skill
- `static all` → run 8 structural/parity checks on all skills (Glob `.agents/skills/*/SKILL.md`)
- `spec [name]` → read skill + test spec, evaluate assertions
- `category [name]` → run category-specific rubric from `skill_testing/quality-rubric.md`
- `category all` → run category rubric for every skill that has a `category:` in catalog
- `audit` (or no argument) → read catalog, list all skills and agents, show coverage

If argument is missing or unrecognized, output usage and stop.

---

## Phase 2A: Static Mode — Structural Linter

For each skill being tested, read its `SKILL.md` fully and run all 8 checks:

### Check 1 — Required Frontmatter Fields
The file must contain all of these in the YAML frontmatter block:
- `name:`
- `description:`
- `argument-hint:`
- `user-invocable:`
- `allowed-tools:`

**FAIL** if any are absent.

### Check 2 — Multiple Phases
The skill must have ≥2 numbered phase headings. Look for patterns like:
- `## Phase N` or `## Phase N:`
- `## N.` (numbered top-level sections)
- At least 2 distinct `##` headings if phases aren't explicitly numbered

**FAIL** if fewer than 2 phase-like headings are found.

### Check 3 — Verdict Keywords
The skill must contain at least one of: `PASS`, `FAIL`, `CONCERNS`, `APPROVED`,
`BLOCKED`, `COMPLETE`, `READY`, `COMPLIANT`, `NON-COMPLIANT`

**FAIL** if none are present.

### Check 4 — Collaborative Protocol Language
The skill must contain ask-before-write language. Look for:
- `"May I write"` (canonical form)
- `"before writing"` or `"approval"` near file-write instructions
- `"ask"` + `"write"` in close proximity (within same section)

**WARN** if absent (some read-only skills legitimately skip this).
**FAIL** if `allowed-tools` includes `Write` or `Edit` but no ask-before-write language is found.

### Check 5 — Next-Step Handoff
The skill must end with a recommended next action or follow-up path. Look for:
- A final section mentioning another skill (e.g., `/story-done`, `/gate-check`)
- "Recommended next" or "next step" phrasing
- A "Follow-Up" or "After this" section

**WARN** if absent.

### Check 6 — Fork Context Complexity
If frontmatter contains `context: fork`, the skill should have ≥5 phase headings
(`##` level or numbered Phase N headers). Fork context is for complex multi-phase
skills; simple skills should not use it.

**WARN** if `context: fork` is set but fewer than 5 phases found.

### Check 7 — Argument Hint Plausibility
`argument-hint` must be non-empty. If the skill body mentions multiple modes
(e.g., "Mode A | Mode B"), the hint should reflect them. Cross-reference the
hint against the first phase's "Parse Arguments" section.

**WARN** if hint is `""` or if documented modes don't match hint.

### Check 8 — Dual-Domain Parity

If the skill advertises Product support in frontmatter or Phase 0, it must also
contain Product-specific implementation guidance beyond the first 50 lines.
Look for at least two of:
- Product context reads (`product-concept.md`, Product CDDs, `docs/reference/<stack>/`, language specialist, API/CLI/UI/data docs)
- Product-specific steps/checks/templates
- Product output report/spec format
- Product next-step handoff

**WARN** if Product appears only near the top of the file.
**FAIL** if the skill claims Product support but the body remains game-only and
would route a Product project through engine/player/playtest/HUD-only behavior.

Also check that game content is preserved:
- Game markers, player/gameplay/engine examples, playtest references, or game
  CDD paths must not be removed when Product support is added.
- A passing dual-domain skill may include game-only sections, as long as Product
  sections are present beside them for Product workflows.

---

### Static Mode Output Format

For a single skill:
```
=== Skill Static Check: /[name] ===

Check 1 — Frontmatter Fields:    PASS
Check 2 — Multiple Phases:       PASS (7 phases found)
Check 3 — Verdict Keywords:      PASS (PASS, FAIL, CONCERNS)
Check 4 — Collaborative Protocol: PASS ("May I write" found)
Check 5 — Next-Step Handoff:     WARN (no follow-up section found)
Check 6 — Fork Context Complexity: PASS (8 phases, context: fork set)
Check 7 — Argument Hint:         PASS

Verdict: WARNINGS (1 warning, 0 failures)
Recommended: Add a "Follow-Up Actions" section at the end of the skill.
```

For `static all`, produce a summary table then list any non-compliant skills:
```
=== Skill Static Check: All 74 Skills ===

Skill                  | Result       | Issues
-----------------------|--------------|-------
gate-check             | COMPLIANT    |
design-review          | COMPLIANT    |
story-readiness        | WARNINGS     | Check 5: no handoff
...

Summary: 48 COMPLIANT, 3 WARNINGS, 1 NON-COMPLIANT
Aggregate Verdict: N WARNINGS / N FAILURES
```

### Static Mode Optional Evidence Write

Static mode displays results by default. If the user wants to preserve the run,
ask:

"May I write this static check to
`memory_bank/t3_archive/skill_testing/results/static/skill-test-static-[name|all]-[YYYY-MM-DD].md`
and update `memory_bank/t3_archive/skill_testing/coverage-index.yaml`?"

If yes:
- Write the static result file under `memory_bank/t3_archive/skill_testing/results/static/`
- Update each affected skill entry in `coverage-index.yaml`:
  - `last_static: [date]`
  - `last_static_result: PASS|WARN|FAIL`
  - `latest_result_path: memory_bank/t3_archive/skill_testing/results/static/skill-test-static-[name|all]-[YYYY-MM-DD].md`

---

## Phase 2B: Spec Mode — Behavioral Verifier

### Step 1 — Locate Files

Find skill at `.agents/skills/[name]/SKILL.md`.
Look up the spec path from `skill_testing/catalog.yaml`
— use the `spec:` field for the matching skill entry.

If either is missing:
- Missing skill: "Skill '[name]' not found in `.agents/skills/`."
- Missing spec path in catalog: "No spec path set for '[name]' in catalog.yaml."
- Spec file not found at path: "Spec file missing at [path]. Run `/skill-test audit`
  to see coverage gaps."

### Step 2 — Read Both Files

Read the skill file and test spec file completely.

### Step 3 — Evaluate Assertions

For each **Test Case** in the spec:

1. Read the **Fixture** description (assumed state of project files)
2. Read the **Expected behavior** steps
3. Read each **Assertion** checkbox

For each assertion, evaluate whether the skill's written instructions, if
followed correctly given the fixture state, would satisfy it. This is a
Codex-evaluated reasoning check, not code execution.

Mark each assertion:
- **PASS** — skill instructions clearly satisfy this assertion
- **PARTIAL** — skill instructions partially address it, but with ambiguity
- **FAIL** — skill instructions would NOT satisfy this assertion given the fixture

For **Protocol Compliance** assertions (always present):
- Check whether the skill requires "May I write" before file writes
- Check whether the skill presents findings before requesting approval
- Check whether the skill ends with a recommended next step
- Check whether the skill avoids auto-creating files without approval

### Step 4 — Build Report

```
=== Skill Spec Test: /[name] ===
Date: [date]
Spec: skill_testing/specs/skills/[category]/[name].md

Case 1: [Happy Path — name]
  Fixture: [summary]
  Assertions:
    [PASS] [assertion text]
    [FAIL] [assertion text]
       Reason: The skill's Phase 3 says "..." but the fixture state means "..."
  Case Verdict: FAIL

Case 2: [Edge Case — name]
  ...
  Case Verdict: PASS

Protocol Compliance:
  [PASS] Uses "May I write" before file writes
  [PASS] Presents findings before asking approval
  [WARN] No explicit next-step handoff at end

Overall Verdict: FAIL (1 case failed, 1 warning)
```

### Step 4b — Dual-Domain Spec Assertions

For any spec that covers a dual-domain skill, evaluate both branches:
- Game fixture: `design/cdd/game-concept.md` exists. The skill should preserve
  game terminology, paths, examples, and next steps.
- Product fixture: `design/cdd/product-concept.md` exists. The skill should use
  Product terminology, paths, examples, and next steps.

Mark assertions:
- **PASS** — both branches are clearly supported.
- **PARTIAL** — Product is mentioned but lacks equivalent depth.
- **FAIL** — Product fixture would still execute only game-specific behavior, or
  the Product change removed game content.

### Step 5 — Offer to Write Results

"May I write these results to
`memory_bank/t3_archive/skill_testing/results/spec/skill-test-spec-[name]-[YYYY-MM-DD].md`
and update `memory_bank/t3_archive/skill_testing/coverage-index.yaml`?"

If yes:
- Write the result file to `memory_bank/t3_archive/skill_testing/results/spec/`
- Update the skill's entry in `memory_bank/t3_archive/skill_testing/coverage-index.yaml`:
  - `last_spec: [date]`
  - `last_spec_result: PASS|PARTIAL|FAIL`
  - `latest_result_path: memory_bank/t3_archive/skill_testing/results/spec/skill-test-spec-[name]-[YYYY-MM-DD].md`

---

## Phase 2D: Category Mode — Rubric Evaluation

### Step 1 — Locate Skill and Category

Find skill at `.agents/skills/[name]/SKILL.md`.
Look up `category:` field in `skill_testing/catalog.yaml`.

If skill not found: "Skill '[name]' not found."
If no `category:` field: "No category assigned for '[name]' in catalog.yaml.
Add `category: [name]` to the skill entry first."

For `category all`: collect all skills with a `category:` field and process each.
`category: utility` skills are evaluated against U1 (static checks pass) and U2
(gate mode correct if applicable) only — skip to the static mode for U1.

### Step 2 — Read Rubric Section

Read `skill_testing/quality-rubric.md`.
Extract the section matching the skill's category (e.g., `### gate`, `### team`).

### Step 3 — Read Skill

Read the skill's `SKILL.md` fully.

### Step 4 — Evaluate Rubric Metrics

For each metric in the category's rubric table:
1. Check whether the skill's written instructions clearly satisfy the criterion
2. Mark PASS, FAIL, or WARN
3. For FAIL/WARN, identify the exact gap in the skill text (quote the relevant section
   or note its absence)

### Step 5 — Output Report

```
=== Skill Category Check: /[name] ([category]) ===

Metric G1 — Review mode read:      PASS
Metric G2 — Full mode directors:   FAIL
  Gap: Phase 3 spawns only CD-PHASE-GATE; TD-PHASE-GATE, PR-PHASE-GATE, AD-PHASE-GATE absent
Metric G3 — Lean mode: PHASE-GATE only: PASS
Metric G4 — Solo mode: no directors:    PASS
Metric G5 — No auto-advance:       PASS

Verdict: FAIL (1 failure, 0 warnings)
Fix: Add TD-PHASE-GATE, PR-PHASE-GATE, and AD-PHASE-GATE to the full-mode director
     panel in Phase 3.
```

### Step 6 — Offer to Write Results

"May I write this category check to
`memory_bank/t3_archive/skill_testing/results/category/skill-test-category-[name]-[YYYY-MM-DD].md`
and update `memory_bank/t3_archive/skill_testing/coverage-index.yaml`
(`last_category`, `last_category_result`, `latest_result_path`) for [name]?"

---

## Phase 2D: Audit Mode — Coverage Report

### Step 1 — Read Catalog

Read `skill_testing/catalog.yaml` for the registry and
`memory_bank/t3_archive/skill_testing/coverage-index.yaml` for test history.
If either is missing, note the missing file and recommend running `/constitute`
to initialize the memory-bank testing templates.

### Step 2 — Enumerate All Skills and Agents

Glob `.agents/skills/*/SKILL.md` to get the complete list of skills.
Extract skill name from each path (directory name).

Also read the `agents:` section from `skill_testing/catalog.yaml` to get the
complete list of agents.

### Step 3 — Build Skill Coverage Table

For each skill:
- Check if a spec file exists (use the `spec:` path from catalog, or glob `skill_testing/specs/skills/*/[name].md`)
- Look up `last_static`, `last_static_result`, `last_spec`, `last_spec_result`,
  `last_category`, `last_category_result`, and `latest_result_path` from
  `coverage-index.yaml` (or mark as "never" / "—" if not in coverage)
- Look up `category` from catalog
- Priority comes from catalog `priority:` field (critical/high/medium/low)

### Step 3b — Build Agent Coverage Table

For each agent in catalog's `agents:` section:
- Check if a spec file exists (use the `spec:` path from catalog, or glob `skill_testing/specs/agents/*/[name].md`)
- Look up `last_spec`, `last_spec_result`, and `latest_result_path` from
  `coverage-index.yaml`
- Look up `tier` from catalog

### Step 4 — Output Report

```
=== Skill Test Coverage Audit ===
Date: [date]

SKILLS (74 total)
Specs written: 74 (100%) | Never static tested: 74 | Never category tested: 74

Skill                  | Cat      | Has Spec | Last Static | S.Result | Last Cat | D.Result | Priority
-----------------------|----------|----------|-------------|----------|----------|----------|----------
gate-check             | gate     | YES      | never       | —        | never    | —        | critical
design-review          | review   | YES      | never       | —        | never    | —        | critical
...

AGENTS (53 total)
Agent specs written: 53 (100%)

Agent                  | Category   | Has Spec | Last Spec   | Result
-----------------------|------------|----------|-------------|--------
creative-director      | director   | YES      | never       | —
technical-director     | director   | YES      | never       | —
...

Top 5 Priority Gaps (skills with no spec, critical/high priority):
(none if all specs are written)

Skill coverage:  74/74 specs (100%)
Agent coverage:  53/53 specs (100%)
```

Audit mode is read-only by default.

Optional write: ask "May I write this audit report to
`memory_bank/t3_archive/skill_testing/results/audit/skill-test-audit-[YYYY-MM-DD].md`?"
Only write the audit report if the user approves.

Offer: "Would you like to run `/skill-test static all` to check structural
compliance across all skills? `/skill-test category all` to run category rubric
checks? Or `/skill-test spec [name]` to run a specific behavioral test?"

---

## Phase 3: Recommended Next Steps

After any mode completes, offer contextual follow-up:

- After `static [name]`: "Run `/skill-test spec [name]` to validate behavioral
  correctness if a test spec exists."
- After `static all` with failures: "Address NON-COMPLIANT skills first. Run
  `/skill-test static [name]` individually for detailed remediation guidance."
- After `spec [name]` PASS: "Update `memory_bank/t3_archive/skill_testing/coverage-index.yaml`
  to record this pass date. Consider running `/skill-test audit` to find the next spec gap."
- After `spec [name]` FAIL: "Review the failing assertions and update the skill
  or the test spec to resolve the mismatch."
- After `audit`: "Start with the critical-priority gaps. Use the spec template at
  `skill_testing/templates/skill-test-spec.md` to create new specs."
