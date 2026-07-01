# Architecture PR Checklist

Use this checklist for changes that add public behavior, new modules, routes,
SDK methods, or compatibility surfaces.

## Ownership

- [ ] The change names a canonical owner.
- [ ] The bounded context is documented or linked.
- [ ] Delivery channels are not presented as new product modules.
- [ ] New code is placed under the canonical path for the owning area.

## Imports And Boundaries

- [ ] Allowed imports follow the local dependency direction.
- [ ] Forbidden legacy or shim imports are absent from production code.
- [ ] Infrastructure construction stays in bootstrap/container/factory code.
- [ ] Compatibility shims re-export, delegate, or warn only.

## Contracts

- [ ] Public HTTP changes update [../API.md](../API.md).
- [ ] Public CLI changes update [../CLI.md](../CLI.md).
- [ ] MCP surface changes update [../MCP_SERVER.md](../MCP_SERVER.md).
- [ ] SDK method changes update the relevant package README.
- [ ] Runtime contract changes update [runtime-contracts.md](runtime-contracts.md)
  and contract tests.

## Maturity And Evidence

- [ ] The change does not claim Stable, GA, or Production Ready unless
  `docs/progress/runtime-maturity.yaml` has changed through an approved gate.
- [ ] Local evidence is separate from external/operator gate evidence.
- [ ] New compatibility surfaces have sunset gates in
  [compatibility-surfaces.md](compatibility-surfaces.md).
- [ ] New reader docs link existing authorities instead of restating them.
