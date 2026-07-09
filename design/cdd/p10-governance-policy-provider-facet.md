# P10 CDD: Governance Policy Provider Facet

Status: Ready for Local Acceptance
Date: 2026-07-09

## 1. Overview

P10 continues restricted facet expansion by allowing installed, signed,
operator-gated providers to contribute governance policy records for tool
entitlement composition.

Governance providers remain local alpha. They run in-process, but their
factory calls and checker methods now execute through the existing slot
permission context when runtime interception is enabled.

## 2. User Promise / JTBD

A local operator can install a signed provider that contributes stricter tool
entitlement policy, while the runtime preserves the built-in forbidden-tool
deny rule and high-risk approval requirement.

A security reviewer can verify that this is not route injection, tenant
isolation expansion, general provider sandboxing, or a production
authorization claim.

## 3. Scope

Included:

- Add `SlotType.GOVERNANCE` to the installed-provider executable type
  allowlist.
- Allow only the `governance_policies` contribution field for governance
  providers.
- Require the existing `slot_governance` flag for governance policy
  resolution.
- Keep monotonic entitlement composition:
  - `can_execute` remains an `all(...)` composition.
  - `requires_approval` remains an `any(...)` composition.
- Wrap provider governance policy factories and checker methods in slot
  permission context when runtime interception is enabled.
- Keep route provider facets restricted.
- Reuse `build_slot_aware_entitlement_checker()` and
  `CompositeToolEntitlementChecker`.
- Add provider execution tests for signed governance providers, slot scope, and
  forbidden-tool denial.
- Add ADR, CDD, evidence, maturity, and registry updates.

Excluded:

- Gateway route provider facets.
- Replacement of the composite entitlement checker.
- Tenant-isolation expansion or production authorization semantics.
- Marketplace/catalog behavior, URL/upload install, YAML manifests, remote
  registry trust, transitive dependency signing, or OS/container/WASM
  sandboxing.
- Any production maturity or external gate closure.

## 4. Configuration

No new feature flag is introduced. Governance provider contributions require
the existing default-off provider execution chain:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_LOADER=1
DOGE_FEATURE_SLOT_INSTALL=1
DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION=1
DOGE_FEATURE_SLOT_PROVIDER_EXECUTION=1
DOGE_FEATURE_SLOT_GOVERNANCE=1
```

Provider execution still also requires trusted publisher keys, signature
revocation storage, package-aware v3 sidecars, SlotKernel admission, and
enterprise allowlist when `DOGE_AUTH_MODE=enterprise`.

## 5. Runtime Behavior

When all provider gates pass and an installed provider manifest has
`type="governance"`, `InstalledProviderSlot` imports the signed package and
accepts only `governance_policies` from the provider contribution.

The contribution then flows through the existing governance path:

```text
InstalledProviderSlot
  -> SlotKernel.resolve_contributions(slot_type=SlotType.GOVERNANCE)
  -> build_slot_aware_entitlement_checker()
  -> CompositeToolEntitlementChecker
```

Provider policy factories and returned checker methods are wrapped so
`current_slot_permission_context()` is populated during entitlement evaluation
when runtime interception is enabled.

If the provider contributes a route or a facet belonging to another slot type,
resolution fails closed with `SlotConfigurationError`.

## 6. Acceptance Criteria

- A signed, installed governance provider contributes a policy through
  `build_slot_aware_entitlement_checker()`.
- Provider checker methods run with active slot permission context.
- Built-in governance slot and parity tests still pass.
- Provider policies cannot re-enable forbidden tools.
- Route facets remain restricted after governance expansion.
- Maturity posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 7. Verification Plan

Focused P10 governance:

```text
py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_governance_slot.py tests\contract\test_governance_slot_parity.py -q
```

Slot API/CLI regression:

```text
py -3 -m pytest tests\contract\test_slot_api.py tests\cli\test_cli_slots.py -q
```

Governance:

```text
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\progress\runtime-maturity.yaml
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\architecture\adr-0071-slot-governance-policy-provider-facet.md
py -3 scripts\validate_alpha_maturity_honesty.py --file design\cdd\p10-governance-policy-provider-facet.md
py -3 scripts\validate_docs_maturity_claims.py
py -3 scripts\validate_governance_yaml_shape.py
py -3 scripts\validate_adr_index_completeness.py
git diff --check
```
