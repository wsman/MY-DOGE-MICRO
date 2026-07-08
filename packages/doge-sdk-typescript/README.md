# OpenDoge TypeScript SDK

TypeScript client for the local OpenDoge daemon `/v1` API.

Maturity: Platform Alpha client surface. Level 3 remains experimental, and this
package must not be described as stable or production ready.

## Install

From the repository root:

```bash
cd packages/doge-sdk-typescript
npm install
npm run build
```

The package is private in this repository. Import from the built package in
local workspace consumers.

## Client Resources

`DogeClient` exposes the current SDK surface:

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

```typescript
import { DogeClient } from 'doge-sdk'

const client = new DogeClient({ baseUrl: 'http://127.0.0.1:8901' })
const session = await client.sessions.create('Local research')
const runId = await session.run('Analyze NVDA earnings risk')

const run = await client.runs.get(runId)
const events = await client.runs.events(runId)
const recentRuns = await client.runs.list({ limit: 5 })
```

Upload a document:

```typescript
const file = new Blob(['alpha beta'], { type: 'text/plain' })
const document = await client.documents.upload(file, 'report.txt')
```

Resume an approval:

```typescript
const run = await client.runs.get(runId)
const approvalId = (run.approvals as Array<{ approval_id: string }>)[0].approval_id
await client.runs.resume(runId, { approvalId, approved: true })
```

Approval objects may include optional explanation metadata:
`why_needed`, `impact`, `deny_consequence`, and `publish_target`. Older daemon
snapshots may omit these fields.

`client.runs.list({ limit, sessionId })` returns compact run rows for history
and comparison views. Rows include counts and status metadata, not full events
or artifacts; use `client.runs.get(runId)` for the full run.

## Cookbook Files

Standalone examples live in `examples/typescript/`:

- `01_create_session.ts`
- `02_upload_and_run.ts`
- `03_stream_and_approve.ts`
- `04_error_handling.ts`

They mirror the quick-start flows without adding SDK resources or changing the
package surface.

## Feature Flags

The daemon owns feature flags; the SDK does not override them.

- `DOGE_FEATURE_PLATFORM_OBJECTS=1` enables `client.platform` workspace,
  project, case, asset, decision, execution, review, and home-queue methods.
- `DOGE_FEATURE_WORKFLOW_TEMPLATES=1` enables workflow-template methods.
- `DOGE_FEATURE_CAPABILITY_REGISTRY=1` enables `client.capabilities`.
- `DOGE_FEATURE_RUN_SUMMARY_API=1` enables run summary, claims, citations, and
  eval methods.
  Claim rows include additive structured metadata: `status`, `evidence_refs`,
  `numeric_check_status`, and `risk_level`.

Disabled feature-flagged endpoints throw `DogeApiError` with status code 404.

## Errors and Auth

If the daemon is configured with `DOGE_API_TOKEN`, pass it to the client:

```typescript
const client = new DogeClient({ apiToken: 'local-token' })
```

HTTP failures throw `DogeApiError`. Error messages are redacted before being
surfaced by the SDK.

## Streaming

`client.runs.stream(runId, { lastEventId })` consumes the daemon SSE stream and
supports replay through `Last-Event-ID`.
