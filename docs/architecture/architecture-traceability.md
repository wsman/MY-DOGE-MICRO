# Architecture Traceability & Wave 4 Review

> **Manifest Version**: 2026-06-12
> **Reviewer**: Wave 4 architecture-review follow-up
> **Scope**: ADR-0001..ADR-0010, 12 module CDDs, module index, `tr-registry.yaml`, and current MCP entrypoint state
> **Stage note**: gate verdict remains **CONCERNS**; `production/stage.txt` stays `Implementation`.

---

## 1. Verdict

The architecture is coherent enough to close the Wave 4 cleanup set, with
residual concerns explicitly carried forward. ADR-0009 and ADR-0010 are now
**Accepted** because their decisions are realized and verified:

- ADR-0009: `ITickerNameCache` and `ITickerMetadataSource` are distinct ports;
  the real yfinance metadata adapter remains follow-on implementation work.
- ADR-0010: the four view-backed services depend on `IMarketViewRepository`;
  `DuckDBMarketViewRepository` and the composition root own infrastructure
  wiring.
- MCP Batch-6 is complete: the legacy `mcp_server.py` monolith is deleted,
  `doge_mcp.py` is the canonical repo-root entrypoint, and the root
  `sys.path` compatibility shim is removed.

Remaining concerns do not block this cleanup but do block a clean Verification
stage transition unless accepted as risk:

- ADR-0004 remains Proposed because the TDX adapter migration is still open.
- ADR-0007 remains Proposed because CORS hardening remains open even though the
  error envelope has shipped.
- FastAPI routers still have direct DB access migration work.
- The DuckDB RSRS view sign-convention test remains xfail-pinned.

---

## 2. ADR Status Inventory

| ADR | Title | Status | Wave 4 assessment |
|---|---|---|---|
| 0001 | Brownfield Clean Architecture Migration | **Accepted** | Foundational migration contract. |
| 0002 | Centralized Runtime Configuration | **Accepted** | Settings singleton/env defaults implemented and tested. |
| 0003 | Storage Repository Contract | **Accepted** | StorageWriteError and retention gates met. |
| 0004 | Data Source Adapter Contract | Proposed | TDX adapter still gated on follow-on migration. |
| 0005 | LLM Client Strategy | **Accepted** | DeepSeek/OpenAI-compatible strategy and env-key handling accepted. |
| 0006 | MCP Transport Strategy | **Accepted** | Transport strategy retained; canonical entrypoint is now `doge_mcp.py`. |
| 0007 | API Surface and CORS | Proposed | Error envelope shipped; CORS hardening still open. |
| 0008 | Vue Web Console Architecture | **Accepted** | Build/test evidence remains green. |
| 0009 | Cache/Metadata Port Split | **Accepted** | Port split realized; yfinance metadata adapter remains follow-on work. |
| 0010 | View-Service Port Injection | **Accepted** | Port injection and composition-root wiring implemented and tested. |

**Net**: 8 Accepted, 2 Proposed.

---

## 3. Module Traceability Coverage

| # | Module | CDD | Governing ADR(s) | Active TR-IDs |
|---|---|---|---|---|
| 1 | Runtime Configuration | `runtime-configuration.md` | ADR-0002, ADR-0001 | TR-001..TR-004 |
| 2 | Market Data Storage | `market-data-storage.md` | ADR-0003, ADR-0001 | TR-005..TR-008 |
| 3 | TDX/YFinance Data Sources | `data-sources.md` | ADR-0004, ADR-0001 | TR-009..TR-012 |
| 4 | Macro Strategy Engine | `macro-strategy-engine.md` | ADR-0005, ADR-0004 | TR-013..TR-016 |
| 5 | Micro Momentum Scanner | `micro-momentum-scanner.md` | ADR-0001 | TR-017..TR-019 |
| 6 | Market Reporting | `market-reporting.md` | ADR-0001, ADR-0002 | TR-043, TR-044 |
| 7 | Research Insight Knowledge Base | `research-insight-knowledge-base.md` | ADR-0003, ADR-0001 | TR-022..TR-024 |
| 8 | MCP Server | `mcp-server.md` | ADR-0006, ADR-0003 | TR-025..TR-028 |
| 9 | FastAPI Service | `fastapi-service.md` | ADR-0007 | TR-029..TR-032 |
| 10 | PyQt Desktop Dashboard | `pyqt-desktop-dashboard.md` | ADR-0001 | TR-033, TR-034 |
| 11 | Vue Web Console | `vue-web-console.md` | ADR-0008, ADR-0007 | TR-035..TR-037 |
| 12 | Clean Architecture Migration | `clean-architecture-migration.md` | ADR-0001, ADR-0009, ADR-0010 | TR-038..TR-042 |

`TR-020` and `TR-021` are retained for ID permanence but are superseded by
`TR-043` and `TR-044`. The former "AI Industry Analysis" Module #6 placeholder
is no longer active; LLM industry-chain analysis is documented under Module #5.

**Total registered TRs**: 44 total IDs, 42 active, 2 superseded.

---

## 4. Current Controls And Evidence

- **MCP entrypoint**: `.mcp.json` and start scripts launch the modular path;
  `doge_mcp.py` imports `doge.interfaces.mcp.server` directly and contains no
  `sys.path` fallback.
- **Layer gate**: `tests/unit/layer_gates/test_no_sys_path_shims_under_src.py`
  asserts no `sys.path.insert/append` under `src/**` and no shim in
  `doge_mcp.py`.
- **Governance gate**: `tests/unit/governance/test_adr_lifecycle_status.py`
  pins ADR-0009 and ADR-0010 as Accepted; ADR-0004 and ADR-0007 remain Proposed
  with promotion-gate callouts.
- **MCP regression**: regular MCP tests now target the modular server. The old
  modular-vs-legacy parity test is retired because the legacy monolith is gone.
- **Market Reporting traceability**: `tests/test_market_reporting.py` verifies
  Module #6 behavior with fake DuckDB connections and no network/live DB.

---

## 5. Follow-Up Concerns

| Concern | Status | Owner path |
|---|---|---|
| TDX adapter still raises `NotImplementedError` | ADR-0004 remains Proposed | Data Sources follow-on story |
| CORS explicit allowlist is not hardened | ADR-0007 remains Proposed | FastAPI hardening story |
| FastAPI routers still include direct DB access | Known migration debt | Clean Architecture Migration / Module #9 |
| DuckDB RSRS sign convention remains xfail-pinned | Known analytical consistency risk | Market Data Storage / RSRS follow-up |
| PyQt smoke may print Windows DLL/import noise while pytest returns 0 | Environment-specific residual | Desktop portability follow-up |

*Reviewed 2026-06-12 against branch `cdd-adoption-2026-06-11`.*
