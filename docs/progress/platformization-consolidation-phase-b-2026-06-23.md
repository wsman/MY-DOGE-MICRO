# Platformization Consolidation Phase B

> **Status**: Complete for facade slice
> **Date**: 2026-06-23
> **Owner**: Codex
> **Governing ADR**: docs/architecture/adr-0022-directory-restructuring.md

## Scope

Phase B established shallow target packages for the bounded-context layout
without moving implementation files. The new packages are compatibility
facades only. Existing import paths remain valid and continue to be the source
of implementation truth until later migration stories move code behind tests.

## Completed

- Added shared and target package markers:
  - `src/doge/shared`
  - `src/doge/platform`
  - `src/doge/products`
  - `src/doge/adapters`
  - `src/doge/entrypoints`
  - `src/doge/bootstrap`
- Added platform facade exports:
  - `doge.platform.runtime`
  - `doge.platform.workspace`
  - `doge.platform.evidence`
  - `doge.platform.governance`
- Added product facade exports:
  - `doge.products.market`
  - `doge.products.research`
  - `doge.products.portfolio`
  - `doge.products.quant`
- Added import identity and boundary tests in
  `tests/unit/architecture/test_phase_b_facades.py`.

## Non-Changes

- No implementation file was physically moved.
- No old import path was removed.
- No behavior, route, SDK, runtime, or provider contract changed.
- No ADR moved from Proposed to Accepted.
- No feature flag was removed.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests/unit/architecture/test_phase_b_facades.py -q
8 passed in 0.63s

.\.venv\Scripts\python.exe -m pytest tests/unit/layer_gates/ -q
65 passed, 1 warning in 1.39s

.\.venv\Scripts\python.exe -m pytest tests/unit/agent/test_runtime_kernel.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_service_facade.py tests/unit/agent/test_tool_registry.py tests/unit/capabilities -q
49 passed in 12.51s

.\.venv\Scripts\python.exe -m pytest tests/contract/test_platform_api.py tests/contract/test_run_summary_api.py tests/contract/test_v1_api.py -q
18 passed in 12.05s
```

The layer-gate warning is the existing deprecation warning for
`doge.core.services.composition`.

## Residual Gaps

- Facades still point to existing implementation modules by design.
- Old paths still need deprecation markers and removal versions once concrete
  symbols move.
- Physical moves remain blocked by ADR-0022 validation criteria.
- Provider Registry parity and direct-path deletion are Phase C work.
- RuntimeKernel service extraction is still pending.

## Phase B Close Criteria

| Criterion | Result |
|-----------|--------|
| Target packages exist | Passed |
| Target packages are shallow facades | Passed |
| Old and new imports resolve to same objects | Passed |
| Runtime facade does not import product contexts | Passed |
| Product facades do not import each other | Passed |
| Layer gates pass | Passed |
| Runtime/tool/provider tests pass | Passed |
| Platform/API contracts pass | Passed |
