# CDD: Micro Momentum Scanner (Module #5)

> **Module #5** — Category: **Core**
> **Slug**: `micro-momentum-scanner`
> **Status**: Reverse-documented (brownfield) — 2026-06-11; BUG E fixed + tests added 2026-06-11
> **Depends on**: #1 `runtime-configuration`, #2 `market-data-storage`, #3 `data-sources`
> **Depended on by**: #6 `ai-industry-analysis`, #9 `fastapi-service`, #10 `pyqt-desktop-dashboard`
> **Source files reverse-documented**: `src/micro/momentum_scanner.py` (**owns the canonical RSRS formula at `momentum_scanner.py:47-71`**), `src/micro/market_scanner.py`, `src/micro/industry_analyzer.py`
> **Related ADRs**: [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) (clean architecture, forbidden patterns), [ADR-0002](../../docs/architecture/adr-0002-centralized-configuration.md) (config centralization). **No new ADR** — RSRS is a product/algorithm decision, not architecture.

---

## 1. Overview

Micro Momentum Scanner is the Core module that ranks the strongest-trending A-share and US-equity names from the local price database and emits a Top-200 momentum CSV per market. It owns the **canonical RSRS (Resistance Support Relative Strength) trend-strength indicator** — the single source of truth for the `R_squared × sign(slope)` formula at `src/micro/momentum_scanner.py:47-71`, reproduced verbatim in Section 4. The module also owns the two supporting pieces of the micro workflow: (a) `src/micro/market_scanner.py` — the data-ingestion driver that scans a local TDX `vipdoc` tree (CN `sh/sz`, US `ds`), prefers a TDX server sync and falls back to local `.day` files, writes into the `stock_prices` table owned by Module #2, and refreshes the DuckDB analytical views; and (b) `src/micro/industry_analyzer.py` — a downstream enrichment step (conceptually closer to Module #6) that reads the Top-200 CSVs, calibrates each ticker's name/sector via `yfinance.Ticker().info` with a local JSON cache and retries, then calls a DeepSeek LLM to produce an "industry prosperity" Markdown report persisted to the research DB. The module is mid-migration: it still contains direct `sqlite3.connect`, `sys.path.insert`, and per-file `_PROJECT_ROOT` recalculation (ADR-0001 forbidden patterns), all flagged in Section 8 as migration targets.

## 2. User Promise / JTBD

**Operator JTBD**: "Every week (or on demand), point the platform at my freshly synced market data, compute a clean, bias-free ranking of the names that are trending strongest — strong meaning *trend structure* (high R²) and *direction* (slope sign), not just raw gain — and hand me a Top-200 CSV plus an AI-curated industry read that says *which sectors* those winners cluster in and whether the move is institutional (RSRS > 0.8) or speculative."

**The module must reliably**:
- Produce a deterministic, reproducible RSRS score in `[-1.0, 1.0]` for every liquid-enough ticker, computed identically whether by the scalar path (`calculate_rsrs`) or the vectorized batch path (`_calculate_rsrs_vectorized`).
- Filter the investable universe per market: CN liquidity floor (avg 60-day amount ≥ RMB 200M), US liquidity floor (≥ USD 20M), CN code whitelist `^(00|30|60|68)`, US leveraged-ETF blacklist (~50 tickers), and a 60-day price-surge circuit breaker (> +400% → rejected as a bad tick).
- Rank survivors by 60-day percent change, keep the top 200, attach the RSRS score, and persist a timestamped CSV.
- Tolerate offline/degraded operation: TDX-server-first with automatic local-file fallback (no crash when no server is reachable); DuckDB view refresh failures are non-fatal.
- Hand the CSV off to the industry analyzer without re-implementing ranking logic.

**The module does NOT yet keep** (open questions, Section 9): env-overridable thresholds, structured logging, or service-layer wrapping for MCP/API consumption. (Single-source config was RESOLVED by S002-008/TR-019 — see §3.2.)

## 3. Detailed Behavior

### 3.1 The three source files and their responsibilities

| File | Class(es) | Responsibility | Cross-ref |
|---|---|---|---|
| `src/micro/momentum_scanner.py` | `MomentumRanker` | Owns the canonical RSRS formula, config load, SQLite read of the last 180 days of `stock_prices`, candidate filtering, vectorized RSRS, CSV emission | Section 3.2–3.6 |
| `src/micro/market_scanner.py` | `MarketScanner`, module fns `_refresh_duckdb_views`, `_tdx_server_sync` | CN/US data ingestion from local TDX files with TDX-server-first sync; writes to `stock_prices`; refreshes DuckDB views | Section 3.7 |
| `src/micro/industry_analyzer.py` | `IndustryAnalyzer` | CSV → metadata calibration → DeepSeek prompt → Markdown report → research DB | Section 3.8 (consumed by Module #6) |

### 3.2 Configuration load (`MomentumRanker._load_config`, `momentum_scanner.py`)

- **S002-008 / TR-019 RESOLVED**: the scanner now reads `get_settings().market` (`src/doge/config/settings.py` `MarketConfig`) as the **single source of truth** for all scanner filters. The `models_config.json` `scanner_filters` block is removed from both the live (gitignored) config and the tracked template; a drift guard (`tests/contract/test_scanner_filter_drift_guard.py`) fails if any production module reintroduces the `scanner_filters` key-read.
- `_load_config` builds and returns a **dict VIEW** over `MarketConfig` (not a copy of `models_config.json`), preserving the legacy key names so existing call sites (`self.config.get('us_blacklist'/'rsrs_window'/'max_change_pct')` in `analyze_market`) keep working unchanged. The mapping: `MarketConfig.us_blacklist` (tuple) → `us_blacklist` (list); `cn_min_volume` → `min_volume_cn`; `us_min_volume` → `min_volume_us`; `max_change_pct` → `max_change_pct`; `rsrs_window` → `rsrs_window`; `cn_universe_prefixes` → `cn_universe_prefixes`.
- Canonical filter values (all on `MarketConfig`, `src/doge/config/settings.py`):
  - `us_blacklist`: ~52 leveraged/inverse ETF tickers (`SQQQ`, `TQQQ`, `SOXL`, ... `BITX`) — stored as a `tuple[str, ...]` (frozen-dataclass constraint), converted to `list` at the call site.
  - `cn_min_volume`: `200_000_000` (RMB), `us_min_volume`: `20_000_000` (USD).
  - `max_change_pct`: `400` (60-day surge circuit breaker, US-only).
  - `rsrs_window`: `18`.
  - `cn_universe_prefixes`: `("00","30","60","68")` — A-share investable-code prefixes, consumed by `analyze_market`'s CN whitelist (no longer hardcoded inline).

### 3.3 Canonical RSRS — scalar path (`MomentumRanker.calculate_rsrs`, `momentum_scanner.py:47-71`)

Reproduced verbatim (post BUG-E fix) in Section 4. Behavior summary:
- Input: a `pandas.Series` of prices (typically daily close) and a `window` (default 18).
- **Length guard** (`momentum_scanner.py:53-54`): if `len(series) < window`, return `0.0` immediately (no regression attempted). This is the `(d)` acceptance case.
- **Zero-variance guard** (`momentum_scanner.py:56-60`, added by BUG-E fix): if the variance of the last `window` bars is `≤ 1e-10` (flat series), return `0.0`. Without this guard `scipy.stats.linregress` returns `rvalue=nan` for zero-variance y, producing `nan` instead of `0.0` and diverging from the vectorized path.
- Otherwise: take `y = series.iloc[-window:].values`, `x = arange(len(y))`, run `scipy.stats.linregress(x, y)`, compute `r_sq = float(r_value) ** 2`, `sign = 1.0 if float(slope) > 0 else -1.0`, return `r_sq * sign`.
- **Defensive nan guard** (`momentum_scanner.py:71`): `return 0.0 if trend_strength != trend_strength else trend_strength` (the `x != x` nan test) so any residual nan is mapped to `0.0`.
- The whole body is wrapped in `try/except Exception: return 0.0` (`momentum_scanner.py:52, 69-72`) — any unexpected error (non-numeric input, etc.) returns `0.0` rather than raising.

### 3.4 Vectorized batch path (`MomentumRanker._calculate_rsrs_vectorized`, `momentum_scanner.py:73-115`)

A closed-form reimplementation of `R² × sign(slope)` over an `(N_stocks, window)` numpy matrix, used for the per-scan Top-200 computation. Mathematically identical to the scalar path; numerically agrees to float epsilon (acceptance case `(e)`, `tests/test_momentum_scanner.py::test_vectorized_path_matches_scalar_path`). Key steps:
- Empty-matrix guard → returns `np.array([])` (`momentum_scanner.py:81-82`).
- `x = arange(T)`, `x_dev = x - x.mean()`, `x_var = sum(x_dev²)` (scalar denominator).
- `slope = dot(y_dev, x_dev) / x_var` (`momentum_scanner.py:97-99`).
- `r_sq = cov_xy² / (x_var * y_var)` with a `valid_mask = y_var > 1e-10` guard so flat rows get `r_sq=0` (`momentum_scanner.py:101-110`).
- `rsrs = r_sq * np.sign(slope)`; `np.sign(0)=0` so flat rows yield exactly `0.0` (`momentum_scanner.py:112-115`).

### 3.5 Self-check (`MomentumRanker.test_rsrs_accuracy`, `momentum_scanner.py:117-140`)

A non-pytest self-check: generates 100×18 random data with `np.random.seed(42)`, runs both paths, prints `[OK]`/`[ERR]` with the max diff, and returns it. Threshold for "pass" is `max_diff < 1e-6`. This is the manual precursor of acceptance case `(e)`; the new `tests/test_momentum_scanner.py` is the regression-test form.

### 3.6 Market analysis workflow (`MomentumRanker.analyze_market`, `momentum_scanner.py:149-304`)

Entry point used by `main()` (`momentum_scanner.py:306-316`) which scans CN (`market_data_cn.db`, amount threshold `2e8`) then US (`market_data_us.db`, `2e7`). Step-by-step:

1. Resolve config: `min_vol = amount_threshold` (the positional arg, **not** overridden by config — `momentum_scanner.py:153` comment "保留原参数，不做覆盖逻辑，以保持兼容"); `blacklist`, `window`, `max_change_pct` from config (`momentum_scanner.py:154-156`).
2. Open SQLite via `get_connection(db_name)` (`momentum_scanner.py:142-147`); returns early if the DB file is missing.
3. `SELECT MAX(date) FROM stock_prices`; early-return if empty (`momentum_scanner.py:165-170`).
4. Load the last **180 calendar days**: `WHERE date >= date('{max_date}', '-180 days')` ordered `ticker, date ASC` into a DataFrame (`momentum_scanner.py:174-180`).
5. Group by ticker; for each group:
   - Require `len(group) >= 61` (enough data for a 60-day change) (`momentum_scanner.py:203`).
   - CN whitelist: raw code (strip `.<market>`) must start with `00|30|60|68` (`momentum_scanner.py:215-219`).
   - US: skip blacklisted tickers; a 5+ char heuristic is present but inert (`pass` — `momentum_scanner.py:206-213`).
   - Liquidity: `avg_amt = group['amount'].tail(60).mean() < min_vol → skip` (`momentum_scanner.py:221-223`).
   - 60-day change: `change_pct = (p_curr - p_prev)/p_prev*100` where `p_prev = group.iloc[-61]['close']`; skip if `p_prev == 0` (`momentum_scanner.py:225-232`).
   - US surge breaker: `change_pct > max_change_pct → skip` (`momentum_scanner.py:234-236`).
   - Collect `recent_prices = group['close'].values[-window:]`; skip if `< window` (defensive, `momentum_scanner.py:238-244`).
   - Append to `candidates_prices` (matrix rows) and `candidates_meta` dicts (`momentum_scanner.py:246-258`).
6. If no candidates: print `[WARN]` and return (`momentum_scanner.py:261-263`).
7. Vectorized RSRS: `price_matrix = np.array(candidates_prices)` → `_calculate_rsrs_vectorized` → write `rsrs_z` into each meta (`momentum_scanner.py:265-275`).
8. Sort by `change_percent` desc, take top 200 (`momentum_scanner.py:278-280`).
9. Filename dates: `file_end = max(global_end_dates)` (latest), `file_start = mode(global_start_dates)` (most common start, filters suspended-stock noise) via `collections.Counter` (`momentum_scanner.py:285-296`).
10. Write CSV `Top200_Momentum_<MARKET>_<start>-<end>.csv` to **project root** (not `micro_report/`) with columns `ticker, price_60d_ago, price_current, change_percent, avg_daily_volume, rsrs_z` (`momentum_scanner.py:297-301`). **Path drift (default-discovery path only)**: the industry analyzer's default-discovery path looks for these CSVs in `<project_root>/micro_report/` (`industry_analyzer.py:222`), so manual copies or a path fix are required for the two to chain *via auto-discovery*. Explicit `run_analysis(cn_path=..., us_path=...)` (`industry_analyzer.py:251,268-276`) bypasses the glob and reads the project-root CSV directly (open question).
11. Print top-1 summary (`momentum_scanner.py:303-304`).

### 3.7 Data ingestion driver (`src/micro/market_scanner.py`)

> This file is shared with Module #3 (data-sources) — it is the active ingestion writer for `stock_prices`. Documented here for the micro workflow; the data-source contracts live in the `data-sources` CDD.

- **ADR-0001 violations (Current State)**: `sys.path.append(current_dir)` (`market_scanner.py:10-11`), `sys.path.insert(0, _PROJECT_ROOT)` (`market_scanner.py:24-26`) — both forbidden patterns, both migration targets.
- `MarketScanner.__init__(tdx_root)` (`market_scanner.py:71-81`): auto-corrects the path to a `vipdoc` child if missing; constructs a `TDXReader(tdx_root)` (Module #3).
- `scan_cn_market(db_path, progress_callback=None, use_server=True)` (`market_scanner.py:83-148`):
  - `init_db_custom(db_path)` (Module #2).
  - Walks `sh` + `sz` `lday` dirs, globs `<market>*.day`, parses code from filename, applies the CN whitelist `^(00|30|60|68)` len-6 filter, builds `"<code>.<SH|SZ>"` tickers (`market_scanner.py:96-109`).
  - **Server-first**: if `use_server`, call `_tdx_server_sync(...)`; on success, refresh DuckDB views and return (`market_scanner.py:115-122`).
  - **Local fallback**: per-ticker `self.reader.get_data(ticker, 'cn')` → add `ticker` col → `save_stock_data_custom(df, db_path)`; per-ticker errors are swallowed (`pass`) (`market_scanner.py:125-138`).
  - Progress callback every 50 tickers (`market_scanner.py:141-142`); final `_refresh_duckdb_views()` (`market_scanner.py:148`).
- `scan_us_market(db_path, progress_callback=None, use_server=True)` (`market_scanner.py:150-212`): mirrors CN but reads `<tdx_root>/ds/lday/*.day`, strips the `74#AAPL`-style prefix, keeps pure-letter codes excluding `HK` (`market_scanner.py:162-175`).
- `_tdx_server_sync(db_path, market, tickers, progress_callback)` (`market_scanner.py:41-68`): wraps `find_working_server` + `download_{cn,us}_kline` from `tdx_downloader`; on `ImportError` (opentdx missing) or any exception, prints and returns `False` → caller falls back to local files. Non-fatal by design.
- `_refresh_duckdb_views()` (`market_scanner.py:29-38`): calls `src.ai_analysis.connect_duckdb` + `run_views_sql(con)`; failures are caught and printed as `[WARN] (non-fatal)`.

### 3.8 Industry enrichment (`src/micro/industry_analyzer.py`) — Module #6 boundary

This file is the bridge from Module #5's CSV output to Module #6 (AI Industry Analysis). It is owned conceptually by Module #6 (the assignment brief flags it as "to be reconciled/renamed Phase 5; has NO LLM client" — note: it **does** construct a `DeepSeekStrategist` and call `client.chat.completions.create`, `industry_analyzer.py:38-39, 329-336`; the "no LLM client" note likely refers to the missing clean-architecture LLM *port*, not the absence of any LLM call). Behavior summary (full detail deferred to the Module #6 CDD):

- Reads `Top200_Momentum_<MARKET>_*.csv` from `<project_root>/micro_report/` (`industry_analyzer.py:219-228`); takes top 50 per market.
- `get_stock_metadata(ticker)` (`industry_analyzer.py:176-217`): checks a local `data/meta_cache.json` cache (thread-safe via `RLock`, atomically written via temp-file + `shutil.move`), else calls `yfinance.Ticker(<remapped>).info` for `shortName`/`sector`, with 3 retries (2s backoff). Sets `HTTP_PROXY`/`HTTPS_PROXY` from a constructor `proxy` arg (`industry_analyzer.py:48-51`) — process-global side effect.
- `_format_stock_line` (`industry_analyzer.py:66-79`): annotates RSRS > 0.8 with a `[HOT]` marker — **this is where the RSRS > 0.8 institutional-trend threshold is consumed**.
- `run_analysis(...)` (`industry_analyzer.py:251-398`): builds a Chinese-language DeepSeek prompt embedding the macro context + the top-50 CN/US formatted lines + the RSRS interpretation rubric ("> 0.8 strong institutional; < 0.3 speculative"), calls the LLM, strips a `TITLE:` line for a semantic title, saves the report to `research_report/report_by_<model>_<ts>.md`, snapshots newly-fetched company data to `data/company_snapshots/`, and archives via `save_research_report(...)` into the research DB (Module #2/#7).

## 4. Contracts / Data Model

### 4.1 Canonical RSRS formula — VERBATIM (`src/micro/momentum_scanner.py:47-71`)

This is the single source of truth. The DuckDB views `vw_rsrs_ranking_cn/us` (Module #2, `data/views.sql:114-122`) reproduce it in SQL **modulo the zero-slope sign convention, which is masked by the zero-variance guard** (see note below); this Python implementation is authoritative.

> **Sign convention — UNIFIED on the zero-boundary (OQ-11 RESOLVED, TR-016, S002-001, 2026-06-12):** The zero-slope sign convention is unified to **sign(slope) = +1 when slope >= 0, -1 otherwise**, across the Python scalar path (`momentum_scanner.py:72` — `sign = 1.0 if float(slope) >= 0 else -1.0`) and the vectorized path (`momentum_scanner.py:121` — `np.where(slope >= 0, 1.0, -1.0)`). The DuckDB-SQL view already uses `CASE WHEN COALESCE(REGR_SLOPE(rn, close), 0) >= 0 THEN 1 ELSE -1 END`, so the zero→+1 boundary matches at the sign-helper level. **For any zero-slope series (palindromic / symmetric) R² is necessarily 0, so the RSRS product is 0.0 under all three implementations — the zero-boundary convention is therefore moot for the product value, but it is pinned for consistency and to prevent the sign helper itself from diverging.** Enforced by `tests/unit/momentum/test_rsrs_parity.py` and `tests/unit/momentum/test_rsrs_sign_unit.py`.
>
> **BLOCKER (separate, NOT closed by S002-001 — discovered during the S002-001 parity test, 2026-06-12):** the DuckDB view `vw_rsrs_ranking_cn/us` computes `ROW_NUMBER() OVER (... ORDER BY date DESC) AS rn` (rn=1 is newest) and then `REGR_SLOPE(rn, close)`, whose sign is INVERTED relative to the Python scalar path (`x = arange(0..17)` oldest→newest) for every monotonic series. Empirically, a perfectly increasing series yields RSRS **−1.0** from the view but **+1.0** from Python. This is independent of the zero-boundary convention above (it affects all monotonic series, not just zero-slope) and requires a `data/views.sql` rn-ordering change plus a view re-materialization to fix — out of scope for S002-001 (the view is gitignored and owned by the market-data-storage refresh path). Tracked as a follow-up; pinned by the strict `xfail` in `tests/migration/test_rsrs_view_sign_convention.py::test_perfectly_increasing_view_is_positive_one`.

**Signature**

```python
def calculate_rsrs(self, series, window=18):
```

**Variables**

| Variable | Type | Definition |
|---|---|---|
| `series` | `pandas.Series` | Input price series (typically daily `close`). Assumed time-ordered ascending; only the **last `window` bars** are used. |
| `window` | `int`, default `18` | Regression lookback length. The default `18` is owned here and mirrored by `Settings().market.rsrs_window` (Module #1) and the DuckDB RSRS view (`REGR_*` over 18 bars). |
| `y` | `numpy.ndarray` | `series.iloc[-window:].values` — the most recent `window` prices. |
| `x` | `numpy.ndarray` | `np.arange(len(y))` — integer time index `0, 1, ..., window-1`. |
| `slope` | `float` | OLS slope of `y` on `x` from `scipy.stats.linregress`. |
| `intercept` | `float` | OLS intercept (unused in the score). |
| `r_value` | `float` | Pearson correlation coefficient from `linregress`. **`nan` when `y` has zero variance** — hence the zero-variance guard. |
| `p_value` | `float` | Two-sided p-value (unused). |
| `std_err` | `float` | Standard error of the slope (unused). |
| `R_squared` (`r_sq`) | `float` | `float(r_value) ** 2` — coefficient of determination ∈ `[0, 1]`. |
| `sign` | `float` | `1.0 if float(slope) >= 0 else -1.0` — zero slope maps to `+1.0` (S002-001 unified convention, matching the vectorized `np.where(slope >= 0, 1.0, -1.0)` path and the DuckDB-SQL `CASE WHEN ... >= 0 THEN 1` view). For the flat-series case the zero-variance guard at evaluation order 2 already returned `0.0` before the sign is computed, so the sign convention only matters for the degenerate zero-slope-with-nonzero-variance edge case. |

**Formula**

```
RSRS(series, window) = R_squared × sign(slope)
                     = (r_value²) × sign(slope_of_y_on_time)
```

- **Range**: `[-1.0, 1.0]`.
  - `+1.0` ⟺ perfect positive linear fit (slope > 0, `r_value = +1`).
  - `-1.0` ⟺ perfect negative linear fit (slope < 0, `r_value = -1`).
  - `0.0` ⟺ no trend (flat series, or `r_value ≈ 0`).
- **Method**: ordinary least squares via `scipy.stats.linregress(x, y)` (`momentum_scanner.py:60`), which uses the standard closed-form `slope = cov(x,y)/var(x)`, `r_value = cov(x,y)/(σ_x·σ_y)`.

**Guards (in evaluation order)**

1. `len(series) < window` → return `0.0` (`momentum_scanner.py:53-54`).
2. `np.var(y) ≤ 1e-10` (flat / zero variance) → return `0.0` (`momentum_scanner.py:56-60`, **BUG-E fix**). Matches the vectorized `y_var > 1e-10` guard.
3. Any `Exception` → return `0.0` (`momentum_scanner.py:69-72`).
4. Residual `nan` product → return `0.0` (`momentum_scanner.py:71`, `x != x` test).

**Verbatim source (post BUG-E fix)**

```python
def calculate_rsrs(self, series, window=18):
    """
    计算趋势强度 (RSRS 替代指标)
    返回: -1.0 ~ 1.0 (R2 * Sign(Slope))
    """
    try:
        if len(series) < window:
            return 0.0

        # 取最近 window 天的数据
        y = series.iloc[-window:].values
        x = np.arange(len(y))

        # 零方差 (flat) 保护：linregress 在 y 无方差时返回 rvalue=nan，
        # 会导致趋势强度为 nan。向量化路径 (_calculate_rsrs_vectorized)
        # 通过 y_var > 1e-10 保护此情形并返回 0.0；此处与之一致，
        # 保证标量与向量化两条路径在 flat 输入上行为相同 (BUG E)。
        if float(np.var(y)) <= 1e-10:
            return 0.0

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # R2 * Slope符号
        # 显式转换类型以消除 Pylance 警告
        r_sq = float(r_value) ** 2
        sign = 1.0 if float(slope) > 0 else -1.0

        trend_strength = r_sq * sign
        # 防御：即使经过方差检查，极端输入仍可能产生 nan。
        return 0.0 if trend_strength != trend_strength else trend_strength
    except Exception as e:
        # print(f"[WARN] RSRS计算异常: {e}")
        return 0.0
```

**Vectorized equivalent (`_calculate_rsrs_vectorized`, `momentum_scanner.py:73-115`)** — closed form over an `(N, T)` matrix:

```
slope_i    = dot(y_i - mean(y_i), x_dev) / x_var
r_sq_i     = dot(...)² / (x_var · y_var_i)        # only where y_var_i > 1e-10, else 0
rsrs_i     = r_sq_i · sign(slope_i)
```

**Worked numeric example (window = 4 for readability)**

Take a strictly increasing series `y = [1, 2, 3, 4]`, `x = [0, 1, 2, 3]`.

- Means: `mean(x) = 1.5`, `mean(y) = 2.5`.
- `x_dev = [-1.5, -0.5, 0.5, 1.5]`; `y_dev = [-1.5, -0.5, 0.5, 1.5]`.
- `cov(x,y) = Σ x_dev·y_dev = 2.25 + 0.25 + 0.25 + 2.25 = 5.0`.
- `var(x) = Σ x_dev² = 2.25 + 0.25 + 0.25 + 2.25 = 5.0` → `slope = 5.0 / 5.0 = 1.0` (> 0, so `sign = +1.0`).
- `r_value = cov(x,y) / (σ_x·σ_y)`. Here `x_dev == y_dev`, so `r_value = 1.0`, `R_squared = 1.0`.
- `RSRS = 1.0 × (+1.0) = +1.0`.

(Verified empirically: `MomentumRanker().calculate_rsrs(pd.Series([1.,2.,3.,4.]), window=4)` returns `1.0`.) For a flat series `[5,5,5,5]` the zero-variance guard fires → `0.0`. For `[4,3,2,1]` → `slope = -1.0`, `r_value = -1.0`, `RSRS = -1.0`. With `window=18` (default) and a perfect linear ramp, the same logic yields `±1.0`.

### 4.2 Top-200 CSV schema (`momentum_scanner.py:300`)

```csv
ticker, price_60d_ago, price_current, change_percent, avg_daily_volume, rsrs_z
```

- `rsrs_z`: the RSRS score rounded to 2 decimals (column name is historical — it is **not** a z-score; it is the `R²×sign(slope)` value, see open question).
- `avg_daily_volume`: 60-day mean of the `amount` column (turnover in market currency), rounded to 0 decimals.
- `change_percent`: 60-day percent change, rounded to 2 decimals.
- Filename: `Top200_Momentum_<CN|US>_<YYYYMMDD_start>-<YYYYMMDD_end>.csv`, written to **project root** (not `micro_report/`) — see open question on path drift. **Drift is on the default-discovery path only**: `industry_analyzer.run_analysis(cn_path=..., us_path=...)` (`industry_analyzer.py:251,268-276`) consumes explicit CSV paths directly via `_process_csv`, bypassing the `micro_report/` glob — so the two modules chain without a copy if the caller passes paths; only the auto-discovery default (`load_momentum_data` → `micro_report/`, `industry_analyzer.py:222`) diverges.

### 4.3 Inputs (`analyze_market`)

| Param | Type | Source | Notes |
|---|---|---|---|
| `market_type` | `"CN"` \| `"US"` | caller | Drives whitelist/blacklist selection. |
| `db_name` | `str` | caller | Resolved against `<project_root>/data/`; must be `market_data_cn.db` / `market_data_us.db`. |
| `amount_threshold` | `int` | caller | Used **directly** as `min_vol`; config's `min_volume_*` are NOT consulted at this call site (`momentum_scanner.py:153`). |

### 4.4 Outputs

- One CSV per market in the project root (Section 4.2).
- Stdout progress lines (`[GO]`, `[CFG]`, `[WAIT]`, `[INFO]`, `[FAST]`, `[OK]`, `[WARN]`, `[ERR]`).
- Return value: `None` on every path (success and failure). **No exit code, no structured result** — the only success signal is the existence of the CSV (open question).

### 4.5 Error behavior (Current State)

- Missing DB file → print `[ERR] 数据库不存在`, return `None` (`momentum_scanner.py:144-145`).
- Empty DB (no `MAX(date)`) → print `[WARN] 数据库为空`, return `None` (`momentum_scanner.py:168-170`).
- SQL read error → print `[ERR] 读取错误: <e>`, return `None` (`momentum_scanner.py:182-184`).
- No candidates after filtering → print `[WARN] 没有符合条件的标的`, return `None` (`momentum_scanner.py:261-263`).
- All of the above are **silent to the caller** (return `None` with no exception); there is no machine-readable failure signal.
- `calculate_rsrs` never raises (broad `except` → `0.0`).

### 4.6 RSRS interpretation thresholds (consumed by Module #6)

These are **not computed** by Module #5; they are documented here because they are the contract Module #6 reads off the CSV's `rsrs_z` column:

| `rsrs_z` range | Interpretation (Module #6 prompt) | Source |
|---|---|---|
| `> 0.8` | `[HOT]` — strong institutional uptrend; high sector-logic credibility | `industry_analyzer.py:73`, `industry_analyzer.py:297-298` |
| `< 0.3` | loose/speculative structure; raw gain may be news-driven | `industry_analyzer.py:299` |

These thresholds are **hardcoded in the prompt text**, not in config (open question).

### 4.7 Registry proposals (BLOCKING Phase 5 — enumerated, not written)

> Routing follows the data-sources CDD convention: cross-ADR stances → `architecture.yaml`; concrete values → a future constants/entities registry (which does not yet exist).

**(a) `architecture.yaml` candidates (stances/port contracts):**
- `micro.rsrs.formula` = `R_squared × sign(slope)` via `scipy.stats.linregress` — the algorithmic stance owned by this module; the DuckDB `vw_rsrs_ranking_*` views and the `Settings().market.rsrs_window` default MUST stay aligned.
- `micro.rsrs.range` = `[-1.0, 1.0]`.
- `micro.rsrs.scalar_vectorized_equivalence` — invariant that `calculate_rsrs` and `_calculate_rsrs_vectorized` agree to `< 1e-6` on identical input (enforced by `tests/test_momentum_scanner.py`).

**(b) Value-constant candidates (NOT architecture.yaml):**
- `micro.rsrs.window` = 18 (bars; mirrored by `Settings().market.rsrs_window`, `models_config.json` `scanner_filters.rsrs_window`, and the DuckDB RSRS view).
- `micro.rsrs.flat_variance_guard` = `1e-10` (the zero-variance threshold shared by both paths).
- `micro.rsrs.hot_threshold` = 0.8 (Module #6 consumer; currently hardcoded in prompt).
- `micro.rsrs.speculative_threshold` = 0.3 (Module #6 consumer; currently hardcoded in prompt).
- `micro.cn_min_amount_60d` = 200_000_000 (RMB); `micro.us_min_amount_60d` = 20_000_000 (USD).
- `micro.max_change_pct_60d` = 400 (%).
- `micro.universe_lookback_days` = 180 (the `analyze_market` SQL window).
- `micro.min_bars_for_change` = 61 (60-day change needs the 61st-ago bar).
- `micro.top_n` = 200.
- `micro.us_blacklist` = 50-ticker list (`momentum_scanner.py:24`, `models_config.json:50`).

> **OPEN QUESTION (registry design):** `docs/registry/entities.yaml` does not exist (same blocker as Module #3 §4.5). Group (b) proposals stay enumerated here only.

## 5. Edge Cases

| Situation | What happens (Current State) |
|---|---|
| **`len(series) < window`** | Length guard returns `0.0` before any regression (`momentum_scanner.py:53-54`). Deterministic. (Acceptance case `(d)`.) |
| **Flat / zero-variance series** | **Pre-fix**: `linregress` returns `rvalue=nan` → scalar path returned `nan`; vectorized path returned `0.0` (paths diverged). **Post-fix (BUG E)**: scalar path's `np.var(y) ≤ 1e-10` guard returns `0.0`, matching the vectorized path (`momentum_scanner.py:56-60`). (Acceptance case `(a)`.) |
| **Strictly monotonic increasing** | `slope > 0`, `r_value → +1` → RSRS → `+1.0` (perfect) or `> 0` (noisy). (Acceptance case `(b)`.) |
| **Strictly monotonic decreasing** | `slope < 0`, `r_value → -1` → RSRS → `-1.0` (perfect) or `< 0` (noisy). (Acceptance case `(c)`.) |
| **Slope exactly 0 but non-flat (impossible for real prices)** | The `sign` literal maps 0 → `-1.0`; but `r_value` would be `nan`/0 and the zero-variance/residual-nan guards return `0.0`. No spurious `-1.0` can escape. |
| **`series` shorter than 60 bars in `analyze_market`** | The per-group `len(group) < 61` filter skips it (`momentum_scanner.py:203`); it never reaches RSRS. |
| **`p_prev == 0`** (60-bar-ago close is zero) | Skip the ticker (`momentum_scanner.py:230-231`) — avoids divide-by-zero in `change_pct`. |
| **60-day surge > `max_change_pct` (US only)** | Rejected as a likely bad tick / reverse-split artifact (`momentum_scanner.py:234-236`). CN has **no** equivalent breaker (open question). |
| **`amount_threshold` disagrees with config** | The positional `amount_threshold` always wins; `config.min_volume_*` are ignored at the call site (`momentum_scanner.py:153`). Operator must pass the right threshold; `main()` hardcodes `2e8`/`2e7`. |
| **`models_config.json` present but missing `scanner_filters`** | `_load_config` prints `[WARN]` and returns the hardcoded default dict (`momentum_scanner.py:39`). |
| **`models_config.json` parse error / missing file** | `_load_config` prints `[WARN]` and returns defaults (`momentum_scanner.py:40-44`). |
| **DB file missing** | `get_connection` prints `[ERR]`, returns `None`; `analyze_market` returns early (`momentum_scanner.py:142-147, 160-161`). No crash. |
| **Empty DB** | `MAX(date)` is `NULL` → `[WARN] 数据库为空` → return (`momentum_scanner.py:168-170`). |
| **No candidates pass filters** | `[WARN] 没有符合条件的标的` → return; no CSV written (`momentum_scanner.py:261-263`). |
| **Non-numeric / object series to `calculate_rsrs`** | `linregress` raises inside the `try`; broad `except` returns `0.0` (`momentum_scanner.py:69-72`). No exception escapes. |
| **`np.sign(0)` in vectorized path on a flat row** | `0.0` × `0` = `0.0` (the `valid_mask` already set `r_sq=0` for that row). Consistent with scalar. |
| **CSV path drift** | `analyze_market` writes to **project root**; `industry_analyzer`'s default-discovery reads from `micro_report/` (`industry_analyzer.py:222`). The two only fail to chain on the **auto-discovery default** (`load_momentum_data` → `micro_report/` glob). If the caller passes explicit paths to `run_analysis(cn_path=..., us_path=...)` (`industry_analyzer.py:251,268-276`), `_process_csv` reads the CSV directly and the modules chain without a copy. So the drift is default-path-only, not a hard chain break (open question). |
| **Concurrent `analyze_market` runs** | Unguarded; two processes writing the same-named CSV (same `start`/`end` date) will race — last writer wins, no lock. SQLite reads are concurrent-safe (read-only). |

## 6. Dependencies

**Upstream (this module depends on):**
- **#1 `runtime-configuration`** — `Settings().market.*` (`src/doge/config/settings.py:57-64`) defines `cn_min_volume`, `us_min_volume`, `max_change_pct`, `rsrs_window`. **Current State**: the live scanner reads `models_config.json` `scanner_filters` instead, and `Settings().market` is **not consulted** by `momentum_scanner.py` — a config-drift open question and ADR-0002 migration target.
- **#2 `market-data-storage`** — reads `stock_prices` from `market_data_cn.db` / `market_data_us.db`; the DuckDB `vw_rsrs_ranking_*` views reproduce this module's RSRS formula in SQL (`data/views.sql:114-122`) **modulo the zero-slope sign convention** (SQL `>= 0` vs Python `> 0` vs `np.sign` — see Section 4.1 sign note; masked by the zero-variance guard); `industry_analyzer.run_analysis` writes reports via `save_research_report` (Module #2/#7).
- **#3 `data-sources`** — `market_scanner.py` is the active ingestion writer (shared file); it depends on `TDXReader`, `init_db_custom`, `save_stock_data_custom`, and the `tdx_downloader` server-sync helpers. Without Module #3 producing `stock_prices` rows, this module has nothing to rank.
- **Python packages**: `scipy.stats` (`linregress`), `numpy`, `pandas`, `sqlite3` (stdlib), `collections.Counter`, `yfinance` (transitively, via `industry_analyzer`), `concurrent.futures` (metadata fetch), `threading` (cache lock).
- **DeepSeek LLM client** (`src/macro.config.MacroConfig`, `src/macro.strategist.DeepSeekStrategist`) — used by `industry_analyzer` only; this is the **same** LLM client surface as Module #4 (not a separate client). `models_config.json` provides `api_key`, `model`, `base_url`.

**Downstream (depend on this module):**
- **#6 `ai-industry-analysis`** — `industry_analyzer.py` *is* the Module #6 implementation today (Phase 5 will reconcile/rename). It consumes the Top-200 CSVs and the RSRS interpretation thresholds (Section 4.6).
- **#9 `fastapi-service`** — scan routers trigger `MarketScanner` runs (per the `market-data-storage` CDD §6, `src/api/routers/scan.py` imports `init_db_custom` and delegates writes to `MarketScanner`).
- **#10 `pyqt-desktop-dashboard`** — the operator UI launches scans and surfaces the Top-200 / industry reports.

**Bidirectional notes (per design-docs rule):**
- The `market-data-storage` CDD (#2 §6) and `data-sources` CDD (#3 §6) MUST list `micro-momentum-scanner` as a dependent (they do).
- The `runtime-configuration` CDD (#1 §6.2) lists this module as a `market.*` consumer (it does; the drift is the open question).

**Docs / ADRs:**
- [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) — governs the layer boundary; this module's `direct_sqlite_import`, `sys_path_insert`, and `_PROJECT_ROOT_recalculation` are forbidden patterns flagged for migration (Section 8).
- [ADR-0002](../../docs/architecture/adr-0002-centralized-configuration.md) — the config-centralization decision this module does not yet honor (`models_config.json` vs `Settings()`).
- **No new ADR** — RSRS is a product/algorithm decision, not an architecture decision; the formula lives in this CDD's Section 4.

## 7. Configuration Knobs

> **Config drift note (S002-008 / TR-019 RESOLVED, 2026-06-12)**: there is now a **single** config surface for the scanner filters — `Settings().market.*` (`src/doge/config/settings.py` `MarketConfig`, the centralized source per ADR-0002). The legacy `<project_root>/models_config.json` → `scanner_filters` block has been removed from both the live (gitignored) config and the tracked `models_config.template.json`; the scanner reads `get_settings().market` directly via `_load_config` (§3.2). A BLOCKING drift guard (`tests/contract/test_scanner_filter_drift_guard.py`) fails if any production `.py` under `src/micro`, `src/macro`, `src/api`, `src/doge` reintroduces the `scanner_filters` key-read.

| Knob | Default | Valid range / type | Owner (Current) | Env owner | Operational risk |
|---|---|---|---|---|---|
| `rsrs_window` | `18` (bars) | positive int, typical 10–30 | `Settings().market.rsrs_window` (`MarketConfig`) | (not env) | **HIGH** — changes ranking output; MUST stay aligned with the DuckDB RSRS view (`REGR_*` over 18 bars, `data/views.sql:114-122`). Drift → inconsistent rankings across CSV vs MCP/API. |
| `min_volume_cn` | `200_000_000` (RMB) | positive int | `Settings().market.cn_min_volume` (`MarketConfig`) | (not env) | **MEDIUM** — over-filters (miss mid-caps) or under-filters (illiquid noise). |
| `min_volume_us` | `20_000_000` (USD) | positive int | `Settings().market.us_min_volume` (`MarketConfig`) | (not env) | **MEDIUM** — same. |
| `max_change_pct` | `400` (%) | positive int | `Settings().market.max_change_pct` (`MarketConfig`) | (not env) | **MEDIUM** — too low rejects legit breakouts; too high admits bad ticks. **Applied to US only**. |
| `us_blacklist` | ~52 tickers | tuple of str (`tuple[str,...]` on `MarketConfig`; list at the call site) | `Settings().market.us_blacklist` (`MarketConfig`) | (not env) | **MEDIUM** — leveraged/inverse ETFs would otherwise dominate US rankings; list must be maintained as new products launch. |
| `cn_universe_prefixes` | `("00","30","60","68")` | tuple of str | `Settings().market.cn_universe_prefixes` (`MarketConfig`) | (not env) | LOW — A-share investable-code whitelist; widening admits funds/indexes. |
| `universe_lookback_days` | `180` (calendar days) | positive int | **HARDCODED** in SQL | (not env) | **MEDIUM** — must be ≥ 60 trading days to compute the 60-day change; shorter → `change_pct` undefined for recent listings. Interacts with Module #2 `retention_days=180`. |
| `top_n` | `200` | positive int | **HARDCODED** | (not env) | LOW — output size; raising increases LLM token cost downstream (Module #6 caps at 50 anyway). |
| `amount_threshold` (call-site) | now `Settings().market.cn_min_volume` (CN) / `.us_min_volume` (US) from `main()` | positive int | `main()` reads `Settings().market` (S002-008) | (not env) | LOW (post-S002-008) — `main()` now sources thresholds from settings, closing the prior call-site-override gap. `analyze_market` still accepts an explicit `amount_threshold` for callers that need to override. |
| RSRS `hot_threshold` | `0.8` | float ∈ (0, 1] | **HARDCODED in Module #6 prompt** (`industry_analyzer.py`) | (not env) | LOW — display/interpretation only; does not affect the score. |
| RSRS `speculative_threshold` | `0.3` | float ∈ [0, 1) | **HARDCODED in Module #6 prompt** (`industry_analyzer.py`) | (not env) | LOW — same. |
| `flat_variance_guard` | `1e-10` | small positive float | **HARDCODED** in both RSRS paths | (not env) | LOW — must be identical across both paths to preserve scalar/vectorized equivalence. |

**Migration target (vs Current State):**
- *Current State (post-S002-008)*: scanner filters sourced from `Settings().market`; `models_config.json` no longer carries `scanner_filters`; `main()` reads thresholds from settings.
- *Target (further migration, owned by #12)*: env-overridable thresholds; `hot_threshold`/`speculative_threshold` promoted to config so Module #6 reads them rather than hardcoding; `analyze_market` reads thresholds from settings, not positional args (the positional `amount_threshold` is retained for backward compat but now defaults to the settings value at the `main()` call site).

## 8. Acceptance Criteria

**RSRS formula (BUG E — RESOLVED):**
- [x] `calculate_rsrs(flat_series)` returns `0.0` (not `nan`) — `tests/test_momentum_scanner.py::test_calculate_rsrs_flat_series_returns_zero`.
- [x] strictly monotonic increasing → `rsrs > 0` (perfect ramp → `1.0`) — `test_calculate_rsrs_increasing_series_is_positive`.
- [x] strictly monotonic decreasing → `rsrs < 0` (perfect decline → `-1.0`) — `test_calculate_rsrs_decreasing_series_is_negative`.
- [x] `len(series) < window` → `0.0` (length guard) — `test_calculate_rsrs_short_series_returns_zero`.
- [x] `_calculate_rsrs_vectorized` matches `calculate_rsrs` to `< 1e-6` on identical input, including a flat row — `test_vectorized_path_matches_scalar_path`, `test_vectorized_path_matches_scalar_path_including_flat_row`.
- [x] every RSRS result lies in `[-1.0, 1.0]` — `test_calculate_rsrs_result_is_in_unit_range`.
- [x] `python -m pytest tests/test_momentum_scanner.py -q` → 11 passed (verified — 11 top-level `def test_` functions). Full suite `python -m pytest -q` → **N passed (re-run on canonical env to pin exact count)** — the previously-cited 137 count could not be re-verified cleanly here because `models_config.json` is GBK-encoded and Python defaults to `gbk` on this Windows env, aborting collection before the count can be confirmed. Re-run with a UTF-8 default encoding on the canonical Windows env to pin the number.

**Contract / data model:**
- [ ] Top-200 CSV columns are exactly `ticker, price_60d_ago, price_current, change_percent, avg_daily_volume, rsrs_z` in order (manual/fixture test — OPEN).
- [ ] RSRS score column `rsrs_z` is `R²×sign(slope)` rounded to 2 decimals, ∈ `[-1.0, 1.0]` (regression test against the scalar formula — OPEN).
- [x] The DuckDB `vw_rsrs_ranking_cn` RSRS column equals `calculate_rsrs` on the same 18-bar window for a zero-slope fixture ticker (cross-implementation agreement at the zero-boundary — RESOLVED S002-001; `tests/unit/momentum/test_rsrs_parity.py`, `tests/migration/test_rsrs_view_sign_convention.py`; cite `data/views.sql:124-133`). NOTE: a SEPARATE sign-inversion blocker between the view's `rn`-ordering and Python's time-index remains open (see §4.1 BLOCKER note); it is out of scope for S002-001 and tracked as a follow-up.

**Workflow:**
- [ ] CN scan with a fixture DB yields a CSV with ≤ 200 rows, all tickers matching `^(00|30|60|68)`, all `avg_daily_volume ≥ min_volume_cn` (fixture integration test — OPEN).
- [ ] US scan excludes every `us_blacklist` ticker and every ticker with `change_pct > max_change_pct` (fixture integration test — OPEN).
- [ ] Missing/empty DB → no CSV written, no exception raised (OPEN).

**Migration / remediation (ADR-0001 / ADR-0002 — OPEN, owned by #12):**
- [ ] `src/micro/momentum_scanner.py:12-13` `current_dir`/`project_root` recalculation removed — routed through `Settings()`.
- [ ] `src/micro/market_scanner.py:10-11, 24-26` `sys.path` hacks removed.
- [ ] `momentum_scanner.py` direct `sqlite3.connect` (`get_connection`, `momentum_scanner.py:142-147`) replaced by `IStockRepository` reads (ADR-0001 `direct_sqlite_import_in_interface`/repository routing).
- [x] Scanner filters sourced from `Settings().market`; `models_config.json` `scanner_filters` removed (ADR-0002) — **RESOLVED S002-008 / TR-019 (2026-06-12)**. `_load_config` builds a dict view over `MarketConfig`; `main()` reads thresholds from settings; drift guard `tests/contract/test_scanner_filter_drift_guard.py` (BLOCKING) prevents reintroduction.
- [ ] CSV output path aligned with `industry_analyzer`'s read path (`micro_report/`), or `industry_analyzer` reads from project root (resolve the path drift — open question).
- [ ] `hot_threshold` / `speculative_threshold` moved out of the Module #6 prompt into config.

**Docs / observability:**
- [ ] This CDD reproduces the canonical RSRS verbatim (done, Section 4.1) and cites real `file:line` for every claim.
- [ ] `analyze_market` failures are surfaced as structured results (not silent `return None`) — OPEN.
- [ ] Registry proposals in Section 4.7 are queued for Phase 5 entry approval.

## 9. Open Questions (aspirational — flagged for Phase 5 reconciliation)

1. **~~Config drift (`models_config.json` vs `Settings().market`)~~ — RESOLVED by S002-008 / TR-019 (2026-06-12).** `Settings().market` is now the single source of truth; `models_config.json` `scanner_filters` removed (live + tracked template); `_load_config` builds a dict view over `MarketConfig`; `main()` reads thresholds from settings. A BLOCKING drift guard prevents reintroduction of the `scanner_filters` key-read. See §3.2 and §7.
2. **`amount_threshold` positional override** — `analyze_market` still accepts an explicit `amount_threshold` (kept for backward compat / explicit-override callers). Post-S002-008 the `main()` call site sources the value from `Settings().market`, but the positional param itself is retained. Should the param be removed entirely (config always wins), or kept as an explicit override?
3. **CSV path drift (default-discovery path only)** — scanner writes to project root; industry analyzer's `load_momentum_data` default-discovery reads `micro_report/` (`industry_analyzer.py:222`). They only fail to chain on the auto-discovery default; explicit `run_analysis(cn_path=..., us_path=...)` (`industry_analyzer.py:251,268-276`) consumes project-root CSVs directly via `_process_csv`. Recommend a single canonical output dir so the default also chains.
4. **`rsrs_z` column name** — historical misnomer (it is not a z-score). Rename to `rsrs` to match the DuckDB view column?
5. **CN surge breaker absent** — US rejects `change_pct > 400%`; CN has no equivalent. Add one for symmetry (CN reverse-split artifacts)?
6. **Silent failures** — `analyze_market` returns `None` on every failure with no structured signal. Add a result type / exit code for CLI and a structured response for API/MCP consumers.
7. **Direct SQLite in a Core module** — `MomentumRanker.get_connection` opens `sqlite3.connect` directly (`momentum_scanner.py:147`), violating the ADR-0001 repository-routing intent. Route through `IStockRepository.get_prices` once the migration provides a batch/universe read.
8. **RSRS hot/speculative thresholds hardcoded in Module #6 prompt** — promote to config so they are testable and tunable without editing prompt text.
9. **`industry_analyzer.py` ownership** — this file lives under `src/micro/` but is the Module #6 implementation. Phase 5 should relocate/rename it (and reconcile the "has NO LLM client" note — it does call a DeepSeek client; the gap is the missing clean-architecture LLM *port*).
10. **`max_change_pct` asymmetry** — applied US-only today; document whether this is intentional (CN price limits make +400% impossible) or an oversight.
11. **Three divergent `sign` conventions for exactly-zero slope** — (a) Python scalar: `1.0 if float(slope) > 0 else -1.0` (`momentum_scanner.py:72`, zero slope → **-1**); (b) Python vectorized: `np.sign(slope)` (`np.sign(0)=0`, zero slope → **0**); (c) DuckDB SQL view: `CASE WHEN COALESCE(REGR_SLOPE(rn, close), 0) >= 0 THEN 1 ELSE -1` (`data/views.sql:118`, zero slope → **+1**). The three only agree because the zero-variance guard forces `r_sq=0` whenever slope can be exactly zero, so the product is `0.0` under all three conventions. Confirm this invariant holds for all numeric inputs (covered by the unit-range test) and consider unifying the `sign` definition across Python scalar, Python vectorized, and the DuckDB view.
