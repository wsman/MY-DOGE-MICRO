# Slot Gateway Route Provider Facet Local Acceptance - 2026-07-09

## Scope

P10 opens the final `routes` provider facet for installed, v3 package-signed,
operator-gated providers. This completes restricted facet expansion for local
alpha provider execution while preserving the default-off provider gate chain.

## Changes Verified

- `InstalledProviderSlot` now treats `SlotType.GATEWAY` as
  provider-executable.
- Gateway providers may contribute `routes` only.
- Route contributions from non-gateway slot types remain rejected.
- Non-built-in provider routes must mount under
  `/v1/slot-providers/<slot_id>`.
- Provider routes with `requires_auth=False` are rejected.
- Provider routes are mounted with the existing `deps.require_api_token`
  dependency.
- Provider route factories and request handlers are wrapped in slot permission
  context when runtime interception is enabled.
- Default route coverage remains 98 documented HTTP routes unless an operator
  installs additional provider routes.
- P8 provider-isolation honesty remains unchanged: provider contribution
  objects and route handlers are in-process and not OS/container/WASM isolated.

## Verification

```text
cmd.exe /c "cd /d D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO && set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_gateway_slot.py tests\contract\test_gateway_slot_parity.py -q"
=> 31 passed, 2 FastAPI deprecation warnings

cmd.exe /c "cd /d D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO && set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_gateway_slot.py tests\contract\test_gateway_slot_parity.py tests\contract\test_slot_api.py tests\cli\test_cli_slots.py tests\contract\test_api_doc_route_coverage.py -q"
=> 86 passed, 2 FastAPI deprecation warnings
```

## Non-Claims

- No marketplace/catalog behavior.
- No URL or upload install.
- No YAML manifests.
- No transitive dependency signing.
- No filesystem mediation or malicious-code containment.
- No OS/container/WASM provider sandbox.
- No external/operator gate closure.
- No maturity promotion.

## Open Gates

- `S017-003`
- `W3-live`
- `AUTH-prod`
- `S017-007`

## Posture

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```
