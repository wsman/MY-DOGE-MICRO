# MY-DOGE-MICRO

MY-DOGE-MICRO is a local-first quantitative investment decision-support
platform for an individual operator. It combines local market-data storage,
market scans, research workflows, portfolio/risk checks, evidence-backed agent
runs, and local API/UI/MCP surfaces without making cloud storage a requirement.

The current architecture authority is the eight bounded-context model accepted
by ADR-0021. Historical Macro/Micro wording is preserved only as archive
material in [legacy-macro-micro.md](docs/archive/old-architecture/legacy-macro-micro.md).

## Current Maturity

Runtime maturity is intentionally conservative:

| Signal | Current value | Authority |
|--------|---------------|-----------|
| Level 1 embedded CLI/session | Preview | [runtime-maturity.yaml](docs/progress/runtime-maturity.yaml) |
| Level 2 daemon gateway | Alpha | [runtime-maturity.yaml](docs/progress/runtime-maturity.yaml) |
| Level 3 SDK/platform | Experimental | [runtime-maturity.yaml](docs/progress/runtime-maturity.yaml) |
| Production ready | `false` | [runtime-maturity.yaml](docs/progress/runtime-maturity.yaml) |
| Stable declaration | `forbidden` | [runtime-maturity.yaml](docs/progress/runtime-maturity.yaml) |

Current machine-readable posture:

```yaml
production_ready: false
stable_declaration: forbidden
```

No README, release note, or docs entry should claim Stable, GA, or Production
readiness while those values remain unchanged.

## Documentation Map

Start with [docs/index.md](docs/index.md). The older product reference paths
remain valid because tests and ADR/CDD references still pin them.

| Need | Start here |
|------|------------|
| Product overview and user scenarios | [docs/product/overview.md](docs/product/overview.md) |
| Operator setup | [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) |
| HTTP API contract | [docs/API.md](docs/API.md) and [docs/reference/api.md](docs/reference/api.md) |
| CLI contract | [docs/CLI.md](docs/CLI.md) and [docs/reference/cli.md](docs/reference/cli.md) |
| MCP tools | [docs/MCP_SERVER.md](docs/MCP_SERVER.md) and [docs/reference/mcp.md](docs/reference/mcp.md) |
| Local deployment and operations | [docs/operations-runbook.md](docs/operations-runbook.md) and [docs/operations/local-deployment.md](docs/operations/local-deployment.md) |
| Architecture overview | [docs/architecture/overview.md](docs/architecture/overview.md) |
| Current quality/status rollup | [docs/quality/status.md](docs/quality/status.md) |

`docs/QUICK-START.md` and `docs/START-HERE.md` describe the CDD governance
framework and agent studio. They are not the operator guide for this product.

## Bounded Contexts

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
ports. Physical source moves remain governed by ADR-0022 and must be story-gated.

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

### MCP Surface

Windows stdio:

```bash
scripts\mcp_stdio.bat
```

Repo-relative path: `scripts/mcp_stdio.bat`.

POSIX stdio:

```bash
./scripts/mcp_stdio.sh
```

SSE helpers:

```bash
scripts\start_mcp_sse.bat
MCP_HOST=127.0.0.1 MCP_PORT=8902 ./scripts/start_mcp_sse.sh
```

All MCP scripts invoke [doge_mcp.py](doge_mcp.py).

### FastAPI And Web Surface

Start the backend:

```bash
python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901
```

The canonical backend source is
[src/doge/interfaces/api/main.py](src/doge/interfaces/api/main.py). The HTTP
reference currently enumerates 76 product routes in [docs/API.md](docs/API.md).

Start the Vue console in another terminal:

```bash
cd web
npm install
npm run dev
```

[web/package.json](web/package.json) owns the web scripts.

### PyQt Desktop Surface

```bash
python src/interface/dashboard.py
```

The desktop entrypoint is [src/interface/dashboard.py](src/interface/dashboard.py).
It still contains a known portability blocker named `qt6_bin_path`: on machines
whose PyQt6 Qt DLLs are not installed at that hardcoded path, the dashboard may
need a local PATH or DLL-location adjustment. This warning should be removed
only when that bootstrap is retired.

## Secrets

The v1 live Kimi release baseline is the Kimi Coding endpoint
(`https://api.kimi.com/coding/v1`) for chat-centered research work. It supports
Research Agent runs, report generation, tool/function calling, thinking mode,
and model routing through the OpenAI-compatible chat API.

Set `KIMI_CODING_MODE=1` and provide an operator-owned `sk-kimi-*` key through
`MOONSHOT_API_KEY`:

```bash
set KIMI_CODING_MODE=1
set MOONSHOT_API_KEY=sk-kimi-your-real-key-here
```

PowerShell:

```powershell
$env:KIMI_CODING_MODE='1'
$env:MOONSHOT_API_KEY='sk-kimi-your-real-key-here'
```

Kimi Coding is chat-centered and does not expose `/files`. API/CLI document
attachments still work through local payload storage, `LocalDocumentParser`,
SQLite evidence records, and local RAG lookup; they are not uploaded to Kimi in
coding mode. If Kimi-side file context becomes required, configure a separate
ordinary Moonshot key and a future split-client path that routes chat to Kimi
Coding and files to Moonshot.

DeepSeek remains a supported compatibility/fallback provider. To use it
explicitly, set `DOGE_TEXT_LLM_PROVIDER=deepseek` and provide
`DEEPSEEK_API_KEY`. The committed model config files ship only the placeholder
`REPLACE_WITH_DEEPSEEK_API_KEY`.

```bash
set DOGE_TEXT_LLM_PROVIDER=deepseek
set DEEPSEEK_API_KEY=sk-your-real-key-here
```

PowerShell:

```powershell
$env:DOGE_TEXT_LLM_PROVIDER='deepseek'
$env:DEEPSEEK_API_KEY='sk-your-real-key-here'
```

The loopback daemon defaults to port `8901`. Override both `doged serve` and
`doged status` defaults with `DOGE_DAEMON_PORT`, or pass `--port` to either
command.

Daemon process roles default to local-development `all`, which starts the API
and in-process worker together. Production-style deployments should set
`DOGE_PROCESS_ROLE` explicitly:

- `api` starts FastAPI without an in-process worker.
- `worker` starts the durable worker and optional outbox publisher only.
- `all` preserves the local combined topology.

The package also exposes `doged-api` and `doged-worker` console scripts for the
split roles.

Never commit real API keys, bearer tokens, provider credentials, or operator
secrets. See [security-and-data-boundaries.md](docs/security-and-data-boundaries.md)
and [operations-runbook.md](docs/operations-runbook.md).

## Verification

Useful local checks:

```bash
python scripts/validate_no_stale_counts.py
python scripts/validate_docs_links.py
python scripts/generate_docs_status.py --check
python -m pytest tests/contract/test_api_doc_route_coverage.py -q
python -m pytest tests/cli/test_cli_arg_parsing.py tests/cli/test_getting_started_links.py -q
```

The full Python regression remains:

```bash
python -m pytest -q
```
