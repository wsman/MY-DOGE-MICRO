# CDD: Macro Strategy Engine (Module #4)

> **Slug**: `macro-strategy-engine`
> **Category**: Core
> **Status**: Designed
> **Created**: 2026-06-12
> **Last Verified**: 2026-06-21
> **Notes**: Brownfield reverse-documentation; provider/runtime hardening is tracked outside this CDD.
> **Depends On**: `market-data-storage` (#2), `data-sources` (#3), `runtime-configuration` (#1)
> **Related ADRs**: [ADR-0005](../../docs/architecture/adr-0005-llm-client-strategy.md) (LLM client strategy), [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) (brownfield clean architecture), [ADR-0002](../../docs/architecture/adr-0002-centralized-configuration.md) (centralized configuration), [ADR-0004](../../docs/architecture/adr-0004-data-source-adapter-contract.md) (data-source adapter contract)
> **Source files reverse-documented**: `src/macro/config.py`, `src/macro/data_loader.py`, `src/macro/strategist.py`, `src/macro/cli.py`, `src/macro/utils.py`, `src/macro/__init__.py`

---

## 1. Overview

The Macro Strategy Engine is the **only LLM-powered module in MY-DOGE-MICRO** and owns the project's DeepSeek/OpenAI-compatible model client. It fetches global cross-asset prices via `yfinance`, computes a layered set of quantitative macro indicators (medium-term trend, short-term momentum, realized volatility, Gold/BTC ratio Z-score, Vol Skew, and an RSRS-style trend-strength proxy), then assembles those indicators into a structured prompt and calls the `deepseek-chat` (or `deepseek-reasoner`) model to produce a Markdown macro strategy report. The engine is composed of five brownfield modules under `src/macro/`: `config.py` (the `MacroConfig` dataclass loaded from `models_config.json` + env overrides), `data_loader.py` (`GlobalMacroLoader` — yfinance fetch + metrics), `strategist.py` (`DeepSeekStrategist` — the LLM client, prompt engineering, and report formatting), `cli.py` (the operator entrypoint), and `utils.py` (logging and formatting helpers).

> **Naming clarification (resolves Bug C context):** Despite its name, **Module #6 (AI Industry Analysis)** has **no LLM client**. The project's LLM access lives **here** in Module #4 (`DeepSeekStrategist` in `src/macro/strategist.py`, which constructs `openai.OpenAI(base_url="https://api.deepseek.com", model="deepseek-chat")`). Any reference to "the project's LLM" or "DeepSeek integration" points at this module, not Module #6.

## 2. User Promise / JTBD

**Operator's job**: "Tell me, in plain language with citations to the underlying numbers, whether the global macro backdrop is risk-on or risk-off right now, and what that implies for my A-share core holdings — without me hand-rolling cross-asset correlations or copy-pasting prices into a chatbot."

**Promise the module must keep**:
- Given the four configured proxy assets (tech `QQQ`, gold `GLD`, crypto `BTC-USD`, target `000300.SS`), fetch the most recent ~120 trading days of aligned daily prices, compute the indicator set, and produce a single Markdown report whose conclusions explicitly cite the computed numbers.
- Keep the operator's API key and provider configuration out of source code (env + `models_config.json` only) and never print a real key to logs or stdout.
- Degrade safely when the LLM provider is unreachable or errors: return a sentinel (`None`) rather than crashing the operator's session, and never silently invent market data when the upstream fetch fails.
- Allow the operator to switch providers/models (DeepSeek Chat, DeepSeek Reasoner, a local LM Studio server) without editing Python source, by changing `models_config.json` or setting `DEEPSEEK_MODEL` / `DEEPSEEK_API_KEY`.

## 3. Detailed Behavior

All file:line citations are against the current brownfield state on the `cdd-adoption-2026-06-11` branch.

### 3.1 Configuration — `src/macro/config.py`

`MacroConfig` (`config.py:7-176`) is a mutable `@dataclass`. Its `__post_init__` (`config.py:38-41`) runs `_load_from_json()` then `_apply_runtime_overrides()`.

- **Defaults** (`config.py:13-36`): `tech_proxy="QQQ"`, `safe_haven_proxy="GLD"`, `crypto_proxy="BTC-USD"`, `target_asset="000300.SS"`, `lookback_days=120`, `volatility_window=20`, `api_key=None`, `base_url="https://api.deepseek.com"`, `model="deepseek-chat"`, `proxy_url=None`, `proxy_enabled=False`.
- **JSON loading** (`config.py:100-161`): resolves the config file by walking up from `src/macro/` to the project root and reading `models_config.json` (`config.py:102-105`). If the file is absent it prints a warning and keeps defaults (`config.py:107-109`). When present it validates structure (`config.py:43-98`) and then loads: assets (`tech/safe/crypto/target` → `symbol`+`name`), `macro_settings` (`lookback_days`, `volatility_window`), the default profile's `api_key`/`base_url`/`model` (`config.py:139-146`), and `proxy_settings`.
- **Runtime env overrides** (`config.py:163-176`): `DEEPSEEK_API_KEY` and `DEEPSEEK_MODEL` (process env, **not** a `.env` file) override the JSON-loaded values. If no API key is set after both passes it prints a warning but does **not** raise — the operator may set it later in the GUI (`config.py:174-176`).

### 3.2 Data fetch + indicator computation — `src/macro/data_loader.py`

`GlobalMacroLoader(config)` (`data_loader.py:14-330`) is the data layer.

- **`fetch_combined_data(max_retries=3, retry_delay=5.0)`** (`data_loader.py:19-147`):
  - Builds the ticker list from config (tech, safe, target, plus crypto if set) (`data_loader.py:36-44`).
  - If `proxy_enabled`, saves and sets `HTTP_PROXY`/`HTTPS_PROXY` env vars for the duration of the call, restoring them in `finally` (`data_loader.py:51-61`, `136-147`).
  - Over-fetches `int(lookback_days * 1.65) + 20` days to guarantee a full `lookback_days` trading rows after cleaning (`data_loader.py:65`).
  - Retry loop (`data_loader.py:68-101`): up to `max_retries` attempts; on error messages containing `"Rate"`, `"429"`, or `"Too Many Requests"` it sleeps `retry_delay` and retries (the same token heuristic reused by the yfinance adapter — ADR-0004). Empty data triggers a retry. After exhaustion returns `None`.
  - Cleaning (`data_loader.py:107-130`): flattens yfinance's MultiIndex to `Close`, drops rows where the tech proxy is NaN, forward-fills other assets (crypto gaps on weekends), drops remaining NaNs, and tails to exactly `lookback_days` rows. Returns `None` if data is empty/insufficient.
- **`get_market_summary(data)`** (`data_loader.py:149-165`): returns a dict of latest prices + date + point count.
- **`calculate_rsrs(prices, window=18)`** (`data_loader.py:167-193`): the macro engine's **local** RSRS proxy (see section 4.3 for the canonical RSRS owned by Module #5). Computes `scipy.stats.linregress` over the last `window` closes and returns `r_value**2 * sign(slope)`, range `[-1.0, 1.0]`. Returns `0.0` when `len(prices) < window`.
- **`calculate_volatility_skew(prices, short_win=5, long_win=20)`** (`data_loader.py:195-206`): short-window std / long-window std of daily returns; returns `1.0` if the long-window std is 0 or NaN.
- **`calculate_advanced_metrics(prices_df, window=None)`** (`data_loader.py:208-265`): adds Gold/BTC ratio, its rolling Z-score, annualized log-return volatility, a `vol_scale_factor = 1/ann_vol`, a `vol_skew` (5d/20d tech-return std), and a `price_efficiency` proxy. Drops NaN rows.
- **`calculate_metrics(data)`** (`data_loader.py:267-330`): the consolidated indicator dict consumed by the strategist. Computes: per-asset medium trend `(P_now - P_start)/P_start` over the whole window; per-asset 5-day momentum `(P_now - P_t-5)/P_t-5` (falls back to medium trend if `< 6` rows); a boolean `risk_on_signal` (`tech_trend_medium > safe_trend_medium`); `tech_volatility` (annualized std over `min(len, 60)` bars); and merges the advanced metrics + RSRS for tech and safe-haven proxies. Returns `{}` on exception.

### 3.3 LLM client + report — `src/macro/strategist.py`

`DeepSeekStrategist(config)` (`strategist.py:10-179`) is the project's LLM integration.

- **Construction** (`strategist.py:11-17`): `self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)`. The OpenAI SDK is used in OpenAI-compatible mode against the DeepSeek endpoint; `OpenAI(...)` itself performs **no** network call.
- **`generate_strategy_report(metrics, market_data) -> str`** (`strategist.py:19-148`): the source annotation at `strategist.py:19` is **`-> str`**, NOT `-> Optional[str]`. Runtime behavior: on **any** exception the method returns `None` (`strategist.py:146-148`), so the effective contract is "returns the report string OR `None` on error". The ADR-0005 target port contract specifies `Optional[str]` to match this behavior — the in-source annotation is mis-typed and is logged as a remediation item in section 8 (annotation should be corrected to `Optional[str]` to match the documented None-returning path).
  - Builds a structured `context_str` (`strategist.py:27-46`) listing each asset's name, ticker, medium trend, and 5d return, plus `Market Volatility (Annualized)` and the `Risk Signal` label.
  - Builds a `dashboard_data` Markdown table (`strategist.py:52-60`) with three rows: **RSRS (Slope\*R²)**, **Vol Skew (5/20)**, **Risk Signal**.
  - Builds a Chinese-language `system_prompt` (`strategist.py:63-84`) that instructs the model to act as an evidence-driven quant macro analyst, to cite every conclusion with a `[数据: ...]` bracket, and to interpret RSRS and Vol Skew using fixed bands (RSRS `>0.8` / `0.5..0.8` / `-0.5..0.5` / `-0.8..-0.5` / `<-0.8`; Vol Skew `<0.8` / `0.8..1.5` / `>1.5`).
  - Builds a `user_prompt` (`strategist.py:89-101`) embedding `context_str`, `dashboard_data`, and the last 5 rows of `market_data` (via `to_string()`).
  - Calls `self.client.chat.completions.create(model=config.model, messages=[system,user], stream=False, temperature=0.6)` (`strategist.py:104-112`).
  - On success: extracts `response.choices[0].message.content` (`strategist.py:114`); returns a fixed string if the content is empty (`strategist.py:117-118`); computes provenance (date range, trading/calendar days, asset list) from `market_data`; calls `format_report_for_display`; archives the formatted report to `macro_report/<YYYY-MM-DD_HH-MM-SS>_macro.md` (`strategist.py:131-142`); and returns the **raw** LLM `content`.
  - On **any** exception: logs the error and returns `None` (`strategist.py:146-148`). This is the offline/degraded fallback.
- **`format_report_for_display(raw_report, metrics, start_date=None, end_date=None, assets=None, trading_days=None, calendar_days=None) -> str`** (`strategist.py:150-179`): prepends a fixed title header, a `🟢 RISK-ON`/`🔴 RISK-OFF` badge from `metrics['risk_on_signal']`, the annualized volatility as a percentage, and (when provenance args are present) a `数据溯源` block with the date range and asset list. Returns a warning string if `raw_report` is falsy (`strategist.py:151-152`).

### 3.4 CLI — `src/macro/cli.py`

`main()` (`cli.py:17-91`) is the operator entrypoint (`python -m macro.cli`).

- **`sys.path.insert`** at `cli.py:12` is an ADR-0001 forbidden pattern (`sys_path_insert`) — recorded as remediation in section 8.
- Parses `--verbose` (currently force-on, `cli.py:47`) and `--config-file` (accepted but documented "暂未实现" — not implemented, `cli.py:37-40`).
- Constructs `MacroConfig()`, `GlobalMacroLoader`, fetches data, computes metrics, constructs `DeepSeekStrategist`, calls `generate_strategy_report`, then `format_report_for_display`, and prints. Exits `1` on any exception or on empty market data (`cli.py:80-87`).

### 3.5 Utilities — `src/macro/utils.py`

`setup_logging(log_level=DEBUG, log_file="logs/app.log", ...)` (`utils.py:13-65`) configures the root logger with a console handler and a 10 MB rotating file handler (5 backups). `validate_api_key` (`utils.py:81-99`) checks non-empty and `len >= 10`. `format_percentage` / `format_currency` (`utils.py:102-125`) are presentation helpers.

## 4. Contracts / Data Model

### 4.1 `MacroConfig` shape (input contract)

| Field | Type | Default | Source | Notes |
|---|---|---|---|---|
| `tech_proxy` | `str` | `"QQQ"` | `models_config.json:assets.tech.symbol` | Risk-on proxy |
| `safe_haven_proxy` | `str` | `"GLD"` | `assets.safe.symbol` | Risk-off proxy |
| `crypto_proxy` | `str` | `"BTC-USD"` | `assets.crypto.symbol` | High-beta liquidity proxy |
| `target_asset` | `str` | `"000300.SS"` | `assets.target.symbol` | Decision target (CSI 300) |
| `lookback_days` | `int` | `120` | `macro_settings.lookback_days` | Window; aligned with Module #3 default (ADR-0004) |
| `volatility_window` | `int` | `20` | `macro_settings.volatility_window` | Rolling-vol window |
| `api_key` | `Optional[str]` | `None` | `profiles[*].api_key` ← `DEEPSEEK_API_KEY` | Required for live calls |
| `base_url` | `str` | `"https://api.deepseek.com"` | `profiles[*].base_url` | OpenAI-compatible endpoint |
| `model` | `str` | `"deepseek-chat"` | `profiles[*].model` ← `DEEPSEEK_MODEL` | Provider model id |
| `proxy_enabled` | `bool` | `False` | `proxy_settings.enabled` | Toggles HTTP_PROXY mutation |
| `proxy_url` | `Optional[str]` | `None` | `proxy_settings.url` | e.g. `http://127.0.0.1:7890` |

### 4.2 `models_config.json` schema (current State)

```jsonc
{
  "profiles": [ { "name", "base_url", "model", "api_key" } ],   // >=1 entry
  "default_profile": "<name>",                                   // must exist in profiles
  "macro_settings": { "lookback_days": int, "volatility_window": int },
  "assets": { "tech": { "symbol", "name" }, "safe": {...}, "crypto": {...}, "target": {...} },
  "proxy_settings": { "enabled": bool, "url": str? }
}
```

Validation is enforced by `_validate_config` (`config.py:43-98`): missing top-level fields, empty `profiles`, missing per-profile fields, a `default_profile` not present in `profiles`, missing assets, or missing `macro_settings`/`proxy_settings.enabled` each raise `ValueError`. **Note:** these `ValueError`s are caught by `_load_from_json`'s broad `except ValueError` (`config.py:158-159`) and only printed — the dataclass keeps its defaults. This is a current-state quirk (silent config-failure), recorded in section 5.

> **Security note (BUG-adjacent, was on disk; env-migrated in S002-013):**
> `models_config.json` historically held a real-looking `api_key` on the local
> disk. As of S002-013 the file ships only the `REPLACE_WITH_DEEPSEEK_API_KEY`
> placeholder and `DEEPSEEK_API_KEY` (env var) is the primary key source; the
> local FastAPI `GET /api/config` additionally drops `api_key` from its HTTP
> response. A later forensic audit confirmed no real key was ever committed to
> git history (`models_config.json` was gitignored from the initial commit),
> so no revocation or history rewrite is required. Operators must only export
> `DEEPSEEK_API_KEY` and verify that `python -m macro.cli` works.

### 4.3 RSRS formulas

There are **two** RSRS implementations in the brownfield tree; the canonical, authoritative one is **owned by Module #5** and must not be redefined elsewhere:

> **Canonical RSRS (owned by Module #5)** — `src/micro/momentum_scanner.py:47-71`:
> `calculate_rsrs(series, window=18)` = `R_squared × sign(slope)`, range `[-1.0, 1.0]`, via `scipy.stats.linregress` over the last `window` bars.

Module #4's `data_loader.calculate_rsrs` (`data_loader.py:167-193`) is a **separate, local copy** used only to populate the macro prompt dashboard.

> **Current State:** the two copies share the core formula `r_value**2 * sign(slope)`, but they have **drifted** — they are NOT mathematically equivalent on edge inputs. Module #5's canonical version (`momentum_scanner.py:64-65,76`) adds two guards Module #4's local copy does NOT have: (1) a flat-variance guard `if float(np.var(y)) <= 1e-10: return 0.0` (`momentum_scanner.py:64-65`), and (2) a post-compute NaN guard `return 0.0 if trend_strength != trend_strength else trend_strength` (`momentum_scanner.py:76`). Module #4's local copy (`data_loader.py:182-193`) has **neither** guard. On a flat / zero-variance series `scipy.stats.linregress` returns `r_value=nan`, so the local macro copy yields `nan` while the canonical Module #5 copy returns `0.0`.
>
> **Target (Migration):** the macro local copy should either delegate to the canonical Module #5 implementation or replicate both guards (flat-variance + NaN). This is a BUG-class drift tracked in section 8 and gated on the shared-formula registry stance in section 4.7.

**Variables (shared core formula):**
- `prices` — a `pd.Series` of close prices for one asset.
- `window` — regression window, default `18`.
- `y = prices.iloc[-window:].values`; `x = arange(len(y))`.
- `slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(x, y)`.
- `trend_strength = (r_value ** 2) * (1 if slope > 0 else -1)`.

**Example** (deterministic, rising series `1..20`, window 18): `x=[0..17]`, `y=[3..20]`; `linregress` yields `slope=1.0`, `r_value=1.0`; result `= 1.0 * 1 = 1.0` (maximal uptrend). For `y` strictly falling, `slope<0` → result `-1.0`.

### 4.4 Indicator-dict shape (output of `calculate_metrics`, input to strategist)

```pythonc
{
  "metadata_days": int,            # len(data)
  "tech_volatility": float,        # annualized std of tech returns
  "risk_on_signal": bool,          # tech_trend_medium > safe_trend_medium
  "<ticker>_trend_medium": float,  # per asset
  "<ticker>_return_5d": float,     # per asset
  "gold_btc_ratio": float,
  "ratio_z_score": float,
  "vol_scale_factor": float,
  "vol_skew": float,               # 5d/20d tech-return std ratio
  "QQQ_rsrs": float,               # local RSRS for tech proxy
  "GLD_rsrs": float,               # local RSRS for safe-haven proxy
}
```

### 4.5 LLM request/response contract

- **Request**: OpenAI Chat Completions shape — `model`, `messages=[{role:"system",...},{role:"user",...}]`, `stream=False`, `temperature=0.6` (`strategist.py:104-112`).
- **Response read**: `response.choices[0].message.content` (string). Empty content → returns the fixed Chinese string `"分析完成，但API返回内容为空。"` (`strategist.py:117-118`). API exception → returns `None` (`strategist.py:146-148`).
- **Archive artifact**: `macro_report/<timestamp>_macro.md` — a Markdown file written from the **formatted** report (not the raw content). Archive failures are caught and printed, never raised (`strategist.py:141-142`).

### 4.6 Exit codes (CLI)

`cli.main()` exits `1` when market data fetch returns `None` (`cli.py:80-82`) or when any exception escapes the try block (`cli.py:84-87`). Normal completion prints the formatted report and exits `0`.

### 4.7 Registry proposals (for later Phase 5 entry approval — DO NOT write registry files)

> **Routing note:** `docs/registry/architecture.yaml` holds cross-ADR stances only. Value constants below belong in a future constants registry (open question, same as Module #3 §4.5). Listed here only.

- `macro.llm.temperature` = 0.6 (default precision-mode temperature)
- `macro.llm.stream` = False
- `macro.lookback_days` = 120 (aligned with `data_source.default_window_days`)
- `macro.volatility_window` = 20
- `macro.rsrs_window` = 18 (local copy; MUST stay aligned with Module #5 canonical window)
- `macro.rsrs_formula` = `r_value**2 * sign(slope)` (architectural stance candidate for `architecture.yaml`) — **NOTE:** the macro local copy and the Module #5 canonical copy have drifted (section 4.3 Current State). The flat-variance + NaN guards from `momentum_scanner.py:64-65,76` must be reconciled into (or delegated by) the macro copy **before** this shared-formula stance is promoted to Phase 5 entry approval — otherwise the registry would bless two divergent behaviors.
- `macro.fetch_overfetch_factor` = 1.65; `macro.fetch_overfetch_padding_days` = 20
- `macro.fetch_max_retries` = 3; `macro.fetch_retry_delay_seconds` = 5.0
- `macro.rate_limit_tokens` = `["Rate", "429", "Too Many Requests"]` (shared with Module #3)
- `macro.default_base_url` = `https://api.deepseek.com`
- `macro.default_model` = `deepseek-chat`
- `macro.report_dir` = `macro_report`
- `macro.vol_skew.short_window` = 5; `macro.vol_skew.long_window` = 20

## 5. Edge Cases

| Situation | What happens (Current State) |
|---|---|
| **`models_config.json` absent** | `_load_from_json` prints a warning and keeps defaults (`config.py:107-109`). No LLM call is possible later because `api_key` stays `None`, but no exception is raised at construction. |
| **`models_config.json` malformed JSON** | `json.JSONDecodeError` is caught and printed (`config.py:155-156`); defaults kept. No raise. |
| **`models_config.json` fails schema validation** | `ValueError` from `_validate_config` is caught by the broad `except ValueError` (`config.py:158-159`) and printed; defaults kept. The operator sees a console warning but the run proceeds with default config — a silent-config-failure risk (see open questions). |
| **`DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` set in env** | Override the JSON-loaded values (`config.py:168-172`). Env wins over JSON. |
| **No API key after both passes** | Prints a warning (`config.py:174-176`); `MacroConfig` constructs anyway. The first LLM call will fail at the provider and be caught → returns `None`. |
| **yfinance returns empty / rate-limited** | Retry up to `max_retries=3` with `5s` backoff, then `fetch_combined_data` returns `None` (`data_loader.py:84-101`). CLI exits `1`. |
| **yfinance returns fewer rows than `lookback_days`** | Cleaning proceeds; a warning is logged (`data_loader.py:127-128`); the short frame is returned (not `None`). Downstream indicators run on the shorter window. |
| **`calculate_metrics` raises** | Caught, logged with traceback, returns `{}` (`data_loader.py:326-330`). The strategist would then receive an empty metrics dict — `metrics.get(...)` calls return `0`/defaults, so the prompt still builds but with zeroed numbers. |
| **LLM provider unreachable / errors** | `generate_strategy_report` catches `Exception`, logs, returns `None` (`strategist.py:146-148`). Caller (CLI/GUI) treats `None` as "no report". No retry in the strategist — only `data_loader` retries. |
| **LLM returns empty content string** | Returns the fixed Chinese message `"分析完成，但API返回内容为空。"` (`strategist.py:117-118`). |
| **Report archive directory write fails** | Archive failure is caught and printed (`strategist.py:141-142`); the raw content is still returned to the caller. |
| **`proxy_enabled` with a bad `proxy_url`** | `HTTP_PROXY`/`HTTPS_PROXY` are set for the yfinance call and restored in `finally` (`data_loader.py:136-147`). A bad proxy causes the fetch to fail and return `None`; env is still restored (no leak). |
| **RSRS on series shorter than `window`** | `calculate_rsrs` returns `0.0` (`data_loader.py:182-183`). |
| **RSRS on a flat / zero-variance series** | Local macro copy returns `nan` — it has **no** flat-variance guard (`data_loader.py:182-193`); `scipy.stats.linregress` yields `r_value=nan`. The canonical Module #5 copy returns `0.0` (it guards `np.var(y) <= 1e-10 -> 0.0` at `momentum_scanner.py:64-65` and NaN at `:76`). **Divergence tracked as remediation** (section 4.3 Current State / Target, section 8 migration). |
| **Vol Skew with zero/NaN long-window std** | Returns `1.0` (neutral) rather than dividing by zero (`data_loader.py:203-205`). |
| **Crypto weekend gaps** | Forward-filled from the last trading day so the aligned frame has no NaNs (`data_loader.py:119`). |

## 6. Dependencies

**Upstream (this module depends on):**
- **Module #1 Runtime Configuration** — the project-level `DOGE_*` env vars and `settings.py`. **Note:** the macro engine's LLM config (`DEEPSEEK_*`, `models_config.json`) is **separate** from `settings.py` today (`src/macro/config.py` owns it). ADR-0002 §Context explicitly flags this as out-of-scope of the centralization so far. Consolidation is an open question.
- **Module #2 Market Data Storage** — the macro engine does **not** currently persist its computed indicators or reports to SQLite/DuckDB; reports are archived to `macro_report/*.md` on the filesystem only. There is no `macro_reports` table today (open question / target).
- **Module #3 Data Sources** — `data_loader.py` calls `yfinance.download` **directly** (not yet through `YFinanceDataSource`). ADR-0004 §Migration Plan item 4 lists routing the macro loader through the adapter as open work. The retry heuristic is duplicated between the two (`macro/data_loader.py:94-97` and `yfinance.py`).

**Downstream (depend on this module):**
- **Module #9 FastAPI Service** — the module-index declares the API depends on the Macro Strategy Engine; the router would call `DeepSeekStrategist` (or a future macro service).
- **Module #10 PyQt Desktop Dashboard** — the GUI triggers macro runs and renders the report; ADR-0002 notes GUI runtime model switching uses the same `DEEPSEEK_MODEL` override path.
- **Module #6 AI Industry Analysis** — despite the "AI" name, **has no LLM**; it consumes yfinance `.info` metadata and is a separate analysis workflow. Any cross-module LLM need routes through Module #4.

**External packages:**
- `openai` 1.62.0 — OpenAI-compatible client (`from openai import OpenAI`, `strategist.py:2`). Drives the chat-completions call against `base_url`.
- `yfinance` 0.2.66 — `yfinance.download` in `data_loader.py`.
- `pandas`, `numpy`, `scipy.stats.linregress` — indicator math.

**Docs / ADRs:**
- [ADR-0005](../../docs/architecture/adr-0005-llm-client-strategy.md) — LLM client strategy, prompt schema, retry/timeout/offline semantics.
- [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) — forbidden patterns this module still violates (`sys_path_insert` at `cli.py:12`; `cross_layer_state_write` via `os.environ` mutation).
- [ADR-0002](../../docs/architecture/adr-0002-centralized-configuration.md) — records that `DEEPSEEK_*`/`models_config.json` live outside `settings.py`.
- [ADR-0004](../../docs/architecture/adr-0004-data-source-adapter-contract.md) — records the yfinance adapter the macro loader should migrate onto.

## 7. Configuration Knobs

| Knob | Where | Default | Valid range / enum | Env ownership | Operational risk |
|---|---|---|---|---|---|
| `DEEPSEEK_API_KEY` | `config.py:168` | `None` (or from `models_config.json`) | non-empty string ≥ 10 chars | operator env / `models_config.json` | **Secret.** Must not be committed. Currently a key ships in `models_config.json` (open question). |
| `DEEPSEEK_MODEL` | `config.py:171` | `"deepseek-chat"` (JSON default may be `deepseek-reasoner`) | provider model id | operator env / `models_config.json` | Wrong id → API error → `None` report. |
| `base_url` | `config.py:31`, profile `base_url` | `https://api.deepseek.com` | OpenAI-compatible URL | `models_config.json` | Pointing at unreachable host → all reports `None`. |
| `temperature` | `strategist.py:111` | `0.6` | float 0.0–2.0 | **hardcoded in impl** | Violates "no hardcoded config in impl modules" rule; should be a knob (open question). |
| `stream` | `strategist.py:110` | `False` | bool | **hardcoded** | Streaming not supported; large reports block until completion. |
| `lookback_days` | `config.py:26` | `120` | positive int | `models_config.json` | Must stay aligned with Module #3 window. |
| `volatility_window` | `config.py:27` | `20` | positive int | `models_config.json` | Affects vol/RSRS smoothing. |
| `macro.fetch_max_retries` | `data_loader.py:19` | `3` | int ≥ 1 | code | Too high → slow offline runs. |
| `macro.fetch_retry_delay_seconds` | `data_loader.py:19` | `5.0` | float ≥ 0 | code | Aggressive → rate-limit not respected. |
| `proxy_enabled` / `proxy_url` | `config.py:35-36` | `False` / `None` | bool / URL | `models_config.json` | Mutates process-global `HTTP_PROXY`/`HTTPS_PROXY` during fetch (ADR-0001 `cross_layer_state_write` concern). |
| `report_dir` | `strategist.py:132` | `"macro_report"` | writable dir | **hardcoded** | Relative to CWD; depends on where the process runs. |

**Migration target (vs. Current State):**
- *Current State*: LLM knobs split across `models_config.json` (provider/model/key), env (`DEEPSEEK_*`), and hardcoded values (`temperature`, `stream`, `report_dir`). No timeout configured on the OpenAI client.
- *Target (Migration)*: all macro/LLM knobs (including `temperature`, `stream`, `timeout`, `retry`) live in a `MacroConfig`/`LLMConfig` dataclass owned by `settings.py` (ADR-0002 consolidation); `models_config.json` becomes one source feeding that dataclass, and no provider secret is committed.

## 8. Acceptance Criteria

**Contract:**
- [ ] `MacroConfig` loads from `models_config.json` and honors `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` env overrides (verified manually — config import succeeds; env wins over JSON).
- [ ] `generate_strategy_report` calls the OpenAI-compatible chat-completions endpoint with `model`, two messages (system+user), `stream=False`, `temperature=0.6` (verified — `tests/test_macro_strategist.py::test_generate_report_includes_asset_context_and_indicators`).
- [ ] The constructed prompt embeds every configured asset ticker, the `[数据: <N>个交易日趋势]` and `[数据: 近5日涨跌]` citation slots, the volatility, the Risk-On/Off label, the RSRS and Vol Skew dashboard rows, and the last-5-days price detail (verified).
- [ ] `format_report_for_display` extracts the `🟢 RISK-ON`/`🔴 RISK-OFF` badge and volatility percentage from `metrics`, and the `数据溯源` provenance block from the passed date/asset args (verified).
- [ ] `generate_strategy_report` returns `None` (never raises) when the API client raises (verified — `tests/test_macro_strategist.py::test_generate_report_returns_none_on_api_error`).
- [ ] `generate_strategy_report` returns the fixed empty-content message when the API returns `""` (verified).
- [ ] Exactly one LLM call is made per report (no retry loop in the strategist) (verified).
- [ ] No test in `tests/test_macro_strategist.py` performs a real network call (all use `MagicMock` / `unittest.mock`).

**Workflow:**
- [ ] `python -m pytest tests/test_macro_strategist.py -q` passes (verified — 9/9).
- [ ] `python -m macro.cli` against a reachable DeepSeek endpoint and a live yfinance connection produces a `macro_report/<timestamp>_macro.md` file containing the `量化风控仪表盘` section (manual smoke — requires network + valid API key). **PASS =** exit code `0` AND the archive file exists AND its content includes `# MY-DOGE PRECISION MACRO REPORT` and `RSRS` (ADVISORY gate).

**Migration / remediation:**
- [ ] **BUG E RESOLVED**: `tests/test_macro_strategist.py` exists, mocks the OpenAI client, and is green (done — 9/9).
- [ ] `src/macro/cli.py:12` `sys.path.insert` removed — replaced by import of `settings.py` or a package install (ADR-0001 forbidden pattern — OPEN).
- [x] `models_config.json` real API key removed / replaced with a placeholder + `.gitignore` entry (security — RESOLVED in S002-013; `DEEPSEEK_API_KEY` env var is now the primary source, `models_config.json` ships the `REPLACE_WITH_DEEPSEEK_API_KEY` placeholder, and `GET /api/config` redacts `api_key` from the HTTP response). A forensic audit confirmed no real key was ever committed to git history, so no rotation/revocation is required; operators only need to export `DEEPSEEK_API_KEY` and verify `python -m macro.cli`.
- [ ] `data_loader.py` yfinance calls routed through `YFinanceDataSource` (ADR-0004 item 4 — OPEN).
- [ ] `DEEPSEEK_*` / `models_config.json` config consolidated under `settings.py` per ADR-0002 (OPEN).
- [ ] Macro reports persisted to a `macro_reports` table (OPEN — section 9.4 target).
- [ ] `strategist.py:19` annotation corrected from `-> str` to `-> Optional[str]` to match the documented `None`-on-error behavior (`strategist.py:146-148`) and the ADR-0005 target port contract (OPEN — type-annotation drift).
- [ ] `data_loader.calculate_rsrs` (`data_loader.py:182-193`) reconciled with the canonical Module #5 copy — either delegate to `momentum_scanner.calculate_rsrs` or replicate its flat-variance guard (`momentum_scanner.py:64-65`) and NaN guard (`:76`). Current drift: macro copy returns `nan` on a flat/zero-variance series; canonical returns `0.0` (OPEN — BUG-class drift, section 4.3).

**Docs / observability:**
- [x] ADR-0005 is Accepted. It remains the load-bearing dependency for this LLM module's Integration Requirements.
- [ ] `_validate_config` `ValueError`s no longer silently swallowed into defaults — at minimum logged at WARNING (OPEN — observability gap).
- [ ] Registry proposals in section 4.7 queued for Phase 5 entry approval.

## 9. Integration Requirements

This section is mandatory for AI/LLM integration modules per the assignment brief.

### 9.1 LLM client strategy

- The project's **single** LLM access point is `DeepSeekStrategist` (`strategist.py`), using the official `openai` SDK in OpenAI-compatible mode against the DeepSeek endpoint. No other module constructs an LLM client.
- **Provider abstraction**: today the client is OpenAI-compatible, so DeepSeek (default), DeepSeek Reasoner, and any OpenAI-compatible local server (e.g. LM Studio, profile `🏠 LM Studio (Local)`, `base_url=http://localhost:1234/v1`) work by swapping `base_url`/`model`/`api_key` in `models_config.json` or via `DEEPSEEK_*` env. No code change is required to switch providers — this is the decision ADR-0005 records.
- **No streaming**: `stream=False` (`strategist.py:110`). The whole report is returned in one response. Streaming is a future enhancement, not current behavior.

### 9.2 Prompt schema

The prompt is a fixed two-message Chat Completions request:

- **System message** (`strategist.py:63-84`): persona ("evidence-driven quant macro analyst"), four core rules requiring `[数据: ...]` citation brackets, a mandate to compare BTC-vs-QQQ and BTC-vs-GLD correlations, and a mandatory `3. 量化风控仪表盘` section with the RSRS interpretation bands (`>0.8` / `0.5..0.8` / `-0.5..0.5` / `-0.8..-0.5` / `<-0.8`) and Vol Skew bands (`<0.8` / `0.8..1.5` / `>1.5`).
- **User message** (`strategist.py:89-101`): three labeled blocks — `【结构化市场数据】` (per-asset trend + 5d return + volatility + risk signal), `【量化仪表盘数据】` (the RSRS/Vol Skew/Risk-Signal Markdown table), and `【最近5日价格明细】` (the `to_string()` of the last 5 rows).

The schema is implicit (a formatted string), not a JSON/tool-call schema. Prompt-token cost scales with `lookback_days` (only 5 rows are sent, so the prompt is bounded).

### 9.3 Retry / timeout budget

- **LLM call**: **no retry and no explicit timeout** in the strategist. A single `chat.completions.create` is issued; on any exception the strategist returns `None` (`strategist.py:146-148`). The OpenAI client uses its SDK default timeout (none configured). This is an operational risk recorded in ADR-0005 — adding a bounded timeout + 1–2 retries is a target, not current behavior.
- **Data fetch**: bounded retry — `max_retries=3`, `retry_delay=5.0s`, rate-limit-token detection, then `None` (`data_loader.py:19`, shared heuristic with Module #3).
- **Total worst-case wall time** for one CLI run ≈ `(3 × 5s) yfinance` + `LLM call latency`. MCP's 30s tool timeout (Module #1) is **not** enforced inside this module — the caller must bound it.

### 9.4 Offline / degraded fallback

- **yfinance failure** → `fetch_combined_data` returns `None` → CLI exits `1` before any LLM call.
- **LLM failure** → `generate_strategy_report` returns `None` → CLI/GUI shows "no report"; the last successful `macro_report/*.md` on disk remains the de-facto fallback (the operator can re-read it). There is **no cached/persisted structured fallback** today — the report is the only artifact.
- **Degraded principle** (inherited from ADR-0001/ADR-0004): a provider or network failure must never crash the session or corrupt local data. Module #4 does not write to SQLite/DuckDB, so there is no data-corruption surface from the LLM path.

### 9.5 Report persistence

- **Current State**: reports are archived only as Markdown files under `macro_report/<YYYY-MM-DD_HH-MM-SS>_macro.md` (`strategist.py:131-142`), written from the formatted report. There is **no `macro_reports` table** and no queryable history.
- **Target (Migration)**: persist report metadata (run timestamp, `model`, `base_url`, `risk_on_signal`, `tech_volatility`, prompt hash, content) into a `macro_reports` table in the macro/research DB so the operator can diff reports across runs. This requires a repository contract (analogous to `IReportRepository`) and is gated on Module #2/#7 storage work. Listed as an open question — do NOT implement without a follow-on CDD.

### 9.6 Secrets handling

- The API key is sourced from `DEEPSEEK_API_KEY` (primary, as of S002-013) and passed only to `OpenAI(api_key=...)`. It is never logged by the strategist. `models_config.json` now ships only the `REPLACE_WITH_DEEPSEEK_API_KEY` placeholder; if the env var is unset and the on-disk value is the placeholder/empty/`None`, `MacroConfig` raises `RuntimeError` rather than letting a placeholder reach the SDK. A forensic audit confirmed no real key was ever committed to git history, so no revocation or history rewrite is required; operators only need to export `DEEPSEEK_API_KEY` and verify `python -m macro.cli` (see `docs/MCP_SERVER.md`). The local FastAPI `GET /api/config` also drops `api_key` from its HTTP response.
- **Repr safety**: `MacroConfig.__repr__` masks `api_key` as `'***'` so that logging or string interpolation of the config object does not leak the key.
- **Loader logging**: `GlobalMacroLoader.__init__` logs only asset tickers and the lookback window, not the full config object.
- **CLI error redaction**: `macro.cli` scrubs both the real key and the `REPLACE_WITH_DEEPSEEK_API_KEY` placeholder from exception messages before printing to stdout.
