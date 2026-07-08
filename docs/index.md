# OpenDoge Documentation Index

This is the product documentation entrance for OpenDoge, formerly developed as
MY-DOGE-MICRO. It separates reader paths, product references, architecture
governance, and CDD framework docs.

## Choose Your Path

| I am... | Start here | Goal |
|---|---|---|
| A local analyst | [start-here/local-analyst.md](start-here/local-analyst.md) | Run `doge session` and produce a local research artifact. |
| Running the daemon | [start-here/daemon-operator.md](start-here/daemon-operator.md) | Start `doged serve`, check readiness, and use `/v1`. |
| Integrating a system | [start-here/sdk-integrator.md](start-here/sdk-integrator.md) | Use the Python or TypeScript SDK against the daemon. |
| Using the research workspace | [start-here/research-workspace.md](start-here/research-workspace.md) | Use the Web workspace through the TypeScript SDK and `/v1`. |
| Owning eval or demo cases | [start-here/eval-demo-owner.md](start-here/eval-demo-owner.md) | Run deterministic cases without mixing demo behavior into production paths. |
| Reviewing architecture | [start-here/architecture-reviewer.md](start-here/architecture-reviewer.md) | Check bounded contexts, runtime path, shims, and maturity. |
| Preparing the Kimi SA demo | [start-here/kimi-sa-demo.md](start-here/kimi-sa-demo.md) | Follow the demo material without mixing it into product setup. |

## Canonical Quick Links

| Topic | Document |
|---|---|
| Product overview | [product/overview.md](product/overview.md) |
| Product modules | [product/modules.md](product/modules.md) |
| First run and local setup | [guides/getting-started.md](guides/getting-started.md) |
| Local deployment notes | [operations/local-deployment.md](operations/local-deployment.md) |
| Operations runbook | [operations/runbook.md](operations/runbook.md) |
| Security and data boundaries | [security-and-data-boundaries.md](security-and-data-boundaries.md) |
| Current human status | [progress/current-status.md](progress/current-status.md) |
| Current generated status | [quality/status.md](quality/status.md) |
| Runtime maturity authority | [progress/runtime-maturity.yaml](progress/runtime-maturity.yaml) |

## Product References

| Topic | Canonical content home |
|---|---|
| HTTP API quick guide | [API.md](API.md) |
| HTTP API reference (route table) | [reference/http-api.md](reference/http-api.md) |
| HTTP API contracts (SSE/CORS/error) | [reference/http-api-contracts.md](reference/http-api-contracts.md) |
| CLI | [CLI.md](CLI.md) |
| MCP server/tools | [MCP_SERVER.md](MCP_SERVER.md) |
| Configuration | [reference/configuration.md](reference/configuration.md) |
| Environment variables | [reference/env-vars.md](reference/env-vars.md) |
| Tool shortcut | [reference/tools.md](reference/tools.md) |
| Python SDK shortcut | [reference/sdk-python.md](reference/sdk-python.md) |
| TypeScript SDK shortcut | [reference/sdk-typescript.md](reference/sdk-typescript.md) |
| Module map | [reference/module-map.md](reference/module-map.md) |

The HTTP API quick guide ([API.md](API.md)) is the reader entry point; the full
route table and per-route reference live in
[reference/http-api.md](reference/http-api.md), and transport/SSE/CORS/error/
concurrency/OpenAPI contracts live in
[reference/http-api-contracts.md](reference/http-api-contracts.md). The
remaining lowercase reference entries are redirect shortcuts.

Reference shortcuts may explain where to go next, but they must not copy the
HTTP route table, CLI command table, MCP tool catalog, SDK API surface, or
environment-variable table. The HTTP route table lives in
reference/http-api.md; put contract changes there first, then update tests.

## Architecture And Governance

| Topic | Document |
|---|---|
| Architecture index | [architecture/index.md](architecture/index.md) |
| Architecture overview | [architecture/overview.md](architecture/overview.md) |
| Bounded context shortcut | [architecture/bounded-contexts.md](architecture/bounded-contexts.md) |
| Runtime path shortcut | [architecture/canonical-runtime-path.md](architecture/canonical-runtime-path.md) |
| Runtime contracts | [architecture/runtime-contracts.md](architecture/runtime-contracts.md) |
| File structure policy | [architecture/file-structure-policy.md](architecture/file-structure-policy.md) |
| Source layout map | [architecture/source-layout-map.md](architecture/source-layout-map.md) |
| Compatibility surfaces | [architecture/compatibility-surfaces.md](architecture/compatibility-surfaces.md) |
| Data ownership | [architecture/data-ownership.md](architecture/data-ownership.md) |
| Bounded context index | [../design/cdd/module-index.md](../design/cdd/module-index.md) |
| Architecture registry | [registry/architecture.yaml](registry/architecture.yaml) |
| Traceability | [architecture/architecture-traceability.md](architecture/architecture-traceability.md) |

The counted product/platform module set is the eight bounded contexts accepted
by ADR-0021. Delivery channels and adapters are not counted modules.

Future architecture docs should add reader paths, review guides, or short
summaries. Do not create a second authority for bounded contexts, runtime path,
file placement rules, compatibility surfaces, or module ownership.

## Quality And Progress

| Topic | Document |
|---|---|
| Generated status rollup | [quality/status.md](quality/status.md) |
| Eval metrics | [quality/eval-metrics.md](quality/eval-metrics.md) |
| Test matrix | [quality/test-matrix.md](quality/test-matrix.md) |
| Validation scripts | [quality/validation-scripts.md](quality/validation-scripts.md) |
| Runtime maturity | [progress/runtime-maturity.yaml](progress/runtime-maturity.yaml) |
| Progress archive index | [progress/README.md](progress/README.md) |
| Historical audits | [archive/audits/](archive/audits/) |

## Demo

| Topic | Document |
|---|---|
| Kimi SA demo script | [demo/kimi-sa-demo-script.md](demo/kimi-sa-demo-script.md) |
| Talk track | [demo/solution-architecture-talk-track.md](demo/solution-architecture-talk-track.md) |
| Demo data | [demo/demo-data.md](demo/demo-data.md) |
| Eval storyboard | [demo/eval-storyboard.md](demo/eval-storyboard.md) |
| Screenshot notes | [demo/screenshots.md](demo/screenshots.md) |

Runtime maturity remains non-production unless
[progress/runtime-maturity.yaml](progress/runtime-maturity.yaml) explicitly
changes `production_ready: false` and `stable_declaration: forbidden`.

## CDD Framework Docs

`docs/governance/cdd/QUICK-START.md`, `docs/governance/cdd/START-HERE.md`, and
`docs/governance/cdd/USER-MANUAL.md` describe the CDD governance and agent
workflow. Use them when operating the agent studio, not when starting the
OpenDoge product.
