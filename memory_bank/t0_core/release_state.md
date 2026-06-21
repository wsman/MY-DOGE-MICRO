# Release State

## Current Release

- Stage: Release
- Latest tagged release: v0.2.1
- Release evidence:
  - `production/releases/release-checklist-v0.2.1-2026-06-14.md`
  - `production/releases/launch-checklist-v0.2.1-2026-06-14.md`
  - `production/releases/release-report-v0.2.1-2026-06-14.md`
  - `production/releases/promotion-review-sprint-015-2026-06-21.md`
- Latest promotion posture: no Stable promotion authorized.

## Release Guardrails

- Local-first single-operator release posture remains accepted.
- Runtime maturity is governed separately from repository Release stage.
- Stable / production-ready language is forbidden while `docs/progress/runtime-maturity.yaml` has `production_ready: false`.
- Non-loopback API exposure requires auth and CORS hardening before use.

## Hotfix State

- No active hotfix recorded in `memory_bank/t3_archive/release_evidence/`.
- Emergency fixes should use `/hotfix` and update this file plus the release evidence archive.
