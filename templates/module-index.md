# Module Index: [Project Title]

> **Status**: [Draft / Under Review / Approved]
> **Created**: [Date]
> **Last Updated**: [Date]
> **Source Concept**: design/cdd/game-concept.md (game) or design/cdd/product-concept.md (product)

---

## Overview

[One paragraph explaining the project's module scope. Reference the core loop or
user journey, project pillars/principles, and the "big picture" of what needs to
be designed and built.]

---

## Module Enumeration

| # | Module Name | Category | Priority | Status | Design Doc | Depends On |
|---|-------------|----------|----------|--------|------------|------------|
| 1 | [e.g., Player Controller or Auth] | Core | MVP | [Not Started / In Design / In Review / Approved / Implemented] | [design/cdd/player-controller.md or "—"] | [e.g., Input System, Physics] |
| 2 | [e.g., Camera System or Dashboard] | Core | MVP | Not Started | — | [Module dependency] |

[Add a row for every identified module. Mark inferred modules with "(inferred)"
in the module name.]

---

## Categories

| Category | Description | Typical Modules |
|----------|-------------|-----------------|
| **Foundation** | Infrastructure or primitives that other modules depend on | Input, persistence, auth, shared data models, state management |
| **Core** | Modules required for the central loop or primary user journey | Movement, combat, editor canvas, dashboard, workflow engine |
| **Feature** | User-facing features built on core modules | Inventory, quests, reporting, notifications, collaboration |
| **Presentation** | UI, audio, visual feedback, or interaction surfaces | HUD, menus, settings, onboarding, alerts |
| **Operations** | Reliability, analytics, admin, release, or support modules | Telemetry, backups, moderation, billing, diagnostics |

[Remove categories that do not apply and add project-specific categories where
needed.]

---

## Priority Tiers

| Tier | Definition | Target Milestone | Design Urgency |
|------|------------|------------------|----------------|
| **MVP** | Required for the core loop or primary user journey to function | First playable/testable prototype | Design FIRST |
| **Vertical Slice** | Required for one complete, polished path through the experience | Vertical slice / demo | Design SECOND |
| **Alpha** | Complete rough scope, placeholder content acceptable | Alpha milestone | Design THIRD |
| **Full Vision** | Polish, edge cases, nice-to-haves, and content-complete features | Beta / Release | Design as needed |

---

## Dependency Map

[Modules sorted by dependency order. Design and build from top to bottom.]

### Foundation Layer (no dependencies)

1. [Module] — [one-line rationale for why this is foundational]

### Core Layer (depends on foundation)

1. [Module] — depends on: [list]

### Feature Layer (depends on core)

1. [Module] — depends on: [list]

### Presentation Layer (depends on features)

1. [Module] — depends on: [list]

### Polish Layer (depends on everything)

1. [Module] — depends on: [list]

---

## Recommended Design Order

[Combine dependency sort and priority tiers. Each module's CDD should be
completed and reviewed before starting dependent modules.]

| Order | Module | Priority | Layer | Agent(s) | Est. Effort |
|-------|--------|----------|-------|----------|-------------|
| 1 | [First module to design] | MVP | Foundation | [agent] | [S/M/L] |
| 2 | [Second module] | MVP | Foundation | [agent] | [S/M/L] |

[Effort estimates: S = 1 session, M = 2-3 sessions, L = 4+ sessions.]

---

## Circular Dependencies

[List any circular dependency chains found during analysis. Resolve each by
introducing an interface, changing ownership, or designing modules together.]

- [None found] OR
- [Module A <-> Module B: description and proposed resolution]

---

## High-Risk Modules

[Modules that are technically unproven, design-uncertain, or scope-dangerous.]

| Module | Risk Type | Risk Description | Mitigation |
|--------|-----------|------------------|------------|
| [Module] | [Technical / Design / Scope] | [What could go wrong] | [Prototype, research, or scope fallback] |

---

## Progress Tracker

| Metric | Count |
|--------|-------|
| Total modules identified | [N] |
| Design docs started | [N] |
| Design docs reviewed | [N] |
| Design docs approved | [N] |
| MVP modules designed | [N/total MVP] |
| Vertical Slice modules designed | [N/total VS] |

---

## Next Steps

- [ ] Review and approve this module enumeration
- [ ] Design MVP-tier modules first (use `/design-system [module-name]`)
- [ ] Run `/design-review` on each completed CDD
- [ ] Run `/gate-check pre-production` when MVP modules are designed
- [ ] Prototype the highest-risk module early (`/prototype [module]`)
