# Sprint 020 — Strategic-Review Reconciliation Manifest (D0 Decision Gate)

> Sprint: 020 (Strategic-Review Reconciliation & Genuinely-Remaining Closure)
> Date: 2026-07-03 · Baseline HEAD: `e1e7f24` · Branch: `main`
> Plan: `C:\Users\WSMAN\.claude\plans\my-doge-micro-glistening-dawn.md`
> Status: **Approved 2026-07-03** — this manifest gates Slices 1–5.

## Purpose

A pasted strategic architecture review proposed a broad structural refactor of
MY-DOGE-MICRO. AST/file-verified exploration against the current codebase confirms
the large majority of it **already shipped** across Sprints E / G / H / I / 018 /
019 and the 2026-06-30 runtime consolidation. This manifest records, claim by
claim, the current truth with `file:line` evidence so the stale review cannot be
re-litigated, and it fixes the small closed set of genuine remainders that
Sprint 020 will close. It is a **D0 decision gate**: every Slice 1–5 change must
map to a row in the [Genuine-remainder register](#genuine-remainder-register);
anything not listed is out of scope.

## Verdict taxonomy

- **DONE** — the claim's target state is verifiable in current code (cite `file:line`). No action.
- **PARTIAL** — the claim is partly met with a documented residual that is either by-design, governed by an open ADR, or slated as a surgical slice in this sprint.
- **STALE** — the claim describes a problem that no longer exists (the proposed target state already shipped). No action; record evidence.
- **NOT STARTED** — the claim's target state is genuinely absent and is **not** being closed this sprint (called out with the reason — usually "requires ADR" or "wire/contract change").

---

## Claim table

### Domain A — Runtime / Gateway / CLI maturity (9 claims)

| # | Claim (paraphrased) | Verdict | Current-code evidence (`file:line`) | By-design / covered-elsewhere note | Sprint-020 action |
|---|---|---|---|---|---|
| 1 | Runtime is in-memory (`self._runs: dict`); restart loses state | **STALE** | `src/doge/infrastructure/agent/persisted_runtime.py:23` (`PersistedResearchAgentRuntime`); SQLite repos `src/doge/infrastructure/database/agent_repositories.py:95,206,338,384,431` (Session/Run/Event/Artifact/Approval) | — | none |
| 2 | `stream_events` is replay-only; no real-time Event Bus | **PARTIAL** | Real-time bus exists: `src/doge/application/agent/event_bus.py:13`, `worker.py:22`, `outbox_publisher.py:10`; persisted runtime's stream is replay-by-default (`persisted_runtime.py:111-128`); outbox gated by `runtime_outbox_publisher` flag | Deliberate feature-flag for maturity staging | none |
| 3 | Approval is fake (default memo only); loop does not resume | **STALE** | `src/doge/application/agent/approval_coordinator.py:25-61` (→ `QUEUED` + `APPROVAL_RESOLVED`/`RUN_QUEUED`); `worker.py:163-176` (`resolve_approval` → `enqueue_continuation` → `run_to_pause_or_completion`) | — | none |
| 4 | `POST /api/agent/runs` is synchronous; no 202/worker | **PARTIAL** | v1 `POST /v1/sessions/{id}/turns` returns `202` (`src/doge/interfaces/gateway/routers/sessions.py:70-105`); legacy sync `POST /api/runs` still mounted deprecated (`src/doge/interfaces/api_legacy/routers/agent.py:42-51`) | Legacy governed by ADR-0027 sunset (`runtime-maturity.yaml` `removal_not_before`) | none (no `api_legacy` deletion) |
| 5 | SSE has no sequence/resume | **STALE** | `/v1/runs/{id}/stream` reads `Last-Event-ID` → `after_sequence`, emits `"id": str(event.sequence)` (`src/doge/interfaces/gateway/routers/run_stream.py:33-62`); port `src/doge/core/ports/event_subscriber.py:9-12` | — | none |
| 6 | No `AgentSession`; Run carries conversation context | **STALE** | `AgentSession` `src/doge/core/domain/agent_models.py:112-129`; port `src/doge/core/ports/agent_repository.py:17-29`; `SQLiteSessionRepository` `agent_repositories.py:95`; `AgentRun.session_id` back-ref `agent_models.py:137`; routes `gateway/routers/sessions.py` | — | none |
| 7 | CLI is one-shot (`stock/rsrs/breadth/...`); no `doge session` | **STALE** | `doge session` subcommand `src/doge/interfaces/cli/main.py:102-117,207-221`; interactive REPL `src/doge/interfaces/cli/commands/session_interactive.py:26-188` (`/new /resume /attach /portfolio /tools /trace /artifacts /approve /deny /cancel /save /exit`) | — | none |
| 8 | `ScriptedAgentModel` defined inside `research_runtime.py` (pollutes kernel) | **STALE** | Defined `src/doge/infrastructure/agent/scripted_model.py:77`; re-export shim `src/doge/infrastructure/llm/scripted_agent_model.py:7-9`; no `research_runtime.py` exists; injected only via `src/doge/bootstrap/runtime_factories/runtime_kernel.py` | — | none |
| 9 | `doged serve --host 127.0.0.1 --port 8901` exists; loopback enforced | **PARTIAL** | `doged` console script `pyproject.toml:36`; `serve` subparser `src/doge/interfaces/daemon/main.py:20-23` parses only `--port/--reload/--role` (no `--host`); host env-driven `DOGE_BIND_HOST`/`settings.api.bind_host` (`src/doge/interfaces/api/startup_gates.py:44-60`); loopback enforced `_LOOPBACK_HOSTS` + `_validate_api_remote_bind_startup` (`startup_gates.py:10-41`) | Host was env-driven, not CLI | **Slice 2** — add `--host` flag |

### Domain B — Tools / Documents / Model plane (7 claims)

| # | Claim (paraphrased) | Verdict | Current-code evidence (`file:line`) | By-design / covered-elsewhere note | Sprint-020 action |
|---|---|---|---|---|---|
| 10 | Tool Registry is one giant file (`application/agent/tools.py`) | **STALE** | `src/doge/application/agent/tools.py` deleted; clean package `src/doge/application/tools/` — `registry.py:18`, `schemas.py`, `factory.py:12`, `registry_factory.py:15`, `execution_service.py:14`, facades `market.py`/`portfolio.py`/`documents.py`/`validation.py`/`approval.py`; `ToolResult` at `src/doge/core/ports/runtime_services.py:27` | — | none |
| 11 | Tools build services directly from `composition` | **STALE** | `src/doge/application/tools/registry_factory.py:15-66` injects `ServiceFactory` callables; `src/doge/products/market/tools.py:10` imports `ServiceFactory` from `doge.shared.tool_utils`; zero `composition` matches in `application/tools/` | — | none |
| 12 | Document API is a placeholder in-memory `_DOCUMENTS` dict | **STALE** | `src/doge/interfaces/gateway/routers/documents.py:36-73` (multipart+JSON via `FileUploadService`); `src/doge/application/services/file_upload_service.py:48-306`; SQLite `documents` table `src/doge/infrastructure/database/agent_repositories.py:487-549`; no `_DOCUMENTS` dict in `src/` | — | none |
| 13 | Document → Page/Table/Image → Evidence Chunk → Citation pipeline | **DONE** | `src/doge/application/services/page_extraction_service.py:32,80,98`; `src/doge/infrastructure/database/evidence_repository.py:24`; `src/doge/application/services/citation_service.py:11-44` (`CitationRecord` with `document_id`/`page_number`/`chunk_id`/`evidence_id`) | — | none |
| 14 | `ScriptedAgentModel` location (dup of #8) | **STALE** | `src/doge/infrastructure/agent/scripted_model.py:77` | — | none |
| 15 | Model plane all under `infrastructure/llm/` | **PARTIAL** | Kimi `infrastructure/llm/kimi_client.py:86` ✓; DeepSeek `infrastructure/llm/deepseek_client.py:20` ✓; ScriptedModel `infrastructure/agent/scripted_model.py:77` ✗; ModelRouter `application/agent/model_router.py:15` ✗ | By design — bounded contexts (agent/model-routing belong to the agent context), not drift | none |
| 16 | `ToolResult` shape + MCP/Runtime/CLI/HTTP share ONE registry | **PARTIAL** | Shape `src/doge/core/ports/runtime_services.py:27-33` (`{ok,name,data,...}`) ✓; HTTP gateway `gateway/routers/tools.py:19` + Runtime `bootstrap/runtime_factories/tools.py:7` share registry ✓; **MCP `src/doge/interfaces/mcp/server.py:30-37` uses parallel hand-rolled wrappers** ✗ | — | **Slice 1** — MCP → `ToolRegistry` convergence |

### Domain C — SDK / Docs / Tests / Structure (8 claims)

| # | Claim (paraphrased) | Verdict | Current-code evidence (`file:line`) | By-design / covered-elsewhere note | Sprint-020 action |
|---|---|---|---|---|---|
| 17 | API docs drift — `docs/API.md` describes only 26 legacy routes | **PARTIAL** | `docs/API.md:5-14` recentered on 5 v1 families (sessions/runs/documents/tools/platform), 88 routes documented; `docs/architecture/runtime-levels.md` + `module-boundaries.md` exist; standalone `docs/AGENT_API.md`/`RUNTIME_LEVELS.md`/`DEMO_SCENARIOS.md` NOT created; `docs/scenarios/demo-scenarios.md` MISSING | Coverage via expanded `API.md` + `architecture/` rather than standalone splits | **Slice 3** — add `docs/scenarios/demo-scenarios.md` |
| 18 | SDK missing; Web does raw fetch | **STALE** | `packages/doge-sdk-python/doge_sdk/client.py:21-40` + `platform.py:227-235` (`CapabilitiesResource`); `packages/doge-sdk-typescript/src/client.ts:29-47`; `web/src/api/agent.ts:1` consumes TS SDK `dogeClient` | — | none |
| 19 | No Agent contract tests | **STALE** | `tests/contract/test_agent_runtime.py` (3), `test_tool_registry.py` (4), `test_golden_runtime_contract.py` (3, golden v1 HTTP + Python SDK); plus `test_v1_api.py` (21), `test_platform_api.py` (10), `tests/cli/test_cli_session.py` (15) | — | none |
| 20 | Interface layer calls concrete services (no facade adoption) | **DONE** | Ratchet gate `tests/unit/layer_gates/test_new_code_imports.py:76` (`test_interface_layers_use_platform_facades`); 2-entry frozen allowlist (`:68-73`); 5 platform facades + `products/portfolio` shim | Sprint 019 | none |
| 21 | Legacy `src/macro` not isolated; runs parallel with new arch | **STALE** | `src/macro` gone; legacy isolated `src/doge/interfaces/api_legacy/routers/`; `src/doge/interfaces/api/routers/__init__.py` pure shim; `docs/architecture/compatibility-surfaces.md`; guard `tests/unit/architecture/test_shim_behavior_guards.py` (8 AST checks) | — | none |
| 22 | Web hardcodes demo document ids | **STALE** | `web/src/views/ResearchAgentView.vue` has zero hardcoded ids; driven by `useDocumentStore().selectedIds` (`:87,90,115-118`) | — | none |
| 23 | README maturity labels | **PARTIAL** | Maturity declared `README.md:53-64` (L1/L2 Alpha, L3 Experimental, `production_ready: false`) + `:68-71` governance block + `docs/progress/runtime-maturity.yaml:28-32`; **Canonical/Compatibility/Legacy/Demo path table missing from README** (only in `runtime-maturity.yaml:42-77`) | Current labels are stricter than the review's proposed planned/prototype | **Slice 4** — restore compact path table |
| 24 | `runtime-levels.md` / `module-boundaries.md` / `demo-scenarios.md` docs | **PARTIAL** | `docs/architecture/runtime-levels.md` EXISTS; `docs/architecture/module-boundaries.md` EXISTS; `docs/scenarios/demo-scenarios.md` MISSING | — | **Slice 3** — add `demo-scenarios.md` |

### Roll-up

- **24** claims total: **STALE 14** · **DONE 2** · **PARTIAL 8** (of which 4 close in this sprint, 4 are by-design/ADR-gated).
- **Genuine code-bearing remainders:** 4 — MCP convergence (#16), `doged --host` (#9), `demo-scenarios.md` (#17/#24), README path table (#23).
- **Record-only correction:** Python SDK `capabilities` parity (#18) — already shipped and parity-enforced; documented as STALE, no code change.

---

## Genuine-remainder register

The closed set of work Sprint 020 takes on. Each row maps to one or more claim rows above.

| Slice | Scope | Closes claims | Gates touched |
|---|---|---|---|
| 0 | This reconciliation manifest (decision gate) | all | — |
| 1 | MCP server → `ToolRegistry` convergence (6 data tools only; preserve `stock_overview` overview format + `list_views` JSON-list contract; delete `interfaces/mcp/tools/`; add convergence contract test + architecture gate) | #16 | `tests/test_mcp_tools.py`, `tests/contract/test_mcp_*`, `test_tool_registry.py`, `tests/unit/architecture`, `tests/unit/layer_gates`, `scripts/validate_import_boundaries.py` |
| 2 | `doged serve --host` flag (env-inject `DOGE_BIND_HOST` + `reset_settings()`; ADR-0007 gate unchanged) | #9 | `tests/cli/test_doged_cli.py`, `tests/unit/interfaces` |
| 3 | `docs/scenarios/demo-scenarios.md` (3 runtime levels × demo scenarios) | #17, #24 | `scripts/validate_docs_links.py`, `scripts/validate_alpha_maturity_honesty.py` |
| 4 | README Canonical/Compatibility/Legacy/Demo path table (compact; sourced from `runtime-maturity.yaml:42-77`; maturity labels untouched) | #23 | `scripts/validate_alpha_maturity_honesty.py` |
| 5 | Housekeeping: conditionally delete orphaned `tools.cpython-312.pyc` (+ dead MCP wrapper `__pycache__` after Slice 1); correct the stale tool-shim note at `production/session-state/active.md:58` (do **not** touch `:55`); record SDK-capabilities STALE verdict | #18 | none (optional test) |

Recommended sequence: **0 → 5 → 2 → 3 → 4 → 1** (land the MCP convergence last on a clean tree).

---

## Posture Invariants (unchanged)

- `production_ready: false`; `stable_declaration: forbidden`; `level_3_sdk_platform: experimental`.
- HTTP wire contract, CLI exit codes, OpenAPI schema set — unchanged.
- No physical implementation moves into `platform/*` (ADR-0022 story-gated; facades are re-export shims only).
- No `api_legacy/` deletion (ADR-0027 shim-sunset policy governs sunset).
- No full-registry auto-discovery into MCP (would widen the MCP wire surface → ADR-required).
- No SDK `capabilities` addition (parity already shipped and enforced).
- External gates S017-003 / W3-live / AUTH-prod / S017-007 remain open / operator-owned. This sprint closes no external gate and fabricates no live evidence.

---

## Appendix — re-derivation commands

The `file:line` citations above were derived from reads of the current working tree at `e1e7f24`. Representative re-derivation commands (Windows Python, repo root):

```bash
# Confirm baseline
git rev-parse HEAD                       # e1e7f24...
git status --short                       # empty at sprint start

# Runtime persistence (claims 1, 3, 6)
e:\LLMs\python312\python.exe -c "import ast,pathlib; t=ast.parse(pathlib.Path('src/doge/infrastructure/agent/persisted_runtime.py').read_text(encoding='utf-8')); print([n.name for n in ast.walk(t) if isinstance(n,ast.ClassDef)])"

# Tool surface (claims 10, 11, 16)
grep -rn "composition" src/doge/application/tools/          # expect 0 matches
grep -rn "from doge.application.tools import" src/doge/     # canonical registry imports
grep -rn "from doge.interfaces.mcp.tools" src/doge/interfaces/mcp/server.py   # the convergence target

# Document persistence (claims 12, 13)
grep -rn "_DOCUMENTS" src/doge/                              # expect 0 matches (only historical docs)
grep -rn "class SQLiteDocumentRepository" src/doge/infrastructure/database/agent_repositories.py

# Facade ratchet (claim 20)
grep -n "INTERFACE_GRANDFATHERED\|test_interface_layers_use_platform_facades" tests/unit/layer_gates/test_new_code_imports.py

# SDK capabilities parity (claim 18)
grep -n "CapabilitiesResource" packages/doge-sdk-python/doge_sdk/platform.py packages/doge-sdk-python/doge_sdk/client.py
grep -n "capabilities" tools/ci/sdk-contract-check.py

# Docs present/absent (claims 17, 23, 24)
ls docs/architecture/runtime-levels.md docs/architecture/module-boundaries.md docs/scenarios/demo-scenarios.md
grep -n "compatibility_surfaces\|production_ready" docs/progress/runtime-maturity.yaml
```

Manifest citations will be re-baselined at sprint close after Slice 1 shifts line numbers.
