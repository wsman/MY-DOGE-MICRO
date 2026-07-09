# P10 CDD: Watcher Provider Facet

Status: Ready for Local Acceptance
Date: 2026-07-09

## 1. Overview

P10 continues restricted facet expansion by allowing installed, signed,
operator-gated providers to contribute runtime event watchers.

Watcher providers remain local alpha. They run in-process, but they now execute
through the existing fail-closed watcher middleware and a slot permission
context wrapper.

## 2. User Promise / JTBD

A runtime operator can install a signed local provider that contributes a
runtime event watcher, while the runtime still fails closed on watcher errors,
unsupported actions, and blocking decisions.

A security reviewer can verify that this is not general provider sandboxing and
does not open governance policy mutation or route injection.

## 3. Scope

Included:

- Add `SlotType.WATCHER` to the installed-provider executable type allowlist.
- Allow only the `watchers` contribution field for watcher providers.
- Require the existing `slot_watcher` flag for watcher resolution.
- Wrap watcher `on_event` callables in slot permission context when runtime
  interception is enabled.
- Keep route and governance policy provider facets restricted.
- Reuse `build_slot_aware_runtime_event_watcher()` and
  `RuntimeEventWatcherMiddleware`.
- Add provider execution tests for signed watcher providers and route rejection.
- Add ADR, CDD, evidence, maturity, and registry updates.

Excluded:

- Governance policy provider facets.
- Gateway route provider facets.
- Marketplace/catalog behavior, URL/upload install, YAML manifests, remote
  registry trust, transitive dependency signing, or OS/container/WASM sandboxing.
- Any production maturity or external gate closure.

## 4. Configuration

No new feature flag is introduced. Watcher provider contributions require the
existing default-off chain:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_LOADER=1
DOGE_FEATURE_SLOT_INSTALL=1
DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION=1
DOGE_FEATURE_SLOT_PROVIDER_EXECUTION=1
DOGE_FEATURE_SLOT_WATCHER=1
```

Provider execution still also requires trusted publisher keys, signature
revocation storage, package-aware v3 sidecars, SlotKernel admission, and
enterprise allowlist when `DOGE_AUTH_MODE=enterprise`.

## 5. Runtime Behavior

When all provider gates pass and an installed provider manifest has
`type="watcher"`, `InstalledProviderSlot` imports the signed package and accepts
only `watchers` from the provider contribution.

The contribution then flows through the existing watcher path:

```text
InstalledProviderSlot
  -> SlotKernel.resolve_contributions(slot_type=SlotType.WATCHER)
  -> build_slot_aware_runtime_event_watcher()
  -> RuntimeEventWatcherMiddleware
```

Watcher `on_event` callables are wrapped so `current_slot_permission_context()`
is populated during watcher evaluation when runtime interception is enabled.

If the provider contributes a route, governance policy, or a facet belonging to
another slot type, resolution fails closed with `SlotConfigurationError`.

## 6. Acceptance Criteria

- A signed, installed watcher provider contributes a watcher through
  `build_slot_aware_runtime_event_watcher()`.
- Provider watcher decisions run with active slot permission context.
- Built-in watcher and watcher parity tests still pass.
- Route facets remain restricted after watcher expansion.
- Maturity posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 7. Verification Plan

Focused P10 watcher:

```text
py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_watcher_slot.py tests\contract\test_watcher_slot_parity.py -q
```

Slot API/CLI regression:

```text
py -3 -m pytest tests\contract\test_slot_api.py tests\cli\test_cli_slots.py -q
```

Governance:

```text
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\progress\runtime-maturity.yaml
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\architecture\adr-0070-slot-watcher-provider-facet.md
py -3 scripts\validate_alpha_maturity_honesty.py --file design\cdd\p10-watcher-provider-facet.md
py -3 scripts\validate_docs_maturity_claims.py
py -3 scripts\validate_governance_yaml_shape.py
py -3 scripts\validate_adr_index_completeness.py
git diff --check
```
