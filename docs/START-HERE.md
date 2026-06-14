# Start Here

This page answers the first decision only: what kind of project are you starting, which command should you run first, what file will appear, and what comes next.

Phase gates use the governed advisory policy from `workflow/workflow-catalog.yaml`: run the gate before normal advancement. `FAIL` does not update `production/stage.txt` unless you explicitly override it and record a risk note.

## Choose Your Path

| You are... | First command | Expected output | Next step |
|------------|---------------|-----------------|-----------|
| Starting a new game | `/constitute` | `memory_bank/t0_core/basic_law_index.md`, `production/review-mode.txt`, and project principles | If your idea is still fuzzy, run `/brainstorm game ideas`; then run `/design-review` and `/gate-check concept` before `/map-systems`. |
| Starting a new product, API, CLI, web app, SDK, or data pipeline | `/constitute` | `memory_bank/t0_core/basic_law_index.md`, `production/review-mode.txt`, and product principles | If the problem or workflow is still fuzzy, run `/brainstorm product ideas`; then run `/design-review` and `/gate-check concept` before `/map-systems`. |
| Bringing in an existing project | `/project-stage-detect` | A current-stage diagnosis based on existing `design/`, `docs/architecture/`, `src/`, `tests/`, and `production/` artifacts | Run `/adopt` or `/constitute` in existing-project mode, then retrofit only the missing artifacts for the detected stage. |

## What Happens After The First Command

| Stage | Normal required path |
|-------|----------------------|
| Concept | `/constitute` -> concept document -> `/design-review` -> `/gate-check concept` |
| Systems Design / Specification | `/map-systems` -> `/design-system` per MVP module -> `/design-review` -> `/review-all-gdds` -> `/gate-check systems-design` |
| Technical Setup / Architecture A | `/setup-engine` -> `/create-architecture` -> `/architecture-decision` -> `/architecture-review` -> `/create-control-manifest` |
| Technical Setup / Architecture B | Create `design/accessibility-requirements.md` from `templates/accessibility-requirements.md` -> `/test-setup` -> `/gate-check technical-setup` |
| Pre-Production / Pre-Implementation | `/ux-design` -> `/ux-review` -> `/prototype` -> `/create-epics` -> `/create-stories` -> `/sprint-plan` -> `/story-readiness` -> `/gate-check pre-production` |
| Production / Implementation | `/sprint-plan` -> `/story-readiness` -> `/dev-story` -> `/story-done` -> `/gate-check production` |
| Polish / Verification | `/playtest-report x3` or product validation x3 -> `/team-polish` -> `/gate-check polish` |
| Release | `/release-checklist` -> `/launch-checklist` -> `/team-release` |

Use `/help` at any time for the next required command based on the files that
already exist. Use `/cdd-status` when you want a saved progress dashboard at
`production/project-roadmap.md`; see
`docs/examples/project-roadmap.example.md` for a sample roadmap shape.

`memory_bank/` is the governance control plane created by `/constitute`: T0
current laws/state, T1 supporting context, T2 execution mirrors, and T3 evidence
indexes. It does not replace detailed work files in `design/`, `docs/`,
`workflow/`, `templates/`, `standards/`, or `production/`; it indexes and
mirrors them.
When `memory_bank/` exists, approved review, smoke/team QA, story closure,
sprint/milestone, gate, validation, and release writes also update T3 audit
indexes while original reports remain in their normal paths.

For the full user manual, see `docs/USER-MANUAL.md`. For a generated phase
artifact map, see `docs/PHASE-CHECKLISTS.md`. For customer delivery validation,
see `docs/CUSTOMER-ACCEPTANCE.md`.
