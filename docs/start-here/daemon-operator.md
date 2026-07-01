# Daemon Operator Start Here

Use this page when you need to run the local daemon, check readiness, and expose
the Alpha `/v1` contract to CLI, SDK, or Web clients.

## Your 3-step first path

1. Start the daemon on loopback.

   ```bash
   doged serve --host 127.0.0.1 --port 8901
   ```

   The full daemon CLI contract stays in [../CLI.md](../CLI.md).

2. Check readiness and route family.

   ```bash
   curl http://127.0.0.1:8901/health/ready
   ```

   Use [../API.md](../API.md) for the complete route table and error contract.

3. Drive the primary runtime workflow.

   Create a session, upload documents when needed, create a turn, stream the
   run, resolve approvals, and read artifacts. The route reference and SSE
   details stay in [../API.md](../API.md).

## What To Expect

- `/v1` is the daemon-facing product contract for new platform work.
- Legacy `/api/*` remains compatibility only.
- Health, audit, enterprise, and portfolio endpoints are operator/reference
  surfaces unless a feature explicitly needs them.
- SDK and remote CLI clients should not bypass the daemon process contract.
- Level 2 daemon gateway maturity remains Alpha.

## Use This Page For

- Starting a local daemon for integration work.
- Checking whether the process is ready before running SDK tests.
- Understanding which reference page owns route details.
- Keeping operator setup separate from product architecture decisions.

## Do Not Use This Page For

- Adding new routes.
- Changing authentication policy.
- Declaring production readiness.
- Moving legacy `/api/*` behavior.
- Documenting every endpoint.

## Key References

- API reference: [../API.md](../API.md)
- CLI reference: [../CLI.md](../CLI.md)
- Operations runbook: [../operations-runbook.md](../operations-runbook.md)
- Local deployment notes: [../operations/local-deployment.md](../operations/local-deployment.md)
- Runtime contracts: [../architecture/runtime-contracts.md](../architecture/runtime-contracts.md)

## Safety Notes

- Keep the default bind on `127.0.0.1`.
- Do not bind to `0.0.0.0` without auth, CORS, and operator approval.
- Treat local success as local evidence only while external gates remain open.
- Redact secrets before writing logs or evidence files.

## Operator Checklist

- The process role is intentional.
- The bind address is loopback unless explicitly approved.
- Readiness output was checked before client tests.
- Token configuration is documented without exposing the token.
- Feature flags are recorded when optional routes are exercised.
- Evidence names local status separately from external gates.

## When To Leave This Page

Move to [sdk-integrator.md](sdk-integrator.md) when a client library should own
the daemon interaction. Move to [architecture-reviewer.md](architecture-reviewer.md)
when route ownership or compatibility boundaries are unclear. Move to
[local-analyst.md](local-analyst.md) when the embedded CLI is enough.
