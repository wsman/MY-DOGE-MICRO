# Quant & Data Lab (`doge.products.quant`)

> Product module: analytical views, read-only SQL, bounded Python analysis, and factor/backtest extensions.
> Authorities: [module-boundaries.md](../../../../docs/architecture/module-boundaries.md) · [modules.md](../../../../docs/product/modules.md) · [source-layout-map.md](../../../../docs/architecture/source-layout-map.md)

## User Goal

A quant or data analyst runs read-only SQL over local analytical views, executes
bounded Python analysis, or drafts factor/backtest experiments — without
ungoverned database access or unrestricted code execution.

## Public Contract

Analytical views, read-only SQL execution, bounded Python analysis capability,
and factors/backtest/data-job extensions.

## Owned Tools

- `QuantToolProvider` (`tools.py`) — canonical quant tool execution. The
  implementation lives in this package; `doge.application.capabilities.quant_provider`
  re-exports it for compatibility only.

## Produced Artifacts

Analytical request/response contracts, query result sets, factor notebook
artifacts, backtest drafts, and quant experiment traces.

## Allowed Collaborators

May call view services/repositories through ports and governance policy. Python
analysis is disabled-by-default and must remain governed; SQL access is read-only.

## Forbidden Ownership / Imports

- Does NOT own product workflow orchestration.
- MUST NOT open unrestricted DB connections, run ungoverned code execution, or
  import sibling product packages (`doge.products.market`,
  `doge.products.research`, `doge.products.portfolio`), runtime implementation,
  or persistence drivers directly. Enforced by
  [module-ownership.yaml](../../../../docs/architecture/module-ownership.yaml)
  and `tests/unit/layer_gates/`.

## Tests and Pytest Markers

- Marker: `module_quant` (registered in `pyproject.toml`; tagging is incremental).
- Boundary ownership: `tests/unit/layer_gates/test_module_ownership.py`.
- Add quant-focused tests and tag them `@pytest.mark.module_quant`.

## Maturity Posture

Level 1/2 Alpha; bounded Python analysis is feature-gated and disabled by
default. `production_ready: false`, `stable_declaration: forbidden`.
See [runtime-maturity.yaml](../../../../docs/progress/runtime-maturity.yaml).
