# Phase Checklists

> Generated from `workflow/workflow-catalog.yaml` by `scripts/generate_phase_checklists.py`.
> Do not hand-maintain phase requirements here; update the catalog, then regenerate this file.

Use this as a customer-facing view of what should exist after each phase.
Domain-specific rows are marked when a step applies only to Game or Product projects.

## Concept

| Required Step | Command | Evidence Generated From Catalog | Applies To |
| ------------- | ------- | ------------------------------- | ---------- |
| Constitution Legislation | `/constitute` | `memory_bank/t0_core/basic_law_index.md` | game, product |
| Concept Document | `/brainstorm` | `design/cdd/*-concept.md` (minimum 1) | game, product |
| Concept Review | `/design-review` | Concept document has been reviewed and does not have a MAJOR REVISION NEEDED verdict. | game, product |

## Systems Design

| Required Step | Command | Evidence Generated From Catalog | Applies To |
| ------------- | ------- | ------------------------------- | ---------- |
| Systems Map | `/map-systems` | `design/cdd/module-index.md` | game, product |
| System CDDs | `/design-system` | Check design/cdd/module-index.md — each MVP system needs Status: Approved | game, product |
| Per-System Design Review | `/design-review` | Manual evidence from the command output or review record | game, product |
| Cross-CDD Review | `/review-all-gdds` | `design/cdd/cross-review-*.md` | game, product |

## Technical Setup

| Required Step | Command | Evidence Generated From Catalog | Applies To |
| ------------- | ------- | ------------------------------- | ---------- |
| Technology Setup | `/setup-engine` | `standards/technical-preferences.md` | game, product |
| Architecture Document | `/create-architecture` | `docs/architecture/architecture.md` | game, product |
| Architecture Decisions (ADRs) | `/architecture-decision` | `docs/architecture/adr-*.md` (minimum 3) | game, product |
| Architecture Review | `/architecture-review` | `docs/architecture/architecture-review-*.md` | game, product |
| Control Manifest | `/create-control-manifest` | `docs/architecture/control-manifest.md` | game, product |
| Accessibility Requirements | Manual / template | `design/accessibility-requirements.md` | game, product |
| Test Framework Baseline | `/test-setup` | Minimum baseline: tests/unit/, tests/integration/, .github/workflows/tests.yml, and at least one example test file. | game, product |

## Pre-Production / Pre-Implementation

| Required Step | Command | Evidence Generated From Catalog | Applies To |
| ------------- | ------- | ------------------------------- | ---------- |
| UX Specs (key screens) | `/ux-design` | `design/ux/*.md` (minimum 1) | game, product |
| Product Interaction Patterns | `/ux-design` | `design/ux/interaction-patterns.md` | [product]; conditional |
| Product Surface Profile | `/ux-design` | `design/ux/surface-profile.md` | [product]; conditional |
| UX Review | `/ux-review` | Manual evidence from the command output or review record | game, product |
| Prototype | `/prototype` | `prototypes/*/README.md` (minimum 1) | game, product |
| Create Epics | `/create-epics` | `production/epics/*/EPIC.md` (minimum 1) | game, product |
| Create Stories | `/create-stories` | `production/epics/**/*.md` (minimum 2) | game, product |
| First Sprint Plan | `/sprint-plan` | `production/sprints/sprint-*.md` (minimum 1) | game, product |
| Story Readiness Baseline | `/story-readiness` | At least one first-sprint story has a READY verdict before normal advancement to Production / Implementation. | game, product |
| Vertical Slice Playtest | `/playtest-report` | `production/qa/evidence/playtests/playtest*.md` (minimum 1) | [game] |
| Product Workflow Validation | `/playtest-report` | `production/qa/evidence/user-tests/*.md` (minimum 1) | [product] |

## Production / Implementation

| Required Step | Command | Evidence Generated From Catalog | Applies To |
| ------------- | ------- | ------------------------------- | ---------- |
| Sprint Plan | `/sprint-plan` | `production/sprints/sprint-*.md` | game, product |
| Implement Stories | `/dev-story` | Check src/ for active code and production/epics/**/*.md for In Progress stories | game, product |
| Story Done Review | `/story-done` | Manual evidence from the command output or review record | game, product |

## Polish / Verification

| Required Step | Command | Evidence Generated From Catalog | Applies To |
| ------------- | ------- | ------------------------------- | ---------- |
| Playtest Sessions (x3) | `/playtest-report` | `production/qa/evidence/playtests/playtest*.md` (minimum 3) | [game] |
| Product Validation Sessions (x3) | `/playtest-report` | `production/qa/evidence/user-tests/*.md` (minimum 3) | [product] |
| Polish Team Pass | `/team-polish` | Manual evidence from the command output or review record | game, product |

## Release

| Required Step | Command | Evidence Generated From Catalog | Applies To |
| ------------- | ------- | ------------------------------- | ---------- |
| Release Checklist | `/release-checklist` | Manual evidence from the command output or review record | game, product |
| Launch Checklist | `/launch-checklist` | Manual evidence from the command output or review record | game, product |
| Release Orchestration | `/team-release` | Manual evidence from the command output or review record | game, product |
