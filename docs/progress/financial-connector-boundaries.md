# Financial Connector Boundaries

Generated: 2026-06-21

## Purpose

Wave 2 establishes replaceable financial data connector boundaries without
claiming that production market-data providers are configured.

## Ports Added

- `IFinancialStatementRepository`
- `ICompanyAnnouncementRepository`
- `IConsensusEstimateRepository`
- `IIndustryClassificationSource`
- `IRiskFactorSource`

Source: `src/doge/core/ports/financial_connectors.py`

## Default Local Adapters

| Connector | Default Adapter | Provider Status |
|---|---|---|
| Financial statements | `StockOverviewFinancialStatementRepository` | `fallback` when local overview fields exist; otherwise `provider_unavailable` |
| Company announcements | `LocalNoteAnnouncementRepository` | `fallback` when local notes exist; otherwise `provider_unavailable` |
| Consensus estimates | `UnavailableConsensusEstimateRepository` | Always `provider_unavailable` until a provider is configured |
| Industry classification | `StaticIndustryClassificationSource` | `fallback` for known demo tickers; otherwise `provider_unavailable` |
| Risk factors | `StaticRiskFactorSource` | Static local assumptions for demo VaR/scenario calculations |

## Tool Behavior

The agent financial tools now return explicit provider metadata instead of
ambiguous demo statuses:

- `get_financial_statements`
- `get_company_announcements`
- `compare_consensus_estimates`
- `get_industry_classification`
- `portfolio_risk`
- `scenario_analysis`

## Production Boundary

These connectors are not production data sources. They are explicit replacement
points for future providers such as exchange disclosures, licensed fundamentals,
consensus feeds, industry classification databases, and factor models.

No production-risk claim is allowed until configured adapters include provider
provenance, freshness metadata, typed error states, and contract tests against
provider-shaped fixtures.

Sprint 016 provider choices and fixture requirements are recorded in
`docs/progress/financial-provider-fixture-contract.md`, with a machine-readable
manifest at
`tests/fixtures/financial_connectors/provider_fixture_contract.json`. Real
provider adapters are transferred to Sprint 017 external validation and provider
hardening.
