# ADR-0059: Tool Slot Domain Migration

## Status

Accepted

## Date

2026-07-08

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P1 extends the `market.core` built-in tool slot pattern from ADR-0042 to five
additional built-in tool domains:

- `portfolio.core`
- `evidence.core`
- `quant.lab`
- `governance.actions`
- `compliance.screening`

The decision moves tool discovery and slot ownership metadata only. It does not
move provider code, change `ToolApplicationService` method bodies, add a feature
flag, change the `/v1/tools` schema set, enable third-party provider execution,
activate bundles persistently, or change production posture.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing dataclass SlotManifest/SlotContribution contracts; FastAPI 0.123.8; pytest 9.0.1 |
| **Domain** | Tool discovery, governance overlay, and Slot Platform composition |
| **Knowledge Risk** | LOW - local built-in slot overlays over existing descriptors |
| **References Consulted** | `docs/reference/python/VERSION.md`, `standards/technical-preferences.md`, `docs/registry/architecture.yaml`, `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0058-slot-platform-controlled-default-on.md`, `design/cdd/sprint-033-slot-platform.md`, `design/cdd/bc-02-research.md`, `design/cdd/bc-03-portfolio-risk.md`, `design/cdd/bc-04-quant-data-lab.md`, `design/cdd/bc-08-governance-evaluation.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | per-slot unit tests, tool-registry parity, slot-owned tool ownership ratchet, `/v1/slots` coverage, CLI/doged coverage, bundle rows, import boundaries, docs/governance validators, source-plan maturity honesty, plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0013 (Tool Governance), ADR-0021 (Bounded Context Consolidation), ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0045 (Slot Discovery Surfaces), ADR-0052 (Slot Kernel, Bundles, Policy, and Lifecycle), ADR-0058 (Slot Platform Controlled Default On) |
| **Extends** | ADR-0042 by applying the built-in tool-slot overlay pattern to portfolio, evidence, quant, governance-action, and compliance-screening domains |
| **Enables** | Later domain-level governance/enforcement work over tool slots after dedicated evidence |
| **Blocks** | Any claim that `run_python_analysis`, third-party provider execution, marketplace install, sandboxing, signing, or persistent bundle activation is delivered by P1 |
| **Ordering Note** | P1 assumes ADR-0058's controlled default-on slot platform posture; rollback remains `DOGE_FEATURE_SLOT_PLATFORM=0`. |

## Context

### Problem Statement

After ADR-0058, built-in Slot Platform contribution resolution is the local
default, but the tool facet still has only one domain-level tool slot:
`market.core`. The remaining tools are registered through the
`ToolApplicationService` facade as undifferentiated fallback descriptors, which
weakens slot discovery, domain-level governance explanation, and later
permission/enforcement seams.

P1 should improve slot ownership without rewriting provider implementations. The
existing service/provider seam is already parity-tested; moving provider code
would expand risk without improving the platform contract.

### Constraints

- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.
- Preserve the frozen `/v1/tools` count and payload parity: 23 descriptors.
- Add no new `FeatureConfig`, `FEATURE_LIFECYCLES`, env var, OpenAPI surface,
  SDK public surface, persistence schema, or provider execution path.
- Do not change `ToolApplicationService` method bodies.
- Do not move provider implementations.
- Keep `run_python_analysis` outside tool slots because it is high-risk and
  separately gated by the Python analysis executor.
- Keep `list_views` owned by `market.core` to avoid re-opening the ADR-0042
  grouping decision.
- Keep third-party slot install previews manifest-only.

### Requirements

- `ToolApplicationService.tool_descriptors()` remains the runtime descriptor
  authority.
- Each new tool slot declares an explicit manifest allowlist and resolves only
  those descriptors.
- Each slot reuses the same `ToolApplicationService` instance as executor.
- Missing allowlisted descriptors fail fast with `SlotConfigurationError`.
- Slot-owned tools total 22: `market.core` 6 plus P1 16.
- The only facade-remaining descriptor is `run_python_analysis`.
- `bundle.local_analyst` includes all five P1 slots.
- `bundle.research_workspace` includes `portfolio.core`, `evidence.core`, and
  `quant.lab`.

## Decision

Add five built-in `SlotType.TOOL` providers:

| Slot | Tools | File |
|------|-------|------|
| `portfolio.core` | `get_portfolio_exposure`, `portfolio_risk`, `scenario_analysis`, `propose_portfolio_rebalance` | `src/doge/products/portfolio/slot.py` |
| `evidence.core` | `validate_financial_claims`, `generate_industry_report`, `lookup_evidence`, `get_financial_statements`, `get_company_announcements`, `calculate_financial_ratios`, `compare_consensus_estimates`, `get_industry_classification` | `src/doge/products/research/slot.py` |
| `quant.lab` | `run_sql_query` | `src/doge/products/quant/slot.py` |
| `governance.actions` | `request_approval`, `publish_investment_memo` | `src/doge/platform/governance/actions_slot.py` |
| `compliance.screening` | `screen_compliance_risk` | `src/doge/platform/governance/compliance_slot.py` |

Each slot mirrors the `MarketCoreSlot` contract:

1. `manifest()` returns a module-level `SlotManifest`.
2. `resolve(context)` requires `context.tool_application_service`.
3. `resolve(context)` builds a descriptor map from
   `service.tool_descriptors()`.
4. Any missing declared tool raises `SlotConfigurationError`.
5. The returned `SlotContribution` uses the allowlisted descriptors in manifest
   order and `executor=service`.

Register the five slots in `build_builtin_slot_registry()` after
`MarketCoreSlot`. Add all five to `bundle.local_analyst`, and add
`portfolio.core`, `evidence.core`, and `quant.lab` to
`bundle.research_workspace`. Do not add them to `bundle.daemon_operator` or
`bundle.enterprise_safe`.

### Architecture Diagram

```text
ToolApplicationService.tool_descriptors()  (23 descriptors)
        |
        v
Built-in tool slots resolve explicit allowlists
        |
        +-- market.core                 6 tools
        +-- portfolio.core              4 tools
        +-- evidence.core               8 tools
        +-- quant.lab                   1 tool
        +-- governance.actions          2 tools
        +-- compliance.screening        1 tool
        |
        v
Slot-aware ToolRegistry registers slot-owned descriptors first
        |
        +-- fallback remaining descriptor: run_python_analysis
```

### Key Interfaces

- Slot ids:
  - `portfolio.core`
  - `evidence.core`
  - `quant.lab`
  - `governance.actions`
  - `compliance.screening`
- Rollback:
  - Whole path: `DOGE_FEATURE_SLOT_PLATFORM=0`
  - Per-slot rollback: unregister the slot and remove its bundle ids; the
    descriptors fall back through the existing facade registration.
- Invariant:
  - `/v1/tools` remains 23 descriptors and parity-equal between slot-on and
    slot-off paths.

## Alternatives Considered

### Alternative 1: Keep Non-Market Tools as Facade Fallback Only

- **Description**: Do not add domain-level tool slots after P0.
- **Pros**: Lowest code churn.
- **Cons**: Slot discovery still underrepresents tool ownership; later
  governance/enforcement work has no domain-level slot ids for most tools.
- **Rejection Reason**: P0 made the built-in slot path the local default, so
  leaving 17 of 23 descriptors unowned by slots would preserve the wrong
  platform shape.

### Alternative 2: Move Provider Implementations into Slot Modules

- **Description**: Put tool implementation code inside slot providers.
- **Pros**: Stronger physical colocation of slot and behavior.
- **Cons**: Rewrites already-tested provider seams, increases regression risk,
  and contradicts ADR-0042's "no code moved" migration discipline.
- **Rejection Reason**: P1 is a discovery/governance overlay, not a provider
  refactor.

### Alternative 3: Create a High-Risk Python Analysis Slot Now

- **Description**: Add `run_python_analysis` to `quant.lab` or a new high-risk
  tool slot.
- **Pros**: Would make every current tool descriptor slot-owned.
- **Cons**: Python execution is high-risk, separately feature-gated, and future
  sandbox/executor decisions are still open.
- **Rejection Reason**: P1 deliberately leaves `run_python_analysis` on the
  facade path until hardened execution policy is ready.

## Consequences

### Positive

- Tool slot discovery now reflects the main product/governance domains.
- Domain-level bundles better describe local analyst and research workspace
  composition.
- Tool registry parity remains intact because all slots reuse the same service
  descriptors and executor.
- Future enforcement/governance work can target domain-level slot ids.

### Negative

- More built-in slot classes and tests must be maintained when descriptor names
  change.
- Cross-provider tool groupings must be documented in manifest metadata to avoid
  confusing implementation location with product/domain ownership.
- `run_python_analysis` remains a deliberate exception until a future high-risk
  execution ADR.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Manifest allowlist drifts from runtime descriptors | LOW | HIGH | Per-slot drift tests and fail-fast `SlotConfigurationError`. |
| Tool registry parity regresses | LOW | HIGH | Contract tests compare slot-on and slot-off schemas/records and assert count 23. |
| Bundle rows disappear due unknown slot ids | LOW | MEDIUM | Bundle tests and `SlotKernel` validation catch unknown bundle references. |
| Cross-provider ownership is misunderstood | MEDIUM | MEDIUM | Manifest metadata documents implementation grouping and no-code-moved semantics. |
| Slot risk metadata is mistaken for tool approval authority | MEDIUM | HIGH | Tool-level `ToolDescriptor` category/metadata and entitlement policy remain the execution authority for high-risk actions; P1 slot manifests are discovery/grouping metadata. |
| P1 is mistaken for high-risk execution hardening | LOW | HIGH | ADR/evidence state that Python execution, sandboxing, signing, and provider execution remain out of scope. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-033-slot-platform.md` | Slot-owned descriptors resolve through the canonical tool registry without changing legacy parity. | Reuses the ADR-0042 `MarketCoreSlot` pattern for five more tool domains. |
| `design/cdd/bc-02-research.md` | Research capabilities must declare evidence and eval requirements explicitly. | Groups evidence and fundamental research descriptors under `evidence.core`. |
| `design/cdd/bc-03-portfolio-risk.md` | Portfolio and risk are first-class product capabilities with governance around investment actions. | Groups portfolio/risk descriptors and the rebalance proposal under `portfolio.core`. |
| `design/cdd/bc-04-quant-data-lab.md` | SQL/Python analysis profiles must remain governed and explicit. | Slots only read-only SQL as `quant.lab` and leaves Python execution deferred. |
| `design/cdd/bc-08-governance-evaluation.md` | Tool entitlement, approval, audit, and maturity boundaries remain governance-owned. | Splits governed actions and compliance screening into governance-owned tool slots while preserving policy slot separation. |

## Performance Implications

- **CPU**: Built-in registry construction creates five additional lightweight
  slot objects and resolves five additional allowlists from the same descriptor
  tuple.
- **Memory**: Small manifest/slot objects are retained for discovery rows.
- **Load Time**: Slot list and bundle rows include five additional built-in
  entries.
- **Network**: None.

## Migration Plan

1. Add five built-in slot modules.
2. Register the slots in `build_builtin_slot_registry()`.
3. Add slot ids to `bundle.local_analyst` and `bundle.research_workspace`.
4. Add per-slot unit tests.
5. Extend `/v1/slots`, CLI, doged, and bundle row coverage.
6. Add a tool ownership ratchet asserting 22 slot-owned descriptors and
   `run_python_analysis` as the only facade-remaining descriptor.
7. Update governance docs, evidence, and session state after validation.

## Validation Criteria

- Five per-slot test files pass.
- `tests/contract/test_tool_registry_slot_parity.py` remains green and asserts
  `/v1/tools` parity at 23 descriptors.
- `/v1/slots`, `doge slots list`, and `doged slots` show all five new tool slots
  as resolved when Slot Platform is enabled.
- `bundle.local_analyst` includes all five P1 slots; `bundle.research_workspace`
  includes `portfolio.core`, `evidence.core`, and `quant.lab`.
- `DOGE_FEATURE_SLOT_PLATFORM=0` disables the new slot rows and preserves the
  legacy facade path.
- Full local Python/Web/SDK/governance validation remains green.

## Related Decisions

- ADR-0013: Tool Governance
- ADR-0021: Bounded Context Consolidation
- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0045: Slot Discovery Surfaces
- ADR-0052: Slot Kernel, Bundles, Policy, and Lifecycle
- ADR-0058: Slot Platform Controlled Default On
