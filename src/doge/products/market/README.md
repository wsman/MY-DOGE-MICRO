# Market Intelligence (`doge.products.market`)

> Product module: market data, scans, breadth, momentum, anomalies, and ticker metadata.
> Authorities: [module-boundaries.md](../../../../docs/architecture/module-boundaries.md) · [modules.md](../../../../docs/product/modules.md) · [source-layout-map.md](../../../../docs/architecture/source-layout-map.md)

## User Goal

A local quant operator or analyst asks "what is the market doing right now?" —
breadth, strongest trends, deteriorating width, unusual volume, or a single
ticker's snapshot — and gets a deterministic, local-first answer without a cloud
round-trip.

## Public Contract

Market scans, stock/ticker lookup, RSRS momentum ranking, market breadth,
volume anomalies, ticker metadata, and market reports. These market-facing
capabilities are exposed through the CLI, MCP, `/v1`, and the Web Market surface.

## Owned Tools

- `MarketToolProvider` (`tools.py`) — canonical market tool execution. The
  implementation lives in this package; `doge.application.capabilities.market_provider`
  re-exports it for compatibility only.

## Produced Artifacts

Market snapshot projections, scan result rows, RSRS rankings, breadth summaries,
volume-anomaly alerts, and ticker query results. Artifacts are local evidence,
not production release proof.

## Allowed Collaborators

May call core market ports/services, market-data adapters through ports,
governance/capability policy, and bootstrap-provided repositories. Composes with
Quant & Data Lab (analytical reads) and Governance & Evaluation (policy).

## Forbidden Ownership / Imports

- Does NOT own research memos, portfolio risk, quant analysis, or runtime state.
- MUST NOT import sibling product packages (`doge.products.research`,
  `doge.products.portfolio`, `doge.products.quant`), runtime implementation, or
  persistence drivers directly. Enforced by
  [module-ownership.yaml](../../../../docs/architecture/module-ownership.yaml)
  and `tests/unit/layer_gates/`.

## Tests and Pytest Markers

- Marker: `module_market` (registered in `pyproject.toml`; tagging is incremental).
- Boundary ownership: `tests/unit/layer_gates/test_module_ownership.py`.
- Add market-focused tests under `tests/unit/` or `tests/integration/` and tag
  them `@pytest.mark.module_market`.

## Maturity Posture

Level 1/2 Alpha. `production_ready: false`, `stable_declaration: forbidden`.
See [runtime-maturity.yaml](../../../../docs/progress/runtime-maturity.yaml).
