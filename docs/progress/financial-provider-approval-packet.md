# Financial Provider Approval Packet

Generated: 2026-06-22

## Purpose

This prepares S017-003 for product-owner/operator approval. It does not approve
licensed providers by itself and does not authorize real data ingestion.

## Approval Request

Please approve or replace the provider direction below before implementation of
real adapters:

| Capability | Preferred Provider Direction | Local Fallback | Approval State |
|---|---|---|---|
| Financial statements | Exchange filings or licensed fundamentals provider | `StockOverviewFinancialStatementRepository` | Pending product/operator approval |
| Company announcements | Exchange disclosure feed | `LocalNoteAnnouncementRepository` | Pending product/operator approval |
| Consensus estimates | Licensed consensus feed | `UnavailableConsensusEstimateRepository` | Pending product/operator approval |
| Industry classification | Licensed taxonomy or exchange sector map | `StaticIndustryClassificationSource` | Pending product/operator approval |
| Risk factors | Licensed factor/risk model feed | `StaticRiskFactorSource` | Pending product/operator approval |

## Fixture Contract

Machine-readable fixture schema:
`tests/fixtures/financial_connectors/provider_fixture_contract.json`

Synthetic safe fixture samples:
`tests/fixtures/financial_connectors/provider_fixture_samples.json`

Approval evidence template:
`production/qa/evidence/provider/financial-provider-approval-template-2026-06-22.json`

Approval evidence validator:
`scripts/validate_financial_provider_approval_evidence.py`

Approval evidence builder:
`scripts/build_financial_provider_approval_evidence.py`

The builder reads a compact operator decision JSON, merges it with the approval
template, runs the validator, and writes completed evidence only if the result
is structurally valid. It supports `approved`, `needs_revision`, and
`rejected`; non-approved evidence must include `issue_refs`.

Required fixture rules:

- Fixtures must be synthetic, licensed for test use, or explicitly approved for
  repository storage.
- Each fixture must include provider, freshness, provenance, license scope,
  resource key, and typed provider status.
- Synthetic fixture samples now cover `ok`, `provider_unavailable`,
  `stale_data`, malformed payload, and `entitlement_denied`; real provider
  fixtures still require operator/license approval before adapter work starts.

## Adapter Gate

Real provider adapter work may start only after:

1. Provider choice or provider-neutral adapter target is approved.
2. Legal/license scope for committed fixtures is recorded.
3. Safe fixtures matching the contract are available for the target provider
   class; synthetic fixtures alone are sufficient only for local contract tests.
4. Contract tests include success, stale, unavailable, malformed, and
   entitlement-denied cases.
5. Tool responses expose provider provenance and freshness metadata.

## Current Decision

S017-003 is ready for review, not done. The local fallback adapters, fixture
contract, synthetic safe fixture samples, approval evidence template, evidence
builder, and validator are implemented; operator approval, provider/license
scope, and any real provider-derived fixtures remain external dependencies. The
template validates only with `--allow-template`; default validation requires
completed approval evidence.
