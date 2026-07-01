# SDK Integrator Start Here

Use this page when you are integrating Python or TypeScript code with the local
daemon. SDKs are client surfaces for `/v1`; they are not a separate runtime.

## Your 3-step first path

1. Start or locate a local daemon.

   ```bash
   doged serve --host 127.0.0.1 --port 8901
   ```

   Check [daemon-operator.md](daemon-operator.md) if readiness or process setup
   is not clear.

2. Choose the SDK package.

   Python users start with
   [../../packages/doge-sdk-python/README.md](../../packages/doge-sdk-python/README.md).
   TypeScript users start with
   [../../packages/doge-sdk-typescript/README.md](../../packages/doge-sdk-typescript/README.md).

3. Use the same runtime workflow as `/v1`.

   Create a session, submit a turn, follow run events, resolve approvals, and
   fetch artifacts or summaries. Check [../API.md](../API.md) when a method
   needs the underlying route contract.

## What To Expect

- Level 3 SDK/platform remains experimental.
- SDKs should reflect daemon contracts instead of inventing local behavior.
- Streaming clients should preserve replay semantics documented by the API.
- Feature-flagged platform resources may be unavailable on a default daemon.
- Error handling follows the daemon response contract.

## Use This Page For

- Building a small Python integration.
- Building a TypeScript or Web client against the local daemon.
- Checking which package README owns client-level examples.
- Confirming that SDK work should not use legacy `/api/*` routes.

## Do Not Use This Page For

- Publishing SDK packages.
- Declaring SDK stability.
- Adding daemon routes.
- Reconstructing citations from browser-local state.
- Bypassing approval or tenant boundaries.

## Key References

- HTTP API reference: [../API.md](../API.md)
- Python SDK README: [../../packages/doge-sdk-python/README.md](../../packages/doge-sdk-python/README.md)
- TypeScript SDK README: [../../packages/doge-sdk-typescript/README.md](../../packages/doge-sdk-typescript/README.md)
- Runtime contracts: [../architecture/runtime-contracts.md](../architecture/runtime-contracts.md)
- SDK progress notes: [../progress/sdk-package-compatibility.md](../progress/sdk-package-compatibility.md)

## Safety Notes

- Do not claim Stable, GA, or Production Ready from SDK examples.
- Use daemon feature discovery before calling optional platform surfaces.
- Keep local tokens and provider keys out of SDK docs and fixtures.
- Preserve `Last-Event-ID` replay behavior when writing stream consumers.

## Integration Checklist

- The daemon base URL is configurable.
- The client handles `DogeApiError`.
- Optional resources are guarded by feature discovery.
- Stream consumers can reconnect without duplicating events.
- New public methods are reflected in the package README.
- Examples avoid stable, GA, and production-ready language.
- Tests do not call live providers unless explicitly marked live.

## When To Leave This Page

Move to [daemon-operator.md](daemon-operator.md) when the daemon is not ready.
Move to [architecture-reviewer.md](architecture-reviewer.md) before adding a new
SDK method or public model. Move to [local-analyst.md](local-analyst.md) if a
one-person embedded CLI workflow is enough.
