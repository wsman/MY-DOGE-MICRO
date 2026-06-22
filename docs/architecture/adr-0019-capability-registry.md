# ADR-0019: Capability Registry

## Status
Proposed

## Date
2026-06-22

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI 0.123.8, Pydantic 2.12.4, SQLite local persistence |
| **Domain** | API Design / Runtime / Security |
| **Knowledge Risk** | LOW for pinned stack; MEDIUM for live provider behavior because checks must avoid spend and secret exposure |
| **References Consulted** | `docs/reference/python/VERSION.md`, `design/cdd/capability-registry.md`, `docs/architecture/adr-0012-enterprise-model-gateway.md`, `docs/architecture/adr-0013-tool-governance.md`, `docs/progress/runtime-maturity.yaml` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Redaction tests, dependency graph tests, provider adapter normalization tests |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0012, ADR-0013 |
| **Enables** | ADR-0018, ADR-0020 |
| **Blocks** | Capability-driven UI/SDK exposure until redaction and status contracts are accepted |
| **Ordering Note** | ADR-0015 controls enterprise identity; this registry must not imply production readiness. |

## Context

### Problem Statement

Provider, tool, workflow, evidence, and maturity availability are currently distributed across config, adapters, docs, and UI assumptions. A platform shell and template system need one redacted discovery surface that can answer "what is usable here" without exposing secrets or making production claims.

### Constraints

- Registry responses must not include API keys, bearer tokens, or raw secrets.
- Live health checks must be optional and bounded.
- Tool governance remains authoritative for entitlement and approval.
- `docs/progress/runtime-maturity.yaml` remains authoritative for production readiness.

### Requirements

- Normalize provider, model, tool, workflow, API, UI, evidence, and maturity capabilities.
- Represent dependency relationships and blocker reasons.
- Provide redacted API discovery.
- Support deterministic tests without live provider spend.

## Decision

Introduce a capability registry facade that assembles normalized capability records from provider adapters, tool governance metadata, feature flags, workflow definitions, and runtime maturity posture. The registry may persist snapshots for diagnostics, but the API response must be redacted and safe for UI/SDK consumption.

Implementation note, 2026-06-22: the first config-only slice is implemented
behind `DOGE_FEATURE_CAPABILITY_REGISTRY`. It includes a
`CapabilityProvider.collect()` port, feature/provider/API/maturity providers,
and a `ToolRegistryCapabilityProvider` that reads tool schema/category/approval
metadata through `ToolRegistry.capability_records_for_context()` without
executing tools. It also adds a provider-backed `ToolApplicationService`
execution facade for market, portfolio, research, fundamental, quant,
compliance, and publishing tools behind `DOGE_FEATURE_CAPABILITY_REGISTRY`,
while retaining the default direct path for rollback. Dependency graph
validation, persisted snapshots, optional live health checks, and workflow
preflight remain future work under this ADR.

### Architecture Diagram

```text
provider adapters ----+
tool governance ------+--> capability registry facade --> redacted snapshot --> /v1/capabilities
workflow templates ---+
feature flags --------+
runtime maturity -----+
```

### Key Interfaces

- `GET /v1/capabilities`
- Internal `CapabilityProvider.collect() -> list[CapabilityRecord]`
- Internal `CapabilityRegistry.resolve_dependencies(records) -> CapabilitySnapshot`

Capability statuses are `available`, `unconfigured`, `degraded`, `disabled`, and `blocked`.

## Alternatives Considered

### Alternative 1: UI-Specific Feature Flags Only
- **Description**: Let the frontend infer capability from config flags.
- **Pros**: Minimal backend work.
- **Cons**: Cannot represent provider/tool/maturity dependencies or secret redaction centrally.
- **Rejection Reason**: The platform needs shared SDK/UI discovery.

### Alternative 2: Live Provider Health Dashboard
- **Description**: Probe every provider and show health.
- **Pros**: Rich operational signal.
- **Cons**: May incur spend, leak timing data, and fail offline-first use.
- **Rejection Reason**: Health checks must be optional and bounded.

### Alternative 3: Redacted Capability Registry Facade
- **Description**: Normalize config, policy, and optional health into safe records.
- **Pros**: Central, testable, UI/SDK friendly, and secret-safe.
- **Cons**: Requires adapter discipline and dependency graph validation.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- UI and SDK clients receive one discovery contract.
- Workflow preflight can explain missing prerequisites.
- Runtime maturity blocks are visible without production claims.
- Provider details are normalized behind adapters.

### Negative

- Registry must stay in sync with provider and tool metadata.
- Dependency cycles need validation.
- Optional live checks add timeout and failure handling complexity.

### Risks

- **Risk**: Secrets leak through provider metadata.
  **Mitigation**: Redaction tests are mandatory before exposing API responses.
- **Risk**: Capability status is mistaken for authorization.
  **Mitigation**: Keep ADR-0013 entitlement/approval checks authoritative at execution.

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `capability-registry.md` | Provide redacted capability status for providers, tools, workflows, evidence, and maturity. | Defines registry facade, statuses, snapshots, and API discovery. |
| `workflow-templates.md` | Block execution when required capabilities are unavailable. | Provides dependency resolution and preflight records. |
| `platform-shell-ui.md` | Show route and feature availability from backend status. | Provides `/v1/capabilities` as a shell discovery source. |

## Performance Implications

- **CPU**: Low for config-only snapshots; bounded by adapter count.
- **Memory**: Small capability record set.
- **Load Time**: Optional live checks must use short timeout and can be disabled.
- **Network**: No network required for config-only mode; live health checks are opt-in.

## Migration Plan

1. Add capability record schemas and registry facade. (Partial: config-only
   facade implemented.)
2. Add provider/tool/template/maturity collectors. (Partial: feature, provider,
   API, maturity, and tool metadata providers implemented.)
3. Add provider-backed tool execution facade. (Implemented behind feature flag
   with direct-path rollback.)
4. Add redaction and dependency validation. (Partial: redaction/parity tests
   implemented; dependency graph validation open.)
5. Add `/v1/capabilities` endpoint. (Implemented behind feature flag.)
6. Integrate workflow preflight and shell route guards.

## Validation Criteria

- API response contains no configured secrets.
- Runtime production readiness is `blocked` when maturity says `production_ready=false`.
- Missing hard dependencies block workflow preflight.
- Optional health checks time out without blocking unrelated local capabilities.
- Dependency cycles are rejected in tests.

## Related Decisions

- ADR-0012: Enterprise Model Gateway
- ADR-0013: Financial Tool Governance
- ADR-0015: Enterprise Identity And Access Boundary
- `design/cdd/capability-registry.md`
