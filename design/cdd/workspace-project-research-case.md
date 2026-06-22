# Workspace Project Research Case

> **Status**: In Design
> **Author**: User + Codex
> **Last Updated**: 2026-06-22
> **Implements Pillar**: Local First; Operator Control; Layered Interfaces

## Overview

Workspace Project Research Case defines the user-level object hierarchy that groups documents, agent runs, artifacts, watchlists, and workflow outputs without rewriting runtime tables. It gives operators a stable way to organize research while preserving the existing runtime and evidence boundaries.

## User Promise

An operator can keep market research organized by workspace, project, and case, then reopen a case later with its runs, documents, summaries, and decisions still connected.

## Detailed Design

### Core Specification

1. A workspace is the top-level local container for a user or team context.
2. A project groups one or more research cases under a workspace.
3. A research case is the actionable unit for a market thesis, stock review, sector study, or due-diligence workflow.
4. Runtime runs, documents, artifacts, notes, watchlists, and workflow executions attach to user objects through association tables.
5. Existing runtime, document, and artifact tables must not gain nullable context columns unless a follow-up ADR explicitly approves that migration.
6. Enterprise mode must treat workspace/project/case membership as an ACL input, but this module does not make ADR-0015 production-ready.
7. Deleting a workspace, project, or case is soft-delete by default.

### States and Transitions

| Object | State | Meaning | Valid Transitions |
|--------|-------|---------|-------------------|
| Workspace | `active` | Available for normal use. | `archived`, `deleted`. |
| Workspace | `archived` | Hidden from default lists but recoverable. | `active`, `deleted`. |
| Project | `active` | Accepts new cases and linked runs. | `archived`, `deleted`. |
| Research Case | `open` | Work is in progress. | `reviewing`, `closed`, `archived`. |
| Research Case | `reviewing` | Outputs are being evaluated. | `open`, `closed`. |
| Research Case | `closed` | Decision has been recorded. | `open`, `archived`. |

### Interactions with Other Modules

| Module | Interaction |
|--------|-------------|
| Research Copilot Agent Runtime | Links runs to projects and cases through association tables. |
| Document Evidence Pipeline | Links documents and evidence sets to cases without changing document ownership. |
| Run Summary Citation API | Reads case context to group summaries and citations. |
| Workflow Templates | Can start a workflow execution inside a selected case. |
| Platform Shell UI | Provides object switchers and navigation context. |
| FastAPI Service | Hosts CRUD and association endpoints under `/v1`. |

## Data Model

The `workspace` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `workspace_id` | string | Yes | Stable UUID or ULID | Workspace identifier. |
| `name` | string | Yes | 1 to 120 chars | Display name. |
| `description` | string | No | 0 to 1000 chars | Operator note. |
| `status` | enum | Yes | `active`, `archived`, `deleted` | Lifecycle state. |
| `created_at` | datetime | Yes | UTC | Creation time. |
| `updated_at` | datetime | Yes | UTC | Last update time. |
| `deleted_at` | datetime | No | UTC | Soft-delete timestamp. |

**Relationships:** `workspace` -> `project` (1:N) via `workspace_id`.
**Indexes:** `status`, `updated_at`.
**Example:** `workspace{name="Local Research"}` owns multiple sector projects.

The `project` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `project_id` | string | Yes | Stable UUID or ULID | Project identifier. |
| `workspace_id` | string | Yes | References `workspace` | Parent workspace. |
| `name` | string | Yes | 1 to 160 chars | Project name. |
| `status` | enum | Yes | `active`, `archived`, `deleted` | Lifecycle state. |
| `default_market` | string | No | `CN`, `US`, or configured market | Optional market focus. |
| `created_at` | datetime | Yes | UTC | Creation time. |
| `updated_at` | datetime | Yes | UTC | Last update time. |

**Relationships:** `project` -> `research_case` (1:N) via `project_id`.
**Indexes:** `workspace_id`, `status`, `updated_at`.
**Example:** A "Semiconductor 2026" project contains issuer and industry-chain cases.

The `research_case` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `case_id` | string | Yes | Stable UUID or ULID | Case identifier. |
| `project_id` | string | Yes | References `project` | Parent project. |
| `title` | string | Yes | 1 to 200 chars | Case title. |
| `thesis` | string | No | Markdown allowed | Working thesis or question. |
| `status` | enum | Yes | `open`, `reviewing`, `closed`, `archived`, `deleted` | Case lifecycle. |
| `decision` | string | No | `watch`, `reject`, `hold`, `buy_candidate`, or empty | Operator decision label. |
| `created_at` | datetime | Yes | UTC | Creation time. |
| `updated_at` | datetime | Yes | UTC | Last update time. |

**Relationships:** `research_case` -> runtime runs, documents, artifacts, watchlists, and workflow executions through association tables.
**Indexes:** `project_id`, `status`, `updated_at`, `decision`.
**Example:** A case asks whether ticker `300750` remains a watch candidate after new filings.

The association tables are defined as:

| Table | Required Fields | Relationship | Notes |
|-------|-----------------|--------------|-------|
| `case_runtime_runs` | `case_id`, `run_id`, `linked_at`, `link_type` | N:M | Links existing runtime runs without modifying runtime tables. |
| `case_documents` | `case_id`, `document_id`, `linked_at`, `purpose` | N:M | Links uploaded or registered evidence. |
| `case_artifacts` | `case_id`, `artifact_id`, `linked_at`, `artifact_kind` | N:M | Links generated reports, charts, and exports. |
| `case_watchlist_items` | `case_id`, `ticker`, `market`, `linked_at` | 1:N | Links market instruments to the case. |
| `project_runtime_runs` | `project_id`, `run_id`, `linked_at` | N:M | Optional project-level linkage for runs not yet assigned to a case. |

**Indexes:** Composite indexes on every foreign-key pair plus `linked_at`.
**Example:** A run can be linked to one case and later also linked to a review project without runtime schema mutation.

## Edge Cases

- **If a run is linked to a deleted case**: preserve the association but hide it from default lists.
- **If a project is archived while cases remain open**: keep cases readable and prevent new default case creation under that project.
- **If the same document is linked twice to a case**: enforce idempotent association by `(case_id, document_id)`.
- **If enterprise context is missing in enterprise mode**: deny membership-sensitive reads by default.
- **If a runtime run predates workspace support**: allow explicit linking through association tables.
- **If a case is closed**: allow read and export but require an explicit reopen before adding new runs.

## Dependencies

- Depends on Runtime Configuration for local database path and feature flags.
- Depends on Market Data Storage conventions for SQLite persistence.
- Depends on Research Copilot Agent Runtime and Document Evidence Pipeline identifiers.
- Consumed by Workflow Templates, Run Summary Citation API, Platform Shell UI, and SDK clients.
- Governed by ADR-0015 and ADR-0016.

## Configuration

| Parameter | Default | Scope | Description |
|-----------|---------|-------|-------------|
| `DOGE_WORKSPACE_OBJECTS_ENABLED` | `false` until implemented | Runtime flag | Enables workspace/project/case APIs and UI. |
| `DOGE_DEFAULT_WORKSPACE_NAME` | `Local Research` | Local profile | Name used for migration-created workspace. |
| `DOGE_CASE_SOFT_DELETE_DAYS` | empty | Local profile | Optional retention marker; empty means no automatic purge. |

## Integration Requirements

- CRUD routes should live under `/v1/workspaces`, `/v1/projects`, and `/v1/cases`.
- Association routes must be idempotent and return stable link records.
- Backfill migration must create a default workspace only when no workspace records exist.
- Existing runtime and evidence endpoints must keep working without a workspace selected.
- SDK clients must expose object IDs but not require them for legacy daemon calls.

## UI Requirements

- Platform shell should expose workspace, project, and case switchers.
- Research Agent view should accept optional case context without breaking `/research-agent`.
- Case detail should show linked runs, documents, summaries, artifacts, and decisions.
- Closed cases should be visibly read-mostly and require an explicit reopen action.

## Acceptance Criteria

- **GIVEN** no workspace records exist, **WHEN** the migration or bootstrap runs, **THEN** a default local workspace can be created without changing runtime run rows.
- **GIVEN** an existing run ID, **WHEN** it is linked to a case twice, **THEN** the second request returns the existing association rather than a duplicate.
- **GIVEN** a closed research case, **WHEN** a new run link is requested, **THEN** the API rejects the write until the case is reopened.
- **GIVEN** enterprise mode without a trusted context, **WHEN** a case list is requested, **THEN** the API denies access by default.
- **GIVEN** a legacy daemon client that sends no workspace ID, **WHEN** it starts a run, **THEN** the runtime still works and no user object is required.

## Open Questions

- Should local-first membership support multiple local users before ADR-0015 is accepted?
- Should watchlists be first-class objects or remain case association records initially?
- Which existing reports should be auto-linked during migration, if any?
