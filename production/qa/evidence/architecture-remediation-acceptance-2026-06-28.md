# Architecture Remediation Acceptance Report

**Plan**: `C:\Users\WSMAN\.claude\plans\my-doge-micro-hidden-tide.md`
**Repository**: `D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO`
**Review Date**: 2026-06-28
**Baseline HEAD**: `65f6efa4b492c7f3e5fc7d81e5ebd72942925ec1`
**Verdict**: `GO (local architecture scope clean; full pytest has 3 known non-scope failures)`

---

## 1. Summary

The architecture remediation plan targeted three local structural debts:

1. RuntimeKernel god-object decomposition
2. GatewayContainer monolithic decomposition
3. Scope-first runtime call + streaming semantics contract hardening

All three targets were met. The full Python test suite passes with 1683 tests; 3 failures remain and are confirmed to be outside the scope of this architecture remediation (environment timeout, dependency dtype drift, and pre-existing plan-closure handoff drift).

---

## 2. Test Results

| Test Suite | Result |
|---|---|
| Full pytest (`python -m pytest tests/ -q`) | **1683 passed, 8 skipped, 3 failed** |
| SDK contract check | **passed (12 surfaces)** |
| Architecture tests (`tests/unit/architecture/`) | **73 passed** |
| Agent tests (`tests/unit/agent/`) | **39 passed** |
| Run stream handler tests | **8 passed** |
| Run scope resolver tests | **4 passed** |
| Gateway decomposition tests | **3 passed** |
| Scope-first runtime call tests | **3 passed** |
| Streaming semantics tests | **9 passed** |

### Remaining 3 Failures (Non-Blocking, Outside Remediation Scope)

| Test | Failure Cause | Remediation-Related? |
|---|---|---|
| `tests/test_transport.py::TestStdioTransport::test_stdio_initialize` | MCP server subprocess startup timeout | No — environmental |
| `tests/test_yfinance_adapter.py::test_download_kline_normalizes_columns_and_dtypes` | `df["date"].dtype` now returns `StringDtype` instead of `object` due to pandas/yfinance version drift | No — dependency drift |
| `tests/unit/qa/test_validate_alpha_pre_commit_readiness.py::test_alpha_pre_commit_readiness_cli_fast` | Plan closure handoff SHA256 mismatch from pre-existing template drift | No — pre-existing workspace drift |

---

## 3. Docs Validation

| Check | Result |
|---|---|
| `python scripts/validate_docs_links.py` | **validated 56 markdown files** |
| `python scripts/generate_docs_status.py --check` | **up to date: docs/quality/status.md** |
| `python scripts/validate_no_stale_counts.py` | **docs stale-count validation passed** |
| `python scripts/validate_plan_closure_gate.py --allow-open` | **5 open / 1 passed / 0 failed** |
| `python scripts/validate_plan_closure_gate.py` (strict) | **5 open / 1 passed / 0 failed** — expected failure until external evidence |
| `git diff --check` | Only CRLF/LF normalization warnings; no whitespace errors |

---

## 4. Architecture Metrics

| Metric | Baseline | Target | Actual | Status |
|---|---|---|---|---|
| `RuntimeKernel` line count | 692 | ≤ 350 | **186** | ✅ |
| `GatewayContainer` line count | 374 | ≤ 150 | **95** | ✅ |
| Production unscoped runtime calls | 5 known | 0 | **0** | ✅ |
| `RuntimeKernel` imports `doge.platform.runtime` | — | no | **no** | ✅ |
| `doge.application.composition` imports outside allowlist | — | no | **no** | ✅ |

### New / Decomposed Modules

**Runtime collaborators** (`src/doge/application/agent/`):
- `transition_recorder.py` — transactional state recording
- `approval_coordinator.py` — approval resolution
- `artifact_finalizer.py` — artifact construction and metrics
- `run_stepper.py` — single model/tool round execution
- `run_lifecycle_service.py` — create/execute/queue/cancel/failure lifecycle

**Scope resolver**:
- `src/doge/core/ports/run_scope_resolver.py` — port
- `src/doge/infrastructure/database/run_scope_resolver.py` — SQLite implementation

**Gateway factories** (`src/doge/bootstrap/gateway_factories/`):
- `__init__.py`
- `secrets.py`
- `llm.py`
- `repositories.py`
- `market.py`
- `documents.py`
- `use_cases.py`
- `tools.py`

**Streaming documentation and tests**:
- `docs/architecture/adr-0025-streaming-semantics.md`
- `tests/unit/interfaces/api/test_run_stream_handler.py`
- `tests/unit/architecture/test_streaming_semantics.py`

**Architecture guard tests**:
- `tests/unit/architecture/test_scope_first_runtime_calls.py`
- `tests/unit/architecture/test_gateway_decomposition.py`

---

## 5. Maturity and External Gate Verification

| Item | Status | Verified |
|---|---|---|
| `production_ready` | `false` | ✅ unchanged |
| `stable_declaration` | `forbidden` | ✅ unchanged |
| Level 3 SDK/platform | `experimental` | ✅ unchanged |
| S017-002 (Live Kimi smoke) | `open` | ✅ not closed |
| S017-003 (Financial provider approval) | `open` | ✅ not closed |
| W3-live (Analyst benchmark) | `open` | ✅ not closed |
| AUTH-prod (Enterprise production validation) | `open` | ✅ not closed |
| S017-007 (SDK release approval) | `open` | ✅ not closed |
| S017-006 (Screen reader pass) | `passed` | ✅ retained |

---

## 6. Git Status Authority

This workspace may be inspected by both Windows Git and WSL Git. Because the working tree lives on the Windows filesystem, WSL Git can report large line-ending-only dirty states (`i/lf w/crlf`) even when Windows Git reports a clean tree.

For this report, **Windows Git is the commit-readiness authority**. The staged file list below was generated from Windows Git and contains only content changes from this remediation. WSL Git's broad `M` output should be treated as CRLF/LF normalization noise unless confirmed otherwise with `git diff --ignore-cr-at-eol`.

---

## 7. Staged File List (47 Items)

_Note: count increased from 46 to 47 because this acceptance report itself is part of the staged set._

### Runtime split (modified)
- `src/doge/application/agent/outbox_publisher.py`
- `src/doge/application/agent/runtime_kernel.py`
- `src/doge/application/agent/worker.py`
- `src/doge/bootstrap/runtime.py`
- `src/doge/core/ports/runtime_services.py`
- `src/doge/infrastructure/agent/inmemory_runtime.py`
- `src/doge/infrastructure/agent/persisted_runtime.py`
- `src/doge/interfaces/api/deps.py`
- `src/doge/interfaces/api/factories.py`
- `src/doge/interfaces/cli/commands/session_embedded.py`
- `tests/cli/test_cli_session.py`
- `tests/unit/agent/test_runtime_hydration.py`
- `tests/unit/agent/test_runtime_kernel.py`
- `tests/unit/agent/test_runtime_transaction.py`
- `tests/unit/agent/test_safe_error_redaction.py`
- `tests/unit/agent/test_worker.py`
- `tests/unit/architecture/test_runtime_kernel_split.py`
- `tests/unit/architecture/test_runtime_tenant_isolation.py`

### Runtime split (new)
- `src/doge/application/agent/approval_coordinator.py`
- `src/doge/application/agent/artifact_finalizer.py`
- `src/doge/application/agent/run_lifecycle_service.py`
- `src/doge/application/agent/run_stepper.py`
- `src/doge/application/agent/runtime_args.py`
- `src/doge/application/agent/transition_recorder.py`
- `tests/unit/agent/test_approval_coordinator.py`
- `tests/unit/agent/test_artifact_finalizer.py`
- `tests/unit/agent/test_run_lifecycle_service.py`
- `tests/unit/agent/test_run_stepper.py`
- `tests/unit/agent/test_runtime_kernel_facade.py`
- `tests/unit/agent/test_transition_recorder.py`

### Gateway factories (modified)
- `src/doge/bootstrap/gateway.py`
- `tests/unit/core/services/test_view_services_port_injection.py`

### Gateway factories (new)
- `src/doge/bootstrap/gateway_factories/`
- `tests/unit/architecture/test_gateway_decomposition.py`

### Scope resolver (modified)
- `src/doge/core/ports/__init__.py`

### Scope resolver (new)
- `src/doge/core/ports/run_scope_resolver.py`
- `src/doge/infrastructure/database/run_scope_resolver.py`
- `tests/unit/infrastructure/test_run_scope_resolver.py`

### Scope-first runtime calls (modified)
- `src/doge/interfaces/api/routers/agent.py`

### Scope-first runtime calls (new)
- `tests/unit/architecture/test_scope_first_runtime_calls.py`

### Streaming semantics (modified)
- `src/doge/core/ports/agent_runtime.py`
- `src/doge/infrastructure/agent/persisted_runtime.py`
- `src/doge/interfaces/api/routers/v1/run_stream.py`

### Streaming semantics (new)
- `docs/architecture/adr-0025-streaming-semantics.md`
- `tests/unit/interfaces/api/test_run_stream_handler.py`
- `tests/unit/architecture/test_streaming_semantics.py`

### Integration test update
- `tests/integration/test_multimodal_chat.py`

### Acceptance report (new)
- `production/qa/evidence/architecture-remediation-acceptance-2026-06-28.md`

---

## 8. Risk Assessment

| Risk | Level | Mitigation |
|---|---|---|
| Public API breakage | Low | `RuntimeKernel` and `GatewayContainer` public methods preserved; all contract tests pass. |
| Behavior regression | Low | 1683 existing tests pass; new collaborator tests cover extracted logic. |
| Scope-first contract drift | Low | `test_scope_first_runtime_calls.py` guards against new unscoped production calls. |
| Container decomposition drift | Low | `test_gateway_decomposition.py` guards against re-inlining factories. |
| External gate premature closure | None | No external gates were closed or modified. |

---

## 9. Recommended Next Steps

1. **Commit authorization pending**: Do not commit without explicit user instruction. Before committing, verify `git status --short` from Windows Git contains only the 47 items listed above (including this report).
2. **Optional pre-commit**: Run `python -m pytest tests/unit/architecture/ tests/unit/agent/ tests/unit/core/services/test_view_services_port_injection.py tests/integration/test_multimodal_chat.py -q` as a focused smoke check.
3. **Track non-blocking failures separately**: The 3 remaining failures (MCP stdio timeout, yfinance dtype drift, plan closure SHA256 drift) should be triaged in follow-up tasks outside this architecture remediation.
4. **External gates still require operator action**: S017-002, S017-003, W3-live, AUTH-prod, S017-007 remain open and cannot be closed autonomously.

---

## 10. Approval Signature

- **Plan**: `my-doge-micro-hidden-tide.md`
- **Verdict**: `GO (local architecture scope clean; full pytest has 3 known non-scope failures)`
- **Production posture**: unchanged (`production_ready: false`, `stable_declaration: forbidden`, Level 3 `experimental`)
- **External gates**: 5 open / 1 passed
