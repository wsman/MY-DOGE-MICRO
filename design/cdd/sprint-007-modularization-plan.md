# Sprint 007: Clean Architecture Modularization Plan

> **Slug**: `sprint-007-modularization-plan`
> **Category**: Operations / Migration
> **Priority**: MVP
> **Status**: Planned
> **Governing ADRs**: ADR-0001 (layer boundaries), ADR-0010 (port injection), ADR-0009 (port naming), ADR-0004 (TDX adapter), ADR-0007 (loopback guarantee)
> **Last Verified**: 2026-06-14
> **Baseline**: 617 passed, 5 skipped, 0 failed, 0 error

---

## 1. Overview

Sprint 007 completes the brownfield clean-architecture migration for MY-DOGE-MICRO by introducing the missing `application` layer (`src/doge/application/`) between `core/services` (thin query primitives) and `interfaces` (MCP tools, API routers, CLI commands). It migrates the remaining legacy orchestration logic from `src/micro/`, `src/macro/`, `src/ai_analysis/`, `src/api/`, `src/interface/`, and `src/cli.py` into port-backed use cases, re-routes all interface entrypoints through the application layer, and converts legacy modules into thin shims. The sprint is structured as eight stories: a foundation story (S007-001: application package + contracts + composition boundary), three sequential migration stories (S007-003 CLI → S007-002 API → S007-004 ai_analysis), two parallel workflow migrations (S007-005 market scanner + S007-006 macro report), a documentation story (S007-007), and a final layer-gate verification story (S007-008). Legacy file deletion is explicitly deferred to Sprint 008. All stories are gated by BLOCKING test evidence per `standards/testing-standards.md`.

---

## 2. User Promise / JTBD

**Operator's job (developer maintaining the platform):** Add a new analysis feature, wire it to a new MCP tool / API route / CLI command / UI button, and have it behave identically across all surfaces — without copy-pasting SQL, recomputing the project root, or opening a database connection inside an interface module.

**Promise the module must keep:**

- One place owns runtime configuration: `src/doge/config/settings.py`. No module outside that file should recompute `_PROJECT_ROOT` or insert into `sys.path` for its own use.
- Business rules live in `src/doge/core/services/` and depend only on ports (`src/doge/core/ports/`), never on `sqlite3`, `duckdb`, or interface frameworks.
- All database/network access lives in `src/doge/infrastructure/` adapters that *implement* the ports.
- Every interface (MCP / FastAPI / CLI / GUI / Web) reaches the data through the application layer (`src/doge/application/use_cases/`), which orchestrates services — never by importing a database driver or legacy module directly.
- During migration, working workflows stay live while each surface moves to the layered implementation. Legacy modules become thin re-export shims, then are deleted after one release cycle.

---

## 3. Detailed Behavior

### 3.1 Dependency Direction (enforced invariant)

```
interfaces/ ──→ application/use_cases/ ──→ core/services/ ──→ core/ports/ 〈── infrastructure/ 〈── SQLite/DuckDB/TDX/yfinance/openai
```

Layers must not point inward; `core` imports no framework; `infrastructure` implements `core/ports`; `interfaces` depends only on `application` and `core/services`.

### 3.2 New Application Layer (`src/doge/application/`)

The application layer is the missing orchestration tier between thin services and interface entrypoints. It owns:

- **Request/Response DTOs** (`contracts/request.py`, `contracts/response.py`) — pure dataclasses, no external dependencies, frozen for immutability.
- **Use cases** (`use_cases/*.py`) — named workflows that compose services, handle error paths, and return structured DTOs. Each use case is a class with an `execute(request) -> response` method.
- **No direct infrastructure imports** — use cases import only `core.ports`, `core.services`, and `application.contracts`.

### 3.3 Use Case Inventory

| Use Case | File | Responsibility | Ports/Services Used |
|----------|------|---------------|---------------------|
| `ScanMarketUseCase` | `use_cases/scan_market.py` | Orchestrate full-market data refresh: discover tickers, download via `IMarketDataSource`, persist via `IStockRepository`, refresh views | `IStockRepository`, `IMarketDataSource`, `refresh_views` (composition root) |
| `GenerateMacroReportUseCase` | `use_cases/generate_macro_report.py` | Fetch market context, build LLM prompt, generate report via `ILLMClient`, persist via `IReportRepository` | `IMarketViewRepository`, `ILLMClient` (new port), `IReportRepository` |
| `ManageNotesUseCase` | `use_cases/manage_notes.py` | CRUD + archive + search + list operations for stock notes, delegating to `INoteRepository` | `INoteRepository` |
| `QueryTickerUseCase` | `use_cases/query_ticker.py` | Composite ticker query: prices from `IStockRepository`, metadata from `ITickerMetadataSource`, notes from `INoteRepository` | `IStockRepository`, `INoteRepository`, `ITickerMetadataSource` |
| `GenerateMarketOverviewUseCase` | `use_cases/generate_market_overview.py` | Markdown report from services: breadth, RSRS ranking, volume anomalies | `BreadthService`, `RankingService`, `AnomalyService` |
| `GenerateAnomalyReportUseCase` | `use_cases/generate_anomaly_report.py` | Markdown anomaly report: volume anomalies, price gaps, consecutive extremes | `AnomalyService` (extended with `price_gaps()`, `consecutive_extremes()`) |
| `GenerateCatalogUseCase` | `use_cases/generate_catalog.py` | Generate `catalog.json` by scanning SQLite + DuckDB metadata | `ISchemaBrowser`, `ViewService` |
| `PopulateStockNamesUseCase` | `use_cases/populate_stock_names.py` | Batch-fetch stock names from metadata source, store in repository | `ITickerMetadataSource`, `INoteRepository` (or new `INameRepository` port) |

### 3.4 New Port: `ILLMClient`

A new port `doge.core.ports.llm.ILLMClient` abstracts LLM text generation (DeepSeek, OpenAI, etc.).

```python
class ILLMClient(ABC):
    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 4096, temperature: float = 0.7) -> Optional[str]:
        ...
```

Implementation: `doge.infrastructure.llm.deepseek_client.DeepSeekClient` — lazily imports `openai`, reads API key from `Settings`, returns `None` on failure.

### 3.5 Legacy-to-Clean Migration Map

#### `src/micro/` (7 files)

| File | Lines | Disposition | Target / Action |
|------|-------|-------------|-----------------|
| `__init__.py` | 9 | **DELETE** after siblings | Package marker; already just a docstring |
| `database.py` | 579 | **DELETE** after all consumers migrated | All functions have clean equivalents in `SQLiteStorageRepository`, `SQLiteReportRepository`, `SQLiteNoteRepository`. `initialize_system_dbs()` moves to `doge.infrastructure.database.bootstrap`. `insights` table and `knowledge_entities`/`knowledge_graph` tables: retire if unused, or add to port if needed. |
| `market_scanner.py` | 230 | **DELETE** after `ScanMarketUseCase` created | `MarketScanner` orchestration → `ScanMarketUseCase`. `progress_callback` preserved as optional callable. |
| `momentum_scanner.py` | 392 | **DELETE** after `industry_analyzer` reads from `RankingService` instead of CSV | RSRS calculation already in DuckDB view `vw_rsrs_ranking_cn`. CSV output is intermediate artifact; clean path reads directly from `RankingService`. |
| `tdx_downloader.py` | 741 | **DELETE** after moving `main()` demo to CLI | `find_working_server`, `download_cn_kline`, `download_us_kline` already delegated to `TDXDataSource` adapter. Raw `.day` file parsing: move to `doge.infrastructure.data_source.tdx_local` if local fallback retained, else delete. |
| `tdx_loader.py` | 140 | **DELETE** or **MOVE** to `doge.infrastructure.data_source.tdx_local.py` | Local `.day` binary file parser. Only used by `market_scanner.py` local-file fallback. |
| `industry_analyzer.py` | 396 | **DELETE** after `GenerateIndustryReportUseCase` created | `IndustryAnalyzer` → `GenerateIndustryReportUseCase`. Breaks `micro → macro` cross-import by injecting `ILLMClient` port instead of importing `DeepSeekStrategist` directly. |

#### `src/macro/` (5 files)

| File | Lines | Disposition | Target / Action |
|------|-------|-------------|-----------------|
| `__init__.py` | 22 | **DELETE** after siblings | Package exports for backward compat |
| `config.py` | 271 | **DELETE** after callers use `Settings` | `MacroConfig` → `doge.config.get_settings()`. `DEEPSEEK_API_KEY` env var already in `Settings`. |
| `data_loader.py` | 424 | **DELETE** after `GenerateMacroReportUseCase` created | `GlobalMacroLoader` → `GenerateMacroReportUseCase._gather_context()`. `yfinance` import is dead code (F401); remove. `requests` import is dead code; remove. |
| `strategist.py` | 194 | **DELETE** after `GenerateMacroReportUseCase` created | `DeepSeekStrategist` → `DeepSeekClient` adapter implementing `ILLMClient`. |
| `cli.py` | 118 | **SHIM** then **DELETE** | Redirect to unified CLI `doge macro` subcommand. |
| `utils.py` | 126 | **DELETE** after `setup_logging()` superseded | `setup_logging()` → centralized logging config in `doge.config`. |

#### `src/ai_analysis/` (6 files)

| File | Lines | Disposition | Target / Action |
|------|-------|-------------|-----------------|
| `__init__.py` | 249 | **DELETE** after all callers migrated | `normalize_ticker` → `doge.core.domain.models`. `get_duckdb_connection` → `DuckDBConnection` adapter. `connect_duckdb` (legacy) → delete. `run_views_sql` → `DuckDBConnection.refresh_views()`. `query_view`, `query_sql` → `IMarketViewRepository.execute()`. `get_sqlite_stats`, `get_duckdb_view_stats` → `ISchemaBrowser.database_stats()`. |
| `anomaly_detection.py` | 167 | **DELETE** after `GenerateAnomalyReportUseCase` created | Report generation → `GenerateAnomalyReportUseCase`. Extend `AnomalyService` with `price_gaps()` and `consecutive_extremes()`. |
| `catalog_generator.py` | 98 | **DELETE** after `GenerateCatalogUseCase` created | Catalog generation → `GenerateCatalogUseCase`. |
| `fetch_names.py` | 156 | **DELETE** after `PopulateStockNamesUseCase` created | Already uses `ITickerMetadataSource` port (S006-006 complete). Direct SQLite writes → `INoteRepository` (or new `INameRepository` port). |
| `market_overview.py` | 183 | **DELETE** after `GenerateMarketOverviewUseCase` created | Report generation → `GenerateMarketOverviewUseCase`. |
| `stock_notes.py` | 306 | **DELETE** after `ManageNotesUseCase` created and CLI entrypoint moved | All CRUD operations → `ManageNotesUseCase` delegating to `INoteRepository`. `get_ticker_with_context` → orchestrates two repository calls in use case. |

#### `src/api/` routers (6 files + main.py)

| File | Disposition | Target / Action |
|------|-------------|-----------------|
| `main.py` | **SHIM** then **DELETE** | New canonical: `doge.interfaces.api.main`. Legacy becomes re-export shim with `DeprecationWarning`. |
| `routers/scan.py` | **SHIM** then **DELETE** | New canonical: `doge.interfaces.api.routers.scan`. `run_scan` handler uses `ScanMarketUseCase` instead of inline `download_cn_kline` / `download_us_kline` / `MarketScanner` imports. `_storage_repo()` helper stays but calls `SQLiteStorageRepository` via composition root. `_scan_locks` and `_scan_status` remain router-local state. |
| `routers/data.py` | **SHIM** then **DELETE** | New canonical: `doge.interfaces.api.routers.data`. `get_ticker_names` fallback to `akshare` → move to infrastructure adapter (`YFinanceMetadataSource` or new `AkshareMetadataSource`). `_ticker_names_cache` module global → `ITickerNameCache` port. |
| `routers/notes.py` | **SHIM** then **DELETE** | New canonical: `doge.interfaces.api.routers.notes`. Already clean — only import path change. `NoteCreate` Pydantic schema stays in router. |
| `routers/macro.py` | **SHIM** then **DELETE** | New canonical: `doge.interfaces.api.routers.macro`. `run_macro` handler uses `GenerateMacroReportUseCase` instead of inline `GlobalMacroLoader` / `DeepSeekStrategist` / `save_macro_report` imports. |
| `routers/analysis.py` | **SHIM** then **DELETE** | New canonical: `doge.interfaces.api.routers.analysis`. Already clean — only import path change. |
| `routers/config.py` | **SHIM** then **DELETE** | New canonical: `doge.interfaces.api.routers.config`. `get_config` / `update_settings` → `ConfigService` (new application service). `validate_tdx` → stays or moves to `TdxValidationService`. |

#### `src/interface/` (PyQt GUI, 5 files)

| File | Disposition | Target / Action |
|------|-------------|-----------------|
| `dashboard.py` | **SHIM** then **DELETE** | `initialize_system_dbs()` → `bootstrap_databases()` from `doge.infrastructure.database.bootstrap`. |
| `scanner_gui.py` | **SHIM** then **DELETE** | `MarketScanner` → `ScanMarketUseCase`. `MacroConfig` / `GlobalMacroLoader` / `DeepSeekStrategist` → `GenerateMacroReportUseCase`. `save_macro_report` → `IReportRepository.save_macro_report()`. |
| `analysis_gui.py` | **SHIM** then **DELETE** | `IndustryAnalyzer` → `GenerateIndustryReportUseCase`. |
| `db_editor.py` | **KEEP** (standalone) | `QSqlDatabase` direct SQLite access is a legacy standalone DB editor. No clean-arch migration planned for this file — it is a standalone tool, not part of the orchestrated workflow. Mark as `legacy_standalone` in docs. |
| `__init__.py` | **DELETE** after siblings | Package marker. |

#### `src/cli.py` and `src/macro/cli.py`

| File | Disposition | Target / Action |
|------|-------------|-----------------|
| `src/cli.py` | **SHIM** then **DELETE** | New canonical: `doge.interfaces.cli.main`. All query commands (`stock`, `rsrs`, `breadth`, `anomaly`, `demo`) delegate to service factories via `doge.core.services.composition`. `normalize_ticker` → `doge.interfaces.cli.normalize` (shared with MCP tools). Exit codes, bilingual output, and tabulate formatting preserved exactly. |
| `src/macro/cli.py` | **SHIM** then **DELETE** | Redirect to unified CLI `doge macro` subcommand. `MacroConfig` / `GlobalMacroLoader` / `DeepSeekStrategist` → `GenerateMacroReportUseCase`. Secret redaction (`_redact_secrets`) preserved verbatim. Bilingual output preserved exactly. |

### 3.8 Sprint Governance Artifacts

This plan is the design CDD. Before implementation begins, the following governance artifacts must also be created and approved:

| Artifact | Path | Purpose |
|---|---|---|
| Sprint plan (human-readable) | `production/sprints/sprint-007-modularization.md` | Story backlog, Definition of Done, verification commands, risk register summary. |
| Sprint status (machine-readable) | `production/sprint-status.yaml` | Story state for `/sprint-status`, `/story-readiness`, and CI gates. |
| QA plan | `production/qa/qa-plan-sprint-007.md` | Test strategy, evidence locations, regression scope, layer-gate verification. |

These artifacts are **BLOCKING** for Sprint 007 start: implementation work (S007-001) does not begin until all three are in place and approved.

### 3.6 Interface Import Gate (enforced by S007-008)

`src/doge/interfaces/**/*.py` must NOT import from:
- `micro` (legacy scanner/analyzer modules)
- `macro` (legacy strategist/data_loader modules)
- `ai_analysis` (legacy catalog/overview/notes modules)
- `src.api` (legacy API routers — interfaces should use `doge.interfaces.api` or `doge.core.services`)
- `src.interface` (legacy GUI modules)
- `sqlite3`, `duckdb`, `yfinance`, `opentdx`, `openai` (all infrastructure concerns)

The only sanctioned imports in `src/doge/interfaces/` are:
- `doge.application.use_cases.*` (application layer)
- `doge.core.services.*` (service layer — for thin query commands that don't need orchestration)
- `doge.core.ports.*` (for type hints in DI)
- `doge.config.*` (for settings read)
- `doge.interfaces.api.deps` (for FastAPI `Depends()` providers)
- Framework imports (`fastapi`, `mcp`, `PyQt6`, `argparse`, `pandas`, `tabulate`) for formatting and transport only

### 3.7 Composition Root Updates

To keep `core/services` purely dependent on `core/ports` (and never on `infrastructure`), the composition root moves out of `core/services` into the application layer:

- **`doge.application.composition`** — canonical, framework-agnostic composition root. All use-case factory functions live here. This module is the **only sanctioned site** under `doge.application` that may import `doge.infrastructure` adapters.
- **`doge.interfaces.api.deps`** — FastAPI-specific `Depends()` providers that call `doge.application.composition` factories. Contains no adapter imports itself.
- **`doge.interfaces.cli.deps`** — CLI-specific providers that call `doge.application.composition` factories. Contains no adapter imports itself.
- **`doge.interfaces.mcp.deps`** — MCP tool dependency providers that call `doge.application.composition` factories. Contains no adapter imports itself.

```python
# doge/application/composition.py
# This is the only module in doge.application allowed to import infrastructure.
from doge.infrastructure.database.repositories import SQLiteStockRepository, SQLiteReportRepository, SQLiteNoteRepository
from doge.infrastructure.database.duckdb import DuckDBConnection
from doge.infrastructure.data_source.yfinance import YFinanceDataSource
from doge.infrastructure.data_source.yfinance_metadata import YFinanceMetadataSource
from doge.infrastructure.data_source.tdx import TDXDataSource
from doge.infrastructure.llm.deepseek_client import DeepSeekClient

from doge.core.services.stock_service import StockService
from doge.core.services.ranking_service import RankingService
from doge.core.services.breadth_service import BreadthService
from doge.core.services.anomaly_service import AnomalyService
from doge.core.services.view_service import ViewService

from doge.application.use_cases.scan_market import ScanMarketUseCase
from doge.application.use_cases.generate_macro_report import GenerateMacroReportUseCase
from doge.application.use_cases.manage_notes import ManageNotesUseCase
from doge.application.use_cases.query_ticker import QueryTickerUseCase
from doge.application.use_cases.generate_market_overview import GenerateMarketOverviewUseCase
from doge.application.use_cases.generate_anomaly_report import GenerateAnomalyReportUseCase
from doge.application.use_cases.generate_catalog import GenerateCatalogUseCase
from doge.application.use_cases.populate_stock_names import PopulateStockNamesUseCase
from doge.application.use_cases.generate_industry_report import GenerateIndustryReportUseCase


def build_scan_market_use_case(stock_repo=None, data_source=None) -> ScanMarketUseCase:
    ...

def build_generate_macro_report_use_case(view_repo=None, llm_client=None, report_repo=None) -> GenerateMacroReportUseCase:
    ...

def build_manage_notes_use_case(note_repo=None) -> ManageNotesUseCase:
    ...

def build_query_ticker_use_case(stock_repo=None, note_repo=None, metadata_source=None) -> QueryTickerUseCase:
    ...

def build_generate_market_overview_use_case(...) -> GenerateMarketOverviewUseCase:
    ...

def build_generate_anomaly_report_use_case(...) -> GenerateAnomalyReportUseCase:
    ...

def build_generate_catalog_use_case(...) -> GenerateCatalogUseCase:
    ...

def build_populate_stock_names_use_case(...) -> PopulateStockNamesUseCase:
    ...

def build_generate_industry_report_use_case(...) -> GenerateIndustryReportUseCase:
    ...
```

After this change, **`doge.core.services` must import only `doge.core.ports`** (verified by S007-008 layer gate). `doge.core.services.composition.py` is retired or reduced to re-export shims during the transition.

---

## 4. Contracts / Data Model

### 4.1 Application Request DTOs (`doge.application.contracts.request`)

All frozen dataclasses — no external dependencies.

```python
@dataclass(frozen=True)
class ScanMarketRequest:
    market: str                       # "cn" | "us"
    source: str = "tdx"             # "tdx" | "yfinance" | "auto"
    tickers: Optional[list[str]] = None  # None = scan all known
    max_workers: int = 4
    batch_size: int = 50

@dataclass(frozen=True)
class GenerateMacroReportRequest:
    analyst_model: str = "deepseek-chat"
    max_tokens: int = 4096
    temperature: float = 0.7
    custom_prompt: Optional[str] = None

@dataclass(frozen=True)
class ManageNoteRequest:
    operation: str                    # "create" | "read" | "update" | "delete" | "archive" | "search" | "list_recent" | "list_tracked"
    ticker: Optional[str] = None
    market: str = "cn"
    note_id: Optional[int] = None
    note_text: Optional[str] = None
    note_type: str = "comment"
    title: Optional[str] = None
    tags: Optional[str] = None
    price_at_note: Optional[float] = None
    source: Optional[str] = None
    sentiment: Optional[str] = None
    keyword: Optional[str] = None
    days: int = 7
    limit: int = 50

@dataclass(frozen=True)
class QueryTickerRequest:
    ticker: str
    market: str = "cn"
    days: int = 20
    include_notes: bool = True
    include_metadata: bool = True
    max_notes: int = 5
```

### 4.2 Application Response DTOs (`doge.application.contracts.response`)

All frozen dataclasses — no external dependencies.

```python
@dataclass(frozen=True)
class ScanResultItem:
    ticker: str
    status: str               # "success" | "skipped" | "failed" | "no_data"
    rows_appended: int = 0
    message: Optional[str] = None

@dataclass(frozen=True)
class ScanMarketResponse:
    market: str
    total_tickers: int
    success_count: int
    failed_count: int
    skipped_count: int
    results: List[ScanResultItem] = field(default_factory=list)
    duration_seconds: float = 0.0

@dataclass(frozen=True)
class MacroReportResponse:
    report_id: Optional[int] = None
    content: str = ""
    risk_signal: str = "neutral"
    volatility: str = "low"
    tags: str = ""
    analyst: str = ""
    generated_at: Optional[str] = None
    error: Optional[str] = None

@dataclass(frozen=True)
class NoteItem:
    note_id: int
    ticker: str
    market: str
    created_at: str
    note_type: str
    title: Optional[str]
    content: str
    tags: Optional[str]
    price_at_note: Optional[float]
    source: Optional[str]

@dataclass(frozen=True)
class ManageNoteResponse:
    operation: str
    success: bool
    note_id: Optional[int] = None
    notes: List[NoteItem] = field(default_factory=list)
    count: int = 0
    message: str = ""

@dataclass(frozen=True)
class TickerPricePoint:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: Optional[float] = None
    ma_5: Optional[float] = None
    ma_10: Optional[float] = None
    ma_20: Optional[float] = None
    ma_60: Optional[float] = None
    atr_14: Optional[float] = None

@dataclass(frozen=True)
class TickerMetadata:
    name: Optional[str] = None
    name_en: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

@dataclass(frozen=True)
class TickerNoteSummary:
    count_total: int = 0
    recent_notes: List[NoteItem] = field(default_factory=list)

@dataclass(frozen=True)
class QueryTickerResponse:
    ticker: str
    market: str
    metadata: TickerMetadata = field(default_factory=TickerMetadata)
    prices: List[TickerPricePoint] = field(default_factory=list)
    notes: TickerNoteSummary = field(default_factory=TickerNoteSummary)
    latest_close: Optional[float] = None
    change_pct: Optional[float] = None
```

### 4.3 New Port Interface (`doge.core.ports.llm`)

```python
class ILLMClient(ABC):
    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 4096, temperature: float = 0.7) -> Optional[str]:
        """Send a chat completion request and return the generated text, or None on failure."""
        ...
```

### 4.4 Exit Codes (CLI — preserved exactly)

| Scenario | Exit Code | Source |
|----------|-----------|--------|
| Success (data present) | 0 | `src/cli.py` implicit return |
| No data (query commands) | 1 | `src/cli.py:EXIT_NO_DATA` |
| Invalid args | 2 | argparse builtin |
| Macro failure / exception | 1 | `src/macro/cli.py` |
| No subcommand (help printed) | 0 | `src/cli.py` |

### 4.5 Error Envelope (API — preserved exactly)

```json
{"error": {"code": "internal_error", "message": "internal server error"}}
```

All API routes return this shape for unhandled exceptions. `HTTPException` returns `{"error": {"code": "<mapped_code>", "message": "<detail>"}}`.

---

## 5. Edge Cases

### 5.1 Import Loops

**Risk:** `doge.application.use_cases` imports `doge.core.services`, which imports `doge.core.ports`, which is fine. But if `doge.core.services.composition` imports `doge.application.use_cases` to provide factory functions, and `doge.application.use_cases` imports `doge.core.services.composition` for `refresh_views`, a circular import forms.

**Resolution:** `composition.py` imports `doge.application.use_cases` at the bottom of the file (after all service/adapter imports), or uses lazy import inside factory functions. Use cases that need `refresh_views` accept it as a `callable` parameter injected at construction time, not imported at module level.

### 5.2 Test Monkeypatch Breakage on Module Moves

**Risk:** 4 test files use `sys.path.insert(0, MICRO_DIR)` or `_INTERFACE_DIR` shims. If `src/micro/` or `src/interface/` files move, these shims break.

| Test File | Shim | Risk |
|-----------|------|------|
| `tests/unit/storage/test_save_stock_data_custom_storage_write_error.py` | `sys.path.insert(0, str(MICRO_DIR))` + `import database` | **High** — if `database.py` moves, both shim and import break |
| `tests/unit/storage/test_market_scanner_write_tolerance.py` | Same pattern | **High** — same as above |
| `tests/unit/micro/test_scanner_opentdx_optional.py` | `sys.path.insert(0, str(MICRO_DIR))` | **High** — if `src/micro/` moves, path is wrong |
| `tests/test_pyqt_smoke.py` | `sys.path.insert(0, _INTERFACE_DIR)` | **High** — if `src/interface/` gains `__init__.py` or moves, shim may be wrong |

**Resolution:** These tests are legacy coverage for modules that are being deleted. They should be replaced by clean-arch tests that import from `doge.*` paths (no `sys.path` shims) before the legacy modules are deleted. The shim tests can be deleted once the new tests pass.

### 5.3 Bilingual CLI Output Preservation

**Risk:** The `macro` CLI command has bilingual output (Chinese primary, English secondary) that is user-facing and must not change.

**Preserved outputs:**
- `🚀 启动 MY-DOGE 宏观战略分析 (Verbose Mode)...`
- `✅ 配置加载成功`
- `📊 市场数据摘要: ...`
- `❌ 无法获取市场数据，请检查网络连接`
- `❌ 运行失败: ...`
- `💡 若与 API Key 有关，请检查 DEEPSEEK_API_KEY 环境变量配置`
- `If this is API-key related, check the DEEPSEEK_API_KEY env var.`
- `Demo complete. See docs/GETTING_STARTED.md for the full walkthrough.`

**Resolution:** These strings are preserved verbatim in `doge.interfaces.cli.commands.macro` and `doge.interfaces.cli.commands.demo`. A grep-based contract test (`tests/cli/test_bilingual_output.py`) asserts their presence.

### 5.4 Secret Redaction in CLI

**Risk:** The `_redact_secrets()` function in `src/macro/cli.py` masks the DeepSeek API key. If the migration loses this, the key could leak into logs.

**Preserved behavior:**
- Placeholder sentinel `REPLACE_WITH_DEEPSEEK_API_KEY` masking
- Runtime `config.api_key` masking
- Belt-and-braces regex `sk-[A-Za-z0-9_-]{20,}` masking for unbound-config cases

**Resolution:** `_redact_secrets()` is migrated verbatim to `doge.interfaces.cli.commands.macro`. A contract test (`tests/cli/test_macro_cli_error_redaction.py` — already exists) asserts no key in logs.

### 5.5 PyQt Side Effects at Import Time

**Risk:** `src/interface/dashboard.py` mutates `os.environ['PATH']` and calls `os.add_dll_directory()` at import time (lines 7-13) with a hardcoded PyQt6 binary path. This is platform-specific and must not be lost.

**Resolution:** The PyQt GUI is a legacy standalone interface. It is not migrated to the clean architecture in Sprint 007. The `src/interface/` files become shims that delegate to `doge.application.use_cases`, but the import-time side effects are preserved in the shim files. The `db_editor.py` file is marked as `legacy_standalone` and not touched.

### 5.6 Partial Migration Rollback

**Risk:** A migrated service breaks a workflow.

**Resolution:** Per ADR-0001:209, route the interface back to the legacy implementation while the service contract is fixed. The shim files (`src/api/routers/*.py`, `src/cli.py`, `src/macro/cli.py`) are kept as re-export shims with `DeprecationWarning` for one release cycle, so rollback is a one-line change: uncomment the legacy import and comment the new one.

### 5.7 TDX Adapter `NotImplementedError`

**Risk:** `TDXDataSource.download_kline` and `get_latest_market_date` currently raise `NotImplementedError` (tdx.py:32,35). If a use case tries to use them before the TDX logic is migrated, it fails.

**Resolution:** The `ScanMarketUseCase` accepts an `IMarketDataSource` parameter. For Sprint 007, the default factory in `composition.py` still constructs `TDXDataSource` (which delegates to `micro.tdx_downloader` via lazy imports). Once Batch 3 (TDX adapter implementation) completes, the lazy imports are removed and the adapter implements the methods directly. The `ScanMarketUseCase` itself is agnostic to the data source implementation.

### 5.8 Dual Source of Truth for Paths

**Risk:** Legacy `ai_analysis/__init__.py` and `doge/config/settings.py` define the same env var names (`DOGE_DB_DIR`, `DOGE_CN_DB`, etc.) with the same defaults. If they diverge, migration and legacy paths behave differently.

**Resolution:** AC-3 (parity test) asserts identical values for all 5 env vars. After all legacy modules are deleted, the legacy constants are gone and the risk disappears.

### 5.9 `insights` Table and `knowledge_graph` Tables

**Risk:** `micro/database.py` writes to `insights`, `knowledge_entities`, and `knowledge_graph` tables. These are not in the clean architecture schema.

**Resolution:** Verify if any live code reads these tables. If not, retire them. If yes, add `save_insight()` and `add_entity()`/`add_relationship()` methods to `IReportRepository` (or a new `IInsightRepository` port) and implement in `SQLiteReportRepository`.

### 5.10 Circular Dependency: `micro → macro`

**Risk:** `micro/industry_analyzer.py` imports `macro.config.MacroConfig` and `macro.strategist.DeepSeekStrategist`. This is a one-way dependency.

**Resolution:** The `GenerateIndustryReportUseCase` replaces both imports:
- `MacroConfig` usage → `doge.config.get_settings()`
- `DeepSeekStrategist` usage → `ILLMClient` port injected at initialization

### 5.11 `requests` Dead Import in `macro/data_loader.py`

**Risk:** `import requests` at line 6 is unused after S005-007 migration. It should be removed.

**Resolution:** Remove during `GenerateMacroReportUseCase` creation. A layer-gate test asserts no `import requests` in `src/macro/`.

### 5.12 Hardcoded Proxy in `micro/industry_analyzer.py`

**Risk:** `os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"` at lines 47-48 is hardcoded.

**Resolution:** Move to `Settings().network.proxy` (new field in `Settings` dataclass). Default is `None` (no proxy). The `GenerateIndustryReportUseCase` reads proxy from settings and passes it to the LLM client adapter.

---

## 6. Dependencies

### 6.1 Governing Documents

- **ADR-0001** (`docs/architecture/adr-0001-brownfield-clean-architecture.md`) — Accepted 2026-06-11. Owns layer boundaries, port inventory, migration plan, validation criteria.
- **ADR-0010** (`docs/architecture/adr-0010-port-injection.md`) — Accepted 2026-06-12. Owns `IMarketViewRepository` port and composition-root pattern.
- **ADR-0009** (`docs/architecture/adr-0009-metadata-port.md`) — Accepted 2026-06-12. Owns `ITickerMetadataSource` / `ITickerNameCache` port split.
- **ADR-0004** (`docs/architecture/adr-0004-tdx-adapter.md`) — Accepted. Owns TDX data source adapter migration.
- **ADR-0007** (`docs/architecture/adr-0007-loopback-guarantee.md`) — Accepted. Owns API bind host loopback enforcement.

### 6.2 Upstream (this sprint depends on)

- **Module #1 — Runtime Configuration** (`runtime-configuration`) — `src/doge/config/settings.py` is the foundation. All new `Settings` fields (`network.proxy`, `deepseek_model`, etc.) must be added here first.
- **Module #2 — Market Data Storage** (`market-data-storage`) — DuckDB views (`vw_rsrs_ranking_*`, `vw_market_breadth_*`, `vw_volume_anomalies_cn`) that services query.
- **Module #8 — MCP Server** (`mcp-server`) — `src/doge/interfaces/mcp/` is the reference implementation of a correctly-wired interface. MCP tools already delegate through services; they gain optional delegation through use cases for complex orchestration.
- **Module #9 — FastAPI Service** (`fastapi-service`) — `src/api/routers/` must be re-routed through application use cases.
- **Module #12 — Clean Architecture Migration** (`clean-architecture-migration`) — This sprint is Batch 5 (interface rewire) + Batch 6 (cleanup) of the migration plan documented in the CDD.

### 6.3 Downstream (depend on this sprint)

- **Module #3 — Data Sources** — TDX/yfinance adapters will be fully exercised by `ScanMarketUseCase` and `QueryTickerUseCase`.
- **Module #4 — Macro Strategy Engine** — Business logic migrates into `GenerateMacroReportUseCase`.
- **Module #5 — Micro Momentum Scanner** — RSRS formula remains canonical in DuckDB view; CSV generation is retired.
- **Module #6 — AI Industry Analysis** — Uses `GenerateIndustryReportUseCase`.
- **Module #7 — Research Insight Knowledge Base** — Uses `ManageNotesUseCase` and `PopulateStockNamesUseCase`.
- **Module #10 — PyQt Desktop Dashboard** — Delegates to use cases via shim.
- **Module #11 — Vue Web Console** — Will call API routes that delegate to use cases.

### 6.4 Packages / Tooling

- `pyproject.toml` (setuptools, packages found at `src/`, pythonpath `["src"]`).
- `duckdb==1.4.4`, `pandas`, `scipy`, `pytest==9.0.1`, `pytest-asyncio==1.3.0`, `fastapi==0.123.8`, `mcp==1.25.0`.
- `opentdx` / `akshare` (optional extras `tdx`, `cn`) for TDX adapter.
- `openai` (optional extra) for `DeepSeekClient` LLM adapter.

---

## 7. Configuration Knobs

| Knob | Source | Default | Valid Range | Env Owner | Migration Role / Risk |
|------|--------|---------|-------------|-----------|----------------------|
| `DOGE_DB_DIR` | `settings.py` | `<root>/data` | absolute dir path | operator shell / `.env` | Single source for data dir; legacy `ai_analysis` reads same name — drift = dual source of truth (risk: MEDIUM) |
| `DOGE_CN_DB` | `settings.py` | `<dir>/market_data_cn.db` | absolute file path | operator | Read by both `DuckDBStockRepository` and legacy `ai_analysis` |
| `DOGE_US_DB` | `settings.py` | `<dir>/market_data_us.db` | absolute file path | operator | Same dual-read concern |
| `DOGE_RESEARCH_DB` | `settings.py` | `<dir>/research_insights.db` | absolute file path | operator | `SQLiteReportRepository` default |
| `DOGE_DUCKDB_PATH` | `settings.py` | `<dir>/market.duckdb` | absolute file path | operator | DuckDB file; opened read_only for queries, read-write for `refresh_views` |
| `DEEPSEEK_API_KEY` | `settings.py` | `None` | valid API key string | operator env var | Required for `GenerateMacroReportUseCase` and `GenerateIndustryReportUseCase`; `DeepSeekClient` returns `None` if missing |
| `DEEPSEEK_BASE_URL` | `settings.py` | `"https://api.deepseek.com/v1"` | valid URL | operator env var | DeepSeek API endpoint; override for proxy/local deployment |
| `DEEPSEEK_MODEL` | `settings.py` | `"deepseek-chat"` | model identifier string | operator env var | LLM model identifier passed to `ILLMClient.chat()` |
| `DOGE_NETWORK_PROXY` | `settings.py` (new) | `None` | `"http://host:port"` or `None` | operator env var | HTTP proxy for LLM and metadata requests; replaces hardcoded `http://127.0.0.1:7890` |
| `OPENBLAS_NUM_THREADS` / `OMP_NUM_THREADS` | `duckdb.py` | `"1"` | `"1"` recommended | runtime (setdefault) | OOM guard during pandas `.df()` conversion; duplicated in legacy and new — dedupe post-migration |
| DuckDB `threads` | `duckdb.py` | `4` | 1–8 | hardcoded in adapter | Adapter-owned; not operator-configurable yet (OQ-3). Raising increases peak memory during `.df()` conversion. |
| MCP `TOOL_TIMEOUT` | `server.py` | `30` (s) | 1–120 | hardcoded | Matches ADR-0001 MCP latency budget |
| `pytest` `asyncio_mode` | `pyproject.toml` | `"strict"` | `strict`/`auto` | pyproject | Migration tests rely on explicit async markers |

---

## 8. Acceptance Criteria

### 8.1 Foundation Story (S007-001)

- [ ] **AC-001-1.** `src/doge/application/` package exists with `__init__.py`, `contracts/__init__.py`, `contracts/request.py`, `contracts/response.py`, `use_cases/__init__.py`, and `composition.py`.
- [ ] **AC-001-2.** All request/response DTOs are frozen dataclasses with no external imports (stdlib only).
- [ ] **AC-001-3.** `pytest tests/unit/application/contracts/test_dtos.py` passes — frozen immutability, default values, field coverage.
- [ ] **AC-001-4.** `python -c "from doge.application.use_cases import ScanMarketUseCase, GenerateMacroReportUseCase, ManageNotesUseCase, QueryTickerUseCase"` imports cleanly.
- [ ] **AC-001-5.** `doge.application.composition` is the only module under `doge.application` that imports `doge.infrastructure` (verified by `grep` gate).
- [ ] **AC-001-6.** `doge.core.services` imports **only** `doge.core.ports` and stdlib/third-party utilities; no `doge.infrastructure` import (verified by `grep` gate).
- [ ] **AC-001-7.** No circular import between `doge.application.use_cases` and `doge.application.composition` (verified by `python -c` import test).

### 8.2 API Scan Workflow Migration (S007-002)

- [ ] **AC-002-1.** `src/doge/interfaces/api/routers/scan.py` exists and `src/api/routers/scan.py` is a re-export shim with `DeprecationWarning`.
- [ ] **AC-002-2.** `grep -rn "from src.micro" src/doge/interfaces/api/routers/scan.py` returns zero hits.
- [ ] **AC-002-3.** `grep -rn "import sqlite3\|import duckdb" src/doge/interfaces/api/routers/scan.py` returns zero hits.
- [ ] **AC-002-4.** `pytest tests/contract/test_api_scan.py` passes — SSE stream events match prior shape, progress 0→100 sequence preserved.
- [ ] **AC-002-5.** Manual smoke: `python -m uvicorn doge.interfaces.api.main:app --reload` + POST `/api/scan/cn` returns `EventSourceResponse` with progress events.

### 8.3 CLI Demo/Query Migration (S007-003)

- [ ] **AC-003-1.** `src/doge/interfaces/cli/` package exists with `main.py`, `commands/*.py`, `formatters.py`, `constants.py`, `normalize.py`.
- [ ] **AC-003-2.** `pyproject.toml` has `[project.scripts]` entry `doge = "doge.interfaces.cli.main:main"`.
- [ ] **AC-003-3.** `grep -rn "from src.micro\|from src.macro\|from src.ai_analysis" src/doge/interfaces/cli/` returns zero hits.
- [ ] **AC-003-4.** `pytest tests/cli/test_cli_service_dispatch.py` passes — all 4 query commands delegate to service factories.
- [ ] **AC-003-5.** `pytest tests/cli/test_cli_exit_codes.py` passes — exit 0 on success, 1 on no data, 2 on bad args.
- [ ] **AC-003-6.** `doge --help` prints correct subcommands (stock, rsrs, breadth, anomaly, demo, macro).
- [ ] **AC-003-7.** Bilingual output preserved: `grep -F "启动 MY-DOGE 宏观战略分析" src/doge/interfaces/cli/commands/macro.py` returns 1 hit.
- [ ] **AC-003-8.** Secret redaction preserved: `pytest tests/cli/test_macro_cli_error_redaction.py` passes.

### 8.4 ai_analysis Cleanup (S007-004)

- [ ] **AC-004-1.** `src/ai_analysis/__init__.py` is reduced to a re-export shim or deleted.
- [ ] **AC-004-2.** `grep -rn "from ai_analysis import" src/doge/` returns zero hits.
- [ ] **AC-004-3.** `grep -rn "ai_analysis" src/doge/` returns zero hits.
- [ ] **AC-004-4.** `pytest tests/unit/infrastructure/test_duckdb_adapter.py` passes — `connect_duckdb` behavior preserved (ATTACH, read_only flag, threads=4).
- [ ] **AC-004-5.** `pytest tests/migration/test_views_sql.py` passes — views.sql DDL runs and all 8 views enumerate.

### 8.5 Market Scanner Migration (S007-005)

- [ ] **AC-005-1.** `ScanMarketUseCase` exists in `src/doge/application/use_cases/scan_market.py`.
- [ ] **AC-005-2.** `pytest tests/unit/application/use_cases/test_scan_market.py` passes — mock `IStockRepository` + `IMarketDataSource`, verify orchestration steps, error handling, `StorageWriteError` path.
- [ ] **AC-005-3.** `pytest tests/integration/test_scan_end_to_end.py` passes — full scan with real TDX files produces identical row counts to pre-migration.
- [ ] **AC-005-4.** `grep -rn "save_stock_data_custom" src/micro/market_scanner.py` returns zero hits.
- [ ] **AC-005-5.** `grep -rn "import sqlite3" src/micro/market_scanner.py` returns zero hits.

### 8.6 Macro Report Generation Migration (S007-006)

- [ ] **AC-006-1.** `GenerateMacroReportUseCase` exists in `src/doge/application/use_cases/generate_macro_report.py`.
- [ ] **AC-006-2.** `ILLMClient` port exists in `src/doge/core/ports/llm.py`.
- [ ] **AC-006-3.** `DeepSeekClient` adapter exists in `src/doge/infrastructure/llm/deepseek_client.py`.
- [ ] **AC-006-4.** `pytest tests/unit/application/use_cases/test_generate_macro_report.py` passes — mock `IMarketViewRepository` + `ILLMClient` + `IReportRepository`, verify prompt building, LLM failure path, persist failure path.
- [ ] **AC-006-5.** `pytest tests/contract/test_api_macro.py` passes — SSE stream events match prior shape.
- [ ] **AC-006-6.** `grep -rn "from src.macro" src/doge/interfaces/api/routers/macro.py` returns zero hits.
- [ ] **AC-006-7.** `grep -rn "save_macro_report" src/doge/interfaces/api/routers/macro.py` returns zero hits.
- [ ] **AC-006-8.** `python -m macro.cli` still runs end-to-end (advisory — requires API key).

### 8.7 Documentation Update (S007-007)

- [ ] **AC-007-1.** `docs/MODULARIZATION_PLAN.md` updated with Sprint 007 story IDs (S007-001 through S007-008).
- [ ] **AC-007-2.** Batches 1-4 marked as "Completed" with story references.
- [ ] **AC-007-3.** Batches 5-6 expanded with Sprint 007 story details.
- [ ] **AC-007-4.** No orphaned references to deleted files (e.g., `mcp_server.py`).

### 8.8 Layer Gate Verification (S007-008)

- [ ] **AC-008-1.** `python -m pytest tests/unit/layer_gates/ -q` passes — all layer gate tests green.
- [ ] **AC-008-2.** `python -m pytest tests/test_api_routers.py -q` passes.
- [ ] **AC-008-3.** `python -m pytest tests/test_mcp_tools.py -q` passes.
- [ ] **AC-008-4.** `python -m pytest tests/cli/ -q` passes.
- [ ] **AC-008-5.** `python -m pytest -q` returns: `617+ passed, 5 skipped, 0 failed, 0 error` (baseline: 617 passed, 5 skipped, 0 failed).
- [ ] **AC-008-6.** `python doge_mcp.py --transport stdio --log-level INFO` starts successfully (manual 5-second check).
- [ ] **AC-008-7.** `python -m uvicorn doge.interfaces.api.main:app --reload` starts successfully (manual 5-second check).
- [ ] **AC-008-8.** `doge demo` runs and produces tabulated output.
- [ ] **AC-008-9.** New layer gate test `tests/unit/layer_gates/test_interface_import_gate.py` passes — zero forbidden imports in `src/doge/interfaces/`.
- [ ] **AC-008-10.** `grep -rnE "import sqlite3\|import duckdb\|sqlite3\.connect\|duckdb\.connect" src/doge/interfaces src/doge/application src/doge/core` returns zero hits (except `doge.infrastructure/` and `doge.application.composition.py` factory functions).
- [ ] **AC-008-11.** `grep -rn "sys.path.insert" src/doge/ doge_mcp.py` returns zero hits.
- [ ] **AC-008-12.** `grep -rnE "_PROJECT_ROOT\|parents\[3\]\|parents\[2\]" src/doge/` returns exactly one line: `doge/config/settings.py` (the sanctioned calculation).

---

## Appendix A: Risk Register

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|------|------------|--------|------------|-------|
| 1 | `market_scanner.py` regression on production data | Medium | High | Run full scan on copy of production data before marking Done; compare row counts and view outputs | S007-005 |
| 2 | Test monkeypatch breakage on module moves | Medium | Medium | Replace shim tests with clean-arch tests before deleting legacy modules | S007-004, S007-005 |
| 3 | Bilingual CLI output lost or changed | Low | Medium | Grep-based contract test asserts presence of all preserved strings | S007-003 |
| 4 | Secret redaction lost in macro CLI | Low | High | `_redact_secrets()` migrated verbatim; existing contract test asserts no key in logs | S007-003, S007-006 |
| 5 | Circular import between `application` and `composition` | Medium | Medium | Use lazy imports in factories or pass callables as constructor parameters | S007-001 |
| 6 | `insights` / `knowledge_graph` tables orphaned | Low | Low | Verify no live code reads them before retiring; add to port if needed | S007-004 |
| 7 | PyQt GUI import-time side effects lost | Low | Medium | Mark `db_editor.py` as `legacy_standalone`; preserve side effects in shim files | S007-002 (advisory) |
| 8 | TDX adapter still raises `NotImplementedError` | Medium | Low | `ScanMarketUseCase` accepts `IMarketDataSource` parameter; default factory uses lazy-import bridge | S007-005 |
| 9 | Dual source of truth for DB paths | Medium | Medium | AC-3 parity test; delete legacy constants after all imports move | S007-004 |
| 10 | Full pytest suite fails at S007-008 | Medium | High | Bisect to offending story; revert that story's changes; fix and re-run gate | S007-008 |

---

## Appendix B: Verification Commands

### Fast Feedback Loop (targeted, run before every commit)

```bash
# Layer gates (~2s)
python -m pytest tests/unit/layer_gates/ -q

# MCP tools (~5s)
python -m pytest tests/test_mcp_tools.py -q

# API routers (~5s)
python -m pytest tests/test_api_routers.py -q

# CLI (~3s)
python -m pytest tests/cli/ -q
```

### Full Gate (before push/PR)

```bash
# Full suite (~30s)
python -m pytest -q
# Expected: 617+ passed, 5 skipped, 0 failed, 0 error

# API contract
python -m pytest tests/test_api_routers.py tests/contract/ -q

# MCP
python -m pytest tests/test_mcp_tools.py tests/test_transport.py -q
```

### Manual Smoke Checks

```bash
# MCP stdio startup (5-second check)
python doge_mcp.py --transport stdio --log-level INFO
# ^C after "=== SERVER START ===" appears

# MCP SSE startup (5-second check)
python doge_mcp.py --transport sse --host 127.0.0.1 --port 8902
# curl http://127.0.0.1:8902/health -> {"status":"ok"}

# API startup (5-second check)
python -m uvicorn doge.interfaces.api.main:app --reload

# CLI demo
python -m doge.interfaces.cli demo --market cn --top 5
```

---

## Appendix C: Legacy-to-New Import Mapping Table

### `src/micro/` → Clean Architecture

| Legacy Symbol | Legacy File | New Location | Notes |
|---------------|-------------|--------------|-------|
| `get_db_connection()` | `micro/database.py:28` | `doge.infrastructure.database.sqlite.SQLiteConnection` | Already exists |
| `init_db()` | `micro/database.py:46` | `doge.infrastructure.database.sqlite_storage` | Already partially delegated |
| `init_db_custom()` | `micro/database.py:116` | `doge.infrastructure.database.sqlite_storage` | Already partially delegated |
| `save_stock_data_custom()` | `micro/database.py:140` | `doge.infrastructure.database.repositories.DuckDBStockRepository` | Already partially delegated |
| `get_tickers_sync_state()` | `micro/database.py:214` | `doge.infrastructure.database.repositories` | New port method needed |
| `save_macro_report()` | `micro/database.py:270` | `doge.infrastructure.database.repositories.SQLiteReportRepository` | Already exists |
| `save_research_report()` | `micro/database.py:313` | `doge.infrastructure.database.repositories.SQLiteReportRepository` | Already exists |
| `save_insight()` | `micro/database.py:355` | `IReportRepository.save_insight()` or new `IInsightRepository` | Decision needed: retire or add to port |
| `get_history_insights()` | `micro/database.py:381` | `IReportRepository.get_history_insights()` | Query port |
| `add_entity()` / `add_relationship()` | `micro/database.py:430` / `457` | `IReportRepository` or new `IKnowledgeGraphRepository` | Decision needed: retire or add to port |
| `initialize_system_dbs()` | `micro/database.py:483` | `doge.infrastructure.database.bootstrap.bootstrap_databases()` | New module |
| `MarketScanner.scan_cn_market()` / `scan_us_market()` | `micro/market_scanner.py:89` / `161` | `doge.application.use_cases.scan_market.ScanMarketUseCase.execute()` | Orchestrates TDX fetch + DB write + DuckDB refresh |
| `MomentumRanker.calculate_rsrs()` | `micro/momentum_scanner.py:85` | `doge.core.domain.indicators.rsrs` or DuckDB view | Already in SQL view |
| `MomentumRanker.analyze_market()` | `micro/momentum_scanner.py:212` | `doge.core.services.ranking_service.RankingService.rsrs()` | Read from view instead of CSV |
| `TDXReader.get_data()` / `_parse_file()` | `micro/tdx_loader.py:22` / `66` | `doge.infrastructure.data_source.tdx.TDXDataSource` or `tdx_local` | Binary parsing already partially moved |
| `find_working_server()` | `micro/tdx_downloader.py:74` | `doge.infrastructure.data_source.tdx.TDXDataSource` | Already delegated |
| `download_cn_kline()` / `download_us_kline()` | `micro/tdx_downloader.py:199` / `267` | `doge.infrastructure.data_source.tdx.TDXDataSource` | Already delegated |
| `IndustryAnalyzer.run_analysis()` | `micro/industry_analyzer.py:244` | `doge.application.use_cases.generate_industry_report.GenerateIndustryReportUseCase.execute()` | Breaks `micro→macro` cross-import |

### `src/macro/` → Clean Architecture

| Legacy Symbol | Legacy File | New Location | Notes |
|---------------|-------------|--------------|-------|
| `MacroConfig` | `macro/config.py` | `doge.config.get_settings()` | Settings dataclass already has all fields |
| `GlobalMacroLoader.fetch_combined_data()` | `macro/data_loader.py:41` | `doge.application.use_cases.generate_macro_report.GenerateMacroReportUseCase._gather_context()` | Already partially migrated to adapter |
| `GlobalMacroLoader.calculate_metrics()` | `macro/data_loader.py:359` | `GenerateMacroReportUseCase._gather_context()` | Metric computation |
| `GlobalMacroLoader.calculate_advanced_metrics()` | `macro/data_loader.py:300` | `GenerateMacroReportUseCase._gather_context()` | Advanced indicators |
| `DeepSeekStrategist.generate_strategy_report()` | `macro/strategist.py:19` | `doge.infrastructure.llm.deepseek_client.DeepSeekClient.chat()` | LLM prompt + API call |
| `DeepSeekStrategist.format_report_for_display()` | `macro/strategist.py:164` | `GenerateMacroReportUseCase.execute()` | Report formatting |
| `setup_logging()` | `macro/utils.py` | `doge.config.logging_config` or stdlib logging | Centralized logging config |

### `src/ai_analysis/` → Clean Architecture

| Legacy Symbol | Legacy File | New Location | Notes |
|---------------|-------------|--------------|-------|
| `normalize_ticker` | `ai_analysis/__init__.py` | `doge.core.domain.models.normalize_ticker()` | Domain utility |
| `get_duckdb_connection` | `ai_analysis/__init__.py` | `doge.infrastructure.database.duckdb.DuckDBConnection` | Already exists |
| `connect_duckdb` | `ai_analysis/__init__.py` | **DELETE** | Legacy direct-connect |
| `run_views_sql` | `ai_analysis/__init__.py` | `doge.infrastructure.database.duckdb.DuckDBConnection.refresh_views()` | Already exists |
| `query_view`, `query_sql` | `ai_analysis/__init__.py` | `doge.core.ports.market_view.IMarketViewRepository.execute()` | Use port |
| `get_sqlite_stats` | `ai_analysis/__init__.py` | `doge.core.ports.repository.ISchemaBrowser.database_stats()` | Use port |
| `get_duckdb_view_stats` | `ai_analysis/__init__.py` | `doge.core.services.view_service.ViewService.list_views()` | Use service |
| `volume_anomalies`, `price_gaps`, `consecutive_extremes` | `anomaly_detection.py` | `doge.core.services.anomaly_service.AnomalyService` (extended) | Pure SQL over DuckDB views |
| `anomaly_detection.generate()` | `anomaly_detection.py` | `doge.application.use_cases.generate_anomaly_report.GenerateAnomalyReportUseCase` | Report orchestrator |
| `market_overview.*` query fns | `market_overview.py` | `doge.core.services.*` (existing) | Already have service equivalents |
| `market_overview.generate()` | `market_overview.py` | `doge.application.use_cases.generate_market_overview.GenerateMarketOverviewUseCase` | Report orchestrator |
| `fetch_names.*` | `fetch_names.py` | `doge.application.use_cases.populate_stock_names.PopulateStockNamesUseCase` | Already uses metadata port |
| `stock_notes.add_note` | `stock_notes.py` | `doge.core.ports.repository.INoteRepository.add_note()` | Use port |
| `stock_notes.get_notes` | `stock_notes.py` | `INoteRepository.get_notes()` | Use port |
| `stock_notes.delete_note` | `stock_notes.py` | `INoteRepository.delete_note()` | Use port |
| `stock_notes.search_notes` | `stock_notes.py` | `INoteRepository.search_notes()` | Use port |
| `stock_notes.list_tracked_tickers` | `stock_notes.py` | `INoteRepository.list_tracked_tickers()` | Use port |
| `stock_notes.get_recent_notes` | `stock_notes.py` | `INoteRepository.get_recent_notes()` | Use port |
| `stock_notes.get_ticker_with_context` | `stock_notes.py` | `doge.application.use_cases.query_ticker.QueryTickerUseCase` | Orchestrates two repository calls |
| `catalog_generator.generate_catalog()` | `catalog_generator.py` | `doge.application.use_cases.generate_catalog.GenerateCatalogUseCase` | Uses schema browser + view service |

### `src/api/` → `src/doge/interfaces/api/`

| Legacy Router | Legacy File | New Location | Notes |
|---------------|-------------|--------------|-------|
| `scan` router | `src/api/routers/scan.py` | `src/doge/interfaces/api/routers/scan.py` | Uses `ScanMarketUseCase` |
| `data` router | `src/api/routers/data.py` | `src/doge/interfaces/api/routers/data.py` | Uses `ITickerNameCache` port for names |
| `notes` router | `src/api/routers/notes.py` | `src/doge/interfaces/api/routers/notes.py` | Already clean — path change only |
| `macro` router | `src/api/routers/macro.py` | `src/doge/interfaces/api/routers/macro.py` | Uses `GenerateMacroReportUseCase` |
| `analysis` router | `src/api/routers/analysis.py` | `src/doge/interfaces/api/routers/analysis.py` | Already clean — path change only |
| `config` router | `src/api/routers/config.py` | `src/doge/interfaces/api/routers/config.py` | Uses `ConfigService` |
| `main.py` | `src/api/main.py` | `src/doge/interfaces/api/main.py` | Composition root |

### `src/cli.py` / `src/macro/cli.py` → `src/doge/interfaces/cli/`

| Legacy Command | Legacy File | New Location | Notes |
|---------------|-------------|--------------|-------|
| `stock` subcommand | `src/cli.py` | `src/doge/interfaces/cli/commands/stock.py` | Delegates to `StockService` |
| `rsrs` subcommand | `src/cli.py` | `src/doge/interfaces/cli/commands/rsrs.py` | Delegates to `RankingService` |
| `breadth` subcommand | `src/cli.py` | `src/doge/interfaces/cli/commands/breadth.py` | Delegates to `BreadthService` |
| `anomaly` subcommand | `src/cli.py` | `src/doge/interfaces/cli/commands/anomaly.py` | Delegates to `AnomalyService` |
| `demo` subcommand | `src/cli.py` | `src/doge/interfaces/cli/commands/demo.py` | Composite walkthrough |
| `macro` subcommand | `src/macro/cli.py` | `src/doge/interfaces/cli/commands/macro.py` | Delegates to `GenerateMacroReportUseCase` |
| `normalize_ticker` | `src/cli.py` | `src/doge/interfaces/cli/normalize.py` | Shared with MCP tools |
| `_redact_secrets` | `src/macro/cli.py` | `src/doge/interfaces/cli/commands/macro.py` | Secret redaction preserved |

---

## Story Dependency Graph

```
S007-001 (application contracts + composition boundary)
    │
    ├──► S007-003 (CLI demo/query migration)
    │        │
    │        └──► S007-002 (API scan workflow migration)
    │                 │
    │                 ├──► S007-004 (ai_analysis → repository)
    │                 │        │
    │                 │        ├──► S007-005 (market_scanner migration)
    │                 │        │
    │                 │        └──► S007-006 (macro report generation)
    │                 │
    │                 └──► S007-007 (docs update, parallel advisory)
    │
S007-008 (layer gates) ◄──────────────────────────────────┘
    (depends on ALL above; final verification gate)
```

**Sequential pairs:**
- S007-001 must complete before all others (foundation: contracts + composition root).
- S007-003 (CLI) must complete before S007-002 (API) because CLI migration surfaces shared formatter/normalize helpers and exit-code behavior that API smoke tests rely on.
- S007-002 (API) must complete before S007-004/005/006 because the API routers are the largest consumers of the legacy workflows; once API is off legacy modules, we have confidence the ports and composition factories are stable.
- S007-004 must complete before S007-005/006 because the DuckDB/SQLite repository cleanup provides the stable persistence boundary that `ScanMarketUseCase` and `GenerateMacroReportUseCase` depend on.
- S007-008 must be last (verification gate).

**Parallel groups after dependencies are met:**
- S007-005 and S007-006 can run in parallel once S007-004 is done (disjoint legacy modules).
- S007-007 runs in parallel as documentation (advisory, no code dependencies).

**Legacy file deletion is NOT in this sprint.** All legacy files become thin re-export shims with `DeprecationWarning` in Sprint 007. Actual deletion is deferred to **Sprint 008** (or one release cycle later) after shim consumers are proven zero and regression evidence is captured.

---

## Files to Create (29 new files)

| # | Path | Description |
|---|------|-------------|
| 1 | `src/doge/application/__init__.py` | Package init |
| 2 | `src/doge/application/contracts/__init__.py` | DTO exports |
| 3 | `src/doge/application/contracts/request.py` | Input DTOs |
| 4 | `src/doge/application/contracts/response.py` | Output DTOs |
| 5 | `src/doge/application/use_cases/__init__.py` | Use case exports |
| 6 | `src/doge/application/use_cases/scan_market.py` | Scan orchestration |
| 7 | `src/doge/application/use_cases/generate_macro_report.py` | Macro report generation |
| 8 | `src/doge/application/use_cases/manage_notes.py` | Note CRUD |
| 9 | `src/doge/application/use_cases/query_ticker.py` | Composite ticker query |
| 10 | `src/doge/application/use_cases/generate_market_overview.py` | Market overview report |
| 11 | `src/doge/application/use_cases/generate_anomaly_report.py` | Anomaly report |
| 12 | `src/doge/application/use_cases/generate_catalog.py` | Catalog generation |
| 13 | `src/doge/application/use_cases/populate_stock_names.py` | Stock name batch fetch |
| 14 | `src/doge/application/use_cases/generate_industry_report.py` | Industry report |
| 15 | `src/doge/application/composition.py` | Canonical composition root (only application module allowed to import infrastructure) |
| 16 | `src/doge/core/ports/llm.py` | New `ILLMClient` port |
| 17 | `src/doge/infrastructure/llm/__init__.py` | Package init |
| 18 | `src/doge/infrastructure/llm/deepseek_client.py` | DeepSeek adapter |
| 19 | `src/doge/infrastructure/database/bootstrap.py` | System DB bootstrap |
| 20 | `src/doge/interfaces/api/main.py` | FastAPI canonical app factory |
| 21 | `src/doge/interfaces/api/routers/__init__.py` | Router exports |
| 22 | `src/doge/interfaces/api/routers/scan.py` | Scan router (use-case backed) |
| 23 | `src/doge/interfaces/api/routers/data.py` | Data router (use-case backed) |
| 24 | `src/doge/interfaces/api/routers/notes.py` | Notes router (use-case backed) |
| 25 | `src/doge/interfaces/api/routers/macro.py` | Macro router (use-case backed) |
| 26 | `src/doge/interfaces/api/routers/analysis.py` | Analysis router (use-case backed) |
| 27 | `src/doge/interfaces/api/routers/config.py` | Config router (use-case backed) |
| 28 | `src/doge/interfaces/cli/__init__.py` | CLI package init |
| 29 | `src/doge/interfaces/cli/main.py` | CLI canonical entrypoint |
| 30 | `src/doge/interfaces/cli/commands/__init__.py` | Command exports |
| 31 | `src/doge/interfaces/cli/commands/stock.py` | `stock` subcommand |
| 32 | `src/doge/interfaces/cli/commands/rsrs.py` | `rsrs` subcommand |
| 33 | `src/doge/interfaces/cli/commands/breadth.py` | `breadth` subcommand |
| 34 | `src/doge/interfaces/cli/commands/anomaly.py` | `anomaly` subcommand |
| 35 | `src/doge/interfaces/cli/commands/demo.py` | `demo` subcommand |
| 36 | `src/doge/interfaces/cli/commands/macro.py` | `macro` subcommand |
| 37 | `src/doge/interfaces/cli/formatters.py` | Shared table/markdown formatters |
| 38 | `src/doge/interfaces/cli/normalize.py` | Shared ticker normalization |
| 39 | `src/doge/interfaces/cli/constants.py` | Exit codes, bilingual strings |

## Files to Modify (10 files)

| # | Path | Change |
|---|------|--------|
| 1 | `src/doge/core/ports/__init__.py` | Add `ILLMClient` export |
| 2 | `src/doge/core/services/composition.py` | **Retire** as composition root; either delete or convert to re-export shim pointing to `doge.application.composition`. Core/services must not import infrastructure after this change. |
| 3 | `src/doge/core/services/anomaly_service.py` | Add `price_gaps()` and `consecutive_extremes()` |
| 4 | `src/doge/config/settings.py` | Add `network.proxy`, `deepseek_model` fields |
| 5 | `pyproject.toml` | Add `[project.scripts]` entry `doge = "doge.interfaces.cli.main:main"` |
| 6 | `src/doge/interfaces/api/deps.py` | Add `get_*_use_case()` providers that call `doge.application.composition` factories |
| 7 | `src/doge/interfaces/mcp/server.py` / `tools/*.py` | Retarget MCP tool construction from `doge.core.services.composition` to `doge.application.composition` |
| 8 | `docs/MODULARIZATION_PLAN.md` | Update with Sprint 007 story IDs and corrected batch sequencing |
| 9 | `src/doge/__init__.py` | Optional: expose canonical CLI entrypoint for `python -m doge` |
| 10 | `src/doge/interfaces/api/__init__.py` | Expose `app` factory if not already present |

## Files to Shim (21 files — kept for one release cycle, deleted in Sprint 008)

| # | Path | Shim Content |
|---|------|-------------|
| 1 | `src/api/main.py` | `from doge.interfaces.api.main import app` + `DeprecationWarning` |
| 2 | `src/api/routers/__init__.py` | Re-export from `doge.interfaces.api.routers` + `DeprecationWarning` |
| 3 | `src/api/routers/scan.py` | `from doge.interfaces.api.routers.scan import router` + `DeprecationWarning` |
| 4 | `src/api/routers/data.py` | `from doge.interfaces.api.routers.data import router` + `DeprecationWarning` |
| 5 | `src/api/routers/notes.py` | `from doge.interfaces.api.routers.notes import router` + `DeprecationWarning` |
| 6 | `src/api/routers/macro.py` | `from doge.interfaces.api.routers.macro import router` + `DeprecationWarning` |
| 7 | `src/api/routers/analysis.py` | `from doge.interfaces.api.routers.analysis import router` + `DeprecationWarning` |
| 8 | `src/api/routers/config.py` | `from doge.interfaces.api.routers.config import router` + `DeprecationWarning` |
| 9 | `src/cli.py` | `from doge.interfaces.cli import main` + `DeprecationWarning` |
| 10 | `src/macro/cli.py` | Redirect to `doge macro` subcommand + `DeprecationWarning` |
| 11 | `src/ai_analysis/__init__.py` | Re-export from `doge.config` / `doge.infrastructure.database` + `DeprecationWarning` |
| 12 | `src/micro/__init__.py` | Re-export nothing; package marker + `DeprecationWarning` |
| 13 | `src/micro/database.py` | Re-export from `doge.infrastructure.database` + `DeprecationWarning` |
| 14 | `src/micro/market_scanner.py` | Re-export `ScanMarketUseCase` wrapper + `DeprecationWarning` |
| 15 | `src/micro/momentum_scanner.py` | Re-export `RankingService` wrapper + `DeprecationWarning` |
| 16 | `src/micro/tdx_downloader.py` | Re-export `TDXDataSource` wrapper + `DeprecationWarning` |
| 17 | `src/micro/tdx_loader.py` | Re-export `tdx_local` adapter + `DeprecationWarning` |
| 18 | `src/micro/industry_analyzer.py` | Re-export `GenerateIndustryReportUseCase` wrapper + `DeprecationWarning` |
| 19 | `src/macro/__init__.py` | Re-export nothing; package marker + `DeprecationWarning` |
| 20 | `src/macro/config.py` | Re-export `doge.config.get_settings()` + `DeprecationWarning` |
| 21 | `src/macro/data_loader.py` | Re-export `GenerateMacroReportUseCase` wrapper + `DeprecationWarning` |
| 22 | `src/macro/strategist.py` | Re-export `DeepSeekClient` wrapper + `DeprecationWarning` |
| 23 | `src/macro/utils.py` | Re-export centralized logging config + `DeprecationWarning` |
| 24 | `src/interface/dashboard.py` | Delegate to use cases; preserve import-time PyQt side effects |
| 25 | `src/interface/scanner_gui.py` | Delegate to use cases |
| 26 | `src/interface/analysis_gui.py` | Delegate to use cases |

## Legacy Files to Delete (deferred to Sprint 008)

The following files become **shims in Sprint 007** and are deleted in Sprint 008 only after:
- All live callers are proven to import from `doge.*` paths.
- Regression evidence shows zero consumer references.
- A dedicated "legacy deletion" story in Sprint 008 is approved.

| # | Path | Sprint 007 Disposition | Sprint 008 Condition |
|---|------|------------------------|----------------------|
| 1 | `src/micro/__init__.py` | shim | zero consumers |
| 2 | `src/micro/database.py` | shim | zero consumers |
| 3 | `src/micro/market_scanner.py` | shim | `ScanMarketUseCase` tested and stable |
| 4 | `src/micro/momentum_scanner.py` | shim | `RankingService` consumers migrated |
| 5 | `src/micro/tdx_downloader.py` | shim | CLI demo no longer references it |
| 6 | `src/micro/tdx_loader.py` | shim | local-file fallback decision made |
| 7 | `src/micro/industry_analyzer.py` | shim | `GenerateIndustryReportUseCase` stable |
| 8 | `src/macro/__init__.py` | shim | zero consumers |
| 9 | `src/macro/config.py` | shim | callers use `Settings` |
| 10 | `src/macro/data_loader.py` | shim | `GenerateMacroReportUseCase` stable |
| 11 | `src/macro/strategist.py` | shim | `DeepSeekClient` adapter stable |
| 12 | `src/macro/utils.py` | shim | centralized logging config adopted |
| 13 | `src/ai_analysis/anomaly_detection.py` | shim | `GenerateAnomalyReportUseCase` stable |
| 14 | `src/ai_analysis/catalog_generator.py` | shim | `GenerateCatalogUseCase` stable |
| 15 | `src/ai_analysis/fetch_names.py` | shim | `PopulateStockNamesUseCase` stable |
| 16 | `src/ai_analysis/market_overview.py` | shim | `GenerateMarketOverviewUseCase` stable |
| 17 | `src/ai_analysis/stock_notes.py` | shim | `ManageNotesUseCase` stable |
| 18 | `src/api/main.py` | shim | `doge.interfaces.api.main` adopted |
| 19 | `src/api/routers/*.py` | shim | API tests retargeted |
| 20 | `src/cli.py` | shim | `doge` console script adopted |
| 21 | `src/interface/__init__.py` | shim | GUI shims no longer needed |
| 22 | `src/interface/dashboard.py` | shim | PyQt GUI fully retargeted |
| 23 | `src/interface/scanner_gui.py` | shim | PyQt GUI fully retargeted |
| 24 | `src/interface/analysis_gui.py` | shim | PyQt GUI fully retargeted |

---

## New Test Files to Create

| Test File | Coverage | Gate Level |
|-----------|----------|------------|
| `tests/unit/application/contracts/test_dtos.py` | Frozen dataclass immutability, default values, field coverage | BLOCKING |
| `tests/unit/application/use_cases/test_scan_market.py` | Mock `IStockRepository` + `IMarketDataSource`, verify orchestration, `StorageWriteError` path | BLOCKING |
| `tests/unit/application/use_cases/test_generate_macro_report.py` | Mock `IMarketViewRepository` + `ILLMClient` + `IReportRepository`, prompt building, LLM failure, persist failure | BLOCKING |
| `tests/unit/application/use_cases/test_manage_notes.py` | Mock `INoteRepository`, all 8 operations, validation errors, DTO mapping | BLOCKING |
| `tests/unit/application/use_cases/test_query_ticker.py` | Mock `IStockRepository` + `INoteRepository` + `ITickerMetadataSource`, composite assembly, partial failure | BLOCKING |
| `tests/unit/application/use_cases/test_generate_market_overview.py` | Mock services, Markdown formatting | BLOCKING |
| `tests/unit/application/use_cases/test_generate_anomaly_report.py` | Mock `AnomalyService` (extended), Markdown formatting | BLOCKING |
| `tests/unit/core/ports/test_llm_port.py` | Verify `ILLMClient` is abstract, `DeepSeekClient` instantiation | BLOCKING |
| `tests/unit/infrastructure/test_deepseek_client.py` | Mock `openai`, API key missing path, failure path, success path | BLOCKING |
| `tests/unit/layer_gates/test_interface_import_gate.py` | Grep-based: zero forbidden imports in `src/doge/interfaces/` | BLOCKING |
| `tests/integration/test_scan_end_to_end.py` | Real TDX files + SQLite, compare row counts to pre-migration | BLOCKING |
| `tests/cli/test_cli_exit_codes.py` | Exit 0/1/2 for all commands | BLOCKING |
| `tests/cli/test_bilingual_output.py` | Grep-based: all preserved Chinese/English strings present | BLOCKING |

---

*End of Sprint 007 Modularization Plan*
