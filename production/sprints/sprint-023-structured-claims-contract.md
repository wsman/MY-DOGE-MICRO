# Sprint 023 — Structured Claims Contract

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-05

## Summary

Sprint 023 implements B3 Phase 1 from the repeated strategic-review backlog:
the structured claim contract needed before a conclusion-evidence matrix can be
built. The sprint does not claim the full matrix UI is complete.

## Delivered Scope

- Added `structured_claims` to investment memo artifact data through the
  citation assembler.
- Added a shared structured-claims builder that derives:
  `claim_id`, `claim_text`, `status`, `evidence_refs`,
  `numeric_check_status`, and `risk_level`.
- Extended `BuildRunSummary` so `/v1/runs/{run_id}/claims` returns the additive
  structured fields even for artifacts that only have legacy
  `claims/citations/relations` data.
- Extended `RunClaimResponse` and the TypeScript SDK `RunClaim` interface under
  the existing SDK parity gate.
- Added a compact Web structured-claims read path in ResearchAgentView.
- Added ADR-0030, the Sprint 023 CDD, and this sprint evidence trail.
- Not registered in `production/sprint-status.yaml`; this is a
  product-contract acceptance sprint, not a story-bearing sprint.

## Explicitly Still Deferred

- Full conclusion-evidence matrix interactions.
- Analyst/Developer mode.
- Artifact export.
- SDK cookbook files.
- `doge demo-pack`.
- Portfolio summary, governance-progress visualization, run comparison, and
  operator status subcommands.
- External/operator gates.

## Verification Scope

Focused verification covers artifact generation, artifact persistence,
response-model preservation, run summary API projection, SDK parity, and Web
fixture rendering. Full regression remains optional because the known
real-HTTP failure predates Sprint 022/023 and is not part of this contract
change.
