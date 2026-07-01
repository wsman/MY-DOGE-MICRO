# MY-DOGE-MICRO

MY-DOGE-MICRO is a local-first quantitative investment decision-support
platform. It combines market scans, research workflows, portfolio/risk checks,
evidence-backed agent runs, and local API/UI/MCP surfaces without requiring
cloud storage.

Architecture details start at [docs/index.md](docs/index.md). The reader-facing
architecture authorities are [overview.md](docs/architecture/overview.md),
[runtime-contracts.md](docs/architecture/runtime-contracts.md), and
[file-structure-policy.md](docs/architecture/file-structure-policy.md).

Legacy `/api/*`, `doge.application.composition`, the in-memory agent runtime, and PyQt
are compatibility or demo surfaces, not alternate platform stacks.

## Quick Start

Install the core package from the repository root:

```bash
pip install -e .
```

Run the zero-key local demo:

```bash
doge demo
```

Recommended Platform Alpha entrypoints:

```bash
doge session --interactive          # embedded local research session
doged serve --port 8901             # loopback daemon gateway
```

Backend source and command:

```bash
# backend source: src/doge/interfaces/api/main.py
python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901
```

Vue console setup is covered in [guides/getting-started.md](docs/guides/getting-started.md).
The MCP stdio helper remains `scripts/mcp_stdio.bat`.

Optional PyQt desktop entrypoint:

```bash
pip install -e ".[gui]"
python src/interface/dashboard.py
```

The desktop dashboard is legacy-maintained for local use. Its bootstrap still
defines a machine-specific `qt6_bin_path` / Qt6 DLL path, so use the Web/SDK/v1
path for new platform UX work.

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

The latest remotely verified SHA remains
`ee4c3283bb69ae21671ffd2d9fef908e4819ce16`, with GitHub Actions run
`28448012096` recorded in
`production/qa/evidence/ci/remote-ci-ee4c328.json`.

The prior pushed HEAD `9f304a82ae603f0d15210d7cbfc4e502a61fea43` had exact-SHA GitHub Actions CI
run `28423757545` with result `failure`; Sprint G repaired that blocker before
promoting the verified SHA above.

No README, release note, or docs entry should claim Stable, GA, or Production
Ready while those values remain unchanged. See
[runtime-levels.md](docs/architecture/runtime-levels.md).

## Security

Model credentials are environment-owned. Set `DEEPSEEK_API_KEY`; the committed
`models_config.template.json` keeps only the `REPLACE_WITH_DEEPSEEK_API_KEY`
placeholder and must not contain real keys.

Never commit real API keys, bearer tokens, provider credentials, or operator
secrets. Keep network services bound to loopback unless the operator has
completed auth and CORS hardening. See
[security-and-data-boundaries.md](docs/security-and-data-boundaries.md).
