# Kimi Live Smoke Evidence

Generated: 2026-06-29T05:31:04.449188+00:00
Result: PASSED

## Scope

S017-002 live Kimi smoke for Kimi Coding v1 (required text + Vision; optional Files and Agent SDK with documented status).
Evidence is intentionally redacted: no API key, raw prompt, raw file id, or sensitive fixture content is stored.

## Environment

- DOGE_LIVE_KIMI: `True`
- MOONSHOT_API_KEY_PRESENT: `True`
- DOGE_LIVE_KIMI_AGENT_SDK: `False`
- kimi_agent_sdk_installed: `False`
- General model: `kimi-k2.6`

## Scenarios

| Scenario | Status | Model/Profile | Latency |
|---|---|---|---|
| text_k26 | passed | kimi-k2.6 / financial_research | 2838.8 ms |
| files_upload | skipped | kimi-k2.6 / document_extract |  ms |
| vision_base64 | passed | kimi-k2.6 / vision_analysis | 3078.63 ms |
| agent_sdk_optional | skipped |  /  |  ms |
