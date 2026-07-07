# Sprint 041 CDD: Gateway Slot Consumer

Status: Ready for Acceptance
Date: 2026-07-07

## 1. Overview

Sprint 041 makes the Slot Platform consume the `gateway` facet for API route
registration.

The sprint adds a built-in `gateway.slots` route slot and route-consumer wiring
so the existing `/v1/slots` discovery router can be mounted through
`GatewayRouteContribution` when `DOGE_FEATURE_SLOT_PLATFORM` is enabled.

The sprint does not migrate every `/v1` router, add bundle activation, or add
route policy/health enforcement.

## 2. User Promise / JTBD

A platform engineer can add gateway route slots without modifying the central
route-registration list for every new router.

An operator can keep the current `/v1/slots` discovery behavior while the
platform starts proving route contributions in a controlled, read-only slice.

## 3. Detailed Behavior

- `SlotDiscoveryGatewaySlot` lives in `doge.interfaces.gateway.slot`.
- `gateway.slots` contributes the existing `doge.interfaces.gateway.routers.slots`
  router.
- The router import is delayed until the contribution factory is invoked.
- `build_slot_aware_gateway_routes()` lives in
  `doge.bootstrap.runtime_factories.slots`.
- The gateway route consumer accepts `GatewayRouteContribution` values.
- Each route contribution must have a unique `router_id`.
- Router factories are resolved against `SlotContext`.
- Router factories must return a FastAPI-compatible router.
- Enabled gateway route contributions are mounted through
  `target_app.include_router(route.router, prefix=route.prefix, tags=route.tags)`.
- `_register_v1_routes()` uses gateway slots when `DOGE_FEATURE_SLOT_PLATFORM`
  is enabled.
- If `gateway.slots` is not mounted by the slot consumer, `_register_v1_routes()`
  falls back to the existing hardcoded slots-router include.
- CLI/API/doged slot discovery shows `gateway.slots` as resolved when slot
  platform is enabled.

## 4. Contracts / Data Model

Gateway route contribution:

```python
GatewayRouteContribution(
    router_id="gateway.slots",
    router_factory=lambda context: slots_router.router,
    prefix="/v1",
    tags=("v1-slots",),
    requires_auth=True,
)
```

Feature flag:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
```

No new feature flag is added for this sprint.

## 5. Edge Cases

- Slot platform off: `/v1/slots` remains mounted directly and endpoint-level
  feature gating remains unchanged.
- Slot platform on: `/v1/slots` is mounted through `gateway.slots`.
- No gateway route contribution is enabled: direct slots-router fallback is
  used.
- Duplicate router ID: gateway route assembly fails fast.
- Router factory returns `None`: gateway route assembly fails fast.
- Router import must not happen at `runtime_factories.slots` import time.

## 6. Dependencies

- ADR-0007 API Surface and CORS.
- ADR-0042 Slot Platform Foundation.
- ADR-0043 Slot Contribution Facets.
- ADR-0045 Slot Discovery Surfaces.
- ADR-0049 Data Slot Consumer.
- Existing `/v1/slots` router and route-registration seam.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; gates slot-aware gateway route
  registration.

No `DOGE_FEATURE_SLOT_GATEWAY` flag is introduced.

## 8. Acceptance Criteria

- Built-in registry includes `gateway.slots`.
- Gateway slot manifest/status is visible through `doge slots`, `doged slots`,
  and `/v1/slots`.
- With slot platform off, `/v1/slots` remains mounted through the direct route
  registration path.
- With slot platform on, `/v1/slots` is mounted through `gateway.slots`.
- Flag-on and flag-off `/v1` route rows are equivalent.
- Duplicate router IDs fail fast.
- Router factories returning no router fail fast.
- No full `/v1` router migration, route policy enforcement, route health
  probes, Web Slot Center, SDK slot client, persistence schema, SlotKernel,
  SlotBundle, SlotPolicy, SlotLoader, third-party install, signing, or
  enterprise allowlist is added.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## 9. Validation Plan

```bash
py -3 -m pytest tests/unit/platform/slots/test_builtin_gateway_slot.py tests/contract/test_gateway_slot_parity.py tests/cli/test_cli_slots.py tests/contract/test_slot_api.py tests/cli/test_doged_cli.py -q
py -3 -m pytest tests/unit/platform/slots tests/contract/test_gateway_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_tool_registry_slot_parity.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0050-gateway-slot-consumer.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-041-gateway-slot-consumer.md
py -3 scripts/validate_no_stale_counts.py
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-041-gateway-slot-consumer-manifest.md`.

## 11. Out of Scope

- Migration of sessions, runs, documents, portfolios, platform, tools, audit,
  enterprise, and health routers to gateway slots.
- Route policy enforcement, route active health, auth-policy changes, OpenAPI
  contract changes, or route count changes.
- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, and `SlotLoader`.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- Persistence schema, ModelRouter/ProfileRegistry, external auth, or worker
  behavior changes.
- Production readiness declaration or external/operator gate closure.
