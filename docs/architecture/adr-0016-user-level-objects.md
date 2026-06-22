# ADR-0016: User Level Objects

## Status
Proposed

## Date
2026-06-22

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI 0.123.8, Pydantic 2.12.4, SQLite local persistence, DuckDB analytical reads |
| **Domain** | Data Storage / API Design / Auth Boundary |
| **Knowledge Risk** | LOW for pinned local stack; MEDIUM for enterprise auth because ADR-0015 is still Proposed |
| **References Consulted** | `docs/reference/python/VERSION.md`, `standards/technical-preferences.md`, `design/cdd/workspace-project-research-case.md`, `design/cdd/research-copilot-agent-runtime.md`, `design/cdd/document-evidence-pipeline.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | SQLite migration tests, route contract tests, ACL-denial tests once enterprise mode is enabled |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0003, ADR-0011 |
| **Enables** | ADR-0018, ADR-0020 |
| **Blocks** | Workspace/project/case implementation stories until this decision is accepted or explicitly superseded |
| **Ordering Note** | Enterprise membership semantics must align with ADR-0015 before non-loopback or hosted deployment is allowed. |

## Context

### Problem Statement

The runtime can persist sessions, runs, events, tools, documents, and artifacts, but operators do not yet have stable product-level containers for research work. Adding nullable `workspace_id`, `project_id`, or `case_id` columns directly to runtime and evidence tables would couple platform organization to runtime internals and create migration risk.

### Constraints

- Runtime maturity remains non-production while Sprint 017 external closure gates are open.
- Existing runtime and document tables must keep working for legacy daemon and API clients.
- Local-first SQLite must remain the default persistence target.
- Enterprise ACL behavior must not be implied as production-ready until ADR-0015 is accepted.

### Requirements

- Support workspace, project, and research case organization.
- Link existing runs, documents, artifacts, and watchlist items to cases.
- Avoid direct mutation of runtime/evidence schemas for optional platform context.
- Preserve soft-delete and audit-friendly timestamps.

## Decision

Create first-class `workspace`, `project`, and `research_case` tables plus association tables for cross-module links. Runtime runs, documents, artifacts, and watchlist items attach through join tables such as `case_runtime_runs`, `case_documents`, `case_artifacts`, and `case_watchlist_items`.

No runtime, document, artifact, or evidence table may receive nullable platform-context columns as part of the default migration. Such mutation requires a follow-up ADR that explains why association tables are insufficient.

### Architecture Diagram

```text
workspace
  |
  +-- project
        |
        +-- research_case
              |
              +-- case_runtime_runs -> runtime runs
              +-- case_documents    -> document evidence records
              +-- case_artifacts    -> generated artifacts
              +-- case_watchlist_items
```

### Key Interfaces

- `GET /v1/workspaces`
- `POST /v1/workspaces`
- `GET /v1/projects?workspace_id=...`
- `POST /v1/projects`
- `GET /v1/cases?project_id=...`
- `POST /v1/cases`
- `POST /v1/cases/{case_id}/runs/{run_id}`
- `POST /v1/cases/{case_id}/documents/{document_id}`

Association writes are idempotent. Duplicate links return the existing link record.

## Alternatives Considered

### Alternative 1: Add Nullable Context Columns To Runtime Tables
- **Description**: Add `workspace_id`, `project_id`, and `case_id` to runtime runs and evidence tables.
- **Pros**: Simple query shape for case views.
- **Cons**: Makes platform context part of every runtime migration and creates null-heavy legacy rows.
- **Rejection Reason**: It violates the plan's default database strategy and increases blast radius.

### Alternative 2: Store Case Context In JSON Metadata
- **Description**: Put workspace/project/case IDs in existing metadata JSON fields.
- **Pros**: Minimal schema work.
- **Cons**: Weak constraints, harder indexing, and unclear ACL enforcement.
- **Rejection Reason**: User-level objects need queryable and enforceable relationships.

### Alternative 3: Association Tables
- **Description**: Keep product organization tables separate and link existing records through join tables.
- **Pros**: Low migration risk, explicit ownership, good indexing, and reversible adoption.
- **Cons**: Requires joins and more repository methods.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- Existing runtime and evidence tables remain stable.
- Legacy clients keep working without workspace IDs.
- Case views can be built incrementally.
- Enterprise ACL can later consume membership without retrofitting every runtime row.

### Negative

- Case detail queries require joins.
- Association tables need idempotency and referential cleanup tests.
- The product must decide how much auto-linking is desirable during migration.

### Risks

- **Risk**: Operators may expect every legacy run to belong to a case immediately.
  **Mitigation**: Provide explicit linking and optional default workspace bootstrap.
- **Risk**: Enterprise semantics may drift before ADR-0015 is accepted.
  **Mitigation**: Keep enterprise deployment blocked and test ACL denial separately.

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `workspace-project-research-case.md` | Organize work by workspace, project, and case without mutating runtime tables. | Defines user object tables and association-table linkage. |
| `research-copilot-agent-runtime.md` | Runtime concepts remain shared across Level 1/2/3. | Keeps runtime run records independent of optional platform context. |
| `document-evidence-pipeline.md` | Evidence provenance remains canonical and local. | Links documents through associations without changing evidence ownership. |

## Performance Implications

- **CPU**: Minor overhead for joins on case detail views.
- **Memory**: Bounded by paginated case/run/document lists.
- **Load Time**: Case detail may require indexed association queries.
- **Network**: Additional API calls for object switchers and case detail.

## Migration Plan

1. Add SQLite migrations for workspace, project, research case, and association tables.
2. Create a default local workspace only when no workspace exists.
3. Add repository methods for CRUD and idempotent association writes.
4. Add `/v1` route contracts.
5. Add UI integration behind feature flags.

## Validation Criteria

- Migration test creates tables without modifying runtime or evidence schemas.
- Duplicate association writes are idempotent.
- Legacy daemon run creation works without workspace context.
- Enterprise mode denies membership-sensitive reads without trusted context.

## Related Decisions

- ADR-0003: Storage Repository Contract
- ADR-0011: Agent Runtime Levels
- ADR-0015: Enterprise Identity And Access Boundary
- `design/cdd/workspace-project-research-case.md`
