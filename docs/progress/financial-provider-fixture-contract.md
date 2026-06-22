# Financial Provider And Fixture Contract

Generated: 2026-06-22

## Purpose

This closes Sprint 016's real-connector planning gap without pretending that
licensed production providers are configured. The current code keeps local
fallback adapters. Sprint 017 may implement the provider adapters below once
credentials, fixtures, and legal access are approved.

## Provider Choices

| Capability | Preferred Provider | Local / Open Fallback | Fixture Owner | Sprint 016 Status |
|---|---|---|---|---|
| Financial statements | Exchange filings or licensed fundamentals provider | `StockOverviewFinancialStatementRepository` | `tests/fixtures/financial_connectors/provider_fixture_contract.json`; `tests/fixtures/financial_connectors/provider_fixture_samples.json` | Contract approved; provider adapter deferred |
| Company announcements | Exchange disclosure feed | `LocalNoteAnnouncementRepository` | same fixture manifest | Contract approved; provider adapter deferred |
| Consensus estimates | Licensed consensus feed | `UnavailableConsensusEstimateRepository` | same fixture manifest | Contract approved; provider adapter deferred |
| Industry classification | Licensed industry taxonomy or exchange sector map | `StaticIndustryClassificationSource` | same fixture manifest | Contract approved; provider adapter deferred |
| Risk factors | Licensed factor/risk model feed | `StaticRiskFactorSource` | same fixture manifest | Contract approved; provider adapter deferred |

## Fixture Requirements

All provider fixtures must include:

- `provider`: provider name or fixture provider alias.
- `as_of`: ISO date for data freshness.
- `retrieved_at`: ISO timestamp for retrieval freshness.
- `source_url` or `source_id`: provider provenance reference.
- `license_scope`: test/demo/prod-use marker.
- `ticker` or `portfolio_id`: resource key.
- `currency` where monetary values are present.
- `provider_status`: `ok`, `fallback`, `provider_unavailable`, `stale_data`,
  or `entitlement_denied`.

Connector-specific minimum fields:

| Connector | Minimum Fixture Fields |
|---|---|
| Financial statements | `period`, `revenue`, `net_income`, `operating_cash_flow`, `total_assets`, `total_liabilities` |
| Announcements | `announcement_id`, `title`, `published_at`, `category`, `source_url`, `summary` |
| Consensus | `metric`, `period`, `mean`, `median`, `low`, `high`, `contributors` |
| Industry classification | `system`, `level_1`, `level_2`, `code`, `name` |
| Risk factors | `factor_model`, `factor`, `exposure`, `beta`, `volatility`, `as_of` |

## Acceptance For Sprint 017 Adapter Work

Before any real adapter can replace the local fallbacks:

- Provider credentials and license scope are confirmed by the operator.
- Synthetic fixtures matching this contract exist and are safe to commit; real
  provider-derived fixtures still require provider/license approval.
- Contract tests cover fresh data, stale data, provider unavailable, malformed
  payload, and entitlement-denied paths.
- Tool responses expose provider provenance and freshness metadata.
- No production investment/risk claim is made until provider-backed smoke
  evidence exists.
