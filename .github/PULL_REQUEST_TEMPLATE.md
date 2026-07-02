# MY-DOGE-MICRO PR Checklist

## Ownership

- [ ] New product behavior is placed under `src/doge/products/*` and names one of Market, Research, Portfolio, or Quant.
- [ ] New platform behavior is placed under `src/doge/platform/*`, `src/doge/interfaces/gateway/routers/*`, or `src/doge/bootstrap/*` as appropriate.
- [ ] Any new `src/doge/application/*` file explains why it cannot live under `products/*` or `platform/*`.
- [ ] Source placement follows `docs/architecture/source-layout-map.md`.

## Compatibility And Maturity

- [ ] Legacy `/api/*`, shim, demo/test, and in-memory runtime rules are preserved.
- [ ] No Stable, GA, Production Ready, enterprise Beta, or production SLA claim is added.
- [ ] External/operator gates are reported separately from local evidence.
- [ ] No real provider key, bearer token, IdP secret, or production data is committed.

## Contracts And Tests

- [ ] `/v1` wire shapes remain backward compatible, or contract tests and docs explain the intentional change.
- [ ] TypeScript SDK platform entity types remain the Web source of truth.
- [ ] SDK/OpenAPI drift is checked with `python tools/ci/sdk-contract-check.py`.
- [ ] Product tests added in this PR use the matching `module_market`, `module_research`, `module_portfolio`, or `module_quant` marker.
- [ ] Relevant selective CI jobs are identified: `ci-market`, `ci-research`, `ci-portfolio`, `ci-quant`, `ci-runtime-gateway`, `ci-sdk`, `ci-eval`.
