# Run The Daemon Gateway

Use this guide when a local process needs the daemon `/v1` contract. Full route
details remain in [../API.md](../API.md).

## Your 3-step first path

1. Start the daemon on loopback.

   ```bash
   doged serve --host 127.0.0.1 --port 8901
   ```

   Keep loopback unless an operator has completed auth, CORS, and remote-bind
   gates.

2. Check readiness.

   ```bash
   curl http://127.0.0.1:8901/health/ready
   ```

   Readiness failures are operator signals. Do not treat a partially available
   daemon as a product-contract pass.

3. Drive the primary `/v1` workflow.

   Create a session, upload documents when needed, create a turn, stream or read
   events, resolve approvals, and fetch artifacts. Route shapes and error
   envelopes are owned by [../API.md](../API.md).

## Checks Before You Stop

- `/health/ready` is green or the failed subsystem is documented.
- The caller uses `/v1` for new work.
- Legacy `/api/*` is used only for compatibility.
- Feature-flagged platform endpoints are either enabled or intentionally absent.

## Related References

- API contract: [../API.md](../API.md)
- CLI daemon commands: [../CLI.md](../CLI.md)
- Operations runbook: [../operations-runbook.md](../operations-runbook.md)
- Runtime contracts: [../architecture/runtime-contracts.md](../architecture/runtime-contracts.md)

## When To Leave This Page

Leave for [use-python-sdk.md](use-python-sdk.md) or
[use-typescript-sdk.md](use-typescript-sdk.md) when a client library owns the
flow. Leave for [upload-documents.md](upload-documents.md) when document upload
behavior is the main uncertainty.
