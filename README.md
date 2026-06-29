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
| Level 1 embedded CLI/session | Preview |
| Level 2 daemon gateway | Alpha |
| Level 3 SDK/platform | Experimental |
| Production ready | `false` |
| Stable declaration | `forbidden` |

Current governance values:

```yaml
production_ready: false
stable_declaration: forbidden
```

The promoted remote baseline remains
`b5ab80bc802df36b58a1e56225a87b0f2473b29e`.

The current pushed HEAD
`fd1768fa690a9a0c3a8d7905a7b72f0af54f6b04`
has local evidence and GitHub Actions run `28326916286` recorded in
`production/qa/evidence/ci/remote-ci-fd1768f.json`.

No README, release note, or docs entry should claim Stable, GA, or Production
Ready while those values remain unchanged. See
[runtime-levels.md](docs/architecture/runtime-levels.md).

## User Scenarios

The product is organized around four primary scenarios:

| Scenario | What it covers |
|----------|----------------|
| Market Scan | Momentum, breadth, anomaly, ticker, and archive workflows. |
| Research Memo | Evidence-backed market/company/industry research. |
| Portfolio Risk | Holdings, exposure, scenarios, and governed rebalance proposals. |
| Governed Agent Workflow | Workspaces, cases, runs, approvals, evidence, audit, and maturity. |

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

Use [module-boundaries.md](docs/architecture/module-boundaries.md) and
[module-ownership.yaml](docs/architecture/module-ownership.yaml) before adding
new files.

Useful local checks:

```bash
python scripts/validate_docs_links.py
python -m pytest tests/unit/layer_gates -q
python -m pytest tests/unit/architecture -q
python -m pytest tests/contract/test_v1_api.py tests/contract/test_python_sdk.py -q
```
