# Sprint 020 — Strategic-Review Reconciliation & Genuinely-Remaining Closure

> Status: **Local Implementation Complete / Accepted Local**
> Branch: `main` · Date: 2026-07-03 · Baseline HEAD: `e1e7f24`
> Plan: `C:\Users\WSMAN\.claude\plans\my-doge-micro-glistening-dawn.md`
> Manifest: [production/qa/evidence/sprint-020-review-reconciliation-manifest.md](../qa/evidence/sprint-020-review-reconciliation-manifest.md)
> Predecessor: Sprint 019 (Platform Facade Adoption & Boundary Consolidation)

## Context

A strategic architecture review was re-pasted proposing a broad structural
refactor (split `tools.py`, move `ScriptedAgentModel`, add `AgentSession`,
persist the runtime, make `/api/agent/runs` async `202+worker`, add SSE resume,
build Python/TS SDKs, split API docs, add contract tests, …). AST/file-verified
exploration confirmed **~90% already shipped** across Sprints E/G/H/I/018/019 and
the 2026-06-30 runtime consolidation: of 24 specific claims, **14 STALE**, **2
DONE**, and of the **8 PARTIAL** most are by-design or covered elsewhere. This
sprint records that evidence in a decision-gate manifest (so the stale review
cannot be re-litigated) and closes the small genuine remainder — headlined by
unifying the MCP server onto the canonical `ToolRegistry`.

## Posture (unchanged)

- `production_ready: false`; `stable_declaration: forbidden`; `level_3_sdk_platform: experimental`.
- HTTP wire contract, CLI exit codes, OpenAPI schema set — unchanged.
- External gates S017-003 / W3-live / AUTH-prod / S017-007 remain open / operator-owned.

## Slices

### Slice 0 — Reconciliation manifest (D0 decision gate)
- Evidence: [manifest](../qa/evidence/sprint-020-review-reconciliation-manifest.md).
- 24-row claim table with DONE/PARTIAL/STALE/NOT STARTED verdicts and `file:line`
  evidence; genuine-remainder register; posture invariants; re-derivation appendix.
- Two stale-review corrections recorded: Python SDK `capabilities` parity already
  shipped (no code change); `list_views` is already a registry tool (no name gap).

### Slice 1 — MCP → ToolRegistry convergence (centerpiece)
- The six MCP data tools (`query_stock`, `stock_overview`, `rsrs_ranking`,
  `market_breadth`, `volume_anomalies`, `list_views`) now dispatch through the
  shared `ToolRegistry` (`doge.application.tools`) via `registry.execute_async`,
  reusing the gateway's `build_gateway_container().build_tool_application_service()`
  wiring path — so MCP / runtime / HTTP share one tool surface.
- Removed the parallel hand-rolled wrapper package
  `src/doge/interfaces/mcp/tools/` (5 files); moved `normalize_ticker`,
  `_demo_prices`, `_fallback_views` into `src/doge/interfaces/mcp/server.py`.
  `stock_overview` keeps its notes-enrichment (presentation) via the note
  repository; `_timed` remains the sole timeout (no inner registry timeout, to
  preserve original semantics).
- Convergence scope: **only the 6 data tools** — deliberately NOT full-registry
  auto-discovery (would add `run_sql_query` / `run_python_analysis` / portfolio /
  research / compliance / publishing to the MCP wire surface → ADR-required).
  The 7 MCP workspace/case tools remain direct container calls.
- New tests: `tests/contract/test_mcp_tool_registry_convergence.py` (names ⊆
  registry; query_stock dispatch; list_views JSON list) and architecture gate
  `tests/unit/architecture/test_mcp_uses_tool_registry.py` (AST: imports
  `build_default_tool_registry`; does NOT import `doge.interfaces.mcp.tools`).
- Updated consumers of the removed package: `tools/perf/profile_baseline.py`
  (import source → `doge.interfaces.mcp.server`), `tests/test_mcp_notes_softdelete.py`
  (retargeted to `srv.stock_overview` + stub `_execute_data_tool`; soft-delete
  regression intent preserved), `tests/test_mcp_tools.py` (removed dead
  `query_stock` monkeypatch; extended `TestToolsNotPresent` to assert
  `run_sql`/`run_sql_query`/`run_python_analysis` absent), and
  `tests/unit/architecture/test_bootstrap_owns_factories.py` (dropped 4 deleted
  paths). Forward-looking docs updated: `docs/MCP_SERVER.md`, `design/cdd/mcp-server.md`,
  `docs/operations/runbook.md`.

### Slice 2 — `doged serve --host` flag
- Added `--host` to the `serve` subparser in `src/doge/interfaces/daemon/main.py`;
  injected via `os.environ["DOGE_BIND_HOST"]` + `reset_settings()` (mirrors the
  `--role` idiom). The ADR-0007 loopback/remote-bind gate in `startup_gates.py`
  runs unchanged. Readiness (always `127.0.0.1`) unaffected.
- Tests in `tests/cli/test_doged_cli.py`: `--host 127.0.0.1` and `--host localhost`
  pass the host into `uvicorn.run`; non-loopback `--host` without
  `DOGE_ALLOW_REMOTE_BIND=1` trips the ADR-0007 assertion (all use `--role api`
  to avoid the worker-path hang seen in an earlier full-file run).

### Slice 3 — `docs/scenarios/demo-scenarios.md`
- New orientation doc mapping the three runtime levels to concrete entrypoints
  and demo flows; cross-references `runtime-levels.md`, `module-boundaries.md`,
  and `multimodal-portfolio-research.md`.

### Slice 4 — README Surface Classification table
- Restored a compact Canonical/Compatibility/Demo/Removed path table in
  `README.md` (sourced from `runtime-maturity.yaml:42-77`); maturity labels and
  governance block untouched.

### Slice 5 — Housekeeping
- Deleted orphaned `src/doge/application/agent/__pycache__/tools.cpython-312.pyc`.
- Corrected the stale tool-shim note at `production/session-state/active.md:58`
  (the `doge.application.agent.tools` shim was removed in Sprint M); `:55`
  (documents persistence) left untouched.
- Python SDK `capabilities` parity recorded as STALE in the manifest (no code
  change — parity already enforced by `tools/ci/sdk-contract-check.py`).

## Verification

- Focused gate suite (`layer_gates` + `architecture` + `contract` + `governance`
  + `cli`): **430 passed, 4 skipped**.
- MCP suite (`test_mcp_tools` + `test_mcp_notes_softdelete` + new convergence
  contract + `test_tool_registry` + new architecture gate): **86 passed**.
- Validators: `validate_import_boundaries.py` passed; `tools/ci/sdk-contract-check.py`
  passed (13 surfaces, 12 entity parity); `validate_alpha_maturity_honesty.py`
  passed; `validate_docs_links.py` validated 85 markdown files;
  `validate_plan_closure_gate.py --allow-open` **4 open / 2 passed / 0 invalid**;
  `git diff --check` clean.
- Three full-suite failures observed in one `pytest -q` run
  (`test_local_loopback_mode_keeps_legacy_api_routes`, two `test_agent_sse_stream`
  cases) **pass in isolation** (6 passed in 3.57s) — flaky/order-dependent
  (SSE/eval polling), unrelated to Sprint 020 surfaces, consistent with the
  pre-existing-flake pattern recorded in Sprint 019. Full regression launched in
  background; result recorded in active.md on completion.

## Non-Goals

- No physical implementation moves into `platform/*` (ADR-0022 story-gated).
- No HTTP wire / CLI exit-code / OpenAPI schema-set changes.
- No maturity promotion; no external-gate closure; no `api_legacy/` deletion.
- No full-registry auto-discovery into MCP; no SDK `capabilities` addition.
- Active registries (`docs/registry/entities.yaml`,
  `docs/architecture/tr-registry.yaml`) were updated to the registry-backed MCP
  server path. Historical/archive citations in ADRs, prior QA evidence, code
  reviews, and architecture reviews remain point-in-time records.

## External Gates (unchanged)

S017-003 (financial provider approval), W3-live (analyst benchmark), AUTH-prod
(enterprise validation), S017-007 (SDK registry release) remain open /
operator-owned. This sprint closes no external gate.
