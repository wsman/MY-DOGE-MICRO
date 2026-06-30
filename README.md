# MY-DOGE-MICRO

MY-DOGE-MICRO is a local-first quantitative investment decision-support
platform. It combines market scans, research workflows, portfolio/risk checks,
evidence-backed agent runs, and local API/UI/MCP surfaces without requiring
cloud storage.

The architecture authority is the eight bounded-context model accepted by
ADR-0021 and mapped in [module-boundaries.md](docs/architecture/module-boundaries.md).
ADR-0024 sets the preferred new platform path:

```text
process roots -> persisted runtime -> /v1/* routes -> SDK clients
```

Legacy `/api/*`, `doge.application.composition`, the in-memory agent runtime, and PyQt
are compatibility or demo surfaces, not alternate platform stacks.

## Quick Start

Install the core package from the repository root:

```bash
pip install -e .
```

Optional surfaces:

```bash
pip install -e ".[gui]"     # PyQt6 desktop dashboard
pip install -e ".[tdx,cn]"  # TDX downloader and akshare extras
```

Run the zero-key local demo:

```bash
doge demo
```

Recommended Platform Alpha paths:

```bash
doge session --interactive          # Level 1 embedded CLI session
doged serve --port 8901             # Level 2 loopback daemon gateway
```

SDK and Web clients should use the daemon `/v1` contract. The primary workflow
is: create a session, upload/select documents, submit a turn, stream a run,
resolve approval when required, and read artifacts/citations. The main `/v1`
families for that path are `sessions`, `runs`, `documents`, `tools`, and
`platform`; `audit`, `enterprise`, `health`, and `portfolios` remain
operator/reference surfaces.

Start the FastAPI backend:

```bash
# backend source: src/doge/interfaces/api/main.py
python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901
```

Start the Vue console in another terminal:

```bash
cd web
npm install
npm run dev
```

MCP entrypoints:

```bash
scripts/mcp_stdio.bat
scripts\mcp_stdio.bat
./scripts/mcp_stdio.sh
scripts\start_mcp_sse.bat
MCP_HOST=127.0.0.1 MCP_PORT=8902 ./scripts/start_mcp_sse.sh
```

PyQt desktop entrypoint:

```bash
python src/interface/dashboard.py
```

The desktop dashboard is legacy-maintained for local use. Its bootstrap still
defines a machine-specific `qt6_bin_path` / Qt6 DLL path, so use the Web/SDK/v1
path for new platform UX work.

Model credentials are environment-owned. Set `DEEPSEEK_API_KEY`; the committed
`models_config.template.json` keeps only the `REPLACE_WITH_DEEPSEEK_API_KEY`
placeholder and must not contain real keys.

Never commit real API keys, bearer tokens, provider credentials, or operator
secrets. See [security-and-data-boundaries.md](docs/security-and-data-boundaries.md).
The main docs index is [docs/index.md](docs/index.md), and API details are in
[docs/API.md](docs/API.md).

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

The latest remotely verified SHA remains
`ee4c3283bb69ae21671ffd2d9fef908e4819ce16`, with GitHub Actions run
`28448012096` recorded in
`production/qa/evidence/ci/remote-ci-ee4c328.json`.

The prior pushed HEAD
`9f304a82ae603f0d15210d7cbfc4e502a61fea43` had exact-SHA GitHub Actions CI
run `28423757545` with result `failure`; Sprint G repaired that blocker before
promoting the new verified SHA above.

No README, release note, or docs entry should claim Stable, GA, or Production
Ready while those values remain unchanged. See
[runtime-levels.md](docs/architecture/runtime-levels.md).

## User Scenarios

Sprint G treats four product modules as the public mental model:

| Product module | What it owns |
|----------------|--------------|
| MY-DOGE Quant Core | Market data, quant views, scanner, notes, reports, and MCP tools. |
| MY-DOGE Research Agent | Session, run, document evidence, tool loop, approval, and artifacts. |
| MY-DOGE Gateway | `/v1/*`, SSE, worker-backed daemon execution, SDK/Web/remote CLI contracts. |
| MY-DOGE Eval | Gold sets, replay, metrics, trace, and regression reports. |

The product is organized around four primary user scenarios:

| Scenario | What it covers |
|----------|----------------|
| Local Quant Operator | Momentum, breadth, anomaly, ticker, archive, local DB, and macro-report workflows. |
| Researcher / Portfolio Manager | Evidence-backed market/company/industry research with approval and artifacts. |
| Enterprise Integrator | API, SDK, MCP, SSE, tenant/auth placeholders, and daemon integration contracts. |
| Eval / Demo Owner | Reproducible cases, deterministic offline runs, metrics, and trace review. |

See [user-scenarios.md](docs/product/user-scenarios.md) for the scenario
contract.

## Architecture Map

The counted product/platform modules are:

| # | Context | Type | CDD |
|---|---------|------|-----|
| 1 | Market Intelligence | Product | [bc-01-market-intelligence.md](design/cdd/bc-01-market-intelligence.md) |
| 2 | Research | Product | [bc-02-research.md](design/cdd/bc-02-research.md) |
| 3 | Portfolio & Risk | Product | [bc-03-portfolio-risk.md](design/cdd/bc-03-portfolio-risk.md) |
| 4 | Quant & Data Lab | Product | [bc-04-quant-data-lab.md](design/cdd/bc-04-quant-data-lab.md) |
| 5 | Workspace & Workflow | Platform | [bc-05-workspace-workflow.md](design/cdd/bc-05-workspace-workflow.md) |
| 6 | Agent Runtime | Platform | [bc-06-agent-runtime.md](design/cdd/bc-06-agent-runtime.md) |
| 7 | Knowledge & Evidence | Platform | [bc-07-knowledge-evidence.md](design/cdd/bc-07-knowledge-evidence.md) |
| 8 | Governance & Evaluation | Platform | [bc-08-governance-evaluation.md](design/cdd/bc-08-governance-evaluation.md) |

Delivery channels such as FastAPI, Web, CLI, daemon, SDK, MCP, and PyQt are
not counted modules. Storage/model/market-data providers are adapters behind
ports. See [module-map.md](docs/reference/module-map.md).

## Where To Add New Code

- New canonical code lives under `src/doge/`.
- Gateway implementation lives under `src/doge/interfaces/gateway/`.
- `/v1` compatibility shims live under `src/doge/interfaces/api/routers/v1/`
  and must stay logic-free.
- Legacy compatibility code lives under `src/macro`, `src/micro`,
  `src/interface`, `doge.interfaces.api_legacy`, and old `/api/*` paths.
- Demo/test-only paths, including in-memory runtime behavior and scripted
  fixtures, must be labeled and must not become runtime defaults.
- Add product-facing market work under `doge.products.market` or its legacy
  implementation path with a facade export.
- Add research work under `doge.products.research`.
- Add portfolio/risk work under `doge.products.portfolio`.
- Add quant/data-lab work under `doge.products.quant`.
- Add workspace/case/template behavior under `doge.platform.workspace`.
- Add runtime orchestration under `doge.platform.runtime`.
- Add document/evidence/claim/citation behavior under `doge.platform.evidence`.
- Add auth, tenant, entitlement, audit, secrets, approval, and maturity work
  under `doge.platform.governance`.

## Path Classification

| Class | Description | Examples |
|-------|-------------|----------|
| **Canonical** | Preferred new platform paths. All new features belong here. | `src/doge/`, `doge.bootstrap.*`, `doge.interfaces.gateway.routers`, `doge.application.tools`, `doge.platform.*`, `doge.products.*` |
| **Compatibility** | Re-export/delegate shims preserving brownfield imports. No new behavior. | `doge.application.composition`, `doge.application.agent.tools`, `doge.interfaces.api.routers`, `doge.interfaces.api.routers.v1` |
| **Legacy** | Active legacy implementations being deprecated. No new platform-only features. | `src/macro/`, `src/micro/`, `src/interface/`, `doge.interfaces.api_legacy.routers`, legacy `/api/*` routes |
| **Demo/Test** | Demo and test-only paths. Must not become production defaults. | `doge.infrastructure.agent.inmemory_runtime`, `doge.infrastructure.agent.scripted_model`, fixture portfolios, `portfolio-demo` seed data |

See [compatibility-surfaces.md](docs/architecture/compatibility-surfaces.md)
and [ADR-0027](docs/architecture/adr-0027-shim-sunset-policy.md) for the
compatibility-surface registry and sunset rules.

Use [module-boundaries.md](docs/architecture/module-boundaries.md) and
[file-structure-policy.md](docs/architecture/file-structure-policy.md) before
adding new files.

Useful local checks:

```bash
python scripts/validate_docs_links.py
python -m pytest tests/unit/layer_gates -q
python -m pytest tests/unit/architecture -q
python -m pytest tests/contract/test_v1_api.py tests/contract/test_python_sdk.py -q
```
