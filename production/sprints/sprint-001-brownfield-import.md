# Sprint 001 -- Brownfield Metadata Import

## Sprint Goal

Capture MY-DOGE-MICRO's current Git state, product intent, architecture migration direction, and development progress in CDD-compatible artifacts without copying source code or migrating Git history.

## Milestone Context

- **Current Milestone**: Implementation / Brownfield Modularization
- **Milestone Deadline**: Not set
- **Sprints Remaining**: Not set

## Capacity

| Resource | Available Days | Allocated | Buffer (20%) | Remaining |
|----------|----------------|-----------|--------------|-----------|
| Programming | Not set | Not set | Not set | Not set |
| Design | Not set | Not set | Not set | Not set |
| QA | Not set | Not set | Not set | Not set |
| **Total** | Not set | Not set | Not set | Not set |

## Tasks

### Must Have (Critical Path)

| ID | Task | Agent/Owner | Est. Days | Dependencies | Acceptance Criteria | Status |
|----|------|-------------|-----------|--------------|---------------------|--------|
| S001-001 | Record source Git snapshot | technical-director | 0.25 | None | Remote, branch, HEAD, dirty state, diff stat, and untracked summary captured | Complete |
| S001-002 | Configure product stack in CDD workspace | technical-director | 0.25 | S001-001 | `AGENTS.md`, technical preferences, and Python stack reference identify the product stack | Complete |
| S001-003 | Create imported product concept | creative-director, technical-director | 0.5 | S001-001 | Product promise, users, workflow, scope, and risks captured with `Status: In Design` | Complete |
| S001-004 | Create module index | technical-director | 0.5 | S001-003 | 12 imported modules listed with exact status values and dependency order | Complete |
| S001-005 | Record clean architecture ADR | lead-programmer | 0.5 | S001-004 | ADR includes Status, Technology Compatibility, ADR Dependencies, CDD Requirements Addressed, and Performance Implications | Complete |

### Should Have

| ID | Task | Agent/Owner | Est. Days | Dependencies | Acceptance Criteria | Status |
|----|------|-------------|-----------|--------------|---------------------|--------|
| S001-010 | Run adoption audit | technical-director | 0.5 | S001-005 | Adoption plan identifies remaining CDD pipeline gaps and next commands | Complete |
| S001-011 | Run source Python tests | qa-lead | 0.5 | S001-005 | `pytest` result recorded as evidence | Complete |
| S001-012 | Run web build/type check | qa-lead | 0.5 | S001-005 | `npm run build` result recorded as evidence | Blocked |

### Nice to Have (Cut First)

| ID | Task | Agent/Owner | Est. Days | Dependencies | Acceptance Criteria | Status |
|----|------|-------------|-----------|--------------|---------------------|--------|
| S001-020 | Draft first module CDD | systems-designer | 1 | S001-004 | Clean Architecture Migration CDD ready for design review | Not Started |

## Carryover from Sprint 000

| Original ID | Task | Reason for Carryover | New Estimate | Priority Change |
|-------------|------|----------------------|--------------|-----------------|
| N/A | N/A | N/A | N/A | N/A |

## Risks to This Sprint

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| Source repository has important untracked work | High | High | Capture untracked state and avoid mutating source repository | technical-director |
| CDD docs lag implemented code | High | Medium | Treat imported docs as baseline, then retrofit module CDDs | systems-designer |
| Tests may require unavailable local data or dependencies | Medium | Medium | Run tests separately and record environment-specific failures | qa-lead |

## External Dependencies

| Dependency | Status | Impact if Delayed | Contingency |
|------------|--------|-------------------|-------------|
| `MY-DOGE-MICRO` source repository | Available locally | Cannot verify imported facts | Keep imported paths and snapshot commands documented |
| Market/API credentials and local data | Not verified during metadata import | Integration tests may fail | Separate metadata import from runtime verification |

## Definition of Done

- [x] Git snapshot and source current-state import docs created.
- [x] Product stack configured in CDD workspace.
- [x] Product concept created.
- [x] Module index created without parenthetical status values.
- [x] Clean architecture ADR created with CDD-required sections.
- [x] Adoption plan created.
- [x] Optional source test evidence recorded.
- [x] Optional web build evidence recorded.

## Daily Status Tracking

| Day | Tasks Completed | Tasks In Progress | Blockers | Notes |
|-----|-----------------|-------------------|----------|-------|
| Day 1 | S001-001 through S001-010 | Optional verification | None | Metadata import completed without source repository mutation |
