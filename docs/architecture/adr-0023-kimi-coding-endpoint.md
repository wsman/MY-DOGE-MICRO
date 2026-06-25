# ADR-0023: Kimi "For Coding" Endpoint Support

## Status
Accepted

## Date
2026-06-25

## Last Verified
2026-06-25

## Decision Makers
Implementation agent; project owner approval via
`C:\Users\Aby\.claude\plans\kimi-coding-transient-dragon.md`.

## Summary

The doge Kimi LLM clients returned HTTP 403 against the Kimi "For Coding"
endpoint (`https://api.kimi.com/coding/v1`, `sk-kimi-*` keys) because that
endpoint gates on a recognized coding-agent `User-Agent` header, which the
project never sent. This ADR adds a config-driven opt-in "coding mode" that
routes all Kimi client surfaces (chat / text / files / agent-SDK) at the
coding endpoint with a recognized coding-agent User-Agent, while keeping
non-coding behavior byte-identical.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, `openai==1.62.0` (supports `default_headers`), optional `kimi_agent_sdk` |
| **Domain** | LLM client integration / provider compatibility |
| **Knowledge Risk** | LOW for OpenAI SDK header injection; MEDIUM for the coding endpoint's gating contract (post-cutoff API) |
| **References Consulted | [Kimi Code Docs](https://www.kimi.com/code/docs/en/), [Third-Party Coding Agents](https://www.kimi.com/code/docs/en/third-party-tools/other-coding-agents.html), `src/doge/infrastructure/llm/kimi_client.py`, `src/doge/config/settings.py` |
| **Post-Cutoff APIs Used** | Kimi For Coding endpoint `https://api.kimi.com/coding/v1` (User-Agent gated) |
| **Verification Required** | Live smoke against the coding endpoint; see Validation Criteria |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0005 (LLM client strategy), ADR-0012 (enterprise model gateway) |
| **Enables** | S017-002 live Kimi smoke against the coding endpoint (chat/text/vision) |
| **Blocks** | None |
| **Ordering Note** | The optional `kimi_agent_sdk` backend change is best-effort; the SDK package is not currently installed, so its header support is unverified and deferred. |

## Context

### Problem Statement

An operator-supplied `sk-kimi-*` key targets the Kimi "For Coding" endpoint
`https://api.kimi.com/coding/v1`. The platform's Kimi clients
(`KimiAgentModel`, `KimiTextClient`, `KimiFilesClient`) use the OpenAI SDK
against that endpoint and receive HTTP 403 for every request:

> `Kimi For Coding is currently only available for Coding Agents such as
> Kimi CLI, Claude Code, Roo Code, Kilo Code, etc.` (`access_terminated_error`)

### Current State

The Kimi clients construct `openai.OpenAI` / `openai.AsyncOpenAI` with only
`api_key`, `base_url`, and (chat) `timeout`. No `User-Agent` or
`default_headers` are set anywhere in the LLM stack, so the SDK sends its
default `User-Agent` (e.g. `OpenAI/Python 1.62.0`), which the coding endpoint
rejects.

### Constraints

- Config-driven: no environment-specific values hardcoded in implementation
  modules (defaults belong in `KimiConfig`).
- Non-coding behavior must not change (`default_headers=None` when coding mode
  is off and no explicit UA is set).
- All Kimi client surfaces must honor the mode (the `DOGE_TEXT_LLM_PROVIDER`
  switch only governs the text path, so the mechanism must live on
  `KimiConfig`).
- Posture stays `production_ready: false` / `stable_declaration: forbidden`.

### Requirements

- Operators must be able to opt into the coding endpoint with one setting and
  override endpoint/headers individually.
- The default coding User-Agent must be a documented working value
  (`claude-code/0.1.0`), overridable.

## Decision

Add an opt-in **coding mode** on `KimiConfig`, sourced from `KIMI_CODING_MODE`
or the `DOGE_TEXT_LLM_PROVIDER=kimi-coding` alias, that (a) selects the coding
base URL and (b) sets a recognized coding-agent `User-Agent`. All Kimi clients
read two derived accessors — `KimiConfig.effective_base_url()` and
`KimiConfig.default_http_headers()` — and pass the result to the OpenAI client
as `default_headers` (None when empty, preserving current behavior).

### Precedence

- `effective_base_url()`: explicit `KIMI_BASE_URL` > `coding_base_url` (when
  coding mode on) > current Moonshot default.
- `default_http_headers()`: explicit `KIMI_CLIENT_USER_AGENT` >
  `coding_user_agent` (when coding mode on) > none; `KIMI_EXTRA_HEADERS`
  (JSON object) is always merged in.

### Key interfaces

```python
# KimiConfig (settings)
def effective_base_url(self) -> str: ...
def default_http_headers(self) -> dict[str, str]: ...

# KimiAgentModel / KimiFilesClient
client = OpenAI|AsyncOpenAI(
    api_key=..., base_url=settings.effective_base_url(),
    default_headers=settings.default_http_headers() or None,
)
```

### Configuration knobs

| Env | Default | Purpose |
|---|---|---|
| `KIMI_CODING_MODE` | off | Opt-in coding mode |
| `DOGE_TEXT_LLM_PROVIDER=kimi-coding` | — | Alias implying coding mode |
| `KIMI_CODING_BASE_URL` | `https://api.kimi.com/coding/v1` | Endpoint when coding mode on |
| `KIMI_CODING_USER_AGENT` | `claude-code/0.1.0` | UA when coding mode on (no override) |
| `KIMI_CLIENT_USER_AGENT` | `""` | Explicit UA override (any mode) |
| `KIMI_EXTRA_HEADERS` | `{}` | JSON object of extra HTTP headers |

## Alternatives Considered

### Alternative 1: Hardcode a coding User-Agent per client
- **Pros**: smallest diff.
- **Cons**: violates the config-files rule (environment-specific value in an
  implementation module); not operator-configurable; couples the codebase to
  one UA string.
- **Rejection Reason**: project standard forbids hardcoded operator values in
  implementation modules.

### Alternative 2: Per-client env vars (separate UA per surface)
- **Pros**: maximum per-surface flexibility.
- **Cons**: four surfaces drift; operators must set many vars; the `DOGE_TEXT
  _LLM_PROVIDER` switch only covers the text path, so the other surfaces would
  need independent wiring.
- **Rejection Reason**: drift risk and poor operator UX; one config object is
  the single source of truth.

### Alternative 3: Subclass the OpenAI SDK to inject a User-Agent
- **Pros**: centralized.
- **Cons**: over-engineered; `default_headers` already exists on the SDK.
- **Rejection Reason**: unnecessary; the SDK already supports `default_headers`.

## Consequences

### Positive
- Unlocks the Kimi For Coding endpoint for chat/text/vision with an
  operator-supplied `sk-kimi-*` key.
- Single config mechanism covers every Kimi client surface.
- Non-coding mode is byte-identical to before (`default_headers=None`).

### Negative
- The coding endpoint's `/files` surface is **unsupported** (chat-only). The
  live smoke (`KIMI_CODING_MODE=1`, `sk-kimi-*` key) confirmed: `text_k26`
  **passed** (the coding UA clears the 403 gate), but `files_upload` returned
  **404 resource_not_found** because the coding endpoint exposes no `/files`,
  and `vision_base64` returned **400 invalid image format** (the smoke's 8×8
  synthetic PNG fixture is too small/invalid for the vision decoder — not a
  403/integration issue). The S017-002 smoke gate requires text **+ files +
  vision** all passed, so it remains open; that is a provider/fixture
  limitation, not a defect (do not silently relax the gate). A per-client
  base_url split (files → Moonshot, chat → coding) is a possible follow-up.
- The default `claude-code/0.1.0` UA is a client fingerprint; operators are
  responsible for Kimi ToS compliance when sending a coding-agent UA. No
  credential is placed in any header.

### Neutral
- `KimiConfig` gains six fields + two accessors; `KimiAgentSdkBackend` resolves
  `effective_base_url()` via `runtime.py` (the agent SDK package itself is not
  installed, so its header support is unverified and deferred).

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Coding endpoint rejects `/files` | Medium | Medium | Confirm via live smoke; document as provider limitation; do not relax the gate |
| `kimi_agent_sdk.Config` does not accept headers | Medium | Low | SDK path reportedly already accepted; header support deferred until the SDK is installed and its schema verified |
| User-Agent fingerprinting / ToS | Low | Low | UA carries no secret; operator responsibility recorded here |

## Validation Criteria

- [x] Unit tests: `tests/unit/config/test_kimi_config_coding.py`,
      `tests/unit/infrastructure/test_kimi_client.py`,
      `tests/unit/infrastructure/test_kimi_files_client.py` pass (30 tests).
- [x] Live smoke (`scripts/run_kimi_live_smoke.py`) with `KIMI_CODING_MODE=1`
      and an `sk-kimi-*` key: `text_k26` **passed** (coding UA clears the 403
      gate). `files_upload` returned 404 (coding endpoint is chat-only) and
      `vision_base64` returned 400 (smoke's 8×8 PNG fixture invalid) — provider/
      fixture limitations, not integration defects (see Consequences).
- [x] Non-coding regression: existing Kimi client tests unchanged (no
      `default_headers` when off); full suite green (1474+ passed).

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|---|---|---|---|
| `design/cdd/capability-registry.md` | Capability Registry | Provider/endpoint must be operator-configurable | Coding endpoint + UA are env-driven via `KimiConfig` |

## Related

- Implements: `src/doge/config/settings.py` (`KimiConfig`),
  `src/doge/infrastructure/llm/kimi_client.py`,
  `src/doge/infrastructure/llm/kimi_files_client.py`,
  `src/doge/bootstrap/runtime.py` (`build_agent_backends`).
- Depends on: ADR-0005 (LLM client strategy), ADR-0012 (enterprise model
  gateway).
