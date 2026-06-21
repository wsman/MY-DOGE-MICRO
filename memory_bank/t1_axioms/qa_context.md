# QA Context

## Test Baseline

- Test setup source: `tests/`, `web/src/**/*.spec.ts`, `packages/doge-sdk-typescript/src/__tests__/`, `tests/contract/`, `tests/integration/`, `tests/performance/`
- CI workflow source: `.github/workflows/ci.yml`
- Current status: current for local Release follow-up; remote CI evidence exists for prior runs and S009-S015 PR evidence, but post-push verification remains a normal follow-up.

## Current Verification Summary

| Area | Latest recorded result | Evidence |
|------|------------------------|----------|
| Python full suite | 833 passed, 5 skipped, 11 warnings | `production/session-state/active.md`, `docs/progress/runtime-maturity.yaml` |
| Web full suite | 75 passed, build passed | `production/session-state/active.md` |
| TypeScript SDK | 3 passed, build passed | `production/session-state/active.md` |
| Sprint 015 targeted gates | performance, Kimi retry, web a11y targeted tests passed | `production/qa/performance-sprint-015.md`, `production/qa/accessibility-sprint-015.md` |
| Remote CI | GitHub Actions run evidence recorded | `docs/progress/runtime-maturity.yaml` |

## Blocking QA Rules

- Contract/API/governance gates are strict.
- Network-dependent tests require isolation, fixtures, or explicit integration handling.
- Stable runtime claims are blocked by `docs/progress/runtime-maturity.yaml`.
- Story completion requires acceptance evidence appropriate to story type.

## Open Evidence Gaps

- Live Kimi file/vision smoke remains operator-environment-dependent.
- Citation-quality evaluation remains open.
- Browser/manual SSE reconnect evidence remains open.
- RAG retrieval quality benchmark remains open.
- Executed one-hour daemon soak evidence remains open.
- Screen-reader manual pass remains deferred.
