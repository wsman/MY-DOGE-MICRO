# ADR-0037: Case Progress Contract

## Status

Accepted

## Date

2026-07-05

## Decision Makers

wsman (product owner) · Codex implementation agent

## Summary

Sprint 028 implements the E4 governance workflow progress item from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`.

The key decision is to add a case-scoped progress contract with explicit
`status`, `owner`, `timestamp`, `blocking_issue`, and `next_action` fields.
Progress can be persisted per case step, but the read API derives a default
four-step governance view when no persisted progress rows exist. This gives the
Web case detail page a stable read path without requiring every existing case
to be backfilled.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10; FastAPI 0.123.8; Pydantic 2.12.4; SQLite; TypeScript ~6.0.2; Vue 3.5.32; Naive UI 2.44.1 |
| **Domain** | Governance Workflow / API Design / SDK / Frontend |
| **Knowledge Risk** | LOW - uses existing platform repository, migration, gateway router, SDK client, Pinia store, and case-detail panel patterns |
| **References Consulted** | `design/cdd/fastapi-service.md`, `docs/reference/http-api.md`, `docs/registry/entities.yaml`, `src/doge/platform/workspace/application/case_service.py`, `web/src/views/CaseDetailView.vue`, `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Focused repository/API/SDK/Web tests, SDK contract parity, route coverage, governance docs tests, docs/maturity validators, plan closure gate |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0024 (Single Stack Runtime Direction), ADR-0036 (Run List And Comparison), workspace/project/research-case platform objects |
| **Enables** | Sprint 028 case progress panel and future workflow-governance timelines |
| **Blocks** | None |
| **Ordering Note** | This ADR adds a read-first progress contract. Editable workflow orchestration, SLA policy, and notification flows require separate design. |

## Context

### Problem Statement

The platform workspace can show case assets, workflow executions, review state,
approvals, citations, evals, and recorded decisions, but it lacks a concise
case-level progress view. E4 asks for a gateway contract and Web component that
surface per-step governance workflow progress.

### Constraints

- Preserve the current local maturity posture: `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.
- Keep progress scoped to research cases and tenant-aware repository access.
- Avoid forcing historical cases through a destructive migration or manual
  backfill.
- Keep the Web feature read-only for this sprint.
- Maintain SDK contract parity for the new OpenAPI response entity.
- Do not close external/operator gates or claim production readiness.

### Requirements

- Add a backend contract for progress steps with status, owner, timestamp,
  blocking issue, and next action.
- Persist explicit progress rows for future workflow orchestration.
- Derive default progress from case, assets, executions, and decisions when no
  persisted rows exist.
- Expose `GET /v1/research-cases/{case_id}/progress`.
- Add Python and TypeScript SDK helpers.
- Render progress in the Web case detail page.
- Keep route registries, API docs, and governance tests synchronized.

## Decision

Add a `CaseProgressStep` domain model and `case_progress_steps` SQLite table
with a unique `(case_id, step_key)` constraint. The platform repository exposes
`save_case_progress_step()` and `list_case_progress_steps()`.

The case service returns persisted steps when available. Otherwise, it derives
four standard steps:

1. `intake`
2. `evidence`
3. `workflow`
4. `decision`

```text
GET /v1/research-cases/{case_id}/progress
  -> ResearchCaseService.build_case_progress(...)
  -> persisted case_progress_steps if present
  -> otherwise derived four-step governance progress
```

Python SDK:

```python
client.platform.get_case_progress("case-...")
```

TypeScript SDK:

```typescript
client.platform.getCaseProgress('case-...')
```

The Web platform store loads progress with the case workspace snapshot, and
`CaseProgressPanel.vue` renders the read-only status list in
`CaseDetailView.vue`.

### Architecture Diagram

```text
CaseDetailView
  -> Platform store loadCaseWorkspace()
    -> web api getCaseProgress()
      -> TypeScript SDK client.platform.getCaseProgress()
        -> GET /v1/research-cases/{case_id}/progress
          -> ResearchCaseService.build_case_progress()
            -> case_progress_steps or derived case/assets/executions/decisions
```

### Key Interfaces

```http
GET /v1/research-cases/{case_id}/progress
```

```json
{
  "case_id": "case-...",
  "source": "derived",
  "warnings": [],
  "steps": [
    {
      "progress_id": "cps-...",
      "case_id": "case-...",
      "step_key": "workflow",
      "label": "Workflow execution",
      "status": "in_progress",
      "owner": "operator",
      "timestamp": "...",
      "blocking_issue": "",
      "next_action": "Monitor run status and resolve approvals",
      "source_type": "workflow_execution",
      "source_id": "exec-...",
      "tenant_id": "local",
      "metadata": {"execution_count": 1}
    }
  ]
}
```

## Alternatives Considered

### Alternative 1: Web-only derived progress

- **Description**: Derive progress entirely in `CaseDetailView.vue`.
- **Pros**: No backend schema or route.
- **Cons**: Duplicates domain interpretation in the frontend and cannot support
  future persisted workflow-state changes.
- **Rejection Reason**: E4 explicitly asks for a gateway contract.

### Alternative 2: Persist only, no derived fallback

- **Description**: Return only rows stored in `case_progress_steps`.
- **Pros**: Simple read path.
- **Cons**: Existing cases would render empty until backfilled.
- **Rejection Reason**: The workspace already has enough case/execution state
  to provide useful progress without destructive backfill.

### Alternative 3: Fold progress into case review

- **Description**: Add progress fields to `/v1/research-cases/{case_id}/review`.
- **Pros**: Reuses an existing endpoint.
- **Cons**: Blurs review/memo state with workflow-progress state and weakens SDK
  ergonomics.
- **Rejection Reason**: Progress has a distinct lifecycle and field contract.

## Consequences

### Positive

- Case detail pages can show governance workflow progress without opening each
  related object.
- Future workflow orchestration can persist explicit per-step progress.
- Existing cases still display a useful derived progress view.
- OpenAPI and TypeScript SDK parity now cover `CaseProgressStepResponse`.
- API route authority includes the case progress route.

### Negative

- Adds one SQLite table and one API route.
- The initial Web panel is read-only.
- Derived progress is intentionally coarse and should not be treated as an SLA
  engine.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Users interpret derived progress as authoritative workflow automation | MEDIUM | LOW | The response includes `source`, and docs describe persisted-vs-derived behavior. |
| Status vocabulary drifts | LOW | MEDIUM | API tests assert the standard derived steps; SDK contract parity checks the response fields. |
| Route/docs drift | LOW | MEDIUM | Route coverage and S017 planning docs tests assert route table parity. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/fastapi-service.md` | `/v1/*` daemon routes must stay documented and route-covered. | Adds `GET /v1/research-cases/{case_id}/progress`, keeps the current route authority aligned, and keeps route coverage tests aligned. |
| `design/cdd/sprint-028-governance-progress.md` | Case progress needs a status/owner/timestamp/blocking/next-action contract. | Defines and implements `CaseProgressStep`. |
| `design/cdd/sprint-027-run-comparison.md` | Run history should support analyst review workflows. | Progress uses workflow executions and run links as part of the case-level governance view. |

## Performance Implications

- **CPU**: Small serialization pass over persisted rows or four derived steps.
- **Memory**: Bounded by a short per-case step list.
- **Load Time**: One additional request in `loadCaseWorkspace()`.
- **Database**: Adds indexed case progress rows with tenant scoping.

## Migration Plan

1. Add `CaseProgressStep` domain model.
2. Add `case_progress_steps` table and workspace migration.
3. Add platform repository save/list methods.
4. Add `ResearchCaseService.build_case_progress()`.
5. Add `GET /v1/research-cases/{case_id}/progress`.
6. Add Python and TypeScript SDK helpers.
7. Add Web API/store wiring and `CaseProgressPanel.vue`.
8. Update API docs, route registries, SDK contract check, and route-count tests.
9. Record Sprint 028 CDD, sprint record, and evidence manifest.

## Validation Criteria

- Repository persists and lists case progress steps.
- API returns the four derived progress steps when no persisted rows exist.
- Python SDK builds the correct progress request.
- TypeScript SDK builds the correct progress request and exports
  `CaseProgressStep`.
- Web store loads progress as part of a case workspace snapshot.
- Web progress panel renders step label, owner, status, and blocking context.
- SDK contract check passes with 15 surfaces and 15 parity checks.
- API doc route coverage and S017 planning docs tests pass against the current route authority.

## Related Decisions

- ADR-0024: Single Stack Runtime Direction
- ADR-0036: Run List And Comparison
