# Kimi Live Smoke Evidence

Generated: 2026-06-25T05:19:16.613901+00:00
Result: PASSED

## Scope

S017-002 live Kimi smoke for required text + Vision/file-Q&A, optional Files upload, and optional Agent SDK.
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
| text_k26 | passed | kimi-k2.6 / financial_research | 1733.94 ms |
| files_upload | skipped | kimi-k2.6 / document_extract |  ms |
| vision_base64 | passed | kimi-k2.6 / vision_analysis | 1525.87 ms |
