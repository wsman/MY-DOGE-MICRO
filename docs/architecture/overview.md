# Architecture Overview

ADR-0021 makes the eight bounded contexts the canonical counted
product/platform module set. ADR-0022 defines a facade-first target directory
strategy, but broad physical source moves remain story-gated. ADR-0024 makes
the runtime/platform direction single-stack: new work goes through process
roots, persisted runtime state, `/v1` routes, and SDK clients.

## Canonical Bounded Contexts

The four `doge.products.*` packages (`market`, `portfolio`, `research`, and
`quant`) are external product-module names used for source ownership and tool
placement. The eight bounded contexts are the internal governance map, adding
Workspace, Runtime, Knowledge/Evidence, and Governance/Evaluation platform
contexts. These are two views of the same architecture, not conflicting module
counts.

| # | Context | Type | Design doc |
|---|---------|------|------------|
| 1 | Market Intelligence | Product | [../../design/cdd/bc-01-market-intelligence.md](../../design/cdd/bc-01-market-intelligence.md) |
| 2 | Research | Product | [../../design/cdd/bc-02-research.md](../../design/cdd/bc-02-research.md) |
| 3 | Portfolio & Risk | Product | [../../design/cdd/bc-03-portfolio-risk.md](../../design/cdd/bc-03-portfolio-risk.md) |
| 4 | Quant & Data Lab | Product | [../../design/cdd/bc-04-quant-data-lab.md](../../design/cdd/bc-04-quant-data-lab.md) |
| 5 | Workspace & Workflow | Platform | [../../design/cdd/bc-05-workspace-workflow.md](../../design/cdd/bc-05-workspace-workflow.md) |
| 6 | Agent Runtime | Platform | [../../design/cdd/bc-06-agent-runtime.md](../../design/cdd/bc-06-agent-runtime.md) |
| 7 | Knowledge & Evidence | Platform | [../../design/cdd/bc-07-knowledge-evidence.md](../../design/cdd/bc-07-knowledge-evidence.md) |
| 8 | Governance & Evaluation | Platform | [../../design/cdd/bc-08-governance-evaluation.md](../../design/cdd/bc-08-governance-evaluation.md) |

## Not Counted As Product Modules

Delivery channels are access surfaces: FastAPI, Web, CLI, daemon, SDK, and MCP.
Adapters are concrete implementations behind ports: SQLite, DuckDB,
TDX, yfinance, akshare, model providers, vector stores, eventing, secrets, and
persistence drivers.

Legacy `/api/*` and the in-memory agent runtime are compatibility or demo
surfaces. The former PyQt desktop dashboard, `doge.application.composition`,
and `doge.application.agent.tools` were removed in Sprint M; none of these are
alternate destinations for new platform features.

## Current Target Layout

```text
src/doge/
+-- shared/
+-- platform/
+-- products/
+-- adapters/
+-- entrypoints/
+-- bootstrap/
```

This is a target layout, not proof that all implementation has moved. New
facades and physical moves require compatibility import tests, layer gates, and
contract tests.

## Governing Documents

- [ADR-0021: Bounded Context Consolidation](adr-0021-bounded-context-consolidation.md)
- [ADR-0022: Directory Restructuring](adr-0022-directory-restructuring.md)
- [ADR-0023: Kimi "For Coding" Endpoint Support](adr-0023-kimi-coding-endpoint.md)
- [ADR-0024: Single-Stack Runtime Direction](adr-0024-single-stack-runtime-direction.md)
- [Control Manifest](control-manifest.md)
- [Architecture Registry](../registry/architecture.yaml)
- [Module Index](../../design/cdd/module-index.md)

Runtime promotion remains blocked while
[../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml) keeps
`production_ready: false`.

Canonical source: this file is the reader-facing prose authority for the eight
bounded contexts; ADR-0021 remains the decision record and
`docs/registry/architecture.yaml` remains the machine-readable registry.
