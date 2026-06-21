# Current Roadmap

> T2 memory mirror initialized from Release follow-up governance evidence on
> 2026-06-21. Future `/cdd-status` runs may regenerate this file from workflow
> and sprint state.

## Current Step

- Step: Release follow-up runtime and evidence hardening.
- Current stage: Release.
- Current sprint evidence: S015 release-quality polish and promotion review.
- Status: active follow-up; Stable runtime promotion is blocked.

## Required Artifacts

- `docs/progress/runtime-maturity.yaml`
- `docs/progress/runtime-stability-followup-plan.md`
- `docs/progress/release-quality-promotion-review.md`
- `docs/architecture/architecture-traceability.md`
- `docs/architecture/tr-registry.yaml`
- `production/sprint-status.yaml`
- `production/qa/qa-plan-sprint-015.md`
- `production/qa/performance-sprint-015.md`
- `production/qa/accessibility-sprint-015.md`
- `production/qa/soak-protocol-sprint-015.md`
- `production/releases/promotion-review-sprint-015-2026-06-21.md`

## Next Steps

1. Keep Stable / production-ready claims blocked until `runtime-maturity.yaml` allows promotion.
2. Close or explicitly defer live Kimi smoke, citation-quality evaluation, browser/manual SSE reconnect, RAG quality benchmark, real fundamentals/connectors, legacy TDX helper deletion, and executed soak evidence.
3. Run targeted `/architecture-review` after any runtime-maturity or contract change.
4. Run `/cdd-status` to regenerate `production/project-roadmap.md` and this T2 mirror when roadmap state changes.
5. Maintain T3 evidence indexes as QA, release, gate, and review artifacts are approved.

## Recent Verification Baseline

- Python full suite: 833 passed, 5 skipped, 11 warnings.
- Web tests/build: 75 passed; build passed.
- TypeScript SDK tests/build: 3 passed; build passed.
- Sprint 015 targeted gates: performance, Kimi retry, and Research Agent a11y targeted tests passed.
