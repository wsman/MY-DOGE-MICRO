# Release Quality Promotion Review

Generated: 2026-06-21

## Summary

Sprint 015 adds the first local release-quality evidence package for the
Kimi-native research demo: performance smoke tests, Kimi retry/fallback tests,
Research Agent accessibility semantics, Core Web Vitals applicability decision,
and a daemon soak protocol.

## Evidence Links

- `tests/performance/test_sprint_015_release_gates.py`
- `tests/unit/infrastructure/test_kimi_client.py`
- `web/src/views/ResearchAgentView.spec.ts`
- `production/qa/performance-sprint-015.md`
- `production/qa/accessibility-sprint-015.md`
- `production/qa/soak-protocol-sprint-015.md`
- `production/releases/promotion-review-sprint-015-2026-06-21.md`

## Decision

No Stable promotion is allowed. `docs/progress/runtime-maturity.yaml` remains
the authority and still sets `stable_declaration: forbidden`.

## Next Evidence Needed

1. Remote CI on the pushed branch/PR.
2. Executed one-hour daemon soak.
3. Browser/manual Research Agent reconnect evidence.
4. Live Kimi Vision/File Q&A smoke, if the operator chooses to spend live API
   quota.
5. Citation-quality evaluation with a measured benchmark.
