# OpenDoge

OpenDoge is a local-first, slot-based financial research agent runtime. It
combines market scans, research workflows, portfolio/risk checks,
evidence-backed agent runs, and local API/UI/MCP surfaces without requiring
cloud storage.

Architecture details start at [docs/index.md](docs/index.md). The reader-facing
architecture authorities are [overview.md](docs/architecture/overview.md),
[runtime-contracts.md](docs/architecture/runtime-contracts.md), and
[file-structure-policy.md](docs/architecture/file-structure-policy.md).
The product-package names and eight bounded contexts are reconciled in
[overview.md](docs/architecture/overview.md#canonical-bounded-contexts).

Legacy `/api/*`, `doge.application.composition`, and the in-memory agent runtime
are compatibility or demo surfaces, not alternate platform stacks. The retired
PyQt desktop dashboard was removed in Sprint M.

## Quick Start

Install the core package from the repository root:

```bash
pip install -e .
doge start
```

`doge start` is the first-run launcher. It routes you to the local CLI session,
daemon gateway, Web workspace, deterministic demo, or readiness check without
requiring you to memorize the subcommands first.

Use one of the three Platform Alpha paths:

- **Local analyst** — `doge session --interactive`
- **Daemon gateway** — `doged serve --port 8901`
- **SDK integrator** — Python or TypeScript SDK against `/v1`; start at
  [docs/start-here/sdk-integrator.md](docs/start-here/sdk-integrator.md)

For browser work, run the daemon and Vite, then start at `/home`. The Home
surface is the analyst entry point for starting research, running a local demo,
reviewing recent runs/uploads/cases/approvals/memos, and checking Local Alpha
readiness.

Secondary surfaces and setup references live outside the quick path:
`doge demo` is covered by [docs/start-here/eval-demo-owner.md](docs/start-here/eval-demo-owner.md),
backend internals remain at `src/doge/interfaces/api/main.py`, Vue setup is in
[guides/getting-started.md](docs/guides/getting-started.md), and MCP stdio
still uses `scripts/mcp_stdio.bat`.

The PyQt desktop dashboard (`src/interface/`) was removed in Sprint M; the
Web/SDK/`/v1` path is the platform UX. The `gui` extra is no longer shipped.

## Recommended Docs

- Reader paths: [docs/index.md](docs/index.md)
- First local setup: [docs/guides/getting-started.md](docs/guides/getting-started.md)
- HTTP API details: [docs/API.md](docs/API.md)
- CLI details: [docs/CLI.md](docs/CLI.md)
- MCP details: [docs/MCP_SERVER.md](docs/MCP_SERVER.md)
- Operations: [docs/operations/runbook.md](docs/operations/runbook.md)
- Architecture review: [docs/architecture/index.md](docs/architecture/index.md)

## Runtime Levels

Runtime maturity is intentionally conservative and governed by
[runtime-maturity.yaml](docs/progress/runtime-maturity.yaml).

| Signal | Current value |
|--------|---------------|
| Level 1 embedded CLI/session | Alpha |
| Level 2 daemon gateway | Alpha |
| Level 3 SDK/platform | Experimental |
| Production ready | `false` |
| Stable declaration | `forbidden` |

Current governance values:

```yaml
production_ready: false
stable_declaration: forbidden
```

The coordinated vocabulary for this Alpha stage is: **Local Alpha** (current
maturity), **Production-shaped** (the architecture has production-shaped
surfaces such as `/v1`, the RuntimeKernel, and the SDKs, but makes no
production claim), **Production-readiness gates open** (S017-003 / W3-live /
AUTH-prod / S017-007 remain operator-owned), and **not production ready** (the
canonical `production_ready: false` / `stable_declaration: forbidden` posture
above).

### Surface Classification

Authoritative source: [runtime-maturity.yaml](docs/progress/runtime-maturity.yaml)
`single_stack_direction.compatibility_surfaces`.

| Surface | Classification | Notes |
|---|---|---|
| `/v1/*` gateway routers | Canonical | `doge.interfaces.gateway.routers` |
| `doge.application.tools` | Canonical | shared tool registry across runtime / MCP / HTTP |
| Legacy `/api/*` | Compatibility | `doge.interfaces.api_legacy.routers`; deprecation headers; removal not before 2026-09-30 |
| In-memory runtime | Demo / test only | `doge.infrastructure.agent.inmemory_runtime`; not the production path |
| `doge.application.composition` | Removed | replaced by `doge.bootstrap.processes` (Sprint M) |
| PyQt desktop dashboard | Removed | replaced by Web / SDK / `/v1` (Sprint M) |

The latest remotely verified SHA is
`030ff9b83c3719eb385fb0bb286e0ca76ce45214`, with GitHub Actions run
`28993837317` recorded in
`production/qa/evidence/ci/remote-ci-030ff9b.json`.

GitHub returns that run under the transferred canonical repository URL
`https://github.com/Negentropy-Laby/OpenDoge/actions/runs/28993837317`
while the historical origin path remains `wsman/MY-DOGE-MICRO`.

The prior pushed HEAD `9f304a82ae603f0d15210d7cbfc4e502a61fea43` had exact-SHA GitHub Actions CI
run `28423757545` with result `failure`; Sprint G repaired that blocker before
promoting the verified SHA above.

No README, release note, or docs entry should claim Stable, GA, or Production
Ready while those values remain unchanged. See
[runtime-levels.md](docs/architecture/runtime-levels.md).

## Slot Platform Status

The Slot Platform (ADR-0042 through ADR-0072) is an experimental, built-in
extension mechanism. It contributes tools, models, data sources, workflows,
documents, gateway routes, UI panels, watchers, eval suites, and governance
policies as slot facets.

Controlled built-in Slot Platform consumers are locally default-on:
`DOGE_FEATURE_SLOT_PLATFORM`, `DOGE_FEATURE_SLOT_GOVERNANCE`,
`DOGE_FEATURE_SLOT_WATCHER`, `DOGE_FEATURE_SLOT_LOADER`, and
`DOGE_FEATURE_WORKFLOW_TEMPLATES`.

Higher-risk surfaces remain default-off and require explicit operator opt-in:
`DOGE_FEATURE_SLOT_UI`, `DOGE_FEATURE_SLOT_ENFORCEMENT`,
`DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION`, `DOGE_FEATURE_SLOT_INSTALL`,
`DOGE_FEATURE_SLOT_PROVIDER_EXECUTION`, `DOGE_FEATURE_CAPABILITY_REGISTRY`,
`DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED`, `DOGE_FEATURE_PLATFORM_OBJECTS`,
`DOGE_FEATURE_RUN_SUMMARY_API`, and `DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER`.

No third-party slot provider code executes unless the operator explicitly
enables `DOGE_FEATURE_SLOT_PROVIDER_EXECUTION` and all trust/runtime gates
pass. The current execution model is in-process `importlib` and is not
OS/container/WASM sandboxing, filesystem mediation, or malicious-code
containment.

Inspect built-in slots from the CLI:

```bash
doge slots list
doge slots bundle list
doge slots show market.core
```

The latest Slot Platform remote-CI milestone is P6.1 (`030ff9b`), recorded in
`production/qa/evidence/ci/remote-ci-030ff9b.json`. The Slot Platform does not
close any external/operator gates and remains experimental. See
[docs/reference/configuration.md](docs/reference/configuration.md) for flag
details and [docs/architecture/index.md](docs/architecture/index.md) for the
ADR chain.

## Architecture At A Glance

OpenDoge has one architecture, counted three ways depending on the
question:

- **3 runtime levels** — Level 1 embedded CLI/session, Level 2 daemon gateway,
  Level 3 SDK & platform; see [runtime-levels.md](docs/architecture/runtime-levels.md).
- **5 reader paths (4 product + 1 eval)** — Local Analyst, Daemon Operator,
  SDK Integrator, Research Workspace, Eval-Demo Owner; see
  [user-scenarios.md](docs/product/user-scenarios.md). The Quick Start above
  highlights the 3 most common entrypoints (Local Analyst / Daemon / SDK
  Integrator); [docs/index.md](docs/index.md) adds Architecture Reviewer and
  Kimi SA Demo as specialist doc-discovery paths on top of these 5.
- **8 bounded contexts** per ADR-0021 (4 product modules plus 4 platform
  contexts); see
  [overview.md](docs/architecture/overview.md#canonical-bounded-contexts).
  This is the only canonical module count.
- **1 RuntimeKernel facade**
  (`doge.bootstrap.runtime_factories.runtime_kernel`) backs all three levels;
  the in-memory runtime is demo/test-only.

The engineering-layer "Interfaces / Runtime / Model / Tools / Evidence" view
sometimes used in reviews is intentionally **not** canonicalized as a module
taxonomy: it conflicts with ADR-0021's bounded-context model and would
introduce a third module-count vocabulary.

## Security

Model credentials are environment-owned. Set `DEEPSEEK_API_KEY`; the committed
`models_config.template.json` keeps only the `REPLACE_WITH_DEEPSEEK_API_KEY`
placeholder and must not contain real keys.

Never commit real API keys, bearer tokens, provider credentials, or operator
secrets. Keep network services bound to loopback unless the operator has
completed auth and CORS hardening. See
[security-and-data-boundaries.md](docs/security-and-data-boundaries.md).
