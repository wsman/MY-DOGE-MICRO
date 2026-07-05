# Sprint 023 CDD: Structured Claims Contract

Status: Ready for Acceptance
Date: 2026-07-05

## User Promise

Analysts need each research memo conclusion to carry enough structure for a
future conclusion-evidence matrix: the claim text, evidence references, numeric
check status, and risk level must be available without parsing Markdown.

## Delivered Contract

Sprint 023 Phase 1 closes the B3 contract foundation only. It adds additive
structured claim rows to runtime artifacts and `/v1` run claim reads.

Required row fields:

| Field | Meaning |
|---|---|
| `claim_id` | Stable claim identifier from the extracted claim. |
| `claim_text` | Human-readable conclusion text. |
| `status` | Product-facing support state such as `supported`, `partial`, `contradicted`, `insufficient_evidence`, or `unverified`. |
| `evidence_refs` | Citation/evidence references attached to the claim. |
| `numeric_check_status` | `passed`, `failed`, `not_checked`, or `not_applicable`. |
| `risk_level` | `low`, `medium`, or `high`, derived from support and numeric status. |

## Non-Goals

- No complete conclusion-evidence matrix UI.
- No new persistence table or migration.
- No artifact export, demo-pack, run comparison, or operator gate closure.
- No approval resolution or entitlement behavior change.

## Acceptance Criteria

- Investment memo artifacts include `data.structured_claims` when citation
  assembly runs.
- Existing claim/citation/relation artifact data can be projected into the same
  structured shape through the run summary use case.
- `/v1/runs/{run_id}/claims` preserves previous fields and adds the structured
  claim metadata.
- TypeScript SDK parity passes for the updated `RunClaimResponse`.
- The Web workspace can read and render a compact structured-claims fixture.
- Closure gate remains `4 open / 2 passed`; production posture is unchanged.
