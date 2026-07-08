# ADR-0042: Slot Platform Foundation

## Status

Accepted

## Date

2026-07-06

## Decision Makers

wsman (product owner) · implementation agent

## Summary

Sprint 033 implements the Slot Platform Foundation slice from
`C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The decision is to introduce a slot contract (`SlotManifest` v1, `ISlot`,
`SlotContribution`, `SlotContext`, `SlotRegistry`) as a broader abstraction for
declarative platform contributions, and to wire exactly one built-in tool slot
(`market.core`) into the existing tool registry through an additive, feature-flagged
dual path. With the flag off, tool-registry and runtime behavior are byte-identical
to the legacy factory path.

No `/v1` route, OpenAPI schema, SDK surface, Web UI, daemon command source,
ModelRouter, persistence schema, or external/operator gate is changed. Manifest
permissions and health are declarative only in Sprint 033.

## Status Update - 2026-07-08

ADR-0058 supersedes the Sprint 033 default-off posture for
`DOGE_FEATURE_SLOT_PLATFORM`: the built-in Slot Platform consumer path is now on
by default for local runs. The legacy direct wiring remains available with
`DOGE_FEATURE_SLOT_PLATFORM=0`, and SlotLoader, install, enforcement, UI,
third-party provider execution, signing, sandboxing, YAML manifests, marketplace
behavior, remote CI promotion, and production readiness remain out of scope.

ADR-0059 extends the same no-code-moved tool-slot overlay from `market.core` to
five additional built-in tool domains: `portfolio.core`, `evidence.core`,
`quant.lab`, `governance.actions`, and `compliance.screening`. The `/v1/tools`
descriptor set remains parity-stable, and `run_python_analysis` remains outside
tool slots until a separate high-risk execution decision.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; stdlib JSON manifest loader (no new dependency) |
| **Domain** | Platform slot contract and additive tool-slot wiring |
| **Knowledge Risk** | LOW - additive contract plus dual-path registration behind a default-off flag |
| **References Consulted** | `src/doge/application/tools/registry.py`, `src/doge/application/tools/factory.py`, `src/doge/bootstrap/runtime_factories/tools.py`, `src/doge/application/agent/tool_service.py`, `src/doge/config/settings.py`, `src/doge/interfaces/cli/main.py`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | slot contract tests, boundary ratchet, tool-registry slot parity test, CLI tests, settings tests, SDK contract parity, docs/maturity validators, import boundaries, plan closure gate, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0013 (tool governance - slots do not override entitlement), ADR-0019 (capability registry - see relationship subsection), ADR-0021 (bounded contexts - referenced, not re-declared), ADR-0027 (shim sunset - slot layer is canonical, not a shim) |
| **Enables** | Future model, workflow, data, document, ui, gateway, governance, eval, and watcher slot migrations, each in its own sprint with its own parity story. |
| **Blocks** | None |
| **Ordering Note** | ADR-0019 CapabilityRegistry unification into slots is explicitly deferred (see below). |

## Context

### Problem Statement

The runtime already exposes heterogeneous platform contributions - tools, model
backends, workflow templates, UI panels, gateway routes, governance policies, eval
suites - but each is wired through its own bespoke registration path. There is no
single declarative contract that lets a contribution state what it provides, what
it requires, its permissions, health, feature flags, and compatibility.

Sprint 033 introduces that contract (the slot manifest) and proves it end-to-end by
migrating exactly one tool slot (`market.core`) through the existing
`ToolRegistry.include_descriptors` seam, additively and behind a feature flag.

### Constraints

- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.
- Add no `/v1` route, OpenAPI schema, SDK surface, Web UI, daemon command source,
  persistence schema, or ModelRouter change.
- Flag-off tool-registry and runtime behavior must remain byte-identical to the
  legacy factory path; diagnostics may newly list the feature flag.
- `doge.platform.slots` must be a pure contract package: it may import only
  `doge.core.*`, `doge.shared.*`, and the standard library.
- No third-party YAML dependency; manifest loading supports Python dicts and JSON
  files only this sprint.
- Manifest permissions and health are declarative only; no runtime enforcement of
  filesystem/network/shell/secret/database permissions is delivered this sprint.

### Relationship to ADR-0019 (Capability Registry)

ADR-0019 introduced a `CapabilityRegistry` for tool discovery, schema redaction, and
provider-backed execution. A *slot* is a strictly broader abstraction: a slot's
`provides.capabilities` is intended to be ONE facet among several (tools, model
backends, workflows, data sources, UI panels, watchers, eval suites).

For Sprint 033:

- The capability record produced by `ToolRegistry.capability_records_for_context()`
  remains the authoritative source for tool entitlement and redaction.
- `SlotContribution.capabilities` is empty; slots do not redact or override
  capability entitlement.
- Unification/migration of `CapabilityRegistry` records into slot manifests is
  explicitly **deferred** to a follow-up sprint (candidate sprint 035+), gated on
  ADR-0019 going default-on, a no-op migration proof, and a dedicated ADR.

Until then, slots and capabilities coexist; a slot's capability facet is reserved
but unused.

## Decision

Add `src/doge/platform/slots/` as a pure contract package:

```text
errors.py     SlotError hierarchy (normal exceptions; to_safe_error() via SafeError.create)
manifest.py   SlotType, SlotManifest v1 + nested dataclasses, load_slot_manifest (dict/JSON)
contracts.py  ISlot, SlotContribution, SlotContext (controlled facade), ToolServiceProtocol, SlotStatus
registry.py   SlotRegistry, SlotStatusRecord
```

`SlotManifest` v1 fields: `schema_version`, `id`, `name`, `version`, `type`
(enum: tool/model/workflow/data/document/ui/gateway/governance/eval/watcher - only
`tool` exercised this sprint), `owner` (bounded-context slug, reference only),
`maturity`, `description`, `entrypoint`, `provides{tools,capabilities,metadata}`,
`requires[]`, `permissions{filesystem,network,shell,database,secrets,risk_level}`,
`health{status,notes}`, `feature_flags[]` (Settings field keys, not env-var names),
`compatibility{runtime_min,replaces,breaking}`. The loader rejects unknown
top-level keys so schema evolution goes through `schema_version`.

`SlotContext` is a controlled facade exposing only `settings` (untyped `Any`),
`feature_flags`, `tool_application_service`, and optional audit/permission/locator
hooks; it never exposes `AppContainer`, `RuntimeContainer`, or the bootstrap graph.

Add one built-in tool slot `src/doge/products/market/slot.py` (`MarketCoreSlot`)
declaring `market.core` and resolving the six market-facing tool descriptors
(`query_stock`, `stock_overview`, `rsrs_ranking`, `market_breadth`,
`volume_anomalies`, `list_views`) from `ToolApplicationService.tool_descriptors()`,
returning the same service as executor. `list_views` remains implemented by
`doge.products.quant.tools` and is grouped under `market.core` for discovery only
(no code moved; recorded in `provides.metadata`).

Wire an additive dual path in `src/doge/bootstrap/runtime_factories/`:

- `slots.py` adds `build_builtin_slot_registry()` and
  `build_slot_aware_tool_registry(gateway_container_fn, *, entitlement_checker, context)`.
- `tools.py` adds a flag branch at the top of `build_default_tool_registry`: when
  `DOGE_FEATURE_SLOT_PLATFORM` is on it delegates to the slot-aware builder;
  otherwise the legacy factory body runs unchanged.

The slot-aware builder registers slot-owned descriptors first via the same
`include_descriptors` seam (against the same service), then registers the remaining
descriptors so nothing is double-registered (`register` appends to `self.schemas`
without dedup).

Add `doge slots list/show` CLI commands (`src/doge/interfaces/cli/commands/slots.py`)
that read manifests only (no live `ToolApplicationService`), keeping the CLI
DB/network-free; flag-off prints a graceful disabled message.

Add feature flag `DOGE_FEATURE_SLOT_PLATFORM` (default `false`) to `FEATURE_LIFECYCLES`
and `FeatureConfig`.

## Alternatives Considered

### Alternative 1: Extend ADR-0019 capabilities instead of a new abstraction

- **Description**: Grow the existing CapabilityRegistry into the slot concept.
- **Pros**: Avoids a second overlapping abstraction.
- **Cons**: Capabilities are tool-execution-specific; the slot concept spans models,
  workflows, data, UI, watchers, and eval. Coupling this sprint to a default-off
  subsystem and a heavier rename.
- **Rejection Reason**: A broader contract is needed; unification is deferred to a
  dedicated ADR rather than forced now.

### Alternative 2: Slots import AppContainer directly

- **Description**: Let slots reach any service via the full container.
- **Pros**: Less indirection.
- **Cons**: Breaks the import boundary and the clean-architecture separation; slots
  could bypass entitlement and governance.
- **Rejection Reason**: `SlotContext` must be a controlled facade.

### Alternative 3: Slots register tools into a separate ToolRegistry

- **Description**: Maintain a slot-only registry distinct from the runtime registry.
- **Pros**: Strong isolation.
- **Cons**: `/v1/tools` and tool execution would diverge from the legacy path,
  breaking parity and doubling maintenance.
- **Rejection Reason**: The slot path must reuse the canonical `ToolRegistry`
  `include_descriptors` seam.

### Alternative 4: Defer until the model slot is ready

- **Description**: Ship the contract only after a second slot type is migrated.
- **Pros**: Larger proof surface in one sprint.
- **Cons**: A contract with no consumer is hard to validate; the thin slice proves
  the contract cheaply and keeps the sprint additive.
- **Rejection Reason**: One tool slot is sufficient to validate the dual-path
  registration and the manifest contract.

## Consequences

### Positive

- One declarative manifest format for future heterogeneous contributions.
- Documented market-tool ownership and a discoverable `doge slots list/show`.
- A boundary ratchet (`tests/unit/architecture/test_slot_boundary.py`) keeps
  `platform/slots` pure.

### Negative

- A second abstraction (slots) coexists with capabilities until a deferred
  unification sprint.
- A small new JSON-loader surface and a frozen parity baseline file to maintain.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep into model/workflow slots | MEDIUM | MEDIUM | Defer all non-tool slot types to later sprints; this sprint ships only `market.core`. |
| Double-registration changes `/v1/tools` | MEDIUM | HIGH | Subtract slot-owned names before registering the remainder; parity test asserts equal count and byte-equal flag-off payload. |
| Boundary leak via `platform/slots` imports | LOW | HIGH | AST ratchet forbids infrastructure/adapters/products/application/bootstrap/interfaces/config imports. |
| Maturity overclaim | LOW | HIGH | Every new doc says `experimental`; preserve `production_ready: false` and `stable_declaration: forbidden`. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/sprint-033-slot-platform.md` | Add a slot contract and migrate one tool slot additively behind a flag. | Adds `platform/slots`, `MarketCoreSlot`, dual-path wiring, CLI, and tests. |

## Performance Implications

- **CPU**: Flag-off adds one `get_settings()` read before the legacy factory path.
  Flag-on builds one `SlotRegistry`/`SlotContext` per registry assembly.
- **Memory**: Flag-on allocates the registry/context and the same descriptor set.
- **Network**: None.
- **Package Size**: No new dependency.

## Migration Plan

1. Add the `slot_platform` feature flag and update settings tests.
2. Add the `platform/slots` contract package and unit tests.
3. Add the boundary ratchet and run import-boundary validation.
4. Add `MarketCoreSlot` and its unit test.
5. Add bootstrap dual-path wiring and the frozen parity baseline.
6. Add the `doge slots` CLI and CLI tests.
7. Add ADR/CDD/sprint/evidence governance records.
8. Run focused tests and governance validators.

## Validation Criteria

- `DOGE_FEATURE_SLOT_PLATFORM` off: `/v1/tools` schemas, capability records, and
  tool execution are byte-identical to the legacy path (frozen baseline + parity test).
- Flag on: the same payload is equivalent (equal schemas, records, count).
- `doge slots list/show` prints the disabled message flag-off and the `market.core`
  manifest flag-on.
- `platform/slots` imports only `core`/`shared`/stdlib (boundary ratchet green).
- Settings lifecycle tests pass with `slot_platform` included.
- SDK contract remains 15/15.
- Docs and maturity validators preserve Local Alpha honesty.
- No external/operator gate is closed; posture remains 4 open / 2 passed.

## Related Decisions

- ADR-0013: Tool Governance
- ADR-0019: Capability Registry
- ADR-0021: Bounded Context Consolidation
- ADR-0027: Shim Sunset Policy
- ADR-0033: Local Daemon Operator CLI
