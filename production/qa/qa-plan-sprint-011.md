# QA Plan Sprint 011 - Web SSE And SDK Streaming Reliability

Generated: 2026-06-21

## Scope

Sprint 011 validates Research Agent client streaming paths: Web helper usage of
v1 SSE, TypeScript SDK reconnect/backoff, Python SDK sync reconnect, and Python
async streaming. It does not validate full browser/manual reconnect evidence or
remote CI.

## Test Strategy

| Area | Required Evidence | Automated Test |
|---|---|---|
| Web create flow | New runs stream until display-ready instead of polling | `web/src/__tests__/agentApi.spec.ts` |
| Web approval flow | Queued approval responses continue via stream with `Last-Event-ID` | `web/src/__tests__/agentApi.spec.ts` |
| Web store compatibility | Store still exposes approvals and memo after helper changes | `web/src/__tests__/agentStore.spec.ts` |
| TypeScript SDK reconnect | Stream reconnects after a network failure and preserves `Last-Event-ID` | `packages/doge-sdk-typescript/src/__tests__/client.spec.ts` |
| Python sync SDK reconnect | Stream reconnects after `httpx` network failure and preserves `Last-Event-ID` | `tests/contract/test_python_sdk.py` |
| Python async SDK | `AsyncDogeClient` can create a session, create a turn, and async-iterate SSE | `tests/contract/test_python_sdk.py` |

## Manual Smoke

```powershell
$nodeDir = Join-Path $env:TEMP 'codex-node-v24.17.0\node-v24.17.0-win-x64'
$env:PATH = "$nodeDir;$env:PATH"
.\.venv\Scripts\python.exe -m pytest tests/contract/test_python_sdk.py -q
cd packages\doge-sdk-typescript; npm test -- --run src/__tests__/client.spec.ts
cd ..\..\web; npm test -- --run src/__tests__/agentApi.spec.ts src/__tests__/agentStore.spec.ts
```

Optional browser smoke:

```text
1. Start the daemon and Web app.
2. Start a Research Agent run.
3. Approve a pending action.
4. Interrupt/reconnect the browser stream.
5. Confirm the UI catches up from event history without manual refresh.
```

## Exit Criteria

- Targeted Python/Web/TypeScript tests pass.
- Full Web test/build and TypeScript SDK test/build pass before merge.
- No Web code path uses post-approval polling.
- Stable remains forbidden until the rest of the roadmap gates pass.

## Remaining QA Gaps

- Browser/manual reconnect evidence is not captured.
- Remote CI is pending.
- Python packaging release notes for async client are not published.
