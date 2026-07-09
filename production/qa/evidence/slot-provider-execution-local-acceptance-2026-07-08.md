# Slot Provider Execution Local Acceptance Evidence

Date: 2026-07-08
Plan: `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md`
ADR: `docs/architecture/adr-0064-slot-provider-execution.md`

## Verdict

PASS. P5 Slot Provider Execution focused gate, broader slot boundary/runtime
gate, and docs governance gate passed locally. Commit/push are operational Git
handoff actions and do not constitute remote CI evidence or
`latest_remotely_verified_sha` promotion.

Remote CI was not run and external/operator gates remain open.

## Scope

P5 adds a default-off local alpha installed-provider execution path:

- `DOGE_FEATURE_SLOT_PROVIDER_EXECUTION` defaults off.
- `SlotLoader` and `DOGE_SLOT_MANIFEST_DIRS` remain manifest-only discovery.
- Installed manifests under `DOGE_SLOT_INSTALL_DIR` may register as
  `InstalledProviderSlot` only when signing, revocation, runtime interception,
  and SlotKernel gates pass.
- Resolve-time signature verification repeats before importlib execution.
- Provider entrypoints must instantiate `ISlot` and match manifest id/type/
  provides.
- Allowed facets are tools, model backends, workflows, data sources, and
  document parsers.
- Restricted facets are gateway routes, UI panels, watchers, eval suites, and
  governance policies.
- `/v1/slots` and `doge slots` status rows expose execution eligibility and
  blockers without importing provider code.

## Non-Scope

No filesystem mediation, OS/container/WASM sandboxing, malicious-code
containment, provider package signing, YAML manifest parser, HTTP install API,
SDK install API, marketplace behavior, external-gate closure, remote CI
assertion, `latest_remotely_verified_sha` promotion, or maturity promotion is
included.

Posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## Local Verification

Focused provider/settings/capability/CLI/API:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/unit/platform/slots/test_slot_provider_execution.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/cli/test_cli_slots.py tests/contract/test_slot_api.py -q"
=> 86 passed, 2 warnings
```

Combined P5 backend:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/unit/platform/slots/test_slot_provider_execution.py tests/unit/platform/slots/test_slot_install.py tests/unit/platform/slots/test_slot_runtime_access.py tests/unit/architecture/test_slot_boundary.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/cli/test_cli_slots.py tests/contract/test_slot_api.py tests/contract/test_tool_registry_slot_parity.py tests/contract/test_data_source_slot_parity.py -q"
=> 137 passed, 2 warnings
```

Broader slot boundary/runtime:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/unit/architecture/test_slot_boundary.py tests/unit/platform/slots/test_slot_install.py tests/unit/platform/slots/test_slot_runtime_access.py tests/contract/test_tool_registry_slot_parity.py tests/contract/test_data_source_slot_parity.py -q"
=> 51 passed
```

Docs governance:

```text
validate_adr_index_completeness.py
validate_governance_yaml_shape.py
validate_docs_authority.py
validate_docs_maturity_claims.py
validate_alpha_maturity_honesty.py --file docs/architecture/adr-0064-slot-provider-execution.md
validate_alpha_maturity_honesty.py --file design/cdd/p5-slot-provider-execution.md
validate_alpha_maturity_honesty.py --file production/qa/evidence/slot-provider-execution-local-acceptance-2026-07-08.md
=> passed
```

## Acceptance Invariants

- Provider execution is not default on.
- Non-installed manifests do not execute.
- Signing alone is not enough; revocation lookup and runtime interception are
  required.
- In-process importlib execution is not described as a hardened sandbox.
- Production and stable declarations remain forbidden.

## Post-P9 Supersession Note - 2026-07-09

This evidence is an at-acceptance historical record. Any "no HTTP install API",
"no SDK install API", "no SDK install method", or "no SDK slot client" wording
in this file remains true for the sprint accepted here. ADR-0067 and
`production/qa/evidence/slot-install-surfaces-local-acceptance-2026-07-09.md`
supersede that deferral going forward by adding default-off local HTTP, SDK, and
Web install surfaces. YAML manifests, URL/upload install, marketplace/catalog
behavior, default-on provider execution, external gate closure, and production
readiness remain deferred.
