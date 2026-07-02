# Source Layout Map

This is a thin placement guide for new work. It does not replace the authorities
in [file-structure-policy.md](file-structure-policy.md),
[module-boundaries.md](module-boundaries.md), or
[module-ownership.yaml](module-ownership.yaml).

## Placement Rules

| New work | Put it here | Notes |
|---|---|---|
| Local CLI commands | `src/doge/entrypoints/` or existing `src/doge/interfaces/cli/` during the compatibility window | Keep command wiring separate from product behavior. |
| Daemon CLI commands | `src/doge/entrypoints/` or existing `src/doge/interfaces/daemon/` during the compatibility window | The daemon owns process role, readiness, and startup checks. |
| HTTP app assembly | `src/doge/interfaces/api/` today; future facade under `src/doge/entrypoints/api/` | `doge.interfaces.api.main:app` remains the compatibility import. |
| New `/v1` HTTP behavior | `src/doge/interfaces/gateway/routers/` | Do not add new product behavior to legacy `/api/*`. |
| Runtime public facade | `src/doge/platform/runtime/` | New callers should prefer platform runtime facade imports when available. |
| Runtime orchestration internals | `src/doge/application/agent/` | Kernel collaborators own lifecycle, approvals, stepping, and artifacts. |
| Tool registry and dispatch | `src/doge/application/tools/` | Registry discovery and dispatch stay separate from compatibility method names. |
| Market behavior | `src/doge/products/market/` | No sibling product imports. Use shared contracts or platform services. |
| Research behavior | `src/doge/products/research/` | Research owns memo/workflow behavior, not model adapters or runtime state. |
| Portfolio behavior | `src/doge/products/portfolio/` | Portfolio owns holdings, exposure, scenarios, and import contracts. |
| Quant behavior | `src/doge/products/quant/` | Keep analytical execution bounded and feature-gated where required. |
| Workspace, evidence, governance | `src/doge/platform/workspace/`, `src/doge/platform/evidence/`, `src/doge/platform/governance/` | These are platform services, not product modules. |
| External adapters | `src/doge/adapters/` or existing `src/doge/infrastructure/` while migrating | Adapters implement ports and do not own business decisions. |
| Process wiring | `src/doge/bootstrap/` | Bootstrap wires implementations; product modules should not become composition roots. |
| Eval and deterministic demo logic | `src/doge/eval/`, `tests/eval/`, or explicit demo fixtures | Demo/test behavior must not become runtime default behavior. |

## Frozen Legacy Paths

New production code must not depend directly on these paths:

- `src/macro`
- `src/micro`
- `doge.interfaces.api_legacy`
- `doge.infrastructure.agent.inmemory_runtime`

Allowed exceptions are compatibility route mounting/shims, `api_legacy` itself,
tests, and explicitly gated demo fallback factories. The enforcement lives in
`scripts/validate_import_boundaries.py` and the layer-gate tests.

## Decision Shortcut

- Write business behavior in `products/*`.
- Write platform capabilities in `platform/*`.
- Write outside-world integrations in `adapters/*` or current infrastructure
  migration paths.
- Write user/process entrypoints in `entrypoints/*` or current interface
  compatibility paths.
- Write wiring in `bootstrap/*`.
- Write eval/demo behavior in `eval/*` or test fixtures.
