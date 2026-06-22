# Capability Registry

> **Status**: In Design
> **Author**: User + Codex
> **Last Updated**: 2026-06-22
> **Implements Pillar**: Operator Control; Evidence Before Narrative; Incremental Migration

## Overview

Capability Registry defines a single inspectable view of model providers, financial tools, workflow prerequisites, feature flags, and runtime readiness. It lets the platform decide what can be shown or executed without scattering provider checks across the UI and runtime.

## User Promise

An operator can see which models, tools, workflows, and evidence features are available in the current environment before starting a workflow that might fail or require approval.

## Detailed Design

### Implementation Status

The first local slice is implemented behind `DOGE_FEATURE_CAPABILITY_REGISTRY`:

- `BuildCapabilityRegistry` now assembles records from `CapabilityProvider`
  implementations.
- Feature, provider, API, maturity, and default tool metadata providers exist.
- Tool records are sourced from `ToolRegistry.capability_records_for_context()`,
  preserving schema redaction and high-risk approval metadata without executing
  tools.
- `ToolApplicationService` remains the public facade and can delegate execution
  to provider-backed market, portfolio, research, fundamental, quant,
  compliance, and publishing adapters when `DOGE_FEATURE_CAPABILITY_REGISTRY`
  is enabled; the default construction path remains direct for rollback.
- Tests cover provider-split zero-delta behavior, tool-schema parity,
  execution-result parity, entitlement redaction, high-risk approval metadata,
  secret redaction, enterprise ACL denial, and runtime maturity blocking.

Still open: dependency graph validation, persisted snapshots, live health
checks, and workflow preflight.

### Core Specification

1. The registry records capabilities, not secrets. API keys and credentials remain in configured secret channels.
2. Capabilities include provider models, tool categories, evidence features, workflow requirements, API surfaces, and UI feature flags.
3. Each capability has status: `available`, `unconfigured`, `degraded`, `disabled`, or `blocked`.
4. Provider-specific checks stay behind provider adapters and expose normalized capability records.
5. Tool governance remains authoritative for entitlement and approval; registry status is advisory for visibility and preflight.
6. Capability snapshots are safe to expose to UI and SDK clients after redaction.
7. Production readiness must remain false while runtime maturity and external closure gates are open.

### States and Transitions

| State | Meaning | Valid Transitions |
|-------|---------|-------------------|
| `available` | Capability can be used under current policy. | `degraded`, `disabled`, `blocked`. |
| `unconfigured` | Capability exists but lacks local configuration. | `available`, `disabled`. |
| `degraded` | Capability works with limitations or stale health. | `available`, `blocked`, `disabled`. |
| `disabled` | Capability is intentionally hidden or inactive. | `available`, `unconfigured`. |
| `blocked` | Capability cannot be used due to policy, missing evidence, or maturity gate. | `available`, `degraded`, `disabled`. |

### Interactions with Other Modules

| Module | Interaction |
|--------|-------------|
| Enterprise Model Gateway | Supplies provider and model availability metadata. |
| Financial Tool Governance | Supplies tool category, entitlement, approval, and risk metadata. |
| Workflow Templates | Uses required capability checks before execution. |
| Platform Shell UI | Displays feature and capability availability. |
| SDK And Daemon Client Interfaces | Exposes capability discovery to clients. |
| Runtime Maturity Governance | Supplies non-production and gate status. |

## Data Model

The `capability` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `capability_id` | string | Yes | Stable slug or UUID | Capability identifier. |
| `kind` | enum | Yes | `model_provider`, `model`, `tool`, `workflow`, `evidence`, `api`, `ui`, `maturity` | Capability type. |
| `name` | string | Yes | 1 to 160 chars | Display name. |
| `status` | enum | Yes | `available`, `unconfigured`, `degraded`, `disabled`, `blocked` | Current status. |
| `source` | string | Yes | Adapter or config key | Source of the status. |
| `risk_level` | enum | No | `low`, `medium`, `high` | Governance risk level. |
| `requires_approval` | bool | Yes | Boolean | Whether use may require explicit approval. |
| `last_checked_at` | datetime | No | UTC | Last health or config check. |
| `metadata` | json | No | Redacted | Non-secret provider/tool metadata. |

**Relationships:** `capability` -> `capability_dependency` (1:N) via `capability_id`.
**Indexes:** `kind`, `status`, `source`, `risk_level`.
**Example:** `kimi-vision` is `unconfigured` if no provider credentials are available.

The `capability_dependency` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `dependency_id` | string | Yes | Stable UUID or ULID | Dependency identifier. |
| `capability_id` | string | Yes | References capability | Capability being gated. |
| `required_capability_id` | string | Yes | References capability | Required capability. |
| `requirement_type` | enum | Yes | `hard`, `soft`, `policy`, `evidence` | Dependency class. |
| `failure_status` | enum | Yes | `degraded`, `blocked`, `disabled` | Status applied when requirement fails. |

**Relationships:** Capability dependency forms a directed graph.
**Indexes:** `capability_id`, `required_capability_id`.
**Example:** `stock-diligence-template` has a hard dependency on model gateway and evidence citation API.

The `capability_snapshot` entity is defined as:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `snapshot_id` | string | Yes | Stable UUID or ULID | Snapshot identifier. |
| `created_at` | datetime | Yes | UTC | Snapshot time. |
| `status_counts` | json | Yes | Count by status | Summary counts. |
| `redaction_version` | string | Yes | Non-empty | Redaction policy version. |
| `maturity_flags` | json | Yes | Redacted gate labels | Runtime maturity and closure posture. |

**Relationships:** Snapshot contains redacted capability records.
**Indexes:** `created_at`.
**Example:** A shell boot response includes the latest snapshot ID for diagnostics.

## Edge Cases

- **If provider health check times out**: mark provider `degraded` or `unconfigured` according to config presence; do not block unrelated local tools.
- **If a secret is accidentally returned by an adapter**: redact before persistence or API response and fail validation.
- **If capability dependencies form a cycle**: reject the update and report the cycle.
- **If runtime maturity says production_ready is false**: expose production readiness as `blocked` regardless of individual feature health.
- **If a tool is available but approval is required**: status can be `available` with `requires_approval=true`.
- **If a workflow requires a disabled capability**: workflow preflight returns blocked with the missing dependency list.

## Dependencies

- Depends on Enterprise Model Gateway, Financial Tool Governance, Runtime Configuration, and runtime maturity governance.
- Integrates with Workflow Templates for optional workflow capability records and is consumed by Platform Shell UI, SDK clients, and web console route guards.
- Governed by ADR-0012, ADR-0013, ADR-0015, and ADR-0019.

## Configuration

| Parameter | Default | Scope | Description |
|-----------|---------|-------|-------------|
| `DOGE_FEATURE_CAPABILITY_REGISTRY` | `false` by default | Runtime flag | Enables registry assembly and API discovery. |
| `DOGE_CAPABILITY_HEALTH_TIMEOUT_MS` | `1000` | Runtime config | Maximum per-adapter health check time. |
| `DOGE_CAPABILITY_INCLUDE_HEALTH` | `false` | Runtime config | Allows live health checks; false means config-only snapshot. |

## Integration Requirements

- API route should expose a redacted discovery endpoint such as `/v1/capabilities`.
- Adapters must register normalized capability records through a facade, not by UI-specific code.
- Workflow execution preflight must consume the same registry facade.
- Tests must verify secret redaction, dependency blocking, maturity-gate blocking, and provider adapter normalization.
- Capability status must be deterministic in tests without live provider spend.

## UI Requirements

- Platform shell should show a compact capability status view with provider, tool, workflow, and maturity sections.
- Disabled or blocked capabilities should explain the blocker without exposing secrets.
- Workflow template cards should show missing capabilities before execution.
- Experimental and blocked runtime maturity labels must be visible.

## Acceptance Criteria

- **GIVEN** a provider adapter with no configured key, **WHEN** capability discovery runs, **THEN** the provider capability is `unconfigured` and no secret value is returned.
- **GIVEN** runtime maturity has `production_ready=false`, **WHEN** capability discovery returns maturity records, **THEN** production readiness is `blocked`.
- **GIVEN** a workflow template requiring a disabled capability, **WHEN** preflight runs, **THEN** the workflow is blocked with the missing capability ID.
- **GIVEN** a high-risk tool that is otherwise available, **WHEN** registry records are returned, **THEN** `requires_approval=true` is preserved.
- **GIVEN** a UI capability request, **WHEN** redaction runs, **THEN** no API keys, bearer tokens, or raw secrets appear in the response.

## Open Questions

- Should capability records be persisted snapshots, computed per request, or both?
- Which provider health checks are safe to run without external spend?
- Should capability dependency definitions live in code, SQLite, template metadata, or a merged source?
