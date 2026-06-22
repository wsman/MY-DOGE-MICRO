# ADR-0017: Run Summary Citation API

## Status
Proposed

## Date
2026-06-22

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI 0.123.8, Pydantic 2.12.4, SQLite local persistence |
| **Domain** | API Design / Evidence / Runtime |
| **Knowledge Risk** | LOW for pinned FastAPI/Pydantic stack; MEDIUM for enterprise ACL because ADR-0015 is Proposed |
| **References Consulted** | `docs/reference/python/VERSION.md`, `design/cdd/run-summary-citation-api.md`, `design/cdd/research-copilot-agent-runtime.md`, `design/cdd/document-evidence-pipeline.md`, `docs/progress/runtime-maturity.yaml` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Contract tests for response schemas, citation ACL tests, eval determinism tests |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0011, ADR-0014 |
| **Enables** | ADR-0018, ADR-0020 |
| **Blocks** | Summary/citation implementation stories until route contracts and persistence semantics are accepted |
| **Ordering Note** | Enterprise citation drill-down must align with ADR-0015 before hosted or non-loopback use. |

## Context

### Problem Statement

The agent runtime can produce events and artifacts, and the evidence pipeline can preserve document provenance, but clients need stable APIs for reviewing run conclusions. If each UI or SDK reconstructs summaries and citations independently, claim support, ACL checks, and maturity labels will drift.

### Constraints

- Runtime remains experimental and production readiness remains false.
- Citation provenance must come from local evidence records, not provider IDs alone.
- `/v1` daemon contracts must stay compatible with SDK clients.
- Eval checks must be deterministic and testable without live provider spend.

### Requirements

- Provide summary, claim, citation, and eval endpoints for a run.
- Preserve provenance and support status per claim.
- Enforce tenant ACL on citation detail in enterprise mode.
- Avoid client-side inference as the source of truth.

## Decision

Add an API-backed summary and citation layer under `/v1/runs/{run_id}`. The backend assembles or retrieves a `run_summary`, `run_claim`, `run_citation`, and `run_eval_result` set from persisted runtime and evidence records. Clients consume this data without reconstructing it from raw events.

### Architecture Diagram

```text
runtime events/artifacts
        |
        v
summary assembler -> run_summary -> run_claim -> run_citation
        |                                |
        v                                v
 run_eval_result                 document evidence ACL
        |
        v
 /v1/runs/{run_id}/{summary|claims|citations|eval}
```

### Key Interfaces

- `GET /v1/runs/{run_id}/summary`
- `GET /v1/runs/{run_id}/claims`
- `GET /v1/runs/{run_id}/citations`
- `GET /v1/runs/{run_id}/eval`

Expected error codes include `404 run_not_found`, `409 run_not_ready`, `403 citation_access_denied`, and `422 malformed_provenance`.

## Alternatives Considered

### Alternative 1: UI-Reconstructed Summaries
- **Description**: The Vue client reads raw events and builds summary panels locally.
- **Pros**: Fast prototype.
- **Cons**: Duplicates logic across clients and bypasses ACL enforcement.
- **Rejection Reason**: Evidence and citation status must be server-authoritative.

### Alternative 2: Single Markdown Export Endpoint
- **Description**: Return one rendered markdown report with inline citations.
- **Pros**: Simple consumption path.
- **Cons**: Hard to test, hard to inspect claim support, and poor SDK ergonomics.
- **Rejection Reason**: The product needs structured claims and eval results.

### Alternative 3: Structured Run Summary API
- **Description**: Provide first-class summary, claims, citations, and eval resources.
- **Pros**: Testable, reusable across UI and SDK, and compatible with ACL checks.
- **Cons**: Requires additional persistence and assembly logic.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- Clients share one citation and claim-support contract.
- Eval gates can be tested without live model calls.
- ACL-sensitive citation detail stays behind the API.

### Negative

- Summary assembly requires freshness tracking.
- Claim extraction quality needs a cautious first implementation.
- More schemas must be kept compatible with SDK clients.

### Risks

- **Risk**: Unsupported claims appear authoritative.
  **Mitigation**: Preserve `support_status` and require UI distinction.
- **Risk**: Provider file IDs are mistaken for canonical evidence.
  **Mitigation**: Store provider IDs as metadata only and validate local provenance.

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `run-summary-citation-api.md` | Provide structured summary, claims, citations, and eval endpoints. | Defines route contracts and server-authoritative assembly. |
| `document-evidence-pipeline.md` | Citation drill-down must recheck document access. | Requires ACL enforcement on citation detail. |
| `sdk-daemon-client-interfaces.md` | SDK clients consume `/v1` runtime contracts. | Keeps the route family under `/v1/runs/{run_id}`. |

## Performance Implications

- **CPU**: Summary assembly is proportional to run event and artifact size.
- **Memory**: Bounded by paginated claims and citations.
- **Load Time**: Cached/current summaries should avoid repeated full event scans.
- **Network**: Structured responses may require multiple client calls; clients can cache snapshot IDs.

## Migration Plan

1. Add schemas and repository methods for summary, claims, citations, and eval results.
2. Add deterministic assembler/evaluator service.
3. Add `/v1/runs/{run_id}` route group.
4. Add SDK client methods.
5. Add Vue panels behind feature flags.

## Validation Criteria

- Contract tests cover all response shapes and error envelopes.
- ACL-denied citations do not return snippet text.
- Eval results are deterministic with mocked runtime/evidence records.
- Docs and UI do not emit production-ready labels while maturity gates remain open.

## Related Decisions

- ADR-0011: Agent Runtime Levels
- ADR-0014: Multimodal Financial Evidence
- ADR-0015: Enterprise Identity And Access Boundary
- `design/cdd/run-summary-citation-api.md`
