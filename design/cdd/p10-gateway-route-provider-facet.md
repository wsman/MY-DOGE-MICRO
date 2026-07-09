# P10 CDD: Gateway Route Provider Facet

Status: Ready for Local Acceptance
Date: 2026-07-09

## 1. Overview

P10 completes restricted facet expansion by allowing installed, signed,
operator-gated providers to contribute FastAPI gateway route routers.

Gateway route providers remain local alpha. They run in-process and add HTTP
surface area only after all provider gates pass. Non-built-in provider routes
must stay under `/v1/slot-providers/<slot_id>`, must require auth, and receive
slot permission context during request handling when runtime interception is
enabled.

## 2. User Promise / JTBD

A local operator can install a signed provider that exposes a bounded HTTP
surface under the provider namespace without letting it shadow canonical `/v1`
routes.

A security reviewer can verify that this is not marketplace behavior, arbitrary
route injection, provider sandboxing, or a production plugin claim.

## 3. Scope

Included:

- Add `SlotType.GATEWAY` to the installed-provider executable type allowlist.
- Allow only the `routes` contribution field for gateway providers.
- Reject route contributions from non-gateway slot types.
- Require non-built-in provider route prefixes to equal
  `/v1/slot-providers/<slot_id>`.
- Reject provider routes that set `requires_auth=False`.
- Include provider routes with the existing `deps.require_api_token`
  dependency.
- Wrap route factories and request handlers in slot permission context when
  runtime interception is enabled.
- Keep default route coverage at the documented 98 HTTP routes unless an
  operator installs additional provider routes.
- Add provider execution tests for signed route providers, auth enforcement,
  namespace guard, and request-time slot scope.
- Add ADR, CDD, evidence, maturity, and registry updates.

Excluded:

- Arbitrary provider route prefixes.
- Route shadowing of canonical `/v1` routes.
- Marketplace/catalog behavior, URL/upload install, YAML manifests, remote
  registry trust, transitive dependency signing, or OS/container/WASM
  sandboxing.
- Any production maturity or external gate closure.

## 4. Configuration

No new feature flag is introduced. Gateway provider contributions require the
existing default-off provider execution chain:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_LOADER=1
DOGE_FEATURE_SLOT_INSTALL=1
DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION=1
DOGE_FEATURE_SLOT_PROVIDER_EXECUTION=1
```

Provider execution still also requires trusted publisher keys, signature
revocation storage, package-aware v3 sidecars, SlotKernel admission, and
enterprise allowlist when `DOGE_AUTH_MODE=enterprise`.

## 5. Runtime Behavior

When all provider gates pass and an installed provider manifest has
`type="gateway"`, `InstalledProviderSlot` imports the signed package and accepts
only `routes` from the provider contribution.

The contribution then flows through the existing gateway path:

```text
InstalledProviderSlot
  -> SlotKernel.resolve_contributions(slot_type=SlotType.GATEWAY)
  -> build_slot_aware_gateway_routes()
  -> FastAPI.include_router()
```

For provider slots other than the built-in `gateway.slots`, each route must use
the prefix `/v1/slot-providers/<slot_id>` and `requires_auth=True`.

If runtime interception is enabled, route factory calls and request handlers
run with `current_slot_permission_context()` populated.

## 6. Acceptance Criteria

- A signed, installed gateway provider contributes a route through
  `build_slot_aware_gateway_routes()`.
- Provider routes require bearer auth when `DOGE_API_TOKEN` is configured.
- Provider route handlers run with active slot permission context.
- Provider routes cannot mount at arbitrary `/v1` prefixes.
- Built-in gateway slot and gateway parity tests still pass.
- Default route coverage still reports 98 documented routes.
- Maturity posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 7. Verification Plan

Focused P10 routes:

```text
py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_gateway_slot.py tests\contract\test_gateway_slot_parity.py -q
```

Slot API/CLI and route coverage regression:

```text
py -3 -m pytest tests\contract\test_slot_api.py tests\cli\test_cli_slots.py tests\contract\test_api_doc_route_coverage.py -q
```

Governance:

```text
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\progress\runtime-maturity.yaml
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\architecture\adr-0072-slot-gateway-route-provider-facet.md
py -3 scripts\validate_alpha_maturity_honesty.py --file design\cdd\p10-gateway-route-provider-facet.md
py -3 scripts\validate_docs_maturity_claims.py
py -3 scripts\validate_governance_yaml_shape.py
py -3 scripts\validate_adr_index_completeness.py
git diff --check
```
