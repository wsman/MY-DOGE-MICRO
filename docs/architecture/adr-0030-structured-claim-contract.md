# ADR-0030: Structured Claim Contract for Research Memo Evidence

Status: Accepted
Date: 2026-07-05

## Context

UX-2 left B3, the conclusion-evidence matrix, deferred because memo output did
not yet expose a matrix-ready claim shape. Sprint 022 closed B4 by adding
approval explanation metadata, but the evidence pane still had to infer claim
state from internal `claims`, `citations`, and `relations` arrays.

## Decision

Add an additive `structured_claims` contract to investment memo artifact data
and mirror the same fields through the feature-flagged `/v1/runs/{run_id}/claims`
resource.

Each structured claim row carries:

- `claim_id`
- `claim_text`
- `status`
- `evidence_refs`
- `numeric_check_status`
- `risk_level`

The implementation derives these rows from the existing artifact claim,
citation, and relation data. It does not add a new table, does not change
approval resolution, and does not declare the full conclusion-evidence matrix
complete.

## Consequences

- Existing artifacts without `structured_claims` can still be projected into the
  new shape by `BuildRunSummary`.
- TypeScript SDK parity is updated for `RunClaimResponse` so SDK/Web consumers
  see the additive fields.
- The Web workspace may display a compact structured-claims list, but full
  matrix interactions remain B3 Phase 2.
- Runtime maturity and external/operator gates are unchanged.
