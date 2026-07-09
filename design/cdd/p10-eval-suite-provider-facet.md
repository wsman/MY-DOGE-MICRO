# P10 CDD: Eval Suite Provider Facet

Status: Ready for Local Acceptance
Date: 2026-07-09

## 1. Overview

P10 starts restricted facet expansion by allowing installed, signed,
operator-gated providers to contribute eval suites. It does not open UI panels,
watchers, governance policies, or routes.

The work builds on ADR-0064 provider execution, ADR-0065 package identity,
ADR-0066 provider-isolation honesty, ADR-0067 install surfaces, and the existing
ADR-0051 eval suite consumer.

## 2. User Promise / JTBD

An eval owner can package a deterministic local eval suite as an installed
provider and run it through the existing eval suite registry once the operator
has explicitly enabled the provider execution chain.

A security reviewer can verify that this is a narrow facet expansion, not a
general plugin marketplace or provider sandbox claim.

## 3. Scope

Included:

- Add `SlotType.EVAL` to the installed-provider executable type allowlist.
- Allow only the `eval_suites` contribution field for eval providers.
- Keep route, UI panel, watcher, and governance policy provider facets
  restricted.
- Reuse `build_slot_aware_eval_suites()` and `EvalSuiteRegistry`.
- Add provider execution tests for signed eval providers and route rejection.
- Add ADR, CDD, evidence, maturity, and registry updates.

Excluded:

- UI panel provider facets.
- Watcher provider facets.
- Governance policy provider facets.
- Gateway route provider facets.
- Marketplace/catalog behavior, URL/upload install, YAML manifests, remote
  registry trust, transitive dependency signing, or OS/container/WASM sandboxing.
- Any production maturity or external gate closure.

## 4. Configuration

No new feature flag is introduced. The existing provider execution chain remains
default off:

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
`type="eval"`, `InstalledProviderSlot` imports the signed package and accepts
only `eval_suites` from the provider contribution.

The contribution then flows through the existing eval registry path:

```text
InstalledProviderSlot
  -> SlotKernel.resolve_contributions(slot_type=SlotType.EVAL)
  -> build_slot_aware_eval_suites()
  -> EvalSuiteRegistry
```

If the provider contributes a route, UI panel, watcher, governance policy, or a
facet belonging to another slot type, resolution fails closed with
`SlotConfigurationError`.

## 6. Acceptance Criteria

- A signed, installed eval provider contributes an eval suite through
  `build_slot_aware_eval_suites()`.
- The registry record includes the provider suite id, cases path, execution
  profile, and eval policy labels.
- Existing workflow provider execution still passes.
- Route facets remain restricted after eval suite expansion.
- Maturity posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 7. Verification Plan

Focused P10 eval:

```text
py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_eval_slot.py tests\unit\eval\test_eval_suite_registry.py -q
```

Governance:

```text
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\progress\runtime-maturity.yaml
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\architecture\adr-0068-slot-eval-suite-provider-facet.md
py -3 scripts\validate_alpha_maturity_honesty.py --file design\cdd\p10-eval-suite-provider-facet.md
py -3 scripts\validate_docs_maturity_claims.py
py -3 scripts\validate_governance_yaml_shape.py
py -3 scripts\validate_adr_index_completeness.py
git diff --check
```
