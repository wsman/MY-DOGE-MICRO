# MY-DOGE-MICRO Documentation Index

This is the product documentation entrance for MY-DOGE-MICRO. It separates
operator-facing product docs from the CDD governance framework docs.

## Product Operation

| Topic | Document |
|-------|----------|
| Product overview | [product/overview.md](product/overview.md) |
| First run and local setup | [GETTING_STARTED.md](GETTING_STARTED.md) |
| Local deployment notes | [operations/local-deployment.md](operations/local-deployment.md) |
| Operations runbook | [operations-runbook.md](operations-runbook.md) |
| Security and data boundaries | [security-and-data-boundaries.md](security-and-data-boundaries.md) |

## Reference

| Topic | Document |
|-------|----------|
| HTTP API | [API.md](API.md) and [reference/api.md](reference/api.md) |
| CLI | [CLI.md](CLI.md) and [reference/cli.md](reference/cli.md) |
| MCP server/tools | [MCP_SERVER.md](MCP_SERVER.md) and [reference/mcp.md](reference/mcp.md) |
| Configuration | [reference/configuration.md](reference/configuration.md) |

The legacy uppercase reference files stay in place because current tests,
ADRs, CDDs, and operator docs still treat them as stable paths.

## Architecture And CDD

| Topic | Document |
|-------|----------|
| Architecture overview | [architecture/overview.md](architecture/overview.md) |
| ADRs | [architecture/](architecture/) |
| Bounded context index | [../design/cdd/module-index.md](../design/cdd/module-index.md) |
| Architecture registry | [registry/architecture.yaml](registry/architecture.yaml) |
| Traceability | [architecture/architecture-traceability.md](architecture/architecture-traceability.md) |

The canonical counted product/platform module set is the eight bounded contexts
accepted by ADR-0021. Delivery channels and adapters are not counted modules.

## Quality And Progress

| Topic | Document |
|-------|----------|
| Current status rollup | [quality/status.md](quality/status.md) |
| Runtime maturity | [progress/runtime-maturity.yaml](progress/runtime-maturity.yaml) |
| Progress archive index | [progress/README.md](progress/README.md) |
| Historical audits | [archive/audits/](archive/audits/) |

Runtime maturity remains non-production unless
[progress/runtime-maturity.yaml](progress/runtime-maturity.yaml) explicitly
changes `production_ready: false` and `stable_declaration: forbidden`.

## CDD Framework Docs

`docs/QUICK-START.md`, `docs/START-HERE.md`, and `docs/USER-MANUAL.md`
describe the CDD governance and agent workflow. Use them when operating the
agent studio, not when starting the MY-DOGE-MICRO product.
