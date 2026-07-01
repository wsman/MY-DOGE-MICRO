# Use The TypeScript SDK

Use this guide for a TypeScript client against the daemon. Full SDK details stay
in [../../packages/doge-sdk-typescript/README.md](../../packages/doge-sdk-typescript/README.md).

## Your 3-step first path

1. Build the package.

   ```bash
   cd packages/doge-sdk-typescript
   npm install
   npm run build
   ```

   Run the daemon in another terminal before executing client code.

2. Create a session and submit a turn.

   ```typescript
   import { DogeClient } from 'doge-sdk'

   const client = new DogeClient({ baseUrl: 'http://127.0.0.1:8901' })
   const session = await client.sessions.create('Local research')
   const runId = await session.run('Analyze earnings risk')
   ```

3. Stream or read run output.

   Use `client.runs.stream(runId, { lastEventId })` when the caller needs SSE
   replay behavior. Check [../API.md](../API.md) for route-level details.

## Checks Before You Stop

- The build passes locally.
- Stream consumers preserve `Last-Event-ID` replay.
- Optional platform resources are feature-flag checked.
- No docs or code comments claim SDK stability.

## Related References

- TypeScript SDK README: [../../packages/doge-sdk-typescript/README.md](../../packages/doge-sdk-typescript/README.md)
- API contract: [../API.md](../API.md)
- SDK integration start page: [../start-here/sdk-integrator.md](../start-here/sdk-integrator.md)
- Current maturity: [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml)

## When To Leave This Page

Leave for [run-daemon-gateway.md](run-daemon-gateway.md) when daemon readiness is
unclear. Leave for [approve-and-resume-runs.md](approve-and-resume-runs.md) when
approval continuation must be implemented.
