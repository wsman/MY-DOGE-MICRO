# CDD: PyQt Desktop Dashboard (Module #10)

> **Module #10** — Category: **Presentation**
> **Slug**: `pyqt-desktop-dashboard`
> **Status**: Reverse-documented (brownfield) — 2026-06-12; BUG E smoke test added 2026-06-12
> **Depends on**: #4 `macro-strategy-engine`, #5 `micro-momentum-scanner`, #6 `ai-industry-analysis`
> **Depended on by**: (terminal Presentation surface — nothing depends on this module)
> **Source files reverse-documented**: `src/interface/dashboard.py` (the `CommandCenter` shell + tab orchestration), `src/interface/scanner_gui.py` (scanner/macro launcher panel + QThread workers), `src/interface/db_editor.py` (the SQLite table editor), `src/interface/analysis_gui.py` (industry-analysis launcher)
> **Related ADRs**: [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) (forbidden patterns this module still violates), [ADR-0002](../../docs/architecture/adr-0002-centralized-configuration.md) (config centralization). **No new ADR** — the desktop composition is a brownfield UI layout, not an architectural stance; ADR-0001 governs the migration direction and is referenced in §6/§8.

---

## 1. Overview

The PyQt Desktop Dashboard is the local-first operator surface of MY-DOGE-MICRO: a single PyQt6 `QMainWindow` (`CommandCenter`, `dashboard.py:30-117`) that hosts five tabs and is the only way to drive a full scan/analyze/archive cycle without a browser or a CLI. Tab 1 (ScannerWidget, `scanner_gui.py:124-317`) launches CN/US market scans and the macro strategy run on background `QThread`s and streams progress to a log panel. Tabs 2–4 (three `DBEditorWidget` instances, `db_editor.py:119-377`) bind `QSqlTableModel` to the three local SQLite databases — `market_data_cn.db`, `market_data_us.db`, `research_insights.db` — for in-place editing, search, add/delete, and post-scan refresh. Tab 5 (AnalysisWidget, `analysis_gui.py:71-227`) launches the AI industry analysis (`IndustryAnalyzer`) on a background `QThread`, injects the operator-chosen LLM profile via environment variables, and renders the generated Markdown report. The module is the heaviest ADR-0001 offender in the project (hardcoded conda Qt6 DLL path, four `sys.path.insert/append` sites, sibling imports, two duplicate `start_scan` definitions, monkey-patching of `builtins.print`, and direct LLM/market modules reached from a Presentation layer) — all flagged in §5/§8 as migration targets, none changed in this reverse-documentation pass.

## 2. User Promise / JTBD

**Operator's job**: "From one local desktop window, kick off my weekly market-data refresh (CN + US), run the macro strategy read, watch progress scroll by, then immediately edit and search the resulting SQLite tables and launch the AI industry write-up — all without leaving the app, and without the UI freezing while a multi-thousand-ticker scan runs."

**The module must reliably**:
- Keep the UI responsive during scans: long-running TDX scans, yfinance fetches, and LLM calls run on `QThread` workers (`scanner_gui.py:34,88`; `analysis_gui.py:17`), with progress and log lines streamed back to the main thread via Qt signals.
- Lock the relevant DB-editor tab while its underlying database is being written by a scan, then auto-refresh and switch to it when the scan completes (`dashboard.py:85-117`) — so the operator never edits a half-written DB.
- Persist the operator's TDX root path across sessions (`scanner_gui.py:242-278`, `user_settings.json`) and let them pick which LLM profile drives the analysis (`analysis_gui.py:151-177`, `models_config.json`).
- Degrade locally: a missing database, a failed TDX path, or an LLM error must surface as a log/QMessageBox message, not crash the window.
- Run entirely against local SQLite files and (optionally) the operator's configured network endpoints; there is no server dependency for the dashboard itself.

**The module does NOT yet keep** (open questions, §9): clean-architecture routing (it imports `src/macro.*`, `src.micro.*`, and `src.ai_analysis` directly from the Presentation layer — ADR-0001 violation), a single canonical config source (it reads `models_config.json` + `user_settings.json` + the macro config's env overrides), structured logging (it uses `print` and `QTextEdit.append`), or a single source of truth for the `start_scan` method (it is defined twice in `scanner_gui.py`).

## 3. Detailed Behavior

All `file:line` citations are against the brownfield state on the `cdd-adoption-2026-06-11` branch.

### 3.1 The four source files and their responsibilities

| File | Class(es) | Responsibility | Cross-ref |
|---|---|---|---|
| `src/interface/dashboard.py` | `CommandCenter(QMainWindow)` | Top-level shell: tab assembly, cross-tab signal wiring (scan-start/finish → lock/unlock + refresh + jump-to-tab), DLL bootstrap, app entrypoint | §3.2 |
| `src/interface/scanner_gui.py` | `ScannerWidget(QWidget)`, `ScannerWorker(QThread)`, `MacroWorker(QThread)` | Tab 1: TDX-path config, CN/US scan launch + progress, macro-strategy launch; settings persistence; **two** duplicate `start_scan` definitions | §3.3 |
| `src/interface/db_editor.py` | `DBEditorWidget(QWidget)`, `AddRecordDialog(QDialog)` | Tabs 2–4: SQLite table view/edit via `QSqlTableModel`; open/refresh/save/add/delete; simple LIKE search; safe connection cleanup | §3.4 |
| `src/interface/analysis_gui.py` | `AnalysisWidget(QWidget)`, `AnalysisWorker(QThread)` | Tab 5: LLM-profile selection, auto-fill of latest macro/CSV paths, `IndustryAnalyzer` launch, Markdown report rendering | §3.5 |

### 3.2 The shell — `CommandCenter` (`dashboard.py`)

- **DLL bootstrap** (`dashboard.py:6-15`): at module import time, before any PyQt6 import, hardcodes `qt6_bin_path = r"E:\LLMs\miniconda3\Lib\site-packages\PyQt6\Qt6\bin"` and, if it exists on disk, prepends it to `PATH` and calls `os.add_dll_directory(...)`. This is a Windows-conda-specific, machine-hardcoded workaround (the developer's machine) — a portability blocker (open question). It prints a check-mark / warning to stdout.
- **Module-level path mutation** (`dashboard.py:22-23`): `sys.path.append(current_dir)` so the sibling imports `from scanner_gui import ...`, `from db_editor import ...`, `from analysis_gui import ...` (`dashboard.py:26-28`) resolve. ADR-0001 `sys_path_append` violation.
- **`CommandCenter.__init__`** (`dashboard.py:31-86`):
  - `setWindowTitle("MY-DOGE QUANT SYSTEM")`, `resize(1000, 700)` (`dashboard.py:34-35`).
  - Builds a `QTabWidget` with a stylesheet (`dashboard.py:49-54`) and adds exactly **five** tabs in this order (`dashboard.py:58-82`):
    1. `🚀 市场扫描 (Scanner)` → `ScannerWidget()`
    2. `🇨🇳 A股档案 (CN Data)` → `DBEditorWidget(connection_name="conn_cn_market")`, then `load_database(<project>/data/market_data_cn.db)`
    3. `🇺🇸 美股档案 (US Data)` → `DBEditorWidget(connection_name="conn_us_market")`, `market_data_us.db`
    4. `🧠 研报智库 (Insights)` → `DBEditorWidget(connection_name="conn_insights")`, `research_insights.db`
    5. `🔎 行业扫描 (Analysis)` → `AnalysisWidget()`
  - The DB paths are computed by walking two parents up from the interface dir (`dashboard.py:64,70,76`): `os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'data', '<name>.db')`. `_PROJECT_ROOT`-style recalculation — ADR-0001 drift.
  - **Cross-tab wiring** (`dashboard.py:85-86`): the ScannerWidget's `scan_started_signal(mode)` → `CommandCenter.lock_editor_tab`; `scan_finished_signal(mode)` → `CommandCenter.unlock_and_refresh`.
- **`lock_editor_tab(mode)`** (`dashboard.py:88-97`): for `'CN'`/`'US'`, disables the matching editor tab, relabels it `… (写入中...)` ("writing…").
- **`unlock_and_refresh(mode)`** (`dashboard.py:99-117`): re-enables the tab, restores its label, calls `refresh_data()` on the editor, and `setCurrentWidget(...)` to jump the operator to the freshly-written table.
- **Entrypoint** (`dashboard.py:119-138`, `if __name__ == "__main__"`): calls `initialize_system_dbs()` (Module #2) with an `ImportError` fallback that re-appends `src/micro` to `sys.path` (`dashboard.py:122-126` — another ADR-0001 violation), then `QApplication`, sets the global font to `Microsoft YaHei 9` (`dashboard.py:133-134`), shows the window, `sys.exit(app.exec())`.

### 3.3 Tab 1 — Scanner + Macro launcher (`scanner_gui.py`)

- **Path bootstrap** (`scanner_gui.py:8-18`): computes `project_root` by three `dirname` calls and `sys.path.insert(0, project_root)`. Then imports the backends directly from the Presentation layer — ADR-0001 `cross_layer_import` violation:
  - `from src.micro.market_scanner import MarketScanner` (Module #5/3)
  - `from src.macro.config import MacroConfig`, `from src.macro.data_loader import GlobalMacroLoader`, `from src.macro.strategist import DeepSeekStrategist` (Module #4)
  - On `ImportError`, prints `❌ 严重导入错误` and continues (the import error is swallowed, not raised — `scanner_gui.py:28-31`).
- **`ScannerWorker(QThread)`** (`scanner_gui.py:88-122`): constructs `MarketScanner(tdx_root)`; on `mode=='CN'` calls `scanner.scan_cn_market(db_path, callback)`, on `'US'` calls `scan_us_market(...)` (Module #5/3). Progress is forwarded via `progress_signal.emit(pct, msg)`; per-ticker and final exceptions are caught and logged; `scan_finished_signal.emit(mode)` always fires (in `finally`, `scanner_gui.py:120-122`) so the UI never stays locked.
- **`MacroWorker(QThread)`** (`scanner_gui.py:34-86`): the full Module #4 workflow on a background thread — `MacroConfig()` → `GlobalMacroLoader(config).fetch_combined_data()` → `calculate_metrics(...)` → `DeepSeekStrategist(config).generate_strategy_report(...)` → `save_macro_report(...)` (Module #2). Risk string and volatility string are extracted for the DB row (`scanner_gui.py:64-66`). Always emits `finished_signal` (`scanner_gui.py:86`).
- **`ScannerWidget(QWidget)`** (`scanner_gui.py:124-317`):
  - Custom Qt signals `scan_started_signal = pyqtSignal(str)` and `scan_finished_signal = pyqtSignal(str)` (`scanner_gui.py:126-127`) — the contract `CommandCenter` wires to.
  - UI (`create_ui`, `scanner_gui.py:138-189`): TDX-root `QLineEdit` with a default of `r"D:\Games\New Tdx Vip2020"` (machine-hardcoded default — open question), a Browse button, three colored scan buttons (`启动 A股扫描`, `启动 美股扫描`, `启动宏观分析`), a `QProgressBar`, a status `QLabel`, and a read-only `QTextEdit` log.
  - `start_scan(mode)` is defined **twice** (`scanner_gui.py:195-215` and `scanner_gui.py:287-317`). Python keeps the **second** definition, so the first is dead code. The live (second) version: saves settings, computes the DB path under `<project>/data/` creating the dir if missing (`scanner_gui.py:296-302`), disables all three scan buttons, emits `scan_started_signal`, constructs and starts a `ScannerWorker`, wiring `log_signal`, `progress_signal`, `scan_finished_signal`. The dead (first) version lacks the settings save and the `btn_macro` lock — a real bug-class duplication tracked in §5/§8.
  - `start_macro_scan()` (`scanner_gui.py:230-240`): disables all three buttons, starts a `MacroWorker`, wires `log_signal` + `finished_signal`.
  - `on_worker_finished(mode)` / `on_macro_finished()` (`scanner_gui.py:222-228,280-285`): re-enable buttons and forward `scan_finished_signal` to `CommandCenter`.
  - `load_settings()` / `save_settings()` (`scanner_gui.py:242-278`): read/write `<project_root>/user_settings.json` for the `tdx_path` key; bare `except:` on the read-back merge (`scanner_gui.py:269-270`) — error swallowing, open question.

### 3.4 Tabs 2–4 — SQLite editor (`db_editor.py`)

- **`DBEditorWidget(connection_name=None)`** (`db_editor.py:119-377`): a generic SQLite table editor parameterized by a Qt SQL connection name. Three instances are created by `CommandCenter` with distinct names (`conn_cn_market`, `conn_us_market`, `conn_insights`).
- **`load_database(db_path)`** (`db_editor.py:192-218`): clears the current model, then **reuses** the named connection if `QSqlDatabase.contains(connection_name)` (creating it once, only re-`setDatabaseName`-ing if the path changed) — so repeated calls during a scan refresh do not leak connections. Opens the DB; on failure shows `QMessageBox.critical` with `lastError().text()`. Loads the table list.
- **`on_table_changed(table_name)`** (`db_editor.py:247-269`): builds a `QSqlTableModel` bound to the connection, `select()`s it, sets it on the `QTableView`, `resizeColumnsToContents()`. Errors → `QMessageBox.critical`.
- **Editing**: double-click or selected-click edit triggers (`db_editor.py:170`); `save_changes()` → `submitAll()` (`db_editor.py:279-292`); `add_record()` opens `AddRecordDialog` (`db_editor.py:294-305`); `delete_selected()` removes rows back-to-front then `submitAll()` with a confirmation `QMessageBox.question` (`db_editor.py:307-337`).
- **`apply_search_filter()`** (`db_editor.py:339-363`): a **simple** filter — takes the table's first field name and applies `LIKE '%<text>%'`. This is a string-interpolated SQL filter, but it is passed to `QSqlTableModel.setFilter`, which parameterizes via Qt's SQL driver rather than executing the raw string; it is still single-column only and a UX limitation (open question).
- **`closeEvent`** (`db_editor.py:365-376`): clears the model, closes the connection, `QSqlDatabase.removeDatabase(connection_name)` — the canonical Qt cleanup pattern that prevents the "connection still in use" warning.
- **`AddRecordDialog`** (`db_editor.py:13-117`): introspects the table's `QSqlRecord` to build a `QFormLayout`. Special-cases the `insights.full_content` field as a `QTextEdit` with a file-import button (`db_editor.py:45-58`); auto-fills `created_at` with `datetime.now()` and marks it read-only (`db_editor.py:61-65`); the import button offers overwrite-vs-append when the field is non-empty (`db_editor.py:99-114`).

### 3.5 Tab 5 — Industry analysis launcher (`analysis_gui.py`)

- **Path bootstrap** (`analysis_gui.py:11-13`): appends `src/micro` to `sys.path` and imports `from industry_analyzer import IndustryAnalyzer` (Module #6's current home, per Module #5 §3.8). ADR-0001 violation.
- **`AnalysisWorker(QThread)`** (`analysis_gui.py:17-69`):
  - Injects the chosen LLM profile into the process environment before constructing the analyzer (`analysis_gui.py:31-33`): `os.environ["DEEPSEEK_API_KEY"] = profile["api_key"]`, `os.environ["DEEPSEEK_MODEL"] = profile["model"]`. This is the same env-override path Module #4's `MacroConfig` honors (`config.py:163-176`, per the macro CDD §3.1) — it lets the GUI switch models without touching `models_config.json`. **ADR-0001 layer-boundary concern (`cross_layer_state_write` — a CDD-local label; ADR-0001 captures this under its general layer-boundary stance rather than naming this exact identifier)**: mutating `os.environ` from a worker thread mutates process-global state.
  - **Monkey-patches `builtins.print`** (`analysis_gui.py:38-46`) for the duration of `analyzer.run_analysis()` so that the analyzer's `print`-based logging is captured into the GUI log panel via `log_signal.emit(msg)`; restores the original `print` afterward. This is brittle (not thread-safe, breaks if the worker is interrupted) — open question.
  - After the run, globs `<project>/research_report/*.md`, picks the newest by `getctime`, reads it, and emits `result_signal(content, filename)` (`analysis_gui.py:58-66`). Errors are caught and logged, **not** re-raised — `run_analysis` failure shows only as a log line.
- **`AnalysisWidget(QWidget)`** (`analysis_gui.py:71-227`):
  - `init_ui` (`analysis_gui.py:79-128`): a fixed-height "战术配置面板" with a model-profile `QComboBox` and a "🚀 执行全景扫描" button; a row of three file pickers (macro `.md`, CN `.csv`, US `.csv`); a center `QTextEdit` report viewer (`setMarkdown`-rendered); a fixed-height log panel.
  - `load_config_profiles()` (`analysis_gui.py:151-177`): reads `<project>/models_config.json`, populates the combo with each `profiles[*]` entry (storing the whole profile dict as the item's userData), and sets the default to `default_profile`. This is the operator-facing model-switcher — the same `models_config.json` Module #4 reads.
  - `auto_fill_paths()` (`analysis_gui.py:183-200`): globs the newest `macro_report/*.md`, `micro_report/Top200_Momentum_CN_*.csv`, `micro_report/Top200_Momentum_US_*.csv` and pre-fills the pickers. **Note the path drift**: the picker looks in `micro_report/` but Module #5's scanner writes the CSV to the project root (Module #5 §3.6 step 10, open question 3) — so auto-fill finds nothing unless the operator manually copies the CSVs.
  - `start_analysis()` (`analysis_gui.py:202-222`): reads the three paths, gets the selected profile (bails with a log line if none), disables the run button, starts the `AnalysisWorker`. `result_signal` → `display_report` which calls `report_viewer.setMarkdown(content)` (`analysis_gui.py:224-226`).

## 4. Contracts / Data Model

### 4.1 Qt-signal contract (the only inter-module contract this module defines)

| Signal | Emitter | Payload | Consumer | Effect |
|---|---|---|---|---|
| `scan_started_signal(str)` | `ScannerWidget` (`scanner_gui.py:126`) | `'CN'` or `'US'` | `CommandCenter.lock_editor_tab` (`dashboard.py:85`) | Disable + relabel the matching editor tab |
| `scan_finished_signal(str)` | `ScannerWidget` (`scanner_gui.py:127`) | `'CN'` or `'US'` | `CommandCenter.unlock_and_refresh` (`dashboard.py:86`) | Re-enable + refresh + jump-to-tab |
| `log_signal(str)` | all three workers | log line text | the panel's `QTextEdit.append` | Append to the log view |
| `progress_signal(int, str)` | `ScannerWorker` (`scanner_gui.py:90`) | percent, status msg | `ScannerWidget.update_progress` | Set progress bar + status label |
| `result_signal(str, str)` | `AnalysisWorker` (`analysis_gui.py:19`) | markdown content, filename | `AnalysisWidget.display_report` | Render report |
| `finished_signal()` | `MacroWorker` (`scanner_gui.py:36`) | none | `ScannerWidget.on_macro_finished` | Re-enable buttons |

### 4.2 Files read/written (local-first data surface)

| Path | Read/Write | Owner in this module | Source |
|---|---|---|---|
| `data/market_data_cn.db` | R/W (open via QSqlDatabase, scanned via ScannerWorker) | `DBEditorWidget` + `ScannerWorker` | `dashboard.py:64-65`, `scanner_gui.py:293-302` |
| `data/market_data_us.db` | R/W | same | `dashboard.py:69-71` |
| `data/research_insights.db` | R/W | `DBEditorWidget` (insights tab) | `dashboard.py:75-77` |
| `user_settings.json` | R/W | `ScannerWidget.load/save_settings` | `scanner_gui.py:245,260` |
| `models_config.json` | R | `AnalysisWidget.load_config_profiles` | `analysis_gui.py:153` |
| `macro_report/*.md` | R (auto-fill) | `AnalysisWidget.auto_fill_paths` | `analysis_gui.py:188` |
| `micro_report/Top200_Momentum_*.csv` | R (auto-fill) | `AnalysisWidget.auto_fill_paths` | `analysis_gui.py:192-197` |
| `research_report/*.md` | R (post-run pickup) | `AnalysisWorker.run` | `analysis_gui.py:60-66` |

### 4.3 Backend call sites (Presentation → Core/Feature — ADR-0001 violations today)

| Backend (module) | Call site in this module | What it does |
|---|---|---|
| `src.micro.market_scanner.MarketScanner` (#5/#3) | `scanner_gui.py:22,105` | CN/US TDX scan → writes `stock_prices` |
| `src.macro.config.MacroConfig` (#4) | `scanner_gui.py:25,42` | Load LLM + macro config |
| `src.macro.data_loader.GlobalMacroLoader` (#4) | `scanner_gui.py:26,47-52` | yfinance fetch + metrics |
| `src.macro.strategist.DeepSeekStrategist` (#4) | `scanner_gui.py:27,56-58` | LLM macro report + archive + DB row |
| `src.micro.database.save_macro_report` (#2) | `scanner_gui.py:70-77` | Persist the macro report row |
| `src.micro.database.initialize_system_dbs` (#2) | `dashboard.py:122-128` | Entrypoint DB self-check |
| `industry_analyzer.IndustryAnalyzer` (#6) | `analysis_gui.py:15,36,53` | AI industry report |

### 4.4 Inputs / outputs

- **Inputs**: operator mouse/keyboard (button clicks, file dialogs, line edits, combo selection). No CLI args to the dashboard itself.
- **Outputs**: SQLite writes (via `submitAll` and via the backend scan/macro/analysis workers); log lines in `QTextEdit`s; rendered Markdown in the report viewer. **No stdout contract** — the dashboard prints to stdout only for the DLL bootstrap banner and via the captured `print` in `AnalysisWorker`.

### 4.5 Error behavior (Current State)

- DB open failure → `QMessageBox.critical` with `lastError().text()`, return without raising (`db_editor.py:213-215`).
- Table-load / refresh / save / delete failure → `QMessageBox.critical`, no raise (`db_editor.py:244-245,268-269,276-277,290-292,335-337`).
- Backend import failure at module load → swallowed `print` (`scanner_gui.py:28-31`) — the dashboard imports but the scan buttons will fail at click time with `NameError`.
- Scan exception → caught in `ScannerWorker.run`, logged, `scan_finished_signal` still emitted (`scanner_gui.py:118-122`).
- Macro exception → caught in `MacroWorker.run`, logged, `finished_signal` still emitted (`scanner_gui.py:83-86`).
- Analysis exception → caught in `AnalysisWorker.run`, logged, **no** result signal emitted (`analysis_gui.py:68-69`) — the run button is re-enabled via the `worker.finished` Qt signal (`analysis_gui.py:221`), but the report viewer stays empty with no error banner.
- Settings load failure → bare `except:` swallows the error, prints to stdout (`scanner_gui.py:269-270`).

### 4.6 Registry proposals (BLOCKING Phase 5 — enumerated, not written)

> Routing follows the macro/micro CDD convention: cross-ADR stances → `architecture.yaml`; concrete values → a future constants/entities registry (which does not yet exist).

**(a) `architecture.yaml` candidates (stances/port contracts):**
- `pyqt.threading_model` = long-running scans/LLM calls on `QThread`; UI updates only via `pyqtSignal` (the architectural stance this module already implements correctly and that ADR-0001 §Validation Criteria implies for UI responsiveness).
- `pyqt.forbidden_direct_backend_import` — Presentation-layer modules (`src/interface/*`) MUST NOT import `src/macro.*`, `src.micro.*`, or `src.ai_analysis` directly; they must route through services/ports once the clean-architecture migration (#12) provides them. (This is the ADR-0001 stance this module currently violates — registering it makes the violation machine-checkable.)

**(b) Value-constant candidates (NOT architecture.yaml):**
- `pyqt.default_window_size` = `1000 × 700` (`dashboard.py:35`).
- `pyqt.default_tdx_path` = `r"D:\Games\New Tdx Vip2020"` (`scanner_gui.py:145`) — **machine-hardcoded**, migration target.
- `pyqt.dll_bootstrap_path` = `r"E:\LLMs\miniconda3\Lib\site-packages\PyQt6\Qt6\bin"` (`dashboard.py:6`) — **machine-hardcoded**, migration target.
- `pyqt.tab_count` = 5 (`dashboard.py:58-82`; asserted by the smoke test).
- `pyqt.db_connection_names` = `conn_cn_market`, `conn_us_market`, `conn_insights` (`dashboard.py:62,69,75`).
- `pyqt.settings_file` = `user_settings.json` (`scanner_gui.py:245`).
- `pyqt.analysis_csv_search_dir` = `micro_report/` (`analysis_gui.py:192-197`) — **drifts** from Module #5's project-root write path (open question).

> **OPEN QUESTION (registry design):** `docs/registry/entities.yaml` does not exist (same blocker as Modules #3/#4/#5). Group (b) proposals stay enumerated here only.

## 5. Edge Cases

| Situation | What happens (Current State) |
|---|---|
| **PyQt6 not installed** | Smoke test `pytest.importorskip("PyQt6")` skips; the dashboard cannot run. ADVISORY gate — does not break CI. |
| **PyQt6 installed but Qt6 DLLs cannot load (headless / DLL-mismatch)** | Smoke test skips with a clear reason via the `qapp` fixture's importability probe (`tests/test_pyqt_smoke.py`). The dashboard itself would crash on `from PyQt6.QtWidgets import ...` at import time. |
| **`dashboard.py:6` DLL path does not exist on this machine** | Bootstrap prints `⚠️ Qt6 DLL path not found` (`dashboard.py:14-15`) and continues; PyQt6 import then succeeds or fails depending on the system `PATH`. On the developer's machine it succeeds; elsewhere it may not. |
| **`data/*.db` missing at construction** | `load_database` opens it via QSqlDatabase — SQLite creates an empty file on open if missing; the table list is empty → `QMessageBox.information("数据库中没有表。")` (`db_editor.py:242-243`). No crash. |
| **`data/` directory missing** | `ScannerWidget.start_scan` creates it with `os.makedirs(data_dir, exist_ok=True)` (`scanner_gui.py:299-300`) before computing the DB path. The three editor tabs at construction time, however, do **not** create the dir — they just fail to open and show the critical message box. |
| **Operator clicks two scan buttons rapidly** | The live `start_scan` disables all three scan buttons before starting the worker (`scanner_gui.py:305-307`), so a second click is impossible until `on_worker_finished` re-enables them. The dead first `start_scan` did **not** lock the macro button — a latent bug masked by the duplication (open question). |
| **Scan fails mid-run** | `ScannerWorker.run` catches the exception, logs it, and emits `scan_finished_signal` in `finally` (`scanner_gui.py:118-122`) — the editor tab is unlocked and refreshed (showing whatever was written before the failure). |
| **Macro run fails** | `MacroWorker.run` catches, logs, emits `finished_signal` (`scanner_gui.py:83-86`) — buttons re-enable. No macro report is written; the operator must re-run. |
| **Analysis run fails** | `AnalysisWorker.run` catches the exception (`analysis_gui.py:68-69`) and logs via the captured `print`→`log_signal`, but **never** emits `result_signal`. The run button re-enables via the `worker.finished` Qt signal (`analysis_gui.py:221`), so the report viewer keeps showing the appended `⏳ 正在初始化 AI 引擎…` line (`analysis_gui.py:216` — appended text set via `report_viewer.append(...)`, not the `setPlaceholderText` value at `analysis_gui.py:113`) because `display_report` is never called. No error banner is shown (open question). |
| **Operator switches the LLM profile mid-session** | `AnalysisWorker` mutates `DEEPSEEK_API_KEY`/`DEEPSEEK_MODEL` for the whole process (`analysis_gui.py:31-33`). A concurrent macro run in `MacroWorker` (which constructs a fresh `MacroConfig()` reading the same env) would pick up the analysis profile's values — a process-global cross-talk risk (`cross_layer_state_write` — a CDD-local label for an ADR-0001 layer-boundary concern; ADR-0001 does not name this exact identifier). |
| **`AnalysisWorker` interrupted (window closed mid-run)** | `builtins.print` is left monkey-patched because the restore at `analysis_gui.py:56` is only reached on the happy path, not on exception or thread termination (open question). |
| **Two `DBEditorWidget` instances target the same DB file** | Each uses a distinct `connection_name` (`dashboard.py:62,69,75`), so Qt keeps them as separate connections — no clash. But the macro insights DB and the insights editor tab can both be open during a scan: the editor is locked via `scan_started_signal` only for CN/US scans, **not** for the macro or analysis runs that also write `research_insights.db` (open question). |
| **`models_config.json` absent** | `AnalysisWidget.load_config_profiles` logs `⚠️ 未找到 models_config.json` and the combo stays empty; clicking "执行全景扫描" bails with `❌ 未选择有效的模型配置` (`analysis_gui.py:155,209-211`). |
| **`micro_report/Top200_*.csv` absent (Module #5 path drift)** | `auto_fill_paths` silently leaves the pickers empty (`analysis_gui.py:192-197` — the `except Exception: pass` at `analysis_gui.py:199-200` swallows the glob miss). The operator must use the `...` browse buttons. |
| **`user_settings.json` malformed** | `load_settings` catches and prints (`scanner_gui.py:254-255`); `save_settings` bare-`except:` swallows the read error (`scanner_gui.py:269-270`) and proceeds to overwrite — potential data loss (open question). |
| **Operator edits a table while a scan writes the same DB** | Prevented for CN/US market DBs by the tab-lock wiring (`dashboard.py:85-117`). **Not** prevented for `research_insights.db` during a macro or analysis run (see above). |

## 6. Dependencies

**Upstream (this module depends on):**
- **#4 `macro-strategy-engine`** — `ScannerWidget.start_macro_scan` → `MacroWorker` constructs `MacroConfig`, `GlobalMacroLoader`, `DeepSeekStrategist` directly (`scanner_gui.py:25-27,42-58`). The GUI is the operator-facing trigger for the macro workflow; `MacroConfig` honors the `DEEPSEEK_*` env overrides the `AnalysisWorker` sets. The macro CDD (#4 §6 downstream) lists this module as a dependent.
- **#5 `micro-momentum-scanner`** — `ScannerWorker` constructs `MarketScanner(tdx_root)` and calls `scan_cn_market`/`scan_us_market` (`scanner_gui.py:22,105-113`), which write the Top-200 scan into `stock_prices` and (transitively) produce the CSVs `AnalysisWidget.auto_fill_paths` looks for. The micro CDD (#5 §6 downstream) lists this module as a dependent.
- **#6 `ai-industry-analysis`** — `AnalysisWorker` constructs `IndustryAnalyzer` and calls `run_analysis()` (`analysis_gui.py:36,53`). IndustryAnalyzer is currently housed in `src/micro/industry_analyzer.py` (per Module #5 §3.8); Phase 5 will relocate/rename it. This module imports it via a `sys.path` append to `src/micro` (`analysis_gui.py:13`).
- **#1 `runtime-configuration`** — indirectly, via `MacroConfig` (Module #4) and the `DEEPSEEK_*` env mutation. The dashboard does **not** read `Settings()` directly today (ADR-0002 drift).
- **#2 `market-data-storage`** — `DBEditorWidget` opens the three local SQLite DBs via `QSqlDatabase`; `dashboard.py:122-128` calls `initialize_system_dbs()` at entrypoint; `MacroWorker` calls `save_macro_report`.
- **Python packages**: `PyQt6` (`QtWidgets`, `QtCore`, `QtGui`, `QtSql`), `sqlite3` (transitively via Qt SQL), `datetime`, `json`, `threading` (transitively), `glob`, `os`, `sys`, `builtins`.

**Downstream (depend on this module):**
- None. This is a terminal Presentation surface. (The web console #11 and the FastAPI service #9 are sibling Presentation/Interface surfaces, not dependents.)

**Bidirectional notes (per design-docs rule):**
- The macro CDD (#4 §6) MUST list `pyqt-desktop-dashboard` as a dependent (it does: "Module #10 PyQt Desktop Dashboard — the GUI triggers macro runs").
- The micro CDD (#5 §6) MUST list `pyqt-desktop-dashboard` as a dependent (it does: "#10 pyqt-desktop-dashboard — the operator UI launches scans and surfaces the Top-200 / industry reports").
- The Module #6 CDD (`ai-industry-analysis`, Phase 5) MUST list this module as a dependent when authored.

**Docs / ADRs:**
- [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) — governs the layer boundary; this module's `sys_path_insert/append` (`dashboard.py:23`, `scanner_gui.py:17`, `analysis_gui.py:13`, `dashboard.py:125`), `_PROJECT_ROOT` recalculation (`dashboard.py:64,70,76`; `scanner_gui.py:11-13,296`), `cross_layer_import` of Core/Feature backends from the Presentation layer, and `cross_layer_state_write` (a CDD-local label; ADR-0001 captures this under its general layer-boundary stance without naming that exact identifier) via `os.environ` mutation (`analysis_gui.py:31-33`) are all forbidden patterns flagged for migration (§8).
- [ADR-0002](../../docs/architecture/adr-0002-centralized-configuration.md) — config centralization; this module reads `user_settings.json` + `models_config.json` + the macro env-override path, none of which route through `Settings()`.
- **No new ADR** — the desktop composition (QMainWindow + 5 tabs + QThread workers) is a brownfield UI layout decision, not an architectural stance worth a dedicated ADR. ADR-0001 already captures the migration direction.

## 7. Configuration Knobs

> **Config drift note**: the dashboard reads from **three** config surfaces today — (a) `user_settings.json` (TDX path, GUI-local), (b) `models_config.json` (LLM profiles, shared with Module #4/#6), and (c) the macro config's `DEEPSEEK_*` env overrides (mutated at runtime by `AnalysisWorker`). None route through `Settings()` (ADR-0002 drift). Two values are **machine-hardcoded** to the developer's Windows box and are portability blockers.

| Knob | Default | Valid range / type | Owner (Current) | Env owner | Operational risk |
|---|---|---|---|---|---|
| `QT_QPA_PLATFORM` | (unset → `windows`) | `"offscreen"` for headless/test | operator env / test | operator env | **LOW** in test (the smoke test forces `offscreen`); **HIGH** if an operator tries to run on a headless server without setting it. |
| `qt6_bin_path` (DLL bootstrap) | `r"E:\LLMs\miniconda3\Lib\site-packages\PyQt6\Qt6\bin"` | absolute Windows path | **HARDCODED** (`dashboard.py:6`) | (not env) | **CRITICAL** portability blocker — the dashboard will not import PyQt6 on any machine whose conda root differs. Migration target: remove entirely once PyQt6 is `pip install`-ed normally. |
| Default TDX root (UI default) | `r"D:\Games\New Tdx Vip2020"` | absolute Windows path | **HARDCODED** (`scanner_gui.py:145`) | (not env) | **HIGH** — operator-specific; the real path is read back from `user_settings.json` on startup if present (`scanner_gui.py:242-253`), so this is only the first-run default. |
| `tdx_path` (persisted) | (last-used) | absolute Windows path | `user_settings.json` | (not env) | LOW — survives across sessions; bare-`except` on read-back (`scanner_gui.py:269-270`) could mask corruption. |
| LLM profile (analysis tab) | `models_config.json:default_profile` | profile name ∈ `profiles[*].name` | `models_config.json` + GUI combo | (mutated into `DEEPSEEK_*` by `AnalysisWorker`) | **MEDIUM** — selecting a profile mutates process-global env for the run; concurrent macro runs cross-talk (open question). |
| Window size | `1000 × 700` | wxh px | **HARDCODED** (`dashboard.py:35`) | (not env) | LOW — operator can resize at runtime; not persisted. |
| Tab count | `5` | int (fixed) | **HARDCODED** (`dashboard.py:58-82`) | (not env) | LOW — asserted by the smoke test. |
| Global font | `Microsoft YaHei 9` | Qt font string | **HARDCODED** (`dashboard.py:133-134`) | (not env) | LOW — affects only rendering; font may be absent on non-Windows. |

**Migration target (vs Current State):**
- *Current State*: three config files + two machine-hardcoded paths + runtime env mutation, none centralized.
- *Target (Migration)*: window/scan settings live in `Settings().desktop.*` (ADR-0002); LLM profile selection routes through the Module #4 service port (not direct `os.environ` mutation); `qt6_bin_path` and the default TDX path are removed in favor of a `pip install`-ed PyQt6 and a `Settings().paths.tdx_root` sourced from env or config; `user_settings.json` becomes a thin GUI preference overlay on top of `Settings()`.

## 8. Acceptance Criteria

**Smoke test (BUG E — RESOLVED):**
- [x] `tests/test_pyqt_smoke.py` exists, sets `QT_QPA_PLATFORM=offscreen` before any PyQt6 import, uses `pytest.importorskip("PyQt6")`, and skips cleanly with a clear reason when PyQt6 is installed but its DLLs cannot load — `tests/test_pyqt_smoke.py`.
- [x] `python -m pytest tests/test_pyqt_smoke.py -q` exits `0` in this environment (`1 skipped in 0.02s`, skip reason "PyQt6 is installed but its native Qt6 DLLs cannot load…"). On a Windows box with a working PyQt6 install, the test constructs `CommandCenter`, asserts `windowTitle() == "MY-DOGE QUANT SYSTEM"` and `tabs.count() == 5`, and closes the window.
- [x] A construct-failure of `CommandCenter` is NOT masked by the skip — the skip only fires on import-time environment problems (`tests/test_pyqt_smoke.py` `_pyqt6_is_importable` probe + `qapp` fixture).

**Contract / data model:**
- [ ] `CommandCenter` constructs exactly five tabs in the documented order (Scanner, CN, US, Insights, Analysis) — partially covered by the smoke test's `tabs.count() == 5` assertion; the order/labels are manual-verify OPEN.
- [ ] `scan_started_signal('CN')` disables the CN editor tab and relabels it `(写入中...)`; `scan_finished_signal('CN')` re-enables, refreshes, and switches to it (manual/interaction test — OPEN; requires a working PyQt6 env).
- [ ] `DBEditorWidget.load_database` reuses the named `QSqlDatabase` connection across calls (does not leak) — fixture interaction test OPEN.
- [ ] `AnalysisWorker` mutates `DEEPSEEK_API_KEY`/`DEEPSEEK_MODEL` from the selected profile before constructing `IndustryAnalyzer` — verified by code reading (`analysis_gui.py:31-33`); regression test OPEN.

**Workflow:**
- [ ] On a Windows box with PyQt6 + the local DBs present, launching `python src/interface/dashboard.py` opens the window and all five tabs render without error (manual smoke — OPEN; ADVISORY gate).
- [ ] A CN scan launched from Tab 1 streams progress to the log panel, locks Tab 2, and on completion refreshes Tab 2 and switches to it (manual — OPEN; ADVISORY gate).

**Migration / remediation (ADR-0001 / ADR-0002 — OPEN, owned by #12):**
- [ ] `dashboard.py:6-15` machine-hardcoded `qt6_bin_path` removed — rely on a `pip install`-ed PyQt6.
- [ ] `dashboard.py:23`, `scanner_gui.py:17`, `analysis_gui.py:13`, `dashboard.py:125` `sys.path` mutations removed — routed through `Settings()` or a package install.
- [ ] `dashboard.py:64,70,76` and `scanner_gui.py:11-13,296` `_PROJECT_ROOT` recalculation replaced by `Settings().paths.*`.
- [ ] `scanner_gui.py:22-27` and `analysis_gui.py:15` direct imports of `src.macro.*` / `src.micro.*` replaced by service-port calls once the clean-architecture migration (#12) provides them.
- [ ] `scanner_gui.py:195-215` dead duplicate `start_scan` removed — keep only the second definition.
- [ ] `analysis_gui.py:31-33` `os.environ` mutation replaced by passing the profile to the analysis service explicitly (no process-global write).
- [ ] `analysis_gui.py:38-56` `builtins.print` monkey-patch replaced by a structured logging callback (or an `IndustryAnalyzer` log-handler injection).
- [ ] `scanner_gui.py:269-270` bare `except:` replaced by a typed exception + log line.
- [ ] Analysis tab's `auto_fill_paths` CSV search dir aligned with Module #5's actual CSV write path (resolve the `micro_report/` vs project-root drift — same open question as Module #5 §9.3).
- [ ] DB-editor tab lock extended to cover macro and analysis runs (which also write `research_insights.db`), not just CN/US market scans.

**Docs / observability:**
- [x] This CDD reproduces the dashboard's tab structure, signal contract, and backend call sites with real `file:line` citations (done, §3/§4).
- [ ] Registry proposals in §4.6 are queued for Phase 5 entry approval.

## 9. Open Questions (aspirational — flagged for Phase 5 reconciliation)

1. **Machine-hardcoded `qt6_bin_path`** (`dashboard.py:6`) — the dashboard will not import on any machine whose conda root differs from `E:\LLMs\miniconda3`. Remove in favor of a normal `pip install PyQt6` (ADR-0001).
2. **Dead duplicate `start_scan`** (`scanner_gui.py:195-215` vs `:287-317`) — Python keeps the second; the first is unreachable and lacks the macro-button lock. Delete the dead copy and confirm the live copy is complete.
3. **`builtins.print` monkey-patch in `AnalysisWorker`** (`analysis_gui.py:38-56`) — not restored on exception or thread termination; not thread-safe. Replace with a logging handler injected into `IndustryAnalyzer`.
4. **Process-global env mutation** (`analysis_gui.py:31-33`) — concurrent macro and analysis runs cross-talk via `DEEPSEEK_*`. Pass the profile explicitly to the analysis service.
5. **DB-editor lock scope** — only CN/US market scans lock their editor tab (`dashboard.py:85-86`); macro and analysis runs that write `research_insights.db` do not lock the Insights tab. Extend the signal contract or add macro/analysis lock signals.
6. **Analysis failure UX** — on `AnalysisWorker` exception, `result_signal` is never emitted, so the report viewer keeps showing the appended `⏳ 正在初始化 AI 引擎…` line (`analysis_gui.py:216`) with no error banner (`analysis_gui.py:68-69`). Add an explicit error state.
7. **CSV path drift (recurring)** — `auto_fill_paths` looks in `micro_report/` (`analysis_gui.py:192-197`) but Module #5 writes to the project root (Module #5 §3.6 step 10). Resolve alongside Module #5 open question 3.
8. **`user_settings.json` bare `except:`** (`scanner_gui.py:269-270`) — could overwrite corrupted settings silently. Use a typed exception + backup-and-recover.
9. **No `__init__.py` in `src/interface/`** — sibling imports (`from scanner_gui import ...`) force the `sys.path` hacks. A package layout would let the dashboard import its tabs normally.
10. **Direct Core/Feature imports from Presentation** — the single biggest ADR-0001 violation cluster (`scanner_gui.py:22-27`, `analysis_gui.py:15`). Blocked on Module #12 providing service ports; until then this module cannot migrate.
11. **Settings persistence scope** — only `tdx_path` is persisted (`user_settings.json`). Window size, last-selected LLM profile, and last-active tab are not. Decide whether to expand `user_settings.json` or move all GUI prefs under `Settings().desktop.*`.
