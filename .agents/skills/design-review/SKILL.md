---
name: design-review
description: "Reviews a CDD for completeness, internal consistency, implementability, and adherence to project design standards. Supports both game and general product domains. Run this before handing a design document to programmers."
argument-hint: "[path-to-design-doc] [--depth full|lean|solo]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Task, AskUserQuestion
---

## User Guide

- When to use: Reviews a CDD for completeness, internal consistency, implementability, and adherence to project design standards. Supports both game and general product domains. Run this before handing a design document to programmers.
- Inputs: Command arguments: `/design-review [path-to-design-doc] [--depth full|lean|solo]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: `memory_bank/t3_archive/reviews/review-index.md`.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

## Phase 0: Parse Arguments

Extract `--depth [full|lean|solo]` if present. Default is `full` when no flag is given.

**Note**: `--depth` controls the *analysis depth* of this skill (how many specialist agents are spawned). It is independent of the global review mode in `production/review-mode.txt`, which controls director gate spawning. These are two different concepts — `--depth` is about how thoroughly *this* skill analyses the document.

- **`full`**: Complete review — all phases + specialist agent delegation (Phase 3b)
- **`lean`**: All phases, no specialist agents — faster, single-session analysis
- **`solo`**: Phases 1-4 only, no delegation, no Phase 5 next-step prompt — use when called from within another skill

---

## Phase 1: Load Documents

Read the target design document in full. Read AGENTS.md to understand project context and standards. Read related design documents referenced or implied by the target doc (check `design/cdd/` for related systems).

**Dependency graph validation:** For every system listed in the Dependencies section, use Glob to check whether its CDD file exists in `design/cdd/`. Flag any that don't exist yet — these are broken references that downstream authors will hit.

**Concept alignment:** Read the appropriate concept context for the detected domain.
- **[游戏专用]** If `design/cdd/game-concept.md` or any file in `design/narrative/` exists, read it. Note any mechanical choices in this CDD that contradict established world rules, tone, or design pillars. Pass this context to `game-designer` in Phase 3b.
- **[通用产品]** If `design/cdd/product-concept.md` exists, read it. Note any module choices in this CDD that contradict the product principles, user promise, JTBD statement, or target workflow. Pass this context to `lead-programmer`, the language specialist, and `creative-director` in Phase 3b.

**Prior review check:** Check whether `design/cdd/reviews/[doc-name]-review-log.md` exists. If it does, read the most recent entry — note what verdict was given and what blocking items were listed. This session is a re-review; track whether prior items were addressed.

---

## Phase 2: Completeness Check

Evaluate against the CDD Standard checklist. [Game] Game CDD sections:

- [ ] Has Overview section (one-paragraph summary)
- [ ] Has Player Fantasy section (intended feeling)
[Product] Product CDD sections:
- [ ] Has User Promise section (intended user value)
- [ ] Has Detailed Design section (unambiguous specification)
- [ ] Has Data Model section (all data structures defined)
- [ ] Has Configuration section (configurable parameters identified)
- [ ] Has Integration section (external system interfaces)

[Game] Game CDD sections (continued):
- [ ] Has Detailed Rules section (unambiguous mechanics)
- [ ] Has Formulas section (all math defined with variables)
- [ ] Has Tuning Knobs section (configurable values identified)

[通用场景] Shared sections (both game and product CDDs):
- [ ] Has Edge Cases section (unusual situations handled)
- [ ] Has Dependencies section (other modules listed)
- [ ] Has Acceptance Criteria section (testable success conditions)

---

## Phase 3: Consistency and Implementability

**Internal consistency:**
- Do the formulas produce values that match the described behavior?
- Do edge cases contradict the main rules?
- Are dependencies bidirectional (does the other system know about this one)?

**Implementability:**
- Are the rules precise enough for a programmer to implement without guessing?
- Are there any "hand-wave" sections where details are missing?
- Are performance implications considered?

**Cross-system consistency:**
- **[游戏专用]** Does this conflict with any existing mechanic?
- **[游戏专用]** Does this create unintended interactions with other game systems?
- **[游戏专用]** Is this consistent with the game's established tone and pillars?
- **[通用产品]** Does this conflict with any existing workflow, module contract, API contract, schema, or permission boundary?
- **[通用产品]** Does this create unintended interactions with other modules, data flows, integrations, or user states?
- **[通用产品]** Is this consistent with the product's established principles, user promise, and JTBD?

---

## Phase 3b: Adversarial Specialist Review (full mode only)

**Skip this phase in `lean` or `solo` mode.**

**This phase is MANDATORY in full mode.** Do not skip it.

**Before spawning any agents**, print this notice:
> "Full review: spawning specialist agents in parallel. This typically takes 8–15 minutes. Use `--review lean` for faster single-session analysis."

### Step 1 — Identify all domains the CDD touches

Read the CDD and identify every domain present. A CDD can touch multiple domains simultaneously — be thorough. Common signals:

| If the CDD contains... | Spawn these agents |
|------------------------|-------------------|
| Costs, prices, drops, rewards, economy | `economy-designer` |
| Combat stats, damage, health, DPS | `game-designer`, `systems-designer` |
| AI behaviour, pathfinding, targeting | `ai-programmer` |
| Level layout, spawning, wave structure | `level-designer` |
| Player progression, XP, unlocks | `economy-designer`, `game-designer` |
| UI, HUD, menus, player-facing displays | `ux-designer`, `ui-programmer` |
| Dialogue, quests, story, lore | `narrative-director` |
| Animation, feel, timing, juice | `gameplay-programmer` |
| Multiplayer, sync, replication | `network-programmer` |
| Audio cues, music triggers | `audio-director` |
| Performance, draw calls, memory | `performance-analyst` |
| Engine-specific patterns or APIs | Primary engine specialist (from `standards/technical-preferences.md`) |
| Acceptance criteria, test coverage | `qa-lead` |
| Data schema, resource structure | `systems-designer` |
| Any gameplay system | `game-designer` (always)
[Product] Product domain mapping:
| If the CDD contains... | Spawn these agents |
|------------------------|-------------------|
| API endpoints, request/response contracts | `lead-programmer`, language specialist |
| Data models, schemas, storage | `lead-programmer`, language specialist |
| Auth, permissions, security | `security-engineer` |
| Deployment, CI/CD, infrastructure | `devops-engineer` |
| UI, UX, user-facing interfaces | `ux-designer`, `ui-programmer` |
| Performance-critical paths | `performance-analyst` |
| Third-party integrations, APIs | `lead-programmer` |
| Acceptance criteria, test coverage | `qa-lead` |
**[游戏专用]** **Always spawn `game-designer` and `systems-designer` as a baseline minimum.** Every game CDD touches their domain.

**[通用产品]** **Always spawn `lead-programmer` and the appropriate language specialist as a baseline minimum for product CDDs.**

### Step 2 — Spawn all relevant specialists in parallel

**CRITICAL: Task in this skill spawns a SUBAGENT — a separate independent Codex session**
with its own context window. It is NOT task tracking. Do NOT simulate specialist
perspectives internally. Do NOT reason through domain views yourself. You MUST issue
actual Task calls. A simulated review is not a specialist review.

****

Issue all Task calls simultaneously. Do NOT spawn one at a time.

**Prompt each specialist adversarially:**
> "Here is the CDD for [system] and the main review's structural findings so far.
> Your job is NOT to validate this design — your job is to find problems.
> Challenge the design choices from your domain expertise. What is wrong,
> underspecified, likely to cause problems, or missing entirely?
> Be specific and critical. Disagreement with the main review is welcome."

**Additional instructions per agent type:**

- **`game-designer`**: Anchor your review to the Player Fantasy stated in Section B of this CDD. Does this design actually deliver that fantasy? Would a player feel the intended experience? Flag any rules that serve implementability but undermine the stated feeling.

- **`systems-designer`**: For every formula in the CDD, plug in boundary values (minimum and maximum plausible inputs). Report whether any outputs go degenerate — negative values, division by zero, infinity, or nonsensical results at the extremes.

- **`lead-programmer`**: For product CDDs, challenge whether the module contract is implementable, whether API/data boundaries are explicit, and whether the design creates hidden coupling or operational risk.

- **Language specialist**: For product CDDs, validate that the proposed data model, integration shape, and configuration approach are idiomatic for the pinned language/framework stack. Flag framework-specific pitfalls, stale assumptions, or missing constraints.

- **`qa-lead`**: Review every acceptance criterion. Flag any that are not independently testable — phrases like "feels balanced", "works correctly", "performs well" are not ACs. Suggest concrete rewrites for any that fail this test.

### Step 3 — Senior lead review

After all specialists respond, spawn `creative-director` as the **senior reviewer**:
- Provide: the CDD, all specialist findings, any disagreements between them
- Ask: "Synthesise these findings. What are the most important issues? Do you agree with the specialists? What is your overall verdict on this design?"
- The creative-director's synthesis becomes the **final verdict** in Phase 4.

### Step 4 — Surface disagreements

If specialists disagree with each other or with the creative-director, do NOT silently pick one view. Present the disagreement explicitly in Phase 4 so the user can adjudicate.

Mark every finding with its source: `[game-designer]`, `[economy-designer]`, `[lead-programmer]`, `[language-specialist]`, `[creative-director]`, etc.

---

## Phase 4: Output Review

```
## Design Review: [Document Title]
Specialists consulted: [list agents spawned]
Re-review: [Yes — prior verdict was X on YYYY-MM-DD / No — first review]

### Completeness: [X/8 sections present]
[List missing sections]

### Dependency Graph
[List each declared dependency and whether its CDD file exists on disk]
- ✓ enemy-definition-data.md — exists
- ✗ loot-system.md — NOT FOUND (file does not exist yet)

### Required Before Implementation
[Numbered list — blocking issues only. Each item tagged with source agent.]

### Recommended Revisions
[Numbered list — important but not blocking. Source-tagged.]

### Specialist Disagreements
[Any cases where agents disagreed with each other or with the main review.
Present both sides — do not silently resolve.]

### Nice-to-Have
[Minor improvements, low priority.]

### Senior Verdict [creative-director]
[Creative director's synthesis and overall assessment.]

### Scope Signal
Estimate implementation scope based on: dependency count, formula count,
systems touched, and whether new ADRs are required.
- **S** — single system, no formulas, no new ADRs, <3 dependencies
- **M** — moderate complexity, 1-2 formulas, 3-6 dependencies
- **L** — multi-system integration, 3+ formulas, may require new ADR
- **XL** — cross-cutting concern, 5+ dependencies, multiple new ADRs likely
Label clearly: "Rough scope signal: M (producer should verify before sprint planning)"

### Verdict: [APPROVED / NEEDS REVISION / MAJOR REVISION NEEDED]
```

This skill is read-only — no files are written during Phase 4.

---

## Phase 5: Next Steps

Use `AskUserQuestion` for ALL closing interactions. Never plain text.

**First widget — what to do next:**

If APPROVED (first-pass, no revision needed), proceed directly to the module-index widget, review-log widget, then the final closing widget. Do not show a separate "what to do" widget — the final closing widget covers next steps.

If NEEDS REVISION or MAJOR REVISION NEEDED, options:
- `[A] Revise the CDD now — address blocking items together`
- `[B] Stop here — revise in a separate session`
- `[C] Accept as-is and move on (only if all items are advisory)`

**If user selects [A] — Revise now:**

Work through all blocking items, asking for design decisions only where you cannot resolve the issue from the CDD and existing docs alone. Group all design-decision questions into a single multi-tab `AskUserQuestion` before making any edits — do not interrupt mid-revision for each blocker individually.

After all revisions are complete, show a summary table (blocker → fix applied) and use `AskUserQuestion` for a **post-revision closing widget**:

- Prompt: "Revisions complete — [N] blockers resolved. What next?"
- Note current context usage: if context is above ~50%, add: "(Recommended: /clear before re-review — this session has used X% context. A full re-review runs 5 agents and needs clean context.)"
- Options:
  - `[A] Re-review in a new session — run /design-review [doc-path] after /clear`
  - `[B] Accept revisions and mark Approved — update module index, skip re-review`
  - `[C] Move to next system — /design-system [next-system] (#N in design order)`
  - `[D] Stop here`

Never end the revision flow with plain text. Always close with this widget.

**Second widget — module index update (always show this separately):**

Use a second `AskUserQuestion`:
- Prompt: "May I update `design/cdd/module-index.md` to mark [system] as [In Review / Approved]?"
- Options: `[A] Yes — update it` / `[B] No — leave it as-is`

**Third widget — review log (always offer):**

Use a third `AskUserQuestion`:
- Prompt: "May I append this review summary to `design/cdd/reviews/[doc-name]-review-log.md`? This creates a revision history so future re-reviews can track what changed."
- Options: `[A] Yes — append to review log` / `[B] No — skip`

If yes, append an entry in this format:
```
## Review — [YYYY-MM-DD] — Verdict: [APPROVED / NEEDS REVISION / MAJOR REVISION NEEDED]
Scope signal: [S/M/L/XL]
Specialists: [list]
Blocking items: [count] | Recommended: [count]
Summary: [2-3 sentence summary of key findings from creative-director verdict]
Prior verdict resolved: [Yes / No / First review]
```

When `memory_bank/` exists and the user approves appending the review log, also
update `memory_bank/t3_archive/reviews/review-index.md`.

- Review Type: `design-review`
- Source Artifact: `design/cdd/reviews/[doc-name]-review-log.md`
- Use `Source Artifact` as the dedupe key.
- If the same source artifact already exists, update Date, Verdict, and
  Follow-up Owner instead of adding a duplicate row.
- If `memory_bank/` does not exist, do not create it from `/design-review`;
  keep the existing review log behavior and say: "Run `/constitute` to establish
  the memory_bank governance control plane."

---

**Final closing widget — always show after all file writes complete:**

Once the module-index and review-log widgets are answered, check project state and show one final `AskUserQuestion`:

Before building options, read:
- `design/cdd/module-index.md` — find any system with Status: In Review or NEEDS REVISION (other than the one just reviewed)
- Count `.md` files in `design/cdd/` (excluding game-concept.md, product-concept.md, module-index.md, principles.md) to determine if `/review-all-gdds` is worth offering (≥2 CDDs)
- Find the next system with Status: Not Started in design order

Build the option list dynamically — only include options that are genuinely next:
- `[_] Run /design-review [other-cdd-path] — [system name] is still [In Review / NEEDS REVISION]` (include if another CDD needs review)
- `[_] Run /consistency-check — verify this CDD's values don't conflict with existing CDDs` (always include if ≥1 other CDD exists)
- `[_] Run /review-all-gdds — holistic design-theory review across all designed systems` (include if ≥2 CDDs exist)
- `[_] Run /design-system [next-system] — next in design order` (always include, name the actual system)
- `[_] Stop here`

Assign letters A, B, C… only to included options. Mark the most pipeline-advancing option as `(recommended)`.

Never end the skill with plain text after file writes. Always close with this widget.
