---
name: skill-improve
description: "Improve a skill using a test-fix-retest loop. Runs static checks, proposes targeted fixes, rewrites the skill, re-tests, and keeps or reverts based on score change."
argument-hint: "[skill-name]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Bash
---

## User Guide

- When to use: Improve a skill using a test-fix-retest loop. Runs static checks, proposes targeted fixes, rewrites the skill, re-tests, and keeps or reverts based on score change.
- Inputs: Command arguments: `/skill-improve [skill-name]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Proposed skill patch, before/after test comparison, and optional improvement evidence written only after user approval.
- Memory-bank writes: Reads `skill_testing/catalog.yaml` and `skill_testing/quality-rubric.md`; with approval writes `memory_bank/t3_archive/skill_testing/improvements/skill-improve-[name]-[YYYY-MM-DD].md`. Retest coverage is updated by `/skill-test`.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

## Phase 0: Domain Routing

Detect the target domain before improving a skill:
- **[Game]** when the skill primarily supports game workflows, preserve game examples, player/gameplay/engine terminology, playtest references, and game CDD templates.
- **[Product]** when the skill is expected to support general projects, add product branches for API/CLI/web/data workflows, technology stack terms, user value, and product evidence.
- **[Both]** prefer dual-domain sections over replacing one domain with another.

Never delete game examples while improving a skill. Move them to `[Game]` / `[游戏专用]` sections if they no longer fit the shared path.
# Skill Improve

Runs an improvement loop on a single skill:
test → fix → retest → keep or revert.

---

## Phase 1: Parse Argument

Read the skill name from the first argument. If missing, output usage and stop:

```
Usage: /skill-improve [skill-name]
Example: /skill-improve tech-debt
```

Verify `.agents/skills/[name]/SKILL.md` exists. If not, stop with:
"Skill '[name]' not found."

---

## Phase 2: Baseline Test

Run `/skill-test static [name]` and record the baseline score:
- Count of FAILs
- Count of WARNs
- Which specific checks failed (Check 1–7)

Display to the user:
```
Static baseline:   [N] failures, [M] warnings
Failing: Check 4 (no ask-before-write), Check 5 (no handoff)
```

If baseline is 0 FAILs and 0 WARNs, note it and proceed to Phase 2b.

### Phase 2b: Category Baseline

Look up the skill's `category:` field in
`skill_testing/catalog.yaml`.

If no `category:` field is found, display:
"Category: not yet assigned — skipping category checks."
and skip to Phase 3.

If category is found, run `/skill-test category [name]` and record the category baseline:
- Count of FAILs
- Count of WARNs
- Which specific category rubric metrics failed

Display to the user:
```
Category baseline: [N] failures, [M] warnings  ([category] rubric)
```

If BOTH static and category baselines are 0 FAILs and 0 WARNs, stop:
"This skill already passes all static and category checks. No improvements needed."

---

## Phase 3: Diagnose

Read the full skill file at `.agents/skills/[name]/SKILL.md`.

For each failing or warning **static** check, identify the exact gap:

- **Check 1 fail** → which frontmatter field is missing
- **Check 2 fail** → how many phases found vs. minimum required
- **Check 3 fail** → no verdict keywords anywhere in the skill body
- **Check 4 fail** → Write or Edit in allowed-tools but no ask-before-write language
- **Check 5 warn** → no follow-up or next-step section at the end
- **Check 6 warn** → `context: fork` set but fewer than 5 phases found
- **Check 7 warn** → argument-hint is empty or doesn't match documented modes

For each failing or warning **category** check (if category was assigned in Phase 2b),
identify the exact gap in the skill's text. For example:
- If G2 fails (gate mode, full directors not spawned): skill body never references all 4
  PHASE-GATE director prompts
- If A2 fails (authoring, no per-section May-I-write): skill asks once at the end, not
  before each section write
- If T3 fails (team, BLOCKED not surfaced): skill doesn't halt dependent work on blocked agent

### Phase 3b: Dual-Domain Parity Diagnosis

If the target skill contains any of these markers, run a Product parity diagnosis
before proposing fixes:
- `Product`, `[Product]`, `[通用产品]`, `general product`
- `product-concept.md`, `API`, `CLI`, `web`, `data pipeline`, `language specialist`

Check whether the Product branch has the same implementation depth as the Game branch:
- Domain detection or routing explains when Product applies.
- Product context reads are listed after line 50 of the skill, not only in the frontmatter or Phase 0 marker.
- Product-specific phases or steps exist for the skill's real job.
- Product output format or report template exists where the Game branch has one.
- Product next steps point to relevant workflows such as `/code-review`, `/test-evidence-review`, `/release-checklist`, `/propagate-design-change`, `/setup-engine refresh`, or `/create-stories`.
- Existing game examples, player/gameplay/engine language, playtest references, and game CDD paths remain present.

Record the diagnosis:

```markdown
Dual-domain parity:
- Game branch preserved: [PASS / FAIL]
- Product routing only: [YES / NO]
- Product context reads: [PASS / MISSING]
- Product steps/checks: [PASS / MISSING]
- Product output/next steps: [PASS / MISSING]
- Recommended fix: [add Product branch / expand Product output / update docs only]
```

Show the full combined diagnosis to the user before proposing any changes.

---

## Phase 4: Propose Fix

Write a targeted fix for each failure and warning. Show the proposed changes
as clearly marked before/after blocks. Only change what is failing — do not
rewrite sections that are passing.

For dual-domain parity fixes:
- Add Product sections beside existing Game content.
- Do not delete, shorten, or genericize game examples.
- Do not create a separate product-only slash command.
- Reuse existing Product paths: `design/cdd/`, `design/ux/`, `docs/architecture/`, `production/qa/`, `production/releases/`, `tests/`, and `docs/reference/<stack>/`.
- Prefer a focused additive patch over a broad rewrite.

Ask: "May I write this improved version to `.agents/skills/[name]/SKILL.md`?"

If the user says no, stop here.

---

## Phase 5: Write and Retest

Record the current content of the skill file (for revert if needed).

Write the improved skill to `.agents/skills/[name]/SKILL.md`.

Re-run `/skill-test static [name]` and record the new static score.
If a category was assigned, also re-run `/skill-test category [name]` and record the new category score.

Display the comparison:
```
Static:   Before [N] failures, [M] warnings  →  After [N'] failures, [M'] warnings
Category: Before [N] failures, [M] warnings  →  After [N'] failures, [M'] warnings  (if applicable)
Combined change: improved / no change / worse
```

---

## Phase 6: Verdict

Count the combined failure total: static FAILs + category FAILs + static WARNs + category WARNs.

**If combined score improved (combined failure count is lower than baseline):**
Report: "Score improved. Changes kept."
Show a summary of what was fixed in each dimension.

**If combined score is the same or worse:**
Report: "Combined score did not improve."
Show what changed and why it may not have helped.
Ask: "May I revert `.agents/skills/[name]/SKILL.md` using git checkout?"
If yes: run `git checkout -- .agents/skills/[name]/SKILL.md`

---

## Phase 6b: Optional Improvement Evidence

After the keep/revert decision, ask:

"May I write the improvement record to
`memory_bank/t3_archive/skill_testing/improvements/skill-improve-[name]-[YYYY-MM-DD].md`?"

Only write this file if the user approves. The record must include:
- Skill name and path
- Baseline static/category result
- Diagnosis summary
- Patch summary
- Retest static/category result
- Keep/revert decision
- Follow-up recommendation

Do not update `memory_bank/t3_archive/skill_testing/coverage-index.yaml` here.
That index is maintained by `/skill-test` when retest evidence is approved.

---

## Phase 7: Next Steps

- Run `/skill-test static all` to find the next skill with failures.
- Run `/skill-improve [next-name]` to continue the loop on another skill.
- Run `/skill-test audit` to see overall coverage progress in `memory_bank/t3_archive/skill_testing/coverage-index.yaml`.
