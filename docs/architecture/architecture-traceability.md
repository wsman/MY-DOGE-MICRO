# Architecture Traceability

> **Manifest Version**: 2026-06-22
> **Reviewer**: Release follow-up documentation governance
> **Scope**: ADR-0001..ADR-0011, 15 module CDDs, module index, `tr-registry.yaml`, runtime maturity registry, and current FastAPI/CLI/daemon/document surfaces
> **Stage note**: `production/stage.txt` is **Release**. Runtime maturity remains gated by `docs/progress/runtime-maturity.yaml` and `production_ready: false`.

---

## 1. Verdict

Architecture traceability is current enough for Release follow-up governance:

- ADR-0001..ADR-0011 are all Accepted.
- The module index now covers 15 modules, including Research Copilot Agent
  Runtime, Document Evidence Pipeline, and SDK And Daemon Client Interfaces.
- FastAPI documentation and CDD coverage reflect the canonical
  `doge.interfaces.api.main` application and 58 product routes.
- Runtime maturity labels remain separate from release stage. Release-stage
  governance does not imply runtime production readiness.

Remaining concerns are follow-up work, not traceability blockers:

- Some legacy interface paths still carry repository-routing debt.
- Live Kimi file/vision smoke evidence remains operator-environment-dependent.
- SDK/daemon packaging and browser reconnect evidence remain maturity blockers.
- Runtime promotion remains forbidden while `production_ready: false`.

## 2. ADR Status Inventory

| ADR | Title | Status | 2026-06-21 assessment |
|---|---|---|---|
| 0001 | Brownfield Clean Architecture Migration | **Accepted** | Foundational layer/port contract remains active. |
| 0002 | Centralized Runtime Configuration | **Accepted** | `get_settings()` remains canonical for project-root/runtime config. |
| 0003 | Storage Repository Contract | **Accepted** | Repository contract governs local SQLite/DuckDB access. |
| 0004 | Data Source Adapter Contract | **Accepted** | TDX adapter promotion complete; follow-up retry consolidation remains non-blocking. |
| 0005 | LLM Client Strategy | **Accepted** | OpenAI-compatible provider strategy remains the LLM boundary. |
| 0006 | MCP Transport Strategy | **Accepted** | `doge_mcp.py` / modular MCP server remains canonical. |
| 0007 | API Surface and CORS | **Accepted** | Loopback-guaranteed posture accepted; non-loopback requires CORS/auth first. |
| 0008 | Vue Web Console Architecture | **Accepted** | Web client architecture remains the presentation contract. |
| 0009 | Cache/Metadata Port Split | **Accepted** | Name cache and metadata source ports are split. |
| 0010 | View-Service Port Injection | **Accepted** | `IMarketViewRepository` port injection remains enforced. |
| 0011 | Agent Runtime Levels | **Accepted** | Level 1/2/3 runtime model is accepted, maturity-gated, and linked to TR-047..054. |

**Net**: 11 Accepted, 0 Proposed.

## 3. Module Traceability Coverage

| # | Module | CDD | Governing ADR(s) | Active TR-IDs |
|---|---|---|---|---|
| 1 | Runtime Configuration | `runtime-configuration.md` | ADR-0002, ADR-0001 | TR-001..TR-004 |
| 2 | Market Data Storage | `market-data-storage.md` | ADR-0003, ADR-0001 | TR-005..TR-008 |
| 3 | TDX/YFinance Data Sources | `data-sources.md` | ADR-0004, ADR-0001 | TR-009..TR-012 |
| 4 | Macro Strategy Engine | `macro-strategy-engine.md` | ADR-0005, ADR-0004 | TR-013..TR-016 |
| 5 | Micro Momentum Scanner | `micro-momentum-scanner.md` | ADR-0001 | TR-017..TR-019 |
| 6 | Market Reporting | `market-reporting.md` | ADR-0001, ADR-0002 | TR-043, TR-044 |
| 7 | Research Insight Knowledge Base | `research-insight-knowledge-base.md` | ADR-0003, ADR-0001 | TR-022..TR-024, TR-045, TR-046 |
| 8 | MCP Server | `mcp-server.md` | ADR-0006, ADR-0003 | TR-025..TR-028 |
| 9 | FastAPI Service | `fastapi-service.md` | ADR-0007, ADR-0011 | TR-029..TR-032, TR-049, TR-051 |
| 10 | PyQt Desktop Dashboard | `pyqt-desktop-dashboard.md` | ADR-0001 | TR-033, TR-034 |
| 11 | Vue Web Console | `vue-web-console.md` | ADR-0008, ADR-0007, ADR-0011 | TR-035..TR-037, TR-050 |
| 12 | Clean Architecture Migration | `clean-architecture-migration.md` | ADR-0001, ADR-0009, ADR-0010 | TR-038..TR-042 |
| 13 | Research Copilot Agent Runtime | `research-copilot-agent-runtime.md` | ADR-0011, ADR-0001, ADR-0002, ADR-0007 | TR-047..TR-050, TR-054 |
| 14 | Document Evidence Pipeline | `document-evidence-pipeline.md` | ADR-0011, ADR-0001, ADR-0003, ADR-0005 | TR-051..TR-054 |
| 15 | SDK And Daemon Client Interfaces | `sdk-daemon-client-interfaces.md` | ADR-0011, ADR-0007, ADR-0008 | TR-049, TR-050, TR-054 |

`TR-020` and `TR-021` are retained for ID permanence but superseded by
`TR-043` and `TR-044`.

**Total registered TRs**: 54 total IDs, 52 active, 2 superseded.

## 4. Current Controls And Evidence

- **API route coverage**: `docs/API.md` enumerates 58 product routes and
  `tests/contract/test_api_doc_route_coverage.py` asserts docs-vs-live parity.
- **CLI entrypoint**: `docs/CLI.md` promotes `doge ...`; legacy `python
  src/cli.py ...` remains a compatibility shim.
- **Runtime maturity**: `docs/progress/runtime-maturity.yaml` is the authority
  for Level 1/2/3 labels and keeps `production_ready: false`.
- **Document evidence**: document upload, page/chunk/evidence, Kimi file/vision
  boundaries, and parser limits are covered by Module #14 and TR-051..053.
- **SDK/daemon clients**: Python/TypeScript SDK and `/v1/*` daemon routes are
  covered by Module #15 and TR-049/TR-050.
- **Governance assets**: `memory_bank/` is the active T0-T3 governance entry
  point; adapter boundaries are documented under `adapters/`.

## 5. Follow-Up Concerns

| Concern | Status | Owner path |
|---|---|---|
| Runtime maturity promotion | Blocked while `production_ready: false` | `docs/progress/runtime-maturity.yaml`, TR-054 |
| Live Kimi File/Vision smoke | Environment-dependent | Module #14 / QA evidence |
| Browser/manual SSE reconnect evidence | Pending | Module #15 / sprint QA |
| Repository-routing debt in legacy API surfaces | Known migration debt | Module #12 / Module #9 |
| SDK packaging/distribution hardening | Pending | Module #15 |

*Reviewed 2026-06-21 against the local Release follow-up working tree.*
