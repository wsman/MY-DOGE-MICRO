# Gate Required Artifacts

> Governance memory mirror generated from `workflow/generated/gate-required-artifacts.md`.
> Do not edit by hand; update `workflow/workflow-catalog.yaml` and regenerate.

> Generated from `workflow/workflow-catalog.yaml` by `scripts/generate_gate_required_sections.py`.
> Do not hand-maintain gate required artifacts in `/gate-check`; update the catalog, then regenerate this file.

Use the section matching the active gate and detected project domain.
`/gate-check` may add hand-authored Quality / Risk Checks, but normal-progression blockers come from this generated file.

## Gate: Concept

### Game: Concept -> Systems Design

- [ ] **Constitution Legislation** (`/constitute`): `memory_bank/t0_core/basic_law_index.md`.
- [ ] **Concept Document** (`/brainstorm`): `design/cdd/*-concept.md` (minimum 1).
- [ ] **Concept Review** (`/design-review`): Concept document has been reviewed and does not have a MAJOR REVISION NEEDED verdict.

### Product: Concept -> Specification

- [ ] **Constitution Legislation** (`/constitute`): `memory_bank/t0_core/basic_law_index.md`.
- [ ] **Concept Document** (`/brainstorm`): `design/cdd/*-concept.md` (minimum 1).
- [ ] **Concept Review** (`/design-review`): Concept document has been reviewed and does not have a MAJOR REVISION NEEDED verdict.

## Gate: Systems Design

### Game: Systems Design -> Technical Setup

- [ ] **Systems Map** (`/map-systems`): `design/cdd/module-index.md`.
- [ ] **System CDDs** (`/design-system`): Check design/cdd/module-index.md — each MVP system needs Status: Approved.
- [ ] **Per-System Design Review** (`/design-review`): Manual evidence from the command output or review record.
- [ ] **Cross-CDD Review** (`/review-all-gdds`): `design/cdd/cross-review-*.md`.

### Product: Specification -> Architecture

- [ ] **Systems Map** (`/map-systems`): `design/cdd/module-index.md`.
- [ ] **System CDDs** (`/design-system`): Check design/cdd/module-index.md — each MVP system needs Status: Approved.
- [ ] **Per-System Design Review** (`/design-review`): Manual evidence from the command output or review record.
- [ ] **Cross-CDD Review** (`/review-all-gdds`): `design/cdd/cross-review-*.md`.

## Gate: Technical Setup

### Game: Technical Setup -> Pre-Production

- [ ] **Technology Setup** (`/setup-engine`): `standards/technical-preferences.md`.
- [ ] **Architecture Document** (`/create-architecture`): `docs/architecture/architecture.md`.
- [ ] **Architecture Decisions (ADRs)** (`/architecture-decision`): `docs/architecture/adr-*.md` (minimum 3).
- [ ] **Architecture Review** (`/architecture-review`): `docs/architecture/architecture-review-*.md`.
- [ ] **Control Manifest** (`/create-control-manifest`): `docs/architecture/control-manifest.md`.
- [ ] **Accessibility Requirements** (Manual / template): `design/accessibility-requirements.md`.
- [ ] **Test Framework Baseline** (`/test-setup`): Minimum baseline: tests/unit/, tests/integration/, .github/workflows/tests.yml, and at least one example test file.

### Product: Architecture -> Pre-Implementation

- [ ] **Technology Setup** (`/setup-engine`): `standards/technical-preferences.md`.
- [ ] **Architecture Document** (`/create-architecture`): `docs/architecture/architecture.md`.
- [ ] **Architecture Decisions (ADRs)** (`/architecture-decision`): `docs/architecture/adr-*.md` (minimum 3).
- [ ] **Architecture Review** (`/architecture-review`): `docs/architecture/architecture-review-*.md`.
- [ ] **Control Manifest** (`/create-control-manifest`): `docs/architecture/control-manifest.md`.
- [ ] **Accessibility Requirements** (Manual / template): `design/accessibility-requirements.md`.
- [ ] **Test Framework Baseline** (`/test-setup`): Minimum baseline: tests/unit/, tests/integration/, .github/workflows/tests.yml, and at least one example test file.

## Gate: Pre-Production / Pre-Implementation

### Game: Pre-Production -> Production

- [ ] **UX Specs (key screens)** (`/ux-design`): `design/ux/*.md` (minimum 1).
- [ ] **UX Review** (`/ux-review`): Manual evidence from the command output or review record.
- [ ] **Prototype** (`/prototype`): `prototypes/*/README.md` (minimum 1).
- [ ] **Create Epics** (`/create-epics`): `production/epics/*/EPIC.md` (minimum 1).
- [ ] **Create Stories** (`/create-stories`): `production/epics/**/*.md` (minimum 2).
- [ ] **First Sprint Plan** (`/sprint-plan`): `production/sprints/sprint-*.md` (minimum 1).
- [ ] **Story Readiness Baseline** (`/story-readiness`): At least one first-sprint story has a READY verdict before normal advancement to Production / Implementation.
- [ ] **Vertical Slice Playtest** (`/playtest-report`): `production/qa/evidence/playtests/playtest*.md` (minimum 1).

### Product: Pre-Implementation -> Implementation

- [ ] **UX Specs (key screens)** (`/ux-design`): `design/ux/*.md` (minimum 1).
- [ ] **Product Interaction Patterns** (`/ux-design`): `design/ux/interaction-patterns.md`. Conditional: Product has an API, CLI, SDK/library, web UI, desktop/mobile UI, admin console, docs-driven consumer journey, or other user/integrator-facing surface. Mark not applicable only for internal headless services with no consumer workflow.
- [ ] **Product Surface Profile** (`/ux-design`): `design/ux/surface-profile.md`. Conditional: Product surface applicability is ambiguous, or the project marks interaction patterns, design system, brand/style guide, or other user/integrator-facing surface artifacts as not applicable.
- [ ] **UX Review** (`/ux-review`): Manual evidence from the command output or review record.
- [ ] **Prototype** (`/prototype`): `prototypes/*/README.md` (minimum 1).
- [ ] **Create Epics** (`/create-epics`): `production/epics/*/EPIC.md` (minimum 1).
- [ ] **Create Stories** (`/create-stories`): `production/epics/**/*.md` (minimum 2).
- [ ] **First Sprint Plan** (`/sprint-plan`): `production/sprints/sprint-*.md` (minimum 1).
- [ ] **Story Readiness Baseline** (`/story-readiness`): At least one first-sprint story has a READY verdict before normal advancement to Production / Implementation.
- [ ] **Product Workflow Validation** (`/playtest-report`): `production/qa/evidence/user-tests/*.md` (minimum 1).

## Gate: Production / Implementation

### Game: Production -> Polish

- [ ] **Sprint Plan** (`/sprint-plan`): `production/sprints/sprint-*.md`.
- [ ] **Implement Stories** (`/dev-story`): Check src/ for active code and production/epics/**/*.md for In Progress stories.
- [ ] **Story Done Review** (`/story-done`): Manual evidence from the command output or review record.

### Product: Implementation -> Verification

- [ ] **Sprint Plan** (`/sprint-plan`): `production/sprints/sprint-*.md`.
- [ ] **Implement Stories** (`/dev-story`): Check src/ for active code and production/epics/**/*.md for In Progress stories.
- [ ] **Story Done Review** (`/story-done`): Manual evidence from the command output or review record.

## Gate: Polish / Verification

### Game: Polish -> Release

- [ ] **Playtest Sessions (x3)** (`/playtest-report`): `production/qa/evidence/playtests/playtest*.md` (minimum 3).
- [ ] **Polish Team Pass** (`/team-polish`): Manual evidence from the command output or review record.

### Product: Verification -> Release

- [ ] **Product Validation Sessions (x3)** (`/playtest-report`): `production/qa/evidence/user-tests/*.md` (minimum 3).
- [ ] **Polish Team Pass** (`/team-polish`): Manual evidence from the command output or review record.
