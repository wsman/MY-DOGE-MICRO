# Sprint H Compatibility Surface Governance Evidence

Date: 2026-07-01
Plan: `C:\Users\WSMAN\.claude\plans\bubbly-inventing-llama.md`
Status: local complete, external gates unchanged

## Implemented Files

- `docs/architecture/compatibility-surfaces.md`
- `tests/unit/architecture/test_shim_behavior_guards.py`
- `tests/unit/architecture/test_composition_allowlist.py`
- `production/qa/qa-plan-sprint-h.md`
- `production/qa/evidence/sprint-h-compatibility-surface-governance.md`
- `README.md`
- `docs/progress/runtime-maturity.yaml`
- `production/session-state/active.md`

## Current Measured Counts

- `doge.application.composition`: 73 public callables.
  - 72 `build_*` callables.
  - 1 non-`build_*` public callable: `refresh_views`.
  - Grouping: 43 gateway-backed, 25 runtime-backed, 5 workspace-backed.
- `src/doge/interfaces/api/routers/v1/`: 22 Python files.
  - 18 route shims.
  - 3 `_common` helper shims.
  - 1 `__init__.py`.
- `doge.interfaces.api_legacy.routers`: 8 legacy router modules, about 32 route decorators.
- `src/macro/`: 6 Python files including `__init__.py`.
- `src/micro/`: 7 Python files including `__init__.py`.
- `src/interface/`: 5 Python files including `__init__.py`.
- `doge.infrastructure.agent.inmemory_runtime`: 1 public runtime class.
- `doge.infrastructure.agent.scripted_model`: 4 public classes.

## Verification Results

- `py -3 -m pytest tests\unit\architecture\test_shim_behavior_guards.py -q`
  - Result: 9 passed in 0.09s.
- `py -3 -m pytest tests\unit\architecture\test_composition_allowlist.py -q`
  - Result: 4 passed in 0.60s.
- `py -3 -m pytest tests\unit\architecture -q`
  - Result: 122 passed, 2 warnings in 2.95s.
- `py -3 scripts\validate_docs_links.py`
  - Result: validated 64 markdown files.
- `py -3 scripts\validate_alpha_maturity_honesty.py`
  - Result: passed; errors empty.
- `py -3 scripts\validate_governance_yaml_shape.py`
  - Result: passed; 5 files checked, 0 findings.
- `py -3 scripts\validate_plan_closure_gate.py --allow-open`
  - Result: acceptable open; 2 passed, 4 open, 0 failed, 0 invalid.
- `py -3 scripts\validate_plan_closure_gate.py`
  - Result: failed as expected; acceptable false while the same 4 external gates remain open.
- `git diff --check`
  - Result: passed.

## Remaining External Gates

Sprint H does not close these external/operator gates:

- `S017-003`
- `W3-live`
- `AUTH-prod`
- `S017-007`

## Maturity Posture

Sprint H does not change runtime maturity:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

Sprint H does not update `latest_remotely_verified_sha`; it is local evidence
only until a later exact-SHA remote CI pass is recorded.
