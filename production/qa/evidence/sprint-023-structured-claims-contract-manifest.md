# Sprint 023 — Structured Claims Contract Manifest

> Sprint: 023 (B3 Phase 1 Structured Claims Contract)
> Date: 2026-07-05
> Status: Local implementation complete; ready for local acceptance.

## Scope

This manifest records the local evidence for B3 Phase 1. The sprint adds a
matrix-ready structured claim contract, but it does not close the full
conclusion-evidence matrix UI.

Structured claim row fields:

- `claim_id`
- `claim_text`
- `status`
- `evidence_refs`
- `numeric_check_status`
- `risk_level`

## Implementation Evidence

| Area | Evidence |
|---|---|
| Contract builder | `src/doge/application/services/structured_claims.py` derives status, evidence refs, numeric status, and risk level. |
| Artifact output | `src/doge/application/agent/artifact_citation_assembler.py` writes `data.structured_claims`. |
| Run summary API | `src/doge/application/use_cases/run_summary.py` projects structured fields into `/v1/runs/{run_id}/claims`. |
| API response model | `src/doge/interfaces/gateway/routers/_response_models.py` extends `RunClaimResponse` additively. |
| SDK parity | `packages/doge-sdk-typescript/src/platform-types.ts` extends `RunClaim`. |
| Web read path | `web/src/views/ResearchAgentView.vue` renders a compact structured-claims list from artifact data. |
| Persistence | `AgentArtifact.data` JSON round-trips `structured_claims`; no schema migration is required. |
| Governance | ADR-0030 and the Sprint 023 CDD document the contract and non-goals. |

## Verification Commands

```bash
cmd.exe /c "set PYTHONPATH=src&&py -3 -m pytest tests\unit\agent\test_artifact_citation_assembler.py tests\unit\agent\test_repositories.py tests\unit\gateway\test_response_models_wire.py tests\contract\test_run_summary_api.py -q"
cmd.exe /c "set PYTHONPATH=src&&py -3 tools\ci\sdk-contract-check.py"
npm run test -- src/views/ResearchAgentView.spec.ts
```

## Posture

- Production posture unchanged.
- Closure gate remains `4 open / 2 passed`.
- B3 Phase 2 remains open for the complete conclusion-evidence matrix UI.
- External/operator gates remain unchanged.
