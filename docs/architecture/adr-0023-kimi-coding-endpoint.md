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

The first v1 release standard uses the Kimi "For Coding" endpoint
(`https://api.kimi.com/coding/v1`, `sk-kimi-*` keys) as the default live
Kimi path for chat-centered model work: Research Agent runs, text/report
generation, tool/function calling, thinking mode, and model routing. The
endpoint gates on a recognized coding-agent `User-Agent` header, which the
project previously did not send.

This ADR adds a config-driven opt-in "coding mode" for chat/text model
clients while making the release boundary explicit: the coding endpoint is
chat-centered and does **not** provide Kimi `/files`. Document upload and
evidence extraction must therefore use the local parser/local evidence store
for v1 unless an operator supplies a separate ordinary Moonshot key and a
future split-client implementation routes files to Moonshot.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, `openai==1.62.0` (supports `default_headers`), optional `kimi_agent_sdk` |
| **Domain** | LLM client integration / provider compatibility |
| **Knowledge Risk** | LOW for OpenAI SDK header injection; MEDIUM for the coding endpoint's gating contract (post-cutoff API) |
| **References Consulted** | [Kimi Code Docs](https://www.kimi.com/code/docs/en/), [Third-Party Coding Agents](https://www.kimi.com/code/docs/en/third-party-tools/other-coding-agents.html), `src/doge/infrastructure/llm/kimi_client.py`, `src/doge/infrastructure/llm/kimi_files_client.py`, `src/doge/config/settings.py` |
| **Post-Cutoff APIs Used** | Kimi For Coding endpoint `https://api.kimi.com/coding/v1` (User-Agent gated) |
| **Verification Required** | Live smoke against the coding endpoint; see Validation Criteria |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0005 (LLM client strategy), ADR-0012 (enterprise model gateway) |
| **Enables** | v1 Kimi Coding release baseline for chat/text/tool-calling/thinking/model-routing; S017-002 text smoke against the coding endpoint |
| **Blocks** | None |
| **Ordering Note** | Kimi `/files` is excluded from the v1 coding baseline. The optional `kimi_agent_sdk` backend remains unverified because the SDK package is not installed. |

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
- The first release must clearly distinguish coding-supported capabilities
  from unsupported Kimi `/files` behavior.
- Local document parsing, SQLite evidence persistence, and local vector/RAG
  lookup must continue working when Kimi Coding is enabled.

## Decision

Add an opt-in **coding mode** on `KimiConfig`, sourced from `KIMI_CODING_MODE`
or the `DOGE_TEXT_LLM_PROVIDER=kimi-coding` alias, that (a) selects the coding
base URL for chat/text model clients and (b) sets a recognized coding-agent
`User-Agent`. Kimi chat/text clients read two derived accessors —
`KimiConfig.effective_base_url()` and `KimiConfig.default_http_headers()` —
and pass the result to the OpenAI client as `default_headers` (None when empty,
preserving current behavior).

`KimiFilesClient` may still be used for ordinary Moonshot `/files` endpoints,
but when its effective base URL is the coding endpoint it must report
`supports_files_api=False` and must fail fast with a local unsupported-files
error if called directly. `FileUploadService` treats that capability flag as a
signal to skip Kimi-side upload and fall back to local parsing.

### V1 Release Capability Matrix

| Capability | Kimi Coding v1 status | Notes |
|---|---|---|
| Research Agent chat / run execution | Supported | `KimiAgentModel.chat` via OpenAI-compatible `chat/completions`. |
| Report generation | Supported | `KimiTextClient` shares the chat path. |
| Tool / function calling | Supported | Coding model supports the existing tool-call flow. |
| Thinking mode | Supported | `kimi-k2.6` thinking path remains chat-centered. |
| Model routing | Supported | General model `kimi-k2.6`; code model `kimi-k2.7-code`. |
| Kimi `/files` upload/content/delete | Not supported | Coding endpoint has no `/files`; use local parser/evidence store for v1. |
| Kimi-side file context | Not supported | Requires future split-client support with an ordinary Moonshot key. |
| Vision / multimodal image input | Supported (verified) | Verified with a real 640×640 JPEG via `DOGE_LIVE_KIMI_VISION_IMAGE`; the earlier failure was the smoke's pathologically tiny 8×8/10×10 synthetic PNG, which the vision decoder rejects as an invalid image. |
| Optional Agent SDK backend | Out of scope | `kimi_agent_sdk` is not installed in the current environment. |

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

# KimiAgentModel / KimiTextClient
client = OpenAI|AsyncOpenAI(
    api_key=..., base_url=settings.effective_base_url(),
    default_headers=settings.default_http_headers() or None,
)

# KimiFilesClient
supports_files_api: bool
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
- Establishes Kimi Coding as the v1 live Kimi release baseline for the
  chat-centered capabilities that have been verified or fit the endpoint:
  research runs, text/report generation, function calling, thinking mode, and
  model routing.
- Single config mechanism covers Kimi chat/text client routing and headers.
- Non-coding mode is byte-identical to before (`default_headers=None`).

### Negative
- The coding endpoint's `/files` surface is **unsupported** (chat-only). The
  live smoke (`KIMI_CODING_MODE=1`, `sk-kimi-*` key) confirmed: `text_k26`
  **passed** (the coding UA clears the 403 gate) and `vision_base64`
  **passed** with a real 640×640 JPEG (`DOGE_LIVE_KIMI_VISION_IMAGE`), but
  `files_upload` returned **404 resource_not_found** because the coding
  endpoint exposes no `/files`. The earlier `vision_base64` 400 was the
  smoke's pathologically tiny 8×8 synthetic PNG, not an integration issue.
  S017-002 now treats `/files` as an optional capability observation for the
  Kimi Coding v1 gate: text + Vision must pass, while `files_upload` may be
  recorded as skipped/failed when the configured endpoint is chat-only. If a
  `/files`-capable Moonshot key is supplied and `files_upload` passes, the
  evidence validator still requires a redacted file id hash and cleanup
  confirmation. A per-client base_url split (files → Moonshot, chat → coding)
  remains a possible follow-up.
- Kimi-side document context is unavailable in the v1 coding baseline. API/CLI
  document attachment remains supported through local payload storage,
  `LocalDocumentParser`, SQLite evidence records, and local vector/RAG lookup.
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
| Coding endpoint rejects `/files` | High | Low | Disable Kimi Files locally in coding mode; use local parser/evidence store; record Files as an optional capability observation for S017-002 |
| `kimi_agent_sdk.Config` does not accept headers | Medium | Low | SDK path reportedly already accepted; header support deferred until the SDK is installed and its schema verified |
| User-Agent fingerprinting / ToS | Low | Low | UA carries no secret; operator responsibility recorded here |

## Validation Criteria

- [x] Unit tests: `tests/unit/config/test_kimi_config_coding.py`,
      `tests/unit/infrastructure/test_kimi_client.py`,
      `tests/unit/infrastructure/test_kimi_files_client.py` pass (30 tests).
- [x] Coding endpoint Files behavior: `KimiFilesClient.supports_files_api`
      is false for `https://api.kimi.com/coding/v1`, and `FileUploadService`
      falls back to local parsing instead of marking text attachments failed.
- [x] Live smoke (`scripts/run_kimi_live_smoke.py`) with `KIMI_CODING_MODE=1`
      and an `sk-kimi-*` key: `text_k26` **passed** (coding UA clears the 403
      gate) and `vision_base64` **passed** with a real 640×640 JPEG
      (`DOGE_LIVE_KIMI_VISION_IMAGE`). `files_upload` returned 404 (coding
      endpoint is chat-only) and is now optional for the Kimi Coding v1 gate;
      this remains a provider capability limitation, not an integration defect
      (see Consequences).
- [x] Non-coding regression: existing Kimi client tests unchanged (no
      `default_headers` when off); full suite green (1474+ passed).

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|---|---|---|---|
| `design/cdd/capability-registry.md` | Capability Registry | Provider/endpoint must be operator-configurable | Coding endpoint + UA are env-driven via `KimiConfig` |
| `design/cdd/document-evidence-pipeline.md` | Document Evidence Pipeline | Evidence should remain locally grounded when providers are unavailable or incomplete | Coding mode skips unsupported Kimi `/files` and preserves local document parsing/evidence storage |

## Related

- Implements: `src/doge/config/settings.py` (`KimiConfig`),
  `src/doge/infrastructure/llm/kimi_client.py`,
  `src/doge/infrastructure/llm/kimi_files_client.py`,
  `src/doge/bootstrap/runtime.py` (`build_agent_backends`).
- Depends on: ADR-0005 (LLM client strategy), ADR-0012 (enterprise model
  gateway).
