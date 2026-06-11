---
name: content-audit
description: "Audit GDD-specified content counts against implemented content. Identifies what's planned vs built."
argument-hint: "[system-name | --summary | (no arg = full audit)]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write
agent: producer
---

## User Guide

- When to use: Audit GDD-specified content counts against implemented content. Identifies what's planned vs built.
- Inputs: Command arguments: `/content-audit [system-name | --summary | (no arg = full audit)]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: None.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

## Phase 0: Domain Routing

Detect the project domain before auditing content:
- `design/cdd/game-concept.md` -> **[Game]** keep the existing planned-vs-built audit for levels, enemies, items, quests, dialogue, encounters, and CDD-specified game content.
- `design/cdd/product-concept.md` -> **[Product]** audit product content and surfaces: docs pages, API endpoints, CLI commands, config examples, migration scripts, seed data, templates, onboarding copy, and workflow states.
- If unclear, ask whether the inventory is game content or product surface/content.

Game content count examples must remain. Product surface counts are an additional mode.
When this skill is invoked:

Parse the argument:
- No argument → full audit across all systems
- `[system-name]` → audit that single system only
- `--summary` → summary table only, no file write

---

## Phase 1 — Context Gathering

1. **Read `design/cdd/module-index.md`** for the full list of systems, their
   categories, and MVP/priority tier.

2. **L0 pre-scan**: Before full-reading any CDDs, Grep all CDD files for
   `## Summary` sections plus common content-count keywords:
   ```
   Grep pattern="(## Summary|N enemies|N levels|N items|N abilities|enemy types|item types)" glob="design/cdd/*.md" output_mode="files_with_matches"
   ```
   For a single-system audit: skip this step and go straight to full-read.
   For a full audit: full-read only the CDDs that matched content-count keywords.
   CDDs with no content-count language (pure mechanics CDDs) are noted as
   "No auditable content counts" without a full read.

   **[Product] Product surface pre-scan**: For product projects, also grep CDDs,
   UX specs, architecture docs, docs, and release notes for product surface keywords:
   ```
   Grep pattern="(endpoint|API|CLI command|screen|workflow|migration|config key|docs page|SDK example|template|seed data|release bundle|user role)" glob="{design,docs,production}/**/*.md" output_mode="files_with_matches"
   ```
   Full-read only matched files for the Product audit unless a single module was requested.

3. **Full-read in-scope CDD files** (or the single system CDD if a system
   name was given).

4. **For each CDD, extract explicit content counts or lists.** Look for patterns
   like:
   - "N enemies" / "enemy types:" / list of named enemies
   - "N levels" / "N areas" / "N maps" / "N stages"
   - "N items" / "N weapons" / "N equipment pieces"
   - "N abilities" / "N skills" / "N spells"
   - "N dialogue scenes" / "N conversations" / "N cutscenes"
   - "N quests" / "N missions" / "N objectives"
   - Any explicit enumerated list (bullet list of named content pieces)

   **[Product] Extract product surface counts/lists**:
   - Endpoints, routes, API operations, request/response schemas
   - CLI commands, flags, subcommands, exit codes, shell completions
   - Web/admin/mobile screens, user flows, onboarding states, empty/error states
   - Config keys, environment variables, feature flags, permission roles
   - Migration files, seed datasets, import/export formats
   - Docs pages, SDK examples, tutorials, templates, release bundles
   - Workflow states, manual handoffs, notifications, emails, status messages

4. **Build a content inventory table** from the extracted data:

   | System | Content Type | Specified Count/List | Source CDD |
   |--------|-------------|---------------------|------------|

   Note: If a CDD describes content qualitatively but gives no count, record
   "Unspecified" and flag it — unspecified counts are a design gap worth noting.

---

## Phase 2 — Implementation Scan

For each content type found in Phase 1, scan the relevant directories to count
what has been implemented. Use Glob and Grep to locate files.

**Levels / Areas / Maps:**
- Glob `assets/**/*.tscn`, `assets/**/*.unity`, `assets/**/*.umap`
- Glob `src/**/*.tscn`, `src/**/*.unity`
- Look for scene files in subdirectories named `levels/`, `areas/`, `maps/`,
  `worlds/`, `stages/`
- Count unique files that appear to be level/scene definitions (not UI scenes)

**Enemies / Characters / NPCs:**
- Glob `assets/data/**/enemies/**`, `assets/data/**/characters/**`
- Glob `src/**/enemies/**`, `src/**/characters/**`
- Look for `.json`, `.tres`, `.asset`, `.yaml` data files defining entity stats
- Look for scene/prefab files in character subdirectories

**Items / Equipment / Loot:**
- Glob `assets/data/**/items/**`, `assets/data/**/equipment/**`,
  `assets/data/**/loot/**`
- Look for `.json`, `.tres`, `.asset` data files

**Abilities / Skills / Spells:**
- Glob `assets/data/**/abilities/**`, `assets/data/**/skills/**`,
  `assets/data/**/spells/**`
- Look for `.json`, `.tres`, `.asset` data files

**Dialogue / Conversations / Cutscenes:**
- Glob `assets/**/*.dialogue`, `assets/**/*.csv`, `assets/**/*.ink`
- Grep for dialogue data files in `assets/data/`

**Quests / Missions:**
- Glob `assets/data/**/quests/**`, `assets/data/**/missions/**`
- Look for `.json`, `.yaml` definition files

**Engine-specific notes (acknowledge in the report):**
- Counts are approximations — the skill cannot perfectly parse every engine
  format or distinguish editor-only files from shipped content
- Scene files may include both gameplay content and system/UI scenes; the scan
  counts all matches and notes this caveat

**[Product] Product implementation scan:**
- Endpoints/routes: Glob `src/**/routes/**`, `src/**/api/**`, `src/**/*controller*`, `src/**/*handler*`, OpenAPI/schema files
- CLI commands: Glob `src/**/commands/**`, `src/**/cli/**`, `cmd/**`, command registration files, generated help output
- Screens/workflows: Glob `src/**/*.{tsx,jsx,vue,svelte,html}`, `apps/**`, `pages/**`, `routes/**`, `components/**`
- Config keys: Grep `.env.example`, config modules, docs, and deployment files for required names
- Migrations/seeds: Glob `migrations/**`, `db/migrations/**`, `seeds/**`, `fixtures/**`
- Docs/examples/templates: Glob `docs/**`, `examples/**`, `templates/**`, SDK sample directories
- Release artifacts: Glob `production/releases/**`, `dist/**`, `build/**`, `packages/**`, `release/**`

**Product scan notes:**
- Counts are approximations; generated routes or framework conventions may need manual confirmation.
- Do not count test-only examples as shipped Product surfaces unless the CDD explicitly treats them as user/developer-facing examples.
- For APIs, count operations, not only files, when OpenAPI or route definitions make operations visible.

---

## Phase 3 — Gap Report

Produce the gap table:

```
| System | Content Type | Specified | Found | Gap | Status |
|--------|-------------|-----------|-------|-----|--------|
```

**Status categories:**
- `COMPLETE` — Found ≥ Specified (100%+)
- `IN PROGRESS` — Found is 50–99% of Specified
- `EARLY` — Found is 1–49% of Specified
- `NOT STARTED` — Found is 0

**Priority flags:**
Flag a system as `HIGH PRIORITY` in the report if:
- Status is `NOT STARTED` or `EARLY`, AND
- The system is tagged MVP or Vertical Slice in the systems index, OR
- The systems index shows the system is blocking downstream systems

**Summary line:**
- Total content items specified (sum of all Specified column values)
- Total content items found (sum of all Found column values)
- Overall gap percentage: `(Specified - Found) / Specified * 100`

**[Product] Product status categories:**
- `COMPLETE` — Documented surface exists and has matching implementation or artifact evidence
- `PARTIAL` — Surface exists but lacks docs, tests, migration/config evidence, or release packaging
- `DESIGNED ONLY` — CDD/UX/docs mention it but implementation/artifact is absent
- `IMPLEMENTED ONLY` — Code/artifact exists but no CDD/UX/docs source claims it
- `NOT STARTED` — Required Product surface has no found implementation

Flag a Product gap as `HIGH PRIORITY` if it blocks the primary workflow, public API/CLI compatibility, migration safety, deployment, support/onboarding, or the Product Concept user promise.

---

## Phase 4 — Output

### Full audit and single-system modes

Present the gap table and summary to the user. Ask: "May I write the full report to `docs/content-audit-[YYYY-MM-DD].md`?"

If yes, write the file:

```markdown
# Content Audit — [Date]

## Summary
- **Total specified**: [N] content items across [M] systems
- **Total found**: [N]
- **Gap**: [N] items ([X%] unimplemented)
- **Scope**: [Full audit | System: name]

> Note: Counts are approximations based on file scanning.
> The audit cannot distinguish shipped content from editor/test assets.
> Manual verification is recommended for any HIGH PRIORITY gaps.

## Gap Table

| System | Content Type | Specified | Found | Gap | Status |
|--------|-------------|-----------|-------|-----|--------|

## HIGH PRIORITY Gaps

[List systems flagged HIGH PRIORITY with rationale]

## Per-System Breakdown

### [System Name]
- **GDD**: `design/cdd/[file].md`
- **Content types audited**: [list]
- **Notes**: [any caveats about scan accuracy for this system]

## Recommendation

Focus implementation effort on:
1. [Highest-gap HIGH PRIORITY system]
2. [Second system]
3. [Third system]

## Unspecified Content Counts

The following CDDs describe content without giving explicit counts.
Consider adding counts to improve auditability:
[List of CDDs and content types with "Unspecified"]
```

After writing the report, ask:

> "Would you like to create backlog stories for any of the content gaps?"

If yes: for each system the user selects, suggest a story title and point them
to `/create-stories [epic-slug]` or `/quick-design` depending on the size of the gap.

### --summary mode

Print the Gap Table and Summary directly to conversation. Do not write a file.
End with: "Run `/content-audit` without `--summary` to write the full report."

### Product full audit and summary modes

Use this report when the Product branch is active:

```markdown
# Product Surface Audit -- [Date]

## Summary
- **Total specified surfaces**: [N] across [M] modules/workflows
- **Total found**: [N]
- **Gap**: [N] surfaces ([X%] missing or partial)
- **Scope**: [Full audit | Module/workflow: name]

> Note: Counts are approximations based on file and contract scanning.
> Manual verification is recommended for API operations generated by framework conventions or for docs examples produced during build.

## Gap Table

| Module / Workflow | Surface Type | Specified | Found | Gap | Status |
|-------------------|--------------|-----------|-------|-----|--------|

## HIGH PRIORITY Product Gaps
[Primary-workflow, API/CLI compatibility, migration, deployment, onboarding, or docs blockers]

## Implemented Without Product Spec
[Endpoints, commands, screens, config keys, migrations, docs examples, or release artifacts found with no CDD/UX/docs source]

## Recommendation
Focus implementation or documentation effort on:
1. [Highest-impact Product gap]
2. [Second Product gap]
3. [Third Product gap]
```

---

## Phase 5 — Next Steps

After the audit, recommend the highest-value follow-up actions:

- If any system is `NOT STARTED` and MVP-tagged → "Run `/design-system [name]` to
  add missing content counts to the CDD before implementation begins."
- If total gap is >50% → "Run `/sprint-plan` to allocate content work across upcoming sprints."
- If backlog stories are needed → "Run `/create-stories [epic-slug]` for each HIGH PRIORITY gap."
- If `--summary` was used → "Run `/content-audit` (no flag) to write the full report to `docs/`."

**[Product] Product next steps:**
- If public surfaces are `DESIGNED ONLY`, run `/create-stories` for the owning epic or `/quick-design` for a small product surface change.
- If public surfaces are `IMPLEMENTED ONLY`, run `/reverse-document` to create or update the module CDD, API/CLI docs, or architecture notes.
- If migration/config/release artifacts are missing, run `/release-checklist` after the fixes are added.
- If docs examples are stale or missing, run `/asset-audit` Product mode after docs and package artifacts are regenerated.

Verdict: **COMPLETE** — content audit finished.
