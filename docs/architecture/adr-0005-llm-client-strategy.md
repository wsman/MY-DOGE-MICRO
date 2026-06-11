# ADR-0005: LLM Client Strategy

## Status

Accepted

## Date

2026-06-12

## Last Verified

2026-06-12

## Decision Makers

WSMAN, python-specialist

## Summary

MY-DOGE-MICRO's only LLM integration (`DeepSeekStrategist` in `src/macro/strategist.py`) must keep working against DeepSeek today while remaining swappable to any OpenAI-compatible provider, and must never hardcode secrets, leak the operator's API key, or crash the session when the provider is unavailable. This ADR decides that all LLM access goes through the official `openai` SDK in OpenAI-compatible mode, that DeepSeek (`deepseek-chat`) is the default provider configured via `models_config.json` + `DEEPSEEK_*` env overrides (never source code), and that provider failures degrade to a `None` sentinel with no in-strategist retry.

## Engine Compatibility

> This is a Product project. The "Engine Compatibility" table is interpreted as the Product Stack Compatibility table per `docs/CLAUDE.md`.

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+, `openai` SDK 1.62.0 (OpenAI-compatible), DeepSeek HTTP API, optional LM Studio local server |
| **Domain** | Core — AI/LLM integration (Macro Strategy Engine, Module #4) |
| **Knowledge Risk** | MEDIUM — the `openai` 1.x SDK's `OpenAI(base_url=...)` OpenAI-compatible-mode shape is in training data but base_url-as-alias behavior is provider-specific; DeepSeek's chat-completions compatibility is documented but empirical |
| **References Consulted** | `src/macro/strategist.py`, `src/macro/config.py`, `docs/reference/python/VERSION.md`, `models_config.json`, `design/cdd/macro-strategy-engine.md`, ADR-0001, ADR-0002 |
| **Post-Cutoff APIs Used** | `openai.OpenAI(base_url=..., api_key=...)` + `client.chat.completions.create(model, messages, stream, temperature)` (1.x SDK; stable surface) |
| **Verification Required** | Mock-based unit tests confirm request shape, response parsing, and `None`-on-error fallback (`tests/test_macro_strategist.py`); a live smoke against DeepSeek before provider/model bumps |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001 (Accepted) — defines the `cross_layer_state_write` forbidden pattern and the clean-architecture layering this client must respect; ADR-0002 (Proposed) — records that `DEEPSEEK_*` / `models_config.json` config lives outside `settings.py` today |
| **Enables** | Module #4 CDD (`macro-strategy-engine`); future routing of LLM access through a clean-architecture `ILLMClient` port (post-migration); report persistence to a `macro_reports` table |
| **Blocks** | New LLM-using features must route through `DeepSeekStrategist` (or its port successor) — no new ad-hoc `openai.OpenAI(...)` constructions elsewhere |
| **Ordering Note** | This ADR documents an already-working integration; the clean-architecture port extraction is a follow-on owned by Module #12 |

## Context

### Problem Statement

The macro engine depends on an external LLM to turn quantitative indicators into a cited, operator-readable strategy report. Three decisions must be made and frozen: (1) which client abstraction is used, so a provider swap does not require rewriting call sites; (2) where secrets and provider config live, so no key is committed and operators can switch providers without code edits; and (3) what happens when the provider is unreachable, so a flaky API never crashes a local-first session or corrupts state. Not deciding means the project's single LLM call site stays an ad-hoc, untestable, key-leaking integration that every future AI feature would copy.

### Current State

- `DeepSeekStrategist` (`src/macro/strategist.py:10-179`) constructs `openai.OpenAI(api_key=config.api_key, base_url=config.base_url)` — OpenAI SDK in OpenAI-compatible mode against `https://api.deepseek.com`.
- Provider/model/key come from `models_config.json` (profiles + `default_profile`) with `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` env overrides (`src/macro/config.py:163-176`).
- `models_config.json` ships a real-looking API key committed to the repo — a security violation per `.claude/rules/config-files.md`. (**Remediated in S002-013**: the file now ships the `REPLACE_WITH_DEEPSEEK_API_KEY` placeholder and `DEEPSEEK_API_KEY` env var is the primary source; the historical key remains in git history and requires operator revocation — see `docs/MCP_SERVER.md`.)
- The strategist issues a single `chat.completions.create(model, messages=[system,user], stream=False, temperature=0.6)`; on exception it logs and returns `None`; there is **no retry and no explicit timeout** on the LLM call.
- `temperature=0.6`, `stream=False`, and `report_dir="macro_report"` are hardcoded in the implementation module, violating the "no hardcoded config in impl modules" rule.
- No `ILLMClient` port exists; the strategist is the only LLM call site. Module #6 ("AI Industry Analysis") has **no** LLM despite its name.
- There is no `macro_reports` table; reports are archived as Markdown files only.

### Constraints

- **Local-first**: no external secrets manager; secrets come from env or a local JSON file.
- **Provider-agnostic by construction**: DeepSeek is default, but the operator must be able to point at a local LM Studio server (`base_url=http://localhost:1234/v1`) by editing config only.
- **No session crashes from upstream failure**: a DeepSeek outage must degrade, never raise to the operator.
- **Test isolation**: tests must not hit the real DeepSeek API (ADR-0001 forbidden pattern `network-dependent tests without isolation`).
- **No secret in source control**: the committed key in `models_config.json` must be remediated.

### Requirements

- One client abstraction for all LLM access, OpenAI-compatible, defaulting to DeepSeek.
- Secrets via env (`DEEPSEEK_API_KEY`) or local config, never hardcoded, never logged.
- Bounded, predictable failure behavior: provider error → `None` sentinel, no raise.
- Deterministic, network-free tests that assert prompt construction, response parsing, and the fallback path.
- A migration path to route LLM access through a clean-architecture port without breaking working entrypoints.

## Decision

All LLM access in MY-DOGE-MICRO flows through the OpenAI-compatible `openai` SDK via a single strategist component (Module #4 `DeepSeekStrategist`, and its future port successor). The contract is:

1. **OpenAI-compatible client abstraction**: instantiate `openai.OpenAI(api_key=..., base_url=...)`. DeepSeek (`https://api.deepseek.com`, `deepseek-chat`) is the default provider; any OpenAI-compatible server (LM Studio, etc.) works by swapping `base_url`/`model`/`api_key` in config. The strategist is the **only** place an `OpenAI(...)` client is constructed.
2. **Secrets via env/config, never code**: `api_key` is sourced from `DEEPSEEK_API_KEY` (preferred) or `models_config.json` profiles; it is passed only to the SDK constructor and never printed or logged.
3. **Single non-streaming chat-completions call per report**: `client.chat.completions.create(model, messages=[system, user], stream=False, temperature=<knob>)`. Streaming is not current behavior.
4. **No in-strategist retry; degrade to `None`**: provider/transport/empty errors are caught and the strategist returns `None`. Retry/timeout policy is owned by the client config (today: SDK defaults), to be made explicit in a follow-on; it is **not** re-implemented per call site.
5. **Structured prompt contract**: a fixed two-message schema (system persona + citation rules + RSRS/Vol Skew bands; user = market context + dashboard + last-5-days). See the CDD section 9.2 for the full schema.
6. **Lazy SDK import is permitted but not required**: `OpenAI(...)` construction performs no network call, so importing at module top is safe; tests mock the instance's `.client` attribute rather than the package import.
7. **No persistence by the client**: the strategist archives a Markdown report to disk but does not write to SQLite/DuckDB. A `macro_reports` table is a future storage-layer concern (Module #2/#7), gated on its own CDD.

### Architecture

```
CLI / GUI / (future) API
        |
        v
DeepSeekStrategist (src/macro/strategist.py)   <-- only LLM client construction
        |
        v
openai.OpenAI(api_key, base_url)  <-- OpenAI-compatible SDK
        |
        v
DeepSeek HTTP API  (default)   |   LM Studio / other OpenAI-compatible server  (swap via config)
        |
        v
chat.completions.create(model, messages=[system,user], stream=False, temperature)
        |
        v
response.choices[0].message.content  -->  format_report_for_display  -->  macro_report/<ts>.md
                                            (on Exception) --> return None (degraded, no raise)
```

### Key Interfaces

```python
# Current State — concrete class, no port yet (src/macro/strategist.py)
class DeepSeekStrategist:
    def __init__(self, config: MacroConfig) -> None:
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def generate_strategy_report(
        self, metrics: dict, market_data: pd.DataFrame
    ) -> Optional[str]:
        """Build prompt, call LLM once, return raw content; None on any error."""

    def format_report_for_display(
        self, raw_report: str, metrics: dict, start_date=None, end_date=None,
        assets=None, trading_days=None, calendar_days=None,
    ) -> str:
        """Prepend a header (title, risk badge, volatility, provenance) to raw_report."""

# Target (Migration) — clean-architecture port (post ADR-0001 migration)
# src/doge/core/ports/llm_client.py
# class ILLMClient(ABC):
#     @abstractmethod
#     def complete(self, system: str, user: str, *, model: str | None = None,
#                  temperature: float = 0.6, stream: bool = False) -> Optional[str]: ...
# DeepSeekAdapter(ILLMClient) wraps the SDK; strategist depends on the port.
```

### Implementation Guidelines

- Treat `temperature`, `stream`, `report_dir`, and an explicit `timeout` as configuration knobs (move out of `strategist.py` into `MacroConfig`/`settings.py`); they are currently hardcoded — recorded as an open migration item.
- Tests inject a `MagicMock` for `strategist.client` and assert on the captured `chat.completions.create(...)` kwargs and on `response.choices[0].message.content`. Never call the real API in tests (`tests/test_macro_strategist.py`).
- When extracting the port, keep the `complete(system, user) -> Optional[str]` shape so the strategist's prompt-building and report-formatting logic is reusable across providers.
- A provider/model bump must be validated by a live smoke before merging (the mock tests prove shape, not provider correctness).

## Alternatives Considered

### Alternative 1: Use the DeepSeek-specific SDK

- **Description**: import and use a DeepSeek-native Python client instead of the OpenAI-compatible path.
- **Pros**: slightly tighter provider coupling if DeepSeek adds non-standard features.
- **Cons**: loses the ability to point at LM Studio or any other OpenAI-compatible server without a second client; one more dependency; DeepSeek itself recommends the OpenAI-compatible endpoint.
- **Estimated Effort**: Medium.
- **Rejection Reason**: OpenAI-compatibility is DeepSeek's documented interface and gives free provider portability.

### Alternative 2: LangChain / LLM framework abstraction

- **Description**: introduce LangChain (or similar) to own the prompt + provider + retry stack.
- **Pros**: built-in retry, output parsers, provider catalogue.
- **Cons**: heavy dependency for a single call site; opaque retry/timeout behavior; couples a local-first tool to a fast-moving framework; violates the "stdlib-only Foundation, minimal surface for Core" stance.
- **Estimated Effort**: Medium now, high long-term (framework churn).
- **Rejection Reason**: the call surface is small and stable; a thin OpenAI-compatible client plus explicit degradation semantics is simpler and more testable.

### Alternative 3: Retry inside the strategist with exponential backoff

- **Description**: wrap `chat.completions.create` in a bounded retry loop like the yfinance adapter.
- **Pros**: more resilient to transient 5xx/429.
- **Cons**: retry policy diverges from the (future) shared client config; doubles operator wall-clock on outage; the current `None`-sentinel contract lets the caller decide whether to retry. The yfinance retry exists because rate limits are common and idempotent re-fetch is cheap — LLM calls are billed and non-idempotent, so retry should be an explicit operator choice.
- **Estimated Effort**: Low.
- **Rejection Reason**: retry belongs in a single client-config-owned place, not duplicated per call site; degrade-to-`None` is the documented contract today.

## Consequences

### Positive

- One, well-tested LLM call site; every future AI feature routes through it.
- Provider swap is a config change, not a code change (DeepSeek ↔ LM Studio ↔ any OpenAI-compatible server).
- Secrets stay out of source code by contract; the committed-key violation becomes a tracked remediation, not an accepted pattern.
- Deterministic, network-free tests cover prompt construction, response parsing, and the offline fallback (BUG E).
- The degrade-to-`None` contract matches the rest of the platform's offline-tolerance principle (ADR-0001/ADR-0004).

### Negative

- No in-strategist retry means a transient 5xx yields an immediate `None`; the operator must re-run.
- No explicit client timeout today — a hung provider could block until the SDK default fires.
- The OpenAI-compatible shape is provider-specific; a provider that drifts from the OpenAI schema could break the strategist with no compile-time signal.
- Hardcoded `temperature`/`stream`/`report_dir` remain until the config-consolidation migration.

### Neutral

- `stream=False` means the whole report arrives at once; large reports block. Acceptable for a single-report-per-run local tool.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Committed `models_config.json` API key is leaked | Low (Mitigated as of S002-013) | High | Remediation DONE (S002-013): replaced with `REPLACE_WITH_DEEPSEEK_API_KEY` placeholder, `DEEPSEEK_API_KEY` env var is the primary source, `MacroConfig` raises `RuntimeError` on a missing/placeholder key, and `GET /api/config` redacts `api_key` from the HTTP response. Residual: the historical key is in git history — operator must revoke+reissue in the DeepSeek console (documented in `docs/MCP_SERVER.md`); history rewrite intentionally not performed. |
| Provider API shape change breaks strategist | Medium | Medium | Pin `openai==1.62.0`; mock tests catch request-shape drift on dependency bump; live smoke before model bumps |
| No client timeout hangs the session on provider outage | Medium | Medium | Add explicit `timeout` to `OpenAI(...)` as part of config consolidation |
| Hardcoded `temperature` violates config rules | High (current state) | Low | Move to `MacroConfig`/`settings.py` (migration target) |
| Operator expects retry; gets `None` on first 5xx | Medium | Low | Document the contract here and in the CDD; optional follow-on adds bounded retry behind a knob |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|---------------|--------|
| LLM call latency | Provider-bound, unbounded timeout | Same (provider-bound); explicit timeout added | Single call; whole CLI run bounded by caller (e.g. MCP 30s) |
| Token cost per report | Prompt scales with 5 rows + indicators (~1–2k tokens) + response (~1–2k tokens) | Same | Bounded by fixed prompt schema |
| Test speed | Network-dependent, minutes | ~6s for 9 mocked tests (measured) | Local iteration friendly |
| Offline run cost | Caller-dependent | `None` after first failure (no retry) | Bounded by yfinance retry (3 × 5s) + 0 LLM calls |

## Migration Plan

1. **DONE** — Document the OpenAI-compatible client strategy (this ADR) and the macro CDD; add `tests/test_macro_strategist.py` (BUG E, 9/9 green) mocking the OpenAI client.
2. **DONE (S002-013)** — **Secrets remediation** — removed the committed key from `models_config.json`, replaced with the `REPLACE_WITH_DEEPSEEK_API_KEY` placeholder (template aligned to the same sentinel), promoted `DEEPSEEK_API_KEY` env var to primary source with a `RuntimeError` on missing/placeholder, redacted `api_key` from the `GET /api/config` HTTP response, and removed the GUI's JSON-key-injection line. `models_config.json` was already in `.gitignore`; the operator revocation+reissue of the historically-committed key is documented in `docs/MCP_SERVER.md` (history rewrite intentionally not performed).
3. **Config consolidation** — move `temperature`, `stream`, `timeout`, `report_dir` out of `strategist.py` into `MacroConfig`/`settings.py` (ADR-0002 scope); fold `DEEPSEEK_*` and `models_config.json` under `settings.py`.
4. **Port extraction** — introduce `ILLMClient` (`src/doge/core/ports/llm_client.py`) with `complete(system, user) -> Optional[str]`; implement `DeepSeekAdapter(ILLMClient)` wrapping the SDK; refactor the strategist to depend on the port.
5. **Optional bounded retry** — if operator demand exists, add a config-owned retry/timeout to the adapter (not the strategist), keeping the degrade-to-`None` contract.
6. **Report persistence** — add a `macro_reports` table and an `IReportRepository` (Module #2/#7) so runs become queryable; gated on its own CDD.

**Rollback plan**: The strategist and SDK are additive. If a port extraction breaks a caller, route that caller back to `DeepSeekStrategist` directly while the port contract is fixed. The OpenAI-compatible client choice is independent of the port layer and does not roll back.

## Validation Criteria

- [ ] `DeepSeekStrategist.generate_strategy_report` issues exactly one `chat.completions.create` with the documented kwargs (verified — `tests/test_macro_strategist.py`).
- [ ] The constructed prompt embeds all configured asset tickers, the citation slots, and the RSRS/Vol Skew dashboard (verified).
- [ ] Provider error → `generate_strategy_report` returns `None`, never raises (verified).
- [ ] Empty-content response → fixed message returned (verified).
- [ ] No test in `tests/test_macro_strategist.py` performs a real network call (verified — all `MagicMock`).
- [ ] `python -m pytest tests/test_macro_strategist.py -q` passes 9/9 (verified — ~6s).
- [x] Committed API key removed from `models_config.json` (DONE — S002-013: placeholder swap + env-primary read + HTTP redaction; operator revocation of the historical key documented in `docs/MCP_SERVER.md`).
- [ ] `temperature`/`stream`/`timeout`/`report_dir` moved to config (OPEN — migration).
- [ ] `ILLMClient` port extracted and strategist depends on it (OPEN — Module #12).

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|--------------|--------|-------------|---------------------------|
| `design/cdd/macro-strategy-engine.md` | Macro Strategy Engine | "Keep the operator's API key and provider configuration out of source code (env + `models_config.json` only) and never print a real key to logs or stdout" (User Promise) | Decision items 2 and 7; secrets-via-env contract. |
| `design/cdd/macro-strategy-engine.md` | Macro Strategy Engine | "Degrade safely when the LLM provider is unreachable or errors: return a sentinel (`None`)" (User Promise) | Decision item 4 mandates the degrade-to-`None` contract. |
| `design/cdd/macro-strategy-engine.md` | Macro Strategy Engine | "Allow the operator to switch providers/models ... without editing Python source" (User Promise) | Decision items 1 and 3 — OpenAI-compatible abstraction + config-driven `base_url`/`model`. |
| `design/cdd/macro-strategy-engine.md` | Macro Strategy Engine | Section 9 Integration Requirements — LLM client strategy, prompt schema, retry budget, offline fallback | This ADR is the authoritative record for all four subsections. |
| `design/cdd/module-index.md` | AI Industry Analysis (#6) / Clean Architecture Migration (#12) | "the project's LLM lives in Macro Strategy Engine (#4), not #6" | Decision item 1 fixes the single LLM client construction site, resolving the naming confusion (Bug C context). |

## Related

- [ADR-0001: Brownfield Clean Architecture Migration](adr-0001-brownfield-clean-architecture.md) — defines the port/adapter layer and forbidden patterns this client must respect (target `ILLMClient` port).
- [ADR-0002: Centralized Runtime Configuration](adr-0002-centralized-configuration.md) — records that `DEEPSEEK_*` / `models_config.json` live outside `settings.py`; this ADR's migration plan consolidates them.
- [ADR-0004: Data Source Adapter Contract](adr-0004-data-source-adapter-contract.md) — sibling pattern (external-access adapter contract) that this LLM-client strategy mirrors for AI access.
- `src/macro/strategist.py`, `src/macro/config.py` — the current implementation.
- `tests/test_macro_strategist.py` — network-free unit tests (BUG E).
- `design/cdd/macro-strategy-engine.md` — full module CDD.
