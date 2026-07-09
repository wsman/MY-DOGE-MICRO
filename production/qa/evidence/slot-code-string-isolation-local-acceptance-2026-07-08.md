# Slot Code-String Isolation Local Acceptance Evidence

Date: 2026-07-08
Plan: `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md`
ADR: `docs/architecture/adr-0066-code-string-isolation-prototype.md`
CDD: `design/cdd/p8-code-string-isolation.md`

## Verdict

PASS. P8 Code-String Isolation Prototype focused gate, broader slot regression,
real Windows Job Object smoke, and docs governance validators passed locally.

Remote CI was not run. `latest_remotely_verified_sha` remains
`a1da266a134ab6e6d2711fab6430c26616210191`. External/operator gates remain
open.

## Scope Delivered

- Added `DOGE_FEATURE_SLOT_CODE_STRING_ISOLATION`, default off.
- Exposed `feature.slot_code_string_isolation` through capability discovery as
  high risk with `run_python_analysis code strings only` scope.
- Extended `SubprocessCodeExecutor` with optional Windows Job Object resource
  limits using stdlib `ctypes`.
- Preserved P4 subprocess env scrub, scratch cwd, timeout clamp, and Windows
  process group behavior.
- Failed closed when P8 isolation is requested on non-Windows hosts.
- Added best-effort `slot_resource_limit_exceeded` audit events for resource
  limit failures.
- Kept Python analysis default-off; the P8 flag alone does not enable code
  execution.

## Non-Scope / Residuals

P8 is not hardened provider isolation.

Still not delivered:

- provider contribution-object subprocess/container/WASM isolation;
- filesystem mediation or absolute-path read denial;
- raw socket/network sandboxing;
- malicious-code containment;
- transitive dependency signing or provider contribution-object isolation;
- marketplace, HTTP install API, SDK install API, YAML manifests;
- external gate closure, remote CI promotion, or maturity promotion.

P7/ADR-0065 covers local provider package identity separately. P8 does not
change that package identity model and does not turn package identity into
runtime containment.

Posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## Local Verification

Focused P8 settings/capability/executor gate:

```text
cmd.exe /c cd /d "D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO" \&\& set PYTHONPATH=src\&\& py -3 -m pytest tests/unit/capabilities/test_code_executor.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py -q
=> 55 passed
```

Real Windows Job Object smoke:

```text
cmd.exe /c cd /d "D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO" \&\& set PYTHONPATH=src\&\& py -3 -c "from doge.infrastructure.code_execution.python import SubprocessCodeExecutor; r=SubprocessCodeExecutor(isolation_enabled=True).execute('print(123)', 1.0); print(r.ok, r.returncode, r.stdout.strip(), r.error)"
=> True 0 123 None
```

Broader P4/P5/CLI regression:

```text
cmd.exe /c cd /d "D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO" \&\& set PYTHONPATH=src\&\& py -3 -m pytest tests/unit/platform/slots/test_slot_runtime_access.py tests/unit/platform/slots/test_slot_provider_execution.py tests/cli/test_cli_slots.py -q
=> 53 passed
```

Docs governance:

```text
validate_alpha_maturity_honesty.py --file docs/progress/runtime-maturity.yaml
validate_alpha_maturity_honesty.py --file docs/architecture/adr-0066-code-string-isolation-prototype.md
validate_alpha_maturity_honesty.py --file design/cdd/p8-code-string-isolation.md
validate_alpha_maturity_honesty.py --file production/qa/evidence/slot-code-string-isolation-local-acceptance-2026-07-08.md
validate_docs_maturity_claims.py
validate_governance_yaml_shape.py
validate_docs_links.py
validate_adr_index_completeness.py
validate_docs_authority.py
validate_plan_closure_gate.py --allow-open --source-plan C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md
git diff --check
=> passed; plan closure remains acceptable-open with 2 passed / 4 open external gates
```

## Acceptance Invariants

- `slot_code_string_isolation` is default off.
- `python_analysis_enabled` is still default off.
- P8 flag-on requires the existing subprocess executor selection.
- Non-Windows P8 isolation fails closed.
- Provider contributions remain in-process and are not represented as isolated.
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
