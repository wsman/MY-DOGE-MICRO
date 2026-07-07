# ADR-0043: Slot Contribution Facets

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 034 extends the Slot Platform Foundation from ADR-0042 from a tool-only
contribution contract into a multi-facet contribution contract. The decision is
to add typed resolve-time facet dataclasses for model, workflow, data, document,
gateway, UI, watcher, eval, and governance contributions while keeping
`doge.platform.slots` pure.

The sprint also migrates exactly one runtime consumer proof: the existing
`kimi_agent_sdk` agent backend can be provided by a built-in
`model.kimi_agent_sdk` slot when `DOGE_FEATURE_SLOT_PLATFORM` is enabled.

This does not complete the full OpenClaw-like Slot Platform. Workflow, data,
document, gateway, UI, watcher, eval, and governance consumers remain deferred.
No `/v1` route, OpenAPI schema, SDK surface, Web UI, daemon command source,
database schema, ModelRouter dispatch rule, or external/operator gate changes.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; stdlib dataclasses and typing only for slot facets |
| **Domain** | Slot contract widening and one model-backend slot proof |
| **Knowledge Risk** | LOW - additive contract fields plus feature-flagged dual-path backend construction |
| **References Consulted** | `docs/architecture/adr-0042-slot-platform.md`, `src/doge/platform/slots/contracts.py`, `src/doge/bootstrap/runtime_factories/runtime_kernel.py`, `src/doge/bootstrap/runtime_factories/slots.py`, `src/doge/infrastructure/agent/backends.py`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | slot facet tests, built-in model slot tests, agent-backend parity tests, tool-registry parity tests, boundary ratchets, SDK contract, governance validators, maturity honesty, plan closure gate, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0013 (tool governance), ADR-0019 (capability registry relationship), ADR-0021 (bounded contexts), ADR-0027 (shim sunset discipline) |
| **Extends** | ADR-0042 by widening `SlotContribution` and adding a model-backend proof |
| **Supersedes** | None |
| **Enables** | Future workflow, data, document, gateway, UI, watcher, eval, governance, and additional model slot migrations |
| **Blocks** | None |

## Context

ADR-0042 introduced `SlotManifest`, `ISlot`, `SlotContribution`, `SlotContext`,
and `SlotRegistry`, and proved the mechanism with one tool slot,
`market.core`. That first slice intentionally left `SlotContribution` shaped
around tool registration: `tools`, `executor`, and reserved `capabilities`.

The OpenClaw-like target requires slot contributions to describe multiple kinds
of platform capability. A slot needs to be able to contribute a model backend,
workflow template, document parser, route, UI panel, watcher, eval suite, or
governance policy without importing FastAPI, frontend modules, infrastructure,
bootstrap containers, or product implementations into `doge.platform.slots`.

Sprint 034 therefore adds pure typed facet dataclasses and proves one real
runtime path by constructing `agent_backends` from a model slot behind the
existing `DOGE_FEATURE_SLOT_PLATFORM` flag.

## Constraints

- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.
- Keep `DOGE_FEATURE_SLOT_PLATFORM` default `false`.
- Keep `doge.platform.slots` pure: stdlib plus `doge.core.*`, `doge.shared.*`,
  and `doge.platform.slots.*` only.
- Do not change `/v1` routes, OpenAPI, SDK packages, Web source, daemon command
  source, persistence, ModelRouter, ProfileRegistry, or runtime dispatch rules.
- Do not invoke slot lifecycle `start`/`stop` hooks yet.
- Do not treat declarative permissions or health as runtime-enforced controls.
- Do not claim any external/operator gate is closed.

## Decision

Add `src/doge/platform/slots/facets.py` with frozen dataclasses for:

- `ModelBackendContribution`
- `WorkflowTemplateContribution`
- `DataSourceContribution`
- `DocumentParserContribution`
- `GatewayRouteContribution`
- `UIPanelContribution`
- `WatcherDecision`
- `WatcherContribution`
- `EvalSuiteContribution`
- `GovernancePolicyContribution`

These classes carry strings, mappings, callables, and `Any` so the contract
package does not import framework or infrastructure types.

Widen `SlotContribution` in `src/doge/platform/slots/contracts.py` with tuple
fields for every facet:

- `model_backends`
- `workflows`
- `data_sources`
- `document_parsers`
- `routes`
- `ui_panels`
- `watchers`
- `eval_suites`
- `governance_policies`

Keep the existing tool fields unchanged: `tools`, `executor`, and
`capabilities`. `SlotManifest` remains schema version 1 because the new fields
are resolve-time contribution fields, not manifest file fields.

Make `SlotContext.tool_application_service` optional. Non-tool slots can now
resolve without a tool service. `MarketCoreSlot.resolve()` fail-fasts with
`SlotConfigurationError` if it is accidentally resolved without a tool service.

Add well-known service-id constants such as `SLOT_SERVICE_SECRET_PROVIDER` and
future registry/repository ids. Slots use `SlotContext.locate(service_id)` for
non-tool services instead of receiving a full bootstrap container.

Add optional no-op `ISlot.start(context)` and `ISlot.stop(context)` hooks for
future lifecycle work. Sprint 034 defines the hooks only; no runtime lifecycle
invocation is introduced.

Add `src/doge/bootstrap/runtime_factories/builtin_model_slot.py` with
`ModelKimiAgentSdkSlot`. Its manifest is:

- `id`: `model.kimi_agent_sdk`
- `type`: `model`
- `owner`: `agent-runtime`
- `maturity`: `experimental`
- `feature_flags`: `slot_platform`
- `permissions`: network allowed, `kimi.api_key` secret, medium risk

The slot contributes one model backend with backend id `kimi_agent_sdk`. The
factory builds the existing `KimiAgentSdkBackend` using settings and a secret
provider resolved through `SLOT_SERVICE_SECRET_PROVIDER`.

Update `src/doge/bootstrap/runtime_factories/slots.py` so
`build_builtin_slot_registry()` registers both `MarketCoreSlot` and
`ModelKimiAgentSdkSlot`. Tool registry construction resolves only tool slots;
agent-backend construction resolves only model slots. This avoids resolving
tool slots without a tool service.

Update `build_agent_backends()` so the public function delegates to
`build_slot_aware_agent_backends()` only when `slot_platform` is enabled. The
flag-off body remains the legacy construction path.

## Per-Facet Rollout

| Facet | Sprint 034 Status | Runtime Consumer |
|-------|-------------------|------------------|
| tool | Existing ADR-0042 path retained | `ToolRegistry.include_descriptors` |
| model | One real proof implemented | `build_agent_backends()` returns `{"kimi_agent_sdk": KimiAgentSdkBackend}` |
| workflow | Representable only | Future workflow-template registry migration |
| data | Representable only | Future data-source registry migration |
| document | Representable only | Future parser dispatcher migration |
| gateway | Representable only | Future route assembly migration |
| UI | Representable only | Future frontend panel registry migration |
| watcher | Representable only | Future runtime event middleware migration |
| eval | Representable only | Future eval-suite registry migration |
| governance | Representable only | Future policy/entitlement registry migration |

## Alternatives Considered

### Alternative 1: Encode all facets in `capabilities`

- **Description**: Keep `SlotContribution` unchanged and place facet-specific
  payloads in the existing `capabilities` tuple.
- **Pros**: Smallest code change.
- **Cons**: Loses type clarity, makes tests stringly typed, and blurs tool
  capability records with slot contribution objects.
- **Rejection Reason**: The platform needs explicit contribution shapes before
  more runtime consumers are migrated.

### Alternative 2: Add typed service accessors to `SlotContext`

- **Description**: Add properties such as `secret_provider`,
  `platform_repository`, `event_bus`, and `fastapi_app`.
- **Pros**: Easier for slot authors to discover services.
- **Cons**: Pushes bootstrap and infrastructure concepts into the pure slot
  contract and encourages a broad implicit container surface.
- **Rejection Reason**: `locate(service_id)` keeps the contract narrow while
  still allowing controlled runtime wiring.

### Alternative 3: Move model slot provider into `doge.platform.slots`

- **Description**: Put the built-in model slot next to the contract package.
- **Pros**: Easier to find all slot-related code in one package.
- **Cons**: Would force `doge.platform.slots` to import
  `doge.infrastructure.agent.backends`, violating the purity ratchet.
- **Rejection Reason**: Built-in providers belong beside their owner or in
  bootstrap wiring. Model backend construction has no product owner, so
  `bootstrap/runtime_factories/` is the correct location.

### Alternative 4: Wire every facet runtime consumer now

- **Description**: Add registries and consumers for all slot facets in one sprint.
- **Pros**: Faster path to the long-term platform vision.
- **Cons**: Large blast radius across runtime, gateway, Web, eval, governance,
  and data paths. Would be hard to prove parity.
- **Rejection Reason**: Sprint 034 is a contract and model-proof slice. Each
  remaining facet needs its own ADR, parity story, and security review.

## Consequences

### Positive

- `SlotContribution` can now represent every planned non-tool facet.
- Model backend construction has a real slot-backed proof without changing
  model dispatch semantics.
- The slot purity boundary remains enforceable by the existing AST ratchet.
- Later facet migrations can build on concrete dataclasses instead of inventing
  new ad hoc payloads.

### Negative

- Most new facet types are representability-only until future sprints add
  runtime consumers.
- `build_builtin_slot_registry()` now contains both tool and model slots, so
  consumers must filter by manifest type before resolving.
- A second bootstrap provider file exists for built-in model slot wiring.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| A non-tool slot is resolved with a tool-only context | MEDIUM | MEDIUM | Consumers filter by `SlotType` before `resolve`; tests cover model+tool coexistence. |
| Duplicate model backend ids silently overwrite each other | LOW | HIGH | `build_slot_aware_agent_backends()` raises `SlotConfigurationError` on duplicates. |
| Facet types imply runtime support that does not exist yet | MEDIUM | MEDIUM | ADR/CDD/evidence explicitly mark 8 facets as representability-only. |
| Boundary leak into `platform/slots` | LOW | HIGH | `tests/unit/architecture/test_slot_boundary.py` scans the new `facets.py` file. |
| Maturity overclaim | LOW | HIGH | Governance docs retain experimental/local-only wording and external gates remain open. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/sprint-034-slot-contribution-facets.md` | Make non-tool slot facets representable and migrate one model backend through the slot registry. | Adds typed facets, widens `SlotContribution`, adds `model.kimi_agent_sdk`, and routes `build_agent_backends()` through the slot path behind the flag. |

## Performance Implications

- **CPU**: Flag-off behavior is unchanged. Flag-on model backend construction
  builds a small slot registry and resolves only model slots before constructing
  the same backend object.
- **Memory**: Adds frozen facet dataclasses and one model slot object during
  registry assembly.
- **Network**: No new network call. `KimiAgentSdkBackend` still performs network
  work only when later used for chat.
- **Package Size**: No new dependency.

## Migration Plan

1. Add `facets.py` and export the facet dataclasses.
2. Widen `SlotContribution`, make `SlotContext.tool_application_service`
   optional, add service-id constants, and add no-op lifecycle hooks.
3. Make `MarketCoreSlot` fail fast when resolved without a tool service.
4. Add contract tests for all 9 non-tool facets.
5. Add `ModelKimiAgentSdkSlot` and register it in the built-in registry.
6. Filter slot resolution by `SlotType` in tool and model consumers.
7. Add `build_slot_aware_agent_backends()` and the public
   `build_agent_backends()` flag branch.
8. Add parity, duplicate-backend, and boundary tests.
9. Add governance records and run validators.

## Validation Criteria

- All 9 non-tool facets round-trip through `SlotRegistry.resolve_contributions`
  in focused tests.
- `model.kimi_agent_sdk` resolves without API-key or network access and builds
  `KimiAgentSdkBackend` only through its factory.
- `build_agent_backends()` returns equivalent backend summaries flag-off and
  flag-on.
- Duplicate model backend ids raise `SlotConfigurationError`.
- Tool registry parity remains green with both `market.core` and
  `model.kimi_agent_sdk` registered.
- `MarketCoreSlot` still works with a tool service and fail-fasts without one.
- Import-boundary and slot-boundary validators remain green.
- SDK contract remains 15/15.
- Maturity posture remains Local Alpha / SDK experimental with external gates
  open.

## Related Decisions

- ADR-0013: Tool Governance
- ADR-0019: Capability Registry
- ADR-0021: Bounded Context Consolidation
- ADR-0027: Shim Sunset Policy
- ADR-0042: Slot Platform Foundation
