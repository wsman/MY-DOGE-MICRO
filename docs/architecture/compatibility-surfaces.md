---
title: Compatibility Surfaces Registry
status: active
last_verified: 2026-07-01
governing_adr: docs/architecture/adr-0027-shim-sunset-policy.md
runtime_maturity_impact: none
external_gates_changed: false
---

# Compatibility Surfaces Registry

This registry is the detailed compatibility-surface inventory governed by
[ADR-0027](adr-0027-shim-sunset-policy.md),
[file-structure-policy.md](file-structure-policy.md), and
[module-boundaries.md](module-boundaries.md). It does not create a new policy
source. If this file conflicts with those architecture documents, the ADR and
policy files win and this registry must be corrected.

Sprint H records the current compatibility, legacy, and demo/test surfaces so
new work has a visible canonical destination. This does not remove any brownfield
code, close external gates, update the latest remotely verified SHA, or promote
runtime maturity.

## Surface Registry

| surface | type | owner | canonical_replacement | allowed_behavior | forbidden_behavior | parity_tests | earliest_removal | migration_status | current_count |
|---|---|---|---|---|---|---|---|---|---|
| `doge.interfaces.api.routers` | `import-shim` | gateway | `doge.interfaces.api_legacy.routers` | Re-export legacy local router modules. | Route definitions or endpoint handlers. | Import tests, `test_shim_behavior_guards.py` | After internal and third-party imports migrate. | Legacy router package shim. | 8 legacy router module exports, verified 2026-07-01. |
| `doge.interfaces.api_legacy.routers` | `legacy` | gateway | `doge.interfaces.gateway.routers` | Serve legacy `/api/*` routes with deprecation headers. | New platform-only features or default new-work ownership. | Route parity and contract tests. | Not before 2026-09-30 and only after route parity, migration notes, and rollback plan. | Active local loopback compatibility implementation. | 8 router modules, about 32 route decorators, verified 2026-07-01. |
| `doge.infrastructure.agent.inmemory_runtime` | `demo-test` | runtime | Persisted runtime repositories, durable queue, `PersistedResearchAgentRuntime` | Zero-key demo and deterministic tests without live keys. | Production-facing default or platform path dependency. | `test_inmemory_runtime.py` | After deterministic alternatives exist or a separate support story keeps it. | Demo/test-only runtime adapter. | 1 public runtime class, verified 2026-07-01. |
| `doge.infrastructure.agent.scripted_model` | `demo-test` | runtime | Live model adapters such as `KimiAgentModel` | Offline deterministic tests and demos. | Production default or live path replacement. | Eval and failure-injection tests. | Separate support/removal story. | Demo/test-only scripted model adapter. | 4 public classes, verified 2026-07-01. |

## Maturity Posture

Sprint H does not change runtime maturity:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

External/operator gates remain open unless separate completed evidence closes
them:

- `S017-003`
- `W3-live`
- `AUTH-prod`
- `S017-007`
