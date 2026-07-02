# Research Workspace Start Here

Use this page when you are using or changing the Web Research Workspace. The Web
surface is a client of the TypeScript SDK and `/v1`; it is not a separate
runtime.

## Your 3-step first path

1. Start or locate a local daemon.

   ```bash
   doged serve --host 127.0.0.1 --port 8901
   ```

   Use [daemon-operator.md](daemon-operator.md) when readiness, auth, or bind
   posture is unclear.

2. Start the Web workspace.

   ```bash
   cd web
   npm run dev
   ```

   Web setup details stay in [../../web/README.md](../../web/README.md).

3. Use the SDK-backed runtime flow.

   Create or select a session, upload documents when needed, submit a turn,
   follow run events, resolve approvals, and inspect artifacts or citations.
   The route contract stays in [../API.md](../API.md).

## What To Expect

- Web calls should flow through the TypeScript SDK or a thin local adapter.
- Runtime types come from the SDK contract.
- Run state comes from `/v1` sessions, runs, events, approvals, and artifacts.
- Feature-flagged workspace views may be hidden on a default daemon.
- Level 3 SDK/platform remains experimental.

## Use This Page For

- Research Workspace onboarding.
- Web client changes that need runtime contract context.
- Verifying that Web state mirrors daemon state.
- Checking whether a feature belongs in Web, SDK, `/v1`, or a product module.

## Do Not Use This Page For

- Direct database access from Web.
- Direct tool execution from Web.
- Rebuilding the run state machine in browser state.
- Calling legacy `/api/*` from new Web code.
- Declaring production readiness from a local browser run.

## Key References

- Web README: [../../web/README.md](../../web/README.md)
- TypeScript SDK README: [../../packages/doge-sdk-typescript/README.md](../../packages/doge-sdk-typescript/README.md)
- HTTP API reference: [../API.md](../API.md)
- Runtime contracts: [../architecture/runtime-contracts.md](../architecture/runtime-contracts.md)
- User scenarios: [../product/user-scenarios.md](../product/user-scenarios.md)

## When To Leave This Page

Move to [sdk-integrator.md](sdk-integrator.md) when the client contract is the
main concern. Move to [architecture-reviewer.md](architecture-reviewer.md) when
file placement or module ownership is unclear. Move to
[eval-demo-owner.md](eval-demo-owner.md) when the work is deterministic demo or
evaluation evidence.
