# Run Summary Citation API

> **Status**: In Design
> **Author**: User + Codex
> **Last Updated**: 2026-06-22
> **Implements Pillar**: Evidence Before Narrative; Operator Control; Local First

## Overview

Run Summary Citation API defines the API contract that turns a Research Copilot run into inspectable outputs: a summary, claim list, citation set, and deterministic evaluation report. It builds on the Research Copilot Agent Runtime and Document Evidence Pipeline, and it is explicitly experimental while Sprint 017 closure gates remain open.

## User Promise

When an operator reviews an agent run, they can see what the run concluded, which claims were made, which evidence supports each claim, and which checks still failed before trusting or exporting the result.

## Detailed Design

### Core Specification

1. The module exposes read-focused `/v1/runs/{run_id}/summary`, `/v1/runs/{run_id}/claims`, `/v1/runs/{run_id}/citations`, and `/v1/runs/{run_id}/eval` endpoints.
2. A run summary is derived from persisted runtime events and artifacts, not from browser-local state.
3. A claim is a discrete assertion extracted from the run's final or latest assistant output. Each claim carries support status: `supported`, `unsupported`, `unverified`, or `conflicted`.
4. A citation links a claim or summary section to local evidence provenance: document ID, page ID, chunk ID, byte or text offsets when available, and a bounded snippet hash. Provider file IDs remain metadata only.
5. The eval endpoint performs deterministic checks: citation coverage, broken evidence references, tenant ACL denial, stale run state, unsupported claims, and malformed provenance.
6. Enterprise mode must apply the same trusted EnterpriseContext and tenant ACL rules described by ADR-0015 before returning citation detail.
7. The API must never convert open Sprint 017 gates into a stable or production-ready runtime label.

### States and Transitions

| State | Meaning | Valid Transitions |
|-------|---------|-------------------|
| `not_available` | No summary snapshot exists and the run has no usable answer artifact. | `draft` when answer artifacts exist. |
| `draft` | Summary or claims were assembled from an in-progress run. | `current`, `stale`, `not_available`. |
| `current` | Summary, claims, citations, and eval reflect the current terminal run state. | `stale` when run events or evidence change. |
| `stale` | Persisted summary exists but no longer matches latest run or evidence metadata. | `current` after refresh, `not_available` after source removal. |

### Interactions with Other Modules

| Module | Interaction |
|--------|-------------|
| Research Copilot Agent Runtime | Supplies run state, events, artifacts, tool calls, and final assistant output. |
| Document Evidence Pipeline | Supplies document, page, chunk, and evidence provenance; enforces citation source integrity. |
| FastAPI Service | Hosts the `/v1/runs/*` route surface and HTTP error envelopes. |
| SDK And Daemon Client Interfaces | Consumes the same route contracts for Python and TypeScript clients. |
| Vue Web Console | Displays summaries, claims, citations, and eval status without reconstructing them client-side. |

## Data Model

The `run_summary` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `summary_id` | string | Yes | Stable UUID or ULID | Summary snapshot identifier. |
| `run_id` | string | Yes | References runtime run | Run summarized by this snapshot. |
| `status` | enum | Yes | `not_available`, `draft`, `current`, `stale` | Snapshot freshness state. |
| `summary_text` | string | No | Redacted for denied citations | Human-readable run summary. |
| `created_at` | datetime | Yes | UTC | Snapshot creation time. |
| `updated_at` | datetime | Yes | UTC | Last refresh time. |
| `source_event_high_watermark` | string | No | Runtime event ID | Latest event included in the snapshot. |

**Relationships:** `run_summary` -> runtime run (N:1) via `run_id`; `run_summary` -> `run_claim` (1:N) via `summary_id`.
**Indexes:** `run_id`, `status`, `updated_at`.
**Example:** A completed run has one `current` summary and five linked claims.

The `run_claim` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `claim_id` | string | Yes | Stable UUID or ULID | Claim identifier. |
| `summary_id` | string | Yes | References `run_summary` | Parent summary snapshot. |
| `claim_text` | string | Yes | Non-empty | The assertion under review. |
| `support_status` | enum | Yes | `supported`, `unsupported`, `unverified`, `conflicted` | Evidence support result. |
| `confidence` | float | No | 0.0 to 1.0 | Deterministic confidence or model-scored value when explicitly marked. |
| `created_at` | datetime | Yes | UTC | Claim creation time. |

**Relationships:** `run_claim` -> `run_citation` (1:N) via `claim_id`.
**Indexes:** `summary_id`, `support_status`.
**Example:** A claim about revenue growth is `supported` when at least one accessible document chunk backs it.

The `run_citation` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `citation_id` | string | Yes | Stable UUID or ULID | Citation identifier. |
| `claim_id` | string | No | References `run_claim` | Claim supported by this citation. |
| `run_id` | string | Yes | References runtime run | Run that produced or used the citation. |
| `document_id` | string | Yes | References document evidence | Source document. |
| `page_id` | string | No | References document page | Source page when available. |
| `chunk_id` | string | No | References document chunk | Source chunk when available. |
| `snippet_hash` | string | Yes | SHA-256 or equivalent | Integrity check for displayed snippet. |
| `provider_file_id` | string | No | Metadata only | Provider-side file handle, never canonical provenance. |

**Relationships:** `run_citation` -> document evidence records (N:1) via document/page/chunk IDs.
**Indexes:** `run_id`, `claim_id`, `document_id`, `chunk_id`.
**Example:** A Kimi file citation stores provider metadata but resolves display text from local chunk storage.

The `run_eval_result` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `eval_id` | string | Yes | Stable UUID or ULID | Evaluation identifier. |
| `run_id` | string | Yes | References runtime run | Run evaluated. |
| `summary_id` | string | No | References `run_summary` | Summary evaluated. |
| `coverage_ratio` | float | Yes | 0.0 to 1.0 | Share of claims with at least one accessible citation. |
| `failed_checks` | array | Yes | String identifiers | Deterministic failures. |
| `created_at` | datetime | Yes | UTC | Evaluation time. |

**Relationships:** `run_eval_result` -> runtime run (N:1) and optional summary (N:1).
**Indexes:** `run_id`, `created_at`.
**Example:** A run with two unsupported claims returns `failed_checks=["unsupported_claims"]`.

## Edge Cases

- **If a run is still running**: return a `draft` summary when enough artifacts exist and mark eval as incomplete.
- **If a citation points to missing local evidence**: return the citation with `support_status=unverified` and include `broken_evidence_reference` in eval failures.
- **If enterprise ACL denies the source document**: hide snippet text, return an authorization failure for drill-down, and count the citation as inaccessible.
- **If no final assistant output exists**: return `not_available` with a stable empty response shape.
- **If provider file metadata exists but local evidence is absent**: do not treat the provider file ID as canonical support.
- **If summary refresh races with new runtime events**: mark the snapshot `stale` unless the high-watermark matches the latest event.

## Dependencies

- Requires Research Copilot Agent Runtime event and artifact persistence.
- Requires Document Evidence Pipeline provenance and tenant ACL checks.
- Requires FastAPI `/v1` routing and Pydantic response schemas.
- Consumed by SDK daemon clients and Vue Web Console.
- Governed by ADR-0011, ADR-0014, ADR-0015, and ADR-0017.

## Configuration

| Parameter | Default | Scope | Description |
|-----------|---------|-------|-------------|
| `DOGE_RUN_SUMMARY_API_ENABLED` | `false` until implemented | Runtime flag | Enables the route group without changing maturity labels. |
| `DOGE_CITATION_SNIPPET_CHARS` | `500` | Process config | Maximum snippet length returned in API responses. |
| `DOGE_RUN_EVAL_STRICT_ACL` | `true` | Enterprise/local mode | Counts ACL-denied citations as inaccessible in eval results. |

## Integration Requirements

- Route prefix must remain `/v1/runs/{run_id}` to align with existing daemon contracts.
- Responses must use explicit schemas rather than ad hoc dictionaries.
- Errors must distinguish `404 run_not_found`, `409 run_not_ready`, `403 citation_access_denied`, and `422 malformed_provenance`.
- SDK clients must preserve bearer token forwarding and correlation IDs.
- Tests must cover route contract, ACL denial, stale summary detection, and unsupported citation evaluation.

## UI Requirements

- The Vue console should show summary, claims, citations, and eval status as API-backed panels.
- Citation drill-down must fetch source detail through the API rather than trusting preloaded browser state.
- Unsupported or unverified claims must be visually distinct from supported claims.
- The UI must continue to label the runtime as experimental while open gates remain.

## Acceptance Criteria

- **GIVEN** a completed run with persisted answer and evidence, **WHEN** `/v1/runs/{run_id}/summary` is requested, **THEN** the response includes a `current` summary and linked counts for claims and citations.
- **GIVEN** a claim with one accessible document chunk citation, **WHEN** `/v1/runs/{run_id}/claims` is requested, **THEN** the claim reports `support_status=supported` and references the citation ID.
- **GIVEN** a citation whose document is denied by tenant ACL, **WHEN** citation detail is requested in enterprise mode, **THEN** the API returns `403 citation_access_denied` and does not expose snippet text.
- **GIVEN** a run with unsupported claims, **WHEN** `/v1/runs/{run_id}/eval` is requested, **THEN** the eval result includes the unsupported claim count and a failed check identifier.
- **GIVEN** open Sprint 017 closure gates, **WHEN** docs or API metadata are generated, **THEN** no stable or production-ready runtime label is emitted.

## Open Questions

- Should claim extraction initially be deterministic text segmentation or adapter-backed model scoring?
- Should summary refresh be synchronous on request or queued as a background task?
- Which UI route owns citation drill-down once the platform shell lands?
