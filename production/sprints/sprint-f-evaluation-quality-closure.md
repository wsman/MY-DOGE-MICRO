# Sprint F: Evaluation Quality Closure

> Status: Complete / Local engineering scope closed
> Created: 2026-06-29
> Source: `C:\Users\WSMAN\.claude\plans\my-doge-micro-0-lexical-meteor.md`
> CDD: `design/cdd/sprint-f-evaluation-quality-closure.md`
> QA plan: `production/qa/qa-plan-sprint-f.md`

## Goal

Make retrieval and citation quality measurable through the persisted runtime.
Sprint F creates a deterministic local baseline over the 35-case financial gold
set, records governance status honestly, and prepares a W3-live observation
input bridge without closing analyst/operator gates.

## Maturity Posture

Sprint F is local engineering evidence only.

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## Scope

Must-have:

- Reconcile S017-002 using strict Kimi Coding v1 evidence.
- Preserve S017-003, AUTH-prod, W3-live, and S017-007 as external/operator
  gates unless real completed evidence exists.
- Run all 35 gold-set cases through persisted runtime with a case-aware scripted
  model and seeded local evidence.
- Write dated citation-quality baseline JSON and markdown summary.
- Map local observations into W3-live input shape with explicit non-closure
  posture.
- Update runtime maturity and session state.

Out of scope:

- Real provider adapter implementation before S017-003 approval.
- SDK registry publication before S017-007 approval.
- Production SSO/SIEM/WORM/remote-bind live closure.
- Web page expansion.
- New financial tools unless a measured benchmark failure requires them.
- Production-ready, stable, GA, or ADR-0015 promotion claims.

## Story Table

| ID | Title | Status | Evidence / Blocker |
|----|-------|--------|--------------------|
| SF-001 | Governance status reconciliation | done | S017-002 strict Kimi Coding v1 evidence validates at `production/qa/evidence/live/kimi-live-smoke-2026-06-29.json`; S017-003/S017-007 remain external approval gates. |
| SF-002 | Runtime-backed gold-set benchmark | done | `tests/eval/gold_set_seed.py`, `tests/eval/gold_set_runner.py`, `tests/eval/test_gold_set_runtime.py`; 35 cases run through `PersistedResearchAgentRuntime`. |
| SF-003 | Baseline evidence artifact | done | `production/qa/evidence/eval/citation-quality-baseline-2026-06-29.json` and `.md`. |
| SF-004 | Regression test | done | `tests/eval/test_gold_set_runtime.py` asserts complete observations, non-`None` aggregate metrics, `citation_precision == 1.0`, and no doubled `evd-evd-*` markers. |
| SF-005 | W3-live packaging bridge | done | Baseline JSON includes `w3_live_observation_input` and `w3_live_closure_allowed: false`; CLI supports `--observations-output`. |
| SF-006 | Runtime maturity sync | done | `docs/progress/runtime-maturity.yaml` records local benchmark and open live/operator blockers. |
| SF-007 | Retrieval/citation targeted fixes | done | Preserved explicit tool-result `evidence_id`, stopped empty `lookup_evidence` results from creating fallback chunks, and removed doubled marker formatting; citation precision improved from 0.8636363636363636 to 1.0. |
| SF-008 | Trend history automation | done | `scripts/analyst_trend_history.py append-local-baseline` writes repeatable local trend rows; `citation-quality-trend-history-2026-06-29.jsonl` validates and does not close W3-live. |
| SF-009 | Sprint F QA plan | done | `production/qa/qa-plan-sprint-f.md`. |

## Baseline Snapshot

Generated local baseline:

- JSON: `production/qa/evidence/eval/citation-quality-baseline-2026-06-29.json`
- Summary: `production/qa/evidence/eval/citation-quality-baseline-2026-06-29.md`

Metrics from the first local run:

| Metric | Value |
|--------|-------|
| retrieval_recall | 1.0 |
| retrieval_precision | 1.0 |
| citation_precision | 1.0 |
| claim_evidence_precision | 1.0 |
| support_classification_accuracy | 1.0 |
| numerical_consistency | 1.0 |
| usage_cost_record_coverage | 1.0 |
| avg_cost_usd | 0.0 |
| avg_latency_ms | 7.5 |

SF-007 fixed the measured citation precision gap from the first local baseline:
runtime tool evidence now preserves explicit `evd-*` IDs, empty evidence-result
lists no longer create synthetic fallback citations, and citation injection no
longer emits doubled `evd-evd-*` markers. The tightened regression threshold is
locked in `tests/eval/test_gold_set_runtime.py`.

Trend history output:

- JSONL: `production/qa/evidence/eval/citation-quality-trend-history-2026-06-29.jsonl`
- Validation: `scripts/analyst_trend_history.py validate ... --expected-case-count 35`
- Repeatability: appending the same baseline again returns `changed: false`.

## Verification

| Check | Result |
|-------|--------|
| Runtime gold-set benchmark test | PASS: `py -3 -m pytest tests/eval/test_gold_set_runtime.py -q` -> `2 passed`. |
| Benchmark CLI | PASS: `py -3 scripts/run_citation_quality_benchmark.py --output-dir production\qa\evidence\eval` generated baseline JSON/summary. |
| Citation targeted tests | PASS: `py -3 -m pytest tests/unit/agent/test_tool_execution_service.py tests/unit/agent/test_artifact_citation_assembler.py -q` -> `26 passed`. |
| Trend-history tests | PASS: `py -3 -m pytest tests/unit/qa/test_analyst_trend_history.py tests/unit/qa/test_build_analyst_benchmark_evidence.py tests/unit/qa/test_validate_analyst_benchmark_evidence.py -q` -> `17 passed`. |
| Trend-history CLI | PASS: append produced `changed: true`, repeat append produced `changed: false`, and validate returned `ok: true`. |
| Kimi Coding v1 evidence | PASS: `python3 scripts/validate_kimi_live_smoke_evidence.py --coding-v1 production/qa/evidence/live/kimi-live-smoke-2026-06-29.json`. |

## External Gate Posture

| Gate | Sprint F Disposition |
|------|----------------------|
| S017-003 provider approval | Remains review/external. Product/operator approval and provider/license scope are still required. |
| W3-live analyst benchmark | Remains open. Local baseline output can be mapped to observation input but does not replace real analyst labels, thresholds, live observations, and trend history. |
| AUTH-prod | Remains pending operator action for live IdP/JWKS, production secret store, SIEM/WORM, live remote-bind, and production data-isolation review. |
| S017-007 SDK registry release | Remains review/external. Registry target, package-name ownership, registry consumer smoke, and release-manager approval are still required. |

## Definition of Done

- [x] Local runtime-backed baseline code exists.
- [x] Runtime benchmark test passes.
- [x] Baseline JSON and markdown summary exist.
- [x] W3-live mapping is present and explicitly non-closing.
- [x] Measured citation precision gap is fixed and regression-locked.
- [x] Local trend-history row can be appended repeatably and validates.
- [x] Sprint status, runtime maturity, and session state are synchronized.
- [x] Focused governance validators pass after synchronization.
