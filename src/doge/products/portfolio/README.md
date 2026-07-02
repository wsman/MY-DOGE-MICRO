# Portfolio & Risk (`doge.products.portfolio`)

> Product module: holdings, portfolio import, exposure, concentration, risk, and scenario analysis.
> Authorities: [module-boundaries.md](../../../../docs/architecture/module-boundaries.md) · [modules.md](../../../../docs/product/modules.md) · [source-layout-map.md](../../../../docs/architecture/source-layout-map.md)

## User Goal

A portfolio manager or risk analyst asks "what is my exposure and concentration,
and what happens to the book if rates or a single name move?" — and gets
holdings, exposure, concentration, scenario stress, and rebalance proposals
gated by approval policy for high-risk actions.

## Public Contract

Holdings, portfolio import, exposure, concentration, risk, scenario analysis,
and rebalance-proposal contracts.

## Owned Tools

- `PortfolioToolProvider` (`tools.py`) — canonical portfolio tool execution. The
  implementation lives in this package; `doge.application.capabilities.portfolio_provider`
  re-exports it for compatibility only.

## Produced Artifacts

Portfolio holdings, scenario inputs, risk summaries, concentration reports, and
rebalance proposals. High-risk rebalance proposals must flow through Governance
approval before they become binding.

## Allowed Collaborators

May call Market Intelligence contracts for price/market context and Governance &
Evaluation for high-risk action policy. Does not duplicate market-data
maintenance or research workflows.

## Forbidden Ownership / Imports

- Does NOT own market-data maintenance, research workflows, or concrete model SDKs.
- MUST NOT import sibling product packages (`doge.products.market`,
  `doge.products.research`, `doge.products.quant`), runtime implementation, or
  persistence drivers directly. Enforced by
  [module-ownership.yaml](../../../../docs/architecture/module-ownership.yaml)
  and `tests/unit/layer_gates/`.

## Tests and Pytest Markers

- Marker: `module_portfolio` (registered in `pyproject.toml`; tagging is incremental).
- Boundary ownership: `tests/unit/layer_gates/test_module_ownership.py`.
- Add portfolio-focused tests and tag them `@pytest.mark.module_portfolio`.

## Maturity Posture

Level 1/2 Alpha. `production_ready: false`, `stable_declaration: forbidden`.
See [runtime-maturity.yaml](../../../../docs/progress/runtime-maturity.yaml).
