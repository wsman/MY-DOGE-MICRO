# Financial Tool Definitions

Generated: 2026-06-21

Sprint 013 adds deterministic local finance tools for the research-agent demo.

Sprint 016 upgrades the registry into an enterprise-governed tool surface:

| Category | Examples | Rule |
|---|---|---|
| Read-only | `query_stock`, `stock_overview`, `market_breadth`, `lookup_evidence`, `get_financial_statements`, `get_company_announcements` | Auto-call when entitled |
| Analytical | `portfolio_risk`, `scenario_analysis`, `validate_financial_claims`, `calculate_financial_ratios`, `run_sql_query`, `run_python_analysis` | Auto-call with trace |
| Generative | `generate_industry_report`, `screen_compliance_risk` | Draft generation only |
| High-risk | `request_approval`, `publish_investment_memo`, `propose_portfolio_rebalance` | Requires approval |
| Forbidden | automatic trading, automatic credit approval, automatic punishment | Not registered for automation |

## Portfolio Exposure

`get_portfolio_exposure` groups holdings by:

- asset class
- sector

Weights are computed as `holding.market_value / portfolio.total_market_value`.

## Risk Metrics

`portfolio_risk` returns approximations:

- `annualized_volatility_approx`: asset-class weighted deterministic volatility.
- `max_drawdown_approx`: asset-class weighted deterministic drawdown assumption.
- `var_95_one_day_approx`: `total_market_value * volatility * 1.65 / sqrt(252)`.

These are demo calculations, not production risk models.

## Scenario Analysis

`scenario_analysis` currently supports a rate shock:

- bond holdings assume duration 7.0
- non-bond holdings assume duration 0.0
- impact is `-market_value * duration * basis_points / 10000`

## Claim Validation

`validate_financial_claims` now reports:

- `supported`: evidence or deterministic market rows support the claim.
- `contradicted`: deterministic market rows conflict with a numeric claim.
- `insufficient_evidence`: evidence exists but does not directly support the claim.
- `data_unavailable`: neither evidence nor market rows are available.

RAG evidence is preferred when available; market-row numeric matching remains a
fallback for deterministic local validation.

## Demo-Only Analysis Tools

- `run_sql_query` accepts read-only `SELECT`/`WITH` statements and returns safe
  generic errors.
- `run_python_analysis` runs in a short-lived subprocess with timeout and a
  small denylist. This is not a production sandbox.

Production deployments must replace demo execution with hardened isolation and
database authorization.
