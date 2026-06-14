---
name: cdd-status
description: "Generate a project progress dashboard from workflow-catalog.yaml. Reads current stage, required steps, artifact evidence, validation gaps, writes production/project-roadmap.md after approval, and mirrors to memory_bank/t2_execution/current_roadmap.md when memory_bank exists."
argument-hint: "[optional: --dry-run | --write]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write
model: haiku
---

## User Guide

- When to use: Generate a project progress dashboard from workflow-catalog.yaml. Reads current stage, required steps, artifact evidence, validation gaps, writes production/project-roadmap.md after approval, and mirrors to memory_bank/t2_execution/current_roadmap.md when memory_bank exists.
- Inputs: Command arguments: `/cdd-status [optional: --dry-run | --write]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: `memory_bank/t0_core/basic_law_index.md`, `memory_bank/t0_core/current_state.md`, `memory_bank/t2_execution/current_roadmap.md`, `memory_bank/t2_execution/workflow_contract.md`.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

# CDD Status Dashboard

Generate a concise progress dashboard and a durable roadmap at
`production/project-roadmap.md`. For the expected shape, see
`docs/examples/project-roadmap.example.md`.

When `memory_bank/` exists, also maintain the T2 governance mirror at
`memory_bank/t2_execution/current_roadmap.md`. This mirror is for project
memory and does not replace `production/project-roadmap.md`.

This skill bridges `/help` and `/project-stage-detect`:
- `/help` gives one next required step.
- `/project-stage-detect` performs a full audit.
- `/cdd-status` creates a saved progress dashboard from the catalog.

## Collaboration Rule

Draft the roadmap first. Before writing, ask:

`May I write this to production/project-roadmap.md and, if memory_bank exists, memory_bank/t2_execution/current_roadmap.md?`

If the user explicitly requested writing or used `/cdd-status --write`, write the
file after showing the concise draft summary. If the user used `--dry-run`, do
not write any files.

If `memory_bank/` does not exist, write only `production/project-roadmap.md` and
note: "Run `/constitute` to establish the memory_bank governance control plane."

## 1. Read Authoritative Inputs

Read these files when present:
- `workflow/workflow-catalog.yaml`
- `production/stage.txt`
- `production/sprint-status.yaml`
- `production/session-state/active.md`
- `memory_bank/t0_core/basic_law_index.md`
- `memory_bank/t0_core/current_state.md`
- `memory_bank/t2_execution/workflow_contract.md`
- `design/cdd/game-concept.md`
- `design/cdd/product-concept.md`
- `design/ux/surface-profile.md`

Detect domain:
- `design/cdd/game-concept.md` exists -> Game
- `design/cdd/product-concept.md` exists -> Product
- neither exists -> Unknown

Detect current phase:
1. Prefer `production/stage.txt` if it exists.
2. Otherwise infer from artifacts, using the same phase order as `/help`.

## 2. Parse The Workflow Catalog

Use `workflow/workflow-catalog.yaml` as the only required-step source of
truth.

For each phase:
- Keep steps with no `applies_to`.
- Keep `applies_to: [game]` only for Game projects.
- Keep `applies_to: [product]` only for Product projects.
- For Unknown projects, keep domain-specific steps but label them as
  domain-specific.

For each step, extract:
- `id`
- `name`
- `command`
- `required`
- `required_when`
- `artifact.glob`
- `artifact.min_count`
- `artifact.note`
- `description`

## 3. Check Completion

Classify every required step:

| Status | Meaning |
| ------ | ------- |
| COMPLETE | Artifact glob exists and meets `min_count`, or manual evidence clearly exists |
| PARTIAL | Some evidence exists but `min_count` or required review status is missing |
| MISSING | No artifact or manual evidence was found |
| N/A | `required_when` is false and a rationale exists, usually in `design/ux/surface-profile.md` |
| MANUAL | The step has no machine-checkable artifact; report what must be verified |

Rules:
- If a step has `artifact.glob`, use Glob and compare against `min_count`
  when present.
- If a step has `required_when`, evaluate it from the domain and
  `design/ux/surface-profile.md` when available.
- If applicability is ambiguous, mark the step `MANUAL`, not `COMPLETE`.
- Do not invent requirements that are not in the catalog.

## 4. Determine The Blocker And Next Commands

Find the first incomplete required step in the current phase.

If all current-phase required steps are complete:
- The current blocker is the phase gate, e.g. `/gate-check technical-setup`.
- The next commands are the first required commands in the next phase.

If a required step is incomplete:
- The current blocker is that step.
- The first next command is its `command`.
- The next two commands are the following required commands in phase order.

## 5. Build The Roadmap

Write a roadmap with this structure:

```markdown
# Project Roadmap

> Generated by `/cdd-status` from `workflow/workflow-catalog.yaml`.
> Last updated: [date]

## Snapshot

- Domain: [Game/Product/Unknown]
- Current phase: [phase]
- Required progress: [complete] / [total]
- Current blocker: [step or gate]

## Next Commands

1. `/command`
2. `/command`
3. `/command`

## Phase Progress

| Phase | Required | Complete | Missing | Status |
| ----- | -------- | -------- | ------- | ------ |
| ... |

## Current Phase Checklist

| Step | Required | Evidence | Status |
| ---- | -------- | -------- | ------ |
| ... |

## Product Surface Decisions

| Artifact | Status | Source |
| -------- | ------ | ------ |
| `design/ux/interaction-patterns.md` | REQUIRED / N/A / MISSING | `design/ux/surface-profile.md` or catalog |
| `design/design-system.md` | REQUIRED / N/A / OPTIONAL | surface profile / scope |
| `design/brand/style-guide.md` | OPTIONAL / REQUIRED BY SCOPE / N/A | surface profile / scope |

## After This Phase You Should Have

- [artifact glob or manual evidence generated from the catalog]

## Risks

- [missing critical evidence, stale sprint data, unresolved gate failure, or N/A without surface profile]

## Notes

- Catalog is authoritative.
- Gate checks remain governed advisory: `FAIL` requires explicit override and a risk note.
```

Keep the console response under 60 lines. The saved roadmap may be longer.

When writing the T2 mirror, use the same roadmap content with this extra header:

```markdown
> Governance memory mirror generated by `/cdd-status` from
> `workflow/workflow-catalog.yaml`.
> Customer/team-facing roadmap: `production/project-roadmap.md`.
```

## 6. Product Surface Profile Handling

For Product projects, read `design/ux/surface-profile.md` when present.

Use it to decide whether these are applicable:
- `design/ux/interaction-patterns.md`
- `design/design-system.md`
- `design/brand/style-guide.md`

Populate the roadmap's `Product Surface Decisions` table for Product projects:
- `interaction-patterns.md`: `REQUIRED` when the product has any API, CLI,
  SDK/library, UI, admin, operator, docs-driven consumer journey, or other
  user/integrator-facing surface; `N/A` only with surface-profile rationale;
  `MISSING` when required and absent.
- `design-system.md`: `REQUIRED` for UI-heavy or multi-surface UI products,
  `N/A` for API-only, CLI-only, SDK/library, or internal headless products with
  rationale, otherwise `OPTIONAL`.
- `style-guide.md`: `REQUIRED BY SCOPE` when public brand, docs imagery,
  screenshots, diagrams, marketing/release visuals, or visual tone are in
  scope; otherwise `OPTIONAL` or `N/A` when explicitly ruled out.

If a project marks one of these N/A without `design/ux/surface-profile.md`,
flag a risk:

`Product surface requirement marked N/A without design/ux/surface-profile.md.`

Recommend creating it from `templates/surface-profile.md`.

## 7. Output

Always report:
- Domain
- Current phase
- Progress count
- Current blocker
- Next 3 commands
- Product surface decision table when domain is Product
- Whether `production/project-roadmap.md` was written or only drafted
- Whether `memory_bank/t2_execution/current_roadmap.md` was written, skipped
  because `memory_bank/` is missing, or skipped because this was `--dry-run`

Do not mark a manual step complete without evidence.
