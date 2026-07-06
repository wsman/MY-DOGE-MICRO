# Sprint 032 - Python SDK Typed Result Models

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-06

## Summary

Sprint 032 implements the Python SDK Typed Result Models plan from
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`.

The sprint adds dict-compatible typed result models for Python SDK run REST
responses. Existing dict usage remains valid, while Python integrators can also
use typed convenience properties on run results.

## Scope

- Add ADR-0041 and this sprint CDD/governance trail.
- Add `packages/doge-sdk-python/doge_sdk/run_models.py`.
- Add dict-subclass `Run`, `RunListItem`, `Artifact`, `Approval`, and
  `RunEvent` models.
- Wrap sync and async Python SDK runs resource returns:
  - `get`, `approve`, `resume`, `cancel` -> `Run`.
  - `list` -> `list[RunListItem]`.
  - `events` -> `list[RunEvent]`.
- Preserve `DogeEvent` streaming dataclass behavior.
- Re-export the new model classes from `doge_sdk`.
- Update the Python SDK README to document additive typed access.
- Extend Python SDK contract tests and add focused run-model unit tests.
- Update active session state and local evidence.

## Explicitly Out of Scope

- `/v1` API surface changes.
- OpenAPI or TypeScript SDK changes.
- SDK method-surface bump.
- Python SDK dependency changes.
- Dataclass or Pydantic replacement for run REST results.
- Documents/platform typed models.
- Citation or MemoExport models.
- SDK happy-path research helper.
- Production readiness declaration.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the UX/product-acceptance and SDK-governance sprint precedent where no new
story-status tracking is introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-032-python-sdk-typed-models-manifest.md`.

Verification results:

- Python SDK focused contract/model suite passed: 32 tests.
- Python SDK compile check passed for run resources, run models, package
  exports, and focused tests.
- SDK contract passed: 15 surfaces, 15 entity parity checks.
- Docs authority, docs links, docs maturity claims, import boundaries,
  ADR/CDD maturity honesty, plan closure, and whitespace checks passed.
- Plan closure posture remains controlled open: 4 open / 2 passed.
