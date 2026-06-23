# Bounded Context 03: Portfolio & Risk

> **Status**: In Review
> **Author**: Codex
> **Last Updated**: 2026-06-23
> **Related ADRs**: ADR-0001, ADR-0013, ADR-0021
> **Source Baseline**: docs/progress/platformization-consolidation-baseline.md

## Overview

Portfolio & Risk owns holdings, exposure, concentration, scenario analysis,
value-at-risk style estimates, and rebalance proposal drafts. The context is a
first-class product domain rather than an implementation detail hidden inside
tools.

## User Promise

An operator can import holdings, review portfolio risk, test scenarios, and
create rebalance drafts with clear governance boundaries around investment
actions.

## Responsibilities

- Own portfolio import validation and normalized holdings semantics.
- Own exposure, concentration, factor/risk grouping, and scenario result
  contracts.
- Own rebalance proposal drafts as non-executing recommendations.
- Publish portfolio and risk capabilities for templates and SDK clients.
- Define ports for price, factor, and market data needed by risk workflows.

## Out of Scope

- Does not execute trades or submit orders.
- Does not own market-data adapters or account/broker integrations.
- Does not own approval, entitlement, audit, or budget policy.
- Does not own UI routes or SDK packages as product modules.

## Public Contract

| Contract | Shape | Consumers |
|----------|-------|-----------|
| Portfolio import | File/rows -> normalized portfolio snapshot | Web, API, SDK |
| Exposure analysis | Portfolio snapshot -> exposure breakdown | Dashboards, templates |
| Concentration analysis | Portfolio snapshot -> concentration metrics | Risk review |
| Scenario analysis | Portfolio + scenario definition -> impact estimate | Research and risk workflows |
| Rebalance draft | Portfolio + constraints -> proposal draft | Approval workflows |

## Current Source Surfaces

| Existing Artifact | Treatment |
|-------------------|-----------|
| Portfolio API/import route | Becomes delivery surface over this context. |
| Portfolio tool provider | Moves toward `products/portfolio`. |
| ToolApplicationService portfolio methods | Become compatibility facade calls. |
| Market data storage | Remains persistence/adapter infrastructure. |

## Dependencies

- Depends on Market Intelligence for price and market capability contracts.
- Depends on Quant & Data Lab for optional factor or model experiments through
  explicit capabilities.
- Depends on Governance & Evaluation for high-risk action policy.
- Depends on Workspace & Workflow for case-linked risk review workflows.
- Must not directly import Research as a product context.

## Migration Acceptance Criteria

- Portfolio and risk appear as a primary bounded context in the module index.
- Portfolio capabilities can be executed through Provider Registry parity tests.
- Rebalance outputs are marked as drafts and require approval before any
  publication or external action.
- Portfolio import and risk routes share application services with SDK/CLI
  clients.

## Governance Notes

- Formal financial data provider approval still gates production use.
- All portfolio outputs are decision support unless a separate approved trade
  execution system exists.
- Audit events must identify actor, source, portfolio id, and run/case context
  when available.
