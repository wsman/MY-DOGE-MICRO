# Canonical Runtime Path

This page is a reader shortcut. The prose authority is
[runtime-contracts.md](runtime-contracts.md), and ADR-0024 remains the decision
record.

## What To Read

| Need | Source |
|---|---|
| Runtime contract and route ownership | [runtime-contracts.md](runtime-contracts.md) |
| Process construction rules | [file-structure-policy.md](file-structure-policy.md) |
| Compatibility and shim inventory | [compatibility-surfaces.md](compatibility-surfaces.md) |
| Current maturity status | [../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml) |

## How To Use This Page

- New runtime work should start from the contract page, not from legacy route
  modules.
- Delivery channels should be treated as clients or adapters, not product
  bounded contexts.
- Compatibility code should keep its migration and sunset path visible.
- Demo-only paths must not become defaults for new platform work.

## When To Leave This Page

- Use [../start-here/daemon-operator.md](../start-here/daemon-operator.md)
  for a first daemon run.
- Use [../guides/run-daemon-gateway.md](../guides/run-daemon-gateway.md)
  for the 10-minute workflow.
- Use [../API.md](../API.md) for the route reference.
