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
- Legacy local API compatibility lives under `doge.interfaces.api_legacy` and
  old `/api/*` paths.
- `doge.application.agent.tools` is a compatibility shim for
  `doge.application.tools`.
- `doge.application.composition` remains a compatibility composition facade;
  new process/root wiring belongs in `doge.bootstrap`.

## Legacy Local Surfaces

- `src/macro`, `src/micro`, and `src/interface` are legacy-maintained local
  surfaces.
- New runtime, gateway, and eval work must not import those modules directly.
- PyQt remains a local legacy surface and is not the preferred platform UX path.

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
