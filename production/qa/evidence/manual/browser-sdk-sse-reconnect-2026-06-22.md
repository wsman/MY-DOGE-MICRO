# Browser SDK SSE Reconnect Smoke

Date: 2026-06-22
Scope: Browser runtime evidence for TypeScript SDK SSE reconnect/replay
Result: PASS

## Environment

| Check | Result |
|---|---|
| Browser | Local Chrome via headless CDP |
| SDK | `packages/doge-sdk-typescript/dist/index.js` imported as a browser ES module |
| Server | Temporary local HTTP/SSE fixture from `scripts/browser_sdk_reconnect_smoke.py` |

Evidence files:

- `production/qa/evidence/manual/browser-sdk-sse-reconnect-2026-06-22.json`
- `production/qa/evidence/manual/browser-sdk-sse-reconnect-2026-06-22.png`

## Scenario

The smoke opens a real Chrome page that imports the built TypeScript SDK and
calls:

```ts
client.runs.stream("run-browser-reconnect", {
  lastEventId: "1",
  reconnect: true,
  maxReconnects: 1,
  backoffMs: 0,
})
```

The fixture SSE server:

- accepts the first browser connection with `Last-Event-ID: 1`;
- sends a complete event `id: 2`, `event: tool_call`;
- appends a truncated malformed SSE frame to force a mid-stream parser error
  after event `2` is already yielded;
- accepts the reconnect with `Last-Event-ID: 2`;
- sends terminal event `id: 3`, `event: artifact_created`.

## Observed

```json
{
  "connection_count": 2,
  "last_event_id_headers": ["1", "2"],
  "event_ids": ["2", "3"]
}
```

The browser SDK consumed the first event, reconnected from the latest processed
event id, and consumed the terminal event once.

## Limitation

This closes a browser-runtime SDK replay risk, but it is not a full Research
Agent manual reconnect pass against a running `doged` session. The broader
operator workflow remains tracked separately.
