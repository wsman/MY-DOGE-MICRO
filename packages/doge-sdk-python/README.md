# MY-DOGE Python SDK

Python client for the local MY-DOGE daemon `/v1` API.

Maturity: Platform Alpha client surface. Level 3 remains experimental, and this
package must not be described as stable or production ready.

## Install

From the repository root:

```bash
py -3 -m pip install -e packages/doge-sdk-python
```

## Client Resources

`DogeClient` and `AsyncDogeClient` expose the current SDK surface:

- `client.sessions` maps to `/v1/sessions`.
- `client.runs` maps to `/v1/runs`.
- `client.documents` maps to `/v1/documents`.
- `client.platform` maps to workspace, project, research-case, case asset,
  decision, execution, review, home-queue, and workflow-template helper flows.
- `client.capabilities` maps to `/v1/capabilities`.

`/v1/tools` is a primary API discovery family, but there is no first-class SDK
`tools` resource in Sprint I. Use `client.capabilities` and `docs/API.md` for
tool availability and schema discovery, or call `/v1/tools` directly through the
daemon API if an operator workflow needs raw tool schemas.

`audit`, `enterprise`, `health`, and `portfolios` are operator/reference APIs.
They are intentionally not primary SDK resources.

## Quick Start

Start the local daemon:

```bash
doged serve
```

Create a session and submit a turn:

```python
from doge_sdk import DogeClient

client = DogeClient(base_url="http://127.0.0.1:8901")
session = client.sessions.create("Local research")
run_id = session.run("Analyze NVDA earnings risk")

run = client.runs.get(run_id)
events = client.runs.events(run_id)
recent_runs = client.runs.list(limit=5)
```

Upload a document:

```python
document = client.documents.upload_path("report.txt", content_type="text/plain")
```

Resume an approval:

```python
run = client.runs.get(run_id)
approval_id = run["approvals"][0]["approval_id"]
client.runs.resume(run_id, approval_id=approval_id, approved=True)
```

Approval dictionaries may include optional explanation metadata:
`why_needed`, `impact`, `deny_consequence`, and `publish_target`. Older daemon
snapshots may omit these keys.

`client.runs.list(limit=20, session_id=None)` returns compact run rows for
history and comparison views. Rows include counts and status metadata, not full
events or artifacts; use `client.runs.get(run_id)` for the full run.

## Cookbook Files

Standalone examples live in `examples/python/`:

- `01_create_session.py`
- `02_upload_and_run.py`
- `03_stream_and_approve.py`
- `04_error_handling.py`

They mirror the quick-start flows without adding SDK resources or changing the
package surface.

## Feature Flags

The daemon owns feature flags; the SDK does not override them.

- `DOGE_FEATURE_PLATFORM_OBJECTS=1` enables `client.platform` workspace,
  project, case, asset, decision, execution, review, and home-queue methods.
- `DOGE_FEATURE_WORKFLOW_TEMPLATES=1` enables workflow-template methods.
- `DOGE_FEATURE_CAPABILITY_REGISTRY=1` enables `client.capabilities`.
- `DOGE_FEATURE_RUN_SUMMARY_API=1` enables `client.runs.summary()`,
  `claims()`, `citations()`, and `evaluation()`.
  Claim dictionaries include additive structured metadata: `status`,
  `evidence_refs`, `numeric_check_status`, and `risk_level`.

Disabled feature-flagged endpoints return `DogeApiError` with status code 404.

## Errors and Auth

If the daemon is configured with `DOGE_API_TOKEN`, pass it to the client:

```python
client = DogeClient(api_token="local-token")
```

HTTP failures raise `DogeApiError(status_code, message)`. Error messages are
redacted before being surfaced by the SDK.

## Async Client

```python
from doge_sdk import AsyncDogeClient

async with AsyncDogeClient() as client:
    session = await client.sessions.create("Async research")
    run_id = await session.run("Analyze AAPL")
```

Streaming helpers reconnect by default and support `Last-Event-ID` replay:

```python
for event in client.runs.stream(run_id):
    print(event.type, event.data)
```
