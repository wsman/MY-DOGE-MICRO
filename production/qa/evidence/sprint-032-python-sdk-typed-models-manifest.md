# Sprint 032 - Python SDK Typed Result Models Manifest

> Sprint: 032 (Python SDK Typed Result Models)
> Date: 2026-07-06
> Status: Local implementation complete; final verification passed.

## Scope

This manifest records local evidence for adding dict-compatible typed result
models to the Python SDK runs resource.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0041-python-sdk-typed-models.md` records the dict-subclass decision. |
| CDD | `design/cdd/sprint-032-python-sdk-typed-models.md` records compatibility and acceptance criteria. |
| Models | `packages/doge-sdk-python/doge_sdk/run_models.py` defines `Run`, `RunListItem`, `Artifact`, `Approval`, and `RunEvent`. |
| Sync runs resource | `packages/doge-sdk-python/doge_sdk/run.py` wraps sync `get`, `list`, `events`, `approve`, `resume`, and `cancel`. |
| Async runs resource | `packages/doge-sdk-python/doge_sdk/run.py` wraps async `get`, `list`, `events`, `approve`, `resume`, and `cancel`. |
| Streaming invariant | `DogeEvent` remains the streaming dataclass returned by `runs.stream`. |
| Package exports | `packages/doge-sdk-python/doge_sdk/__init__.py` re-exports the typed run models. |
| README | `packages/doge-sdk-python/README.md` documents typed access as additive to dict access. |
| Contract tests | `tests/contract/test_python_sdk.py` preserves dict equality/access and adds typed return assertions. |
| Model tests | `tests/unit/sdk/test_python_sdk_run_models.py` covers dict semantics, nested models, exports, and no runtime modeling dependency. |
| Session state | `production/session-state/active.md` records Sprint 032 as the current local implementation. |

## Verification Commands

```bash
PYTHONPATH=packages/doge-sdk-python python3 -m py_compile \
  packages/doge-sdk-python/doge_sdk/run.py \
  packages/doge-sdk-python/doge_sdk/run_models.py \
  packages/doge-sdk-python/doge_sdk/__init__.py \
  tests/contract/test_python_sdk.py \
  tests/unit/sdk/test_python_sdk_run_models.py

cmd.exe /c py -3 -m pytest tests/contract/test_python_sdk.py tests/unit/sdk/test_python_sdk_run_models.py -q
cmd.exe /c py -3 tools/ci/sdk-contract-check.py
cmd.exe /c py -3 scripts/validate_import_boundaries.py
cmd.exe /c py -3 scripts/validate_docs_authority.py
cmd.exe /c py -3 scripts/validate_docs_links.py
cmd.exe /c py -3 scripts/validate_docs_maturity_claims.py
cmd.exe /c py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0041-python-sdk-typed-models.md
cmd.exe /c py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-032-python-sdk-typed-models.md
cmd.exe /c py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/a038a698-harmonic-mango.md
git diff --check
```

## Verification Results

| Gate | Result |
|---|---|
| Python compile | Passed for Python SDK run resource, run models, package exports, contract test, and model test. |
| Python SDK focused suite | Passed: 32 tests. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0041 and Sprint 032 CDD. |
| Plan closure | Passed with controlled open posture: 4 open / 2 passed. |
| Whitespace | Passed with `git diff --check`. |

## Posture

- Production posture unchanged.
- No external/operator gates are closed by this sprint.
- No `/v1` route, OpenAPI schema, TypeScript SDK type, persistence schema,
  daemon behavior, authorization behavior, or production readiness declaration
  is part of this sprint.
- Python SDK Level 3 remains `experimental`; this is an additive Local Alpha
  developer-experience improvement.
