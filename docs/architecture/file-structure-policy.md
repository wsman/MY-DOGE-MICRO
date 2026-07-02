# File Structure Policy

> Sprint G policy. Runtime maturity remains governed by
> `docs/progress/runtime-maturity.yaml`.

## Canonical Paths

- New canonical code lives under `src/doge/`.
- Gateway implementation lives under `src/doge/interfaces/gateway/`.
- Runtime orchestration lives under `src/doge/application/agent/` and public
  runtime facades under `doge.platform.runtime`.
- Canonical tool registry work lives under `src/doge/application/tools/`.
- Deterministic eval runner code lives under `src/doge/eval/`.

## Compatibility Paths

- `/v1` compatibility shims live under `src/doge/interfaces/api/routers/v1/`.
  They must remain logic-free re-exports of `doge.interfaces.gateway.routers`.
  The only named exception is `run_stream.py`, which may additionally re-export
  `RunStreamHandler` for legacy/static checks; it must not implement stream
  behavior.
- Legacy local API compatibility lives under `doge.interfaces.api_legacy` and
  old `/api/*` paths.
- `doge.application.agent.tools` was removed in Sprint M; use
  `doge.application.tools`.
- `doge.application.composition` was removed in Sprint M; process/root wiring
  belongs in `doge.bootstrap`.

## Shim Sunset Rules

ADR-0027 governs compatibility-surface sunset. Shim files may re-export,
delegate, warn, and preserve documented compatibility symbols only. They may
not add routing logic, persistence access, tool implementation, model routing,
approval policy, worker behavior, or feature defaults.

Removal of a shim requires parity tests, migration notes, and a rollback plan.
Repository-wide grep counts are not valid acceptance criteria while public
compatibility imports remain; import gates must distinguish production imports
from intentional shim/parity tests.

## Legacy Local Surfaces

- `src/macro` and `src/micro` are legacy-maintained local surfaces.
- New runtime, gateway, and eval work must not import those modules directly.
- The former PyQt dashboard under `src/interface` was removed in Sprint M; Web,
  SDK, and `/v1` are the platform UX paths.

## Demo And Test Paths

- In-memory runtime, scripted model scenarios, and fixture portfolios are
  demo/test-only unless explicitly passed by the caller.
- Demo/test-only behavior must not become a runtime default. In particular,
  `portfolio-demo` must not be injected unless a case, run, CLI argument, or
  fixture explicitly supplies it.

## Planned Or External-Gated Paths

- Live provider, live IdP/JWKS, SDK registry, production data, and external
  benchmark evidence remain operator-gated until real completed evidence exists.
- Local consolidation work must preserve:
  - `production_ready: false`
  - `stable_declaration: forbidden`
  - `level_3_sdk_platform: experimental`

Canonical source: this file is the reader-facing prose authority for shim
behavior rules; ADR-0027 remains the decision record and
`compatibility-surfaces.md` remains the detailed surface registry.
