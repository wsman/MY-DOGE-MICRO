# Sprint C CDD: Kimi Live Smoke Closure

> Status: Accepted
> Story: S017-002
> Gate: Kimi Coding v1 (required text + Vision; optional Files + Agent SDK)

## Overview

Sprint C closes the S017-002 external validation gate for live Kimi integration.
The project already has a local adapter layer for Kimi chat, Files, Vision, and
the optional Agent SDK; this sprint focuses on executing a redacted, operator-
controlled live smoke against the real Moonshot/Kimi endpoint and recording the
result so that runtime maturity can honestly advance the Kimi live-smoke gate.

Because the primary Kimi endpoint used by the product is Kimi Coding v1
(`https://api.kimi.com/coding/v1` via OpenAI-compatible chat), the Files API is
not available on that endpoint and the Agent SDK is an optional add-on. Sprint C
therefore defines a **Kimi Coding v1 closure gate**: text chat and Vision/base64
are required to pass; Files upload and Agent SDK are optional but must be
documented with a skipped status and reason when they are not exercised.

## User Promise / JTBD

As an operator, I need confidence that the Research Agent's live Kimi path
(text, Vision, optional Files/Agent SDK) works against the real provider before
I enable it for my local workflows. The product must:

- Provide a deterministic, env-gated live smoke runner.
- Record only redacted evidence (no API keys, raw prompts, raw file IDs).
- Validate the evidence shape automatically.
- Distinguish between "local implementation ready" and "live execution passed"
  so that maturity labels remain honest.

## Detailed Behavior

### Runner

`scripts/run_kimi_live_smoke.py` is the live smoke runner.

- It is **blocked by default**. It only executes when:
  - `DOGE_LIVE_KIMI=1` is set explicitly by the operator.
  - `MOONSHOT_API_KEY` is present in the environment.
- It runs four scenarios:
  1. `text_k26` — simple text completion through `KimiAgentModel`.
  2. `files_upload` — file upload/list/delete through `KimiFilesClient`.
  3. `vision_base64` — base64 image chat through `KimiAgentModel`.
  4. `agent_sdk_optional` — optional Agent SDK chat through `KimiAgentSdkBackend`.
- With `--coding-v1`, the runner labels the evidence with `gate: coding-v1` and
  treats `files_upload` and `agent_sdk_optional` as optional scenarios. A skipped
  optional scenario must include a `reason`.
- The runner captures per-scenario latency, token usage, finish reasons, and
  redacted file-id hashes.
- The runner writes both a JSON evidence file and a Markdown summary under
  `production/qa/evidence/live/`.

### Validator

`scripts/validate_kimi_live_smoke_evidence.py` checks the evidence file.

- Default mode requires all four scenarios to pass (full closure).
- `--coding-v1` mode requires:
  - `text_k26` and `vision_base64` passed.
  - `files_upload` and `agent_sdk_optional` present with status `passed` or
    `skipped` + `reason`.
- `--allow-blocked` permits `result: blocked` evidence for readiness tracking.
- The validator rejects raw file IDs, API keys, bearer tokens, unresolved
  placeholders, and missing redaction flags.

### Tests

- `tests/live/test_kimi_live_smoke.py` contains pytest cases gated by
  `DOGE_LIVE_KIMI=1`.
- `tests/unit/qa/test_validate_kimi_live_smoke_evidence.py` validates the
  validator itself with synthetic fixtures.

## Contracts / Data Model

### Evidence JSON schema

```json
{
  "schema": "doge.kimi_live_smoke.v1",
  "story_id": "S017-002",
  "created_at": "ISO-8601 timestamp",
  "result": "passed | failed | blocked",
  "gate": "coding-v1 | null",
  "environment": {
    "DOGE_LIVE_KIMI": true,
    "MOONSHOT_API_KEY_PRESENT": true,
    "DOGE_LIVE_KIMI_AGENT_SDK": false,
    "kimi_agent_sdk_installed": false,
    "base_url": "https://api.moonshot.ai/v1",
    "general_model": "kimi-k2.6",
    "vision_image_supplied": true
  },
  "redaction": {
    "api_key_recorded": false,
    "raw_file_id_recorded": false,
    "raw_prompt_recorded": false,
    "sensitive_fixture_used": false
  },
  "scenarios": [
    {
      "name": "text_k26",
      "status": "passed",
      "profile": "financial_research",
      "model": "kimi-k2.6",
      "latency_ms": 120.5,
      "event_count": 1,
      "response_chars": 17,
      "finish_reasons": ["stop"],
      "usage": { "reported": true, "prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16 }
    }
  ]
}
```

### Optional skipped scenario contract

```json
{
  "name": "files_upload",
  "status": "skipped",
  "profile": "document_extract",
  "model": "kimi-k2.6",
  "reason": "configured Kimi endpoint does not support the Files API",
  "usage": { "reported": false, "reason": "files_upload_optional_not_supported" }
}
```

## Edge Cases

- **Missing API key**: runner exits with `result: blocked` and lists blockers.
- **Kimi Coding v1 endpoint lacks Files API**: `files_upload` is skipped with
  reason; evidence can still pass under `--coding-v1`.
- **Agent SDK not installed**: `agent_sdk_optional` is skipped with reason
  `kimi_agent_sdk is not installed`; evidence can still pass under `--coding-v1`.
- **Network/provider failure**: individual scenario is marked `failed` with a
  redacted error; overall result is `failed`.
- **Raw secret leak**: validator rejects any evidence containing bearer tokens,
  `sk-*` keys, or raw `file_id` values.
- **Stale placeholders**: validator rejects unresolved template tokens such as
  `YYYY-MM-DD` in `created_at`.

## Dependencies

- `src/doge/infrastructure/llm/kimi_client.py` — `KimiAgentModel` text/Vision chat.
- `src/doge/infrastructure/llm/kimi_files_client.py` — `KimiFilesClient` upload/list/delete.
- `src/doge/infrastructure/agent/backends.py` — `KimiAgentSdkBackend` optional Agent SDK.
- `src/doge/infrastructure/agent/kimi_sdk_adapter.py` — semantic adapter used by backend.
- `scripts/evidence_placeholders.py` — placeholder rejection.
- `scripts/evidence_redaction.py` — secret-leak rejection.
- `docs/progress/runtime-maturity.yaml` — records the gate status.
- `production/sprints/sprint-017-external-validation-and-provider-hardening.md` —
  parent sprint plan.

## Configuration Knobs

| Variable | Default | Purpose |
|---|---|---|
| `DOGE_LIVE_KIMI` | `0` / unset | Master gate; must be `1` to run live smoke. |
| `MOONSHOT_API_KEY` | unset | Operator-owned API key (never logged or committed). |
| `DOGE_LIVE_KIMI_AGENT_SDK` | `0` / unset | Set to `1` to exercise optional Agent SDK scenario. |
| `KIMI_GENERAL_MODEL` | `kimi-k2.6` | Model used for all scenarios. |
| `KIMI_BASE_URL` | `https://api.moonshot.ai/v1` | Provider base URL. |
| `DOGE_LIVE_KIMI_VISION_IMAGE` | unset | Optional JPEG/PNG/WEBP path for vision smoke. |

## Acceptance Criteria

1. `scripts/run_kimi_live_smoke.py --coding-v1` exists and emits blocked evidence
   with `gate: coding-v1` when env gates are missing.
2. `scripts/validate_kimi_live_smoke_evidence.py --coding-v1` passes for evidence
   with `text_k26` + `vision_base64` passed and optional scenarios documented
   (passed or skipped with reason).
3. `tests/unit/qa/test_validate_kimi_live_smoke_evidence.py` covers coding-v1
   pass, missing optional, skipped-without-reason, and required-failure cases.
4. The existing historical evidence
   `production/qa/evidence/live/kimi-live-smoke-2026-06-22.json` and blocked
   readiness evidence are retained; passed Kimi Coding v1 evidence is generated
   at `production/qa/evidence/live/kimi-live-smoke-2026-06-29.json`.
5. `docs/progress/runtime-maturity.yaml` records a new `sprint_c_*` gate for
   Kimi Coding v1 local readiness and live execution as `passed`.
6. A Sprint C acceptance report is created and records **GO** after strict
   validation passes without `--allow-blocked`.
7. No `production_ready`, `stable_declaration`, or Level 3 maturity promotion is
   introduced.
