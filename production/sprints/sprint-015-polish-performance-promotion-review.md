# Sprint 015 - Polish, Performance, And Promotion Review

## Goal

Close the release-quality evidence gap for the Kimi-native research demo and
make an evidence-backed maturity decision. This sprint does not promote Stable;
it records the remaining blockers explicitly.

## Story Status

| ID | Story | Status | Evidence |
|---|---|---|---|
| S015-001 | Performance smoke gates for ingestion, RAG/cache, and concurrent enqueue | done | `tests/performance/test_sprint_015_release_gates.py`, `production/qa/performance-sprint-015.md` |
| S015-002 | Kimi chat adapter retry/rate-limit fallback | done | `src/doge/infrastructure/llm/kimi_client.py`, `tests/unit/infrastructure/test_kimi_client.py` |
| S015-003 | Research Agent accessibility pass | done | `web/src/views/ResearchAgentView.vue`, `web/src/views/ResearchAgentView.spec.ts`, `production/qa/accessibility-sprint-015.md` |
| S015-004 | Core Web Vitals applicability decision | done | `production/qa/accessibility-sprint-015.md` |
| S015-005 | Long-running daemon soak protocol | done | `production/qa/soak-protocol-sprint-015.md` |
| S015-006 | API/CLI/operator docs update | done | `docs/API.md`, `docs/CLI.md`, `docs/GETTING_STARTED.md` |
| S015-007 | Runtime maturity and promotion review | done | `production/releases/promotion-review-sprint-015-2026-06-21.md`, `docs/progress/runtime-maturity.yaml` |
| S015-008 | Remote CI after push | deferred | Requires pushed branch/PR; not run in this local pass. |
| S015-009 | Executed soak session | deferred | Protocol exists; one-hour operator run not executed in this local pass. |

## Acceptance Criteria

- [x] Performance evidence exists for document ingestion throughput, RAG
  latency, concurrent enqueue, and embedding cache behavior.
- [x] Kimi adapter has bounded retry behavior for rate-limit/transient errors
  and keeps no-key fallback safe.
- [x] Research Agent screen has an accessibility pass and regression test for
  status/approval/timeline semantics.
- [x] Core Web Vitals are explicitly scoped not applicable to the local-first
  loopback operator app for this sprint.
- [x] Soak protocol exists for long-running daemon sessions.
- [x] API/CLI/operator docs reflect the current fallback and retry behavior.
- [x] Formal promotion review completed.
- [ ] Remote CI green after push.
- [ ] Executed soak session evidence.

## Local Gate

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/infrastructure/test_kimi_client.py tests/performance/test_sprint_015_release_gates.py -q
```

Result: `11 passed in 2.65s`.

Final local gates:

- `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `833 passed, 5 skipped, 11 warnings in 63.68s`.
- `cd web; npm test` -> `75 passed`; `cd web; npm run build` -> passed.
- `cd packages/doge-sdk-typescript; npm test` -> `3 passed`; `cd packages/doge-sdk-typescript; npm run build` -> passed.

## Verdict

Sprint 015 closes the local release-quality evidence foundation, but it does not
authorize a Stable promotion. Remaining release blockers are remote CI after
push, an executed soak run, browser/manual reconnect evidence, live Kimi smoke,
and citation-quality evaluation.
