# Platformization Consolidation Phase D

> **Status**: Complete for platform router service-extraction slice
> **Date**: 2026-06-23
> **Owner**: Codex
> **Governing ADRs**: ADR-0016, ADR-0018, ADR-0021, ADR-0022

## Scope

Phase D moved Workspace, Project, Research Case, Workflow Template, and
case-run orchestration out of the FastAPI platform router and into
`doge.platform.workspace.service`. The public API routes and response shapes
remain unchanged.

## Completed

- Added `PlatformRequestContext` for tenant, actor, and request id context.
- Added platform service exceptions with route-level HTTP mapping.
- Added `WorkspaceService`, `ProjectService`, `ResearchCaseService`, and
  `WorkflowService`.
- Moved repository access, ACL checks, creator grants, audit writes,
  template-to-run request construction, run creation, and case-run linking into
  the service layer.
- Refactored `src/doge/interfaces/api/routers/v1/platform.py` so route
  handlers delegate to services.
- Added `tests/unit/architecture/test_platform_router_delegation.py` to block
  router regression back into direct repository and ACL orchestration.

## Non-Changes

- No route path changed.
- No API response schema changed.
- No database schema changed.
- No feature flag was removed.
- ADR-0016 and ADR-0018 remain Proposed.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests/contract/test_platform_api.py -q
7 passed in 6.70s

.\.venv\Scripts\python.exe -m pytest tests/contract/test_enterprise_acl_api.py tests/contract/test_run_summary_api.py -q
19 passed in 11.99s

.\.venv\Scripts\python.exe -m pytest tests/unit/architecture/test_phase_b_facades.py tests/unit/layer_gates/ -q
73 passed, 1 warning in 1.59s

.\.venv\Scripts\python.exe -m pytest tests/contract/test_v1_api.py tests/contract/test_agent_router.py -q
10 passed in 8.75s

.\.venv\Scripts\python.exe -m pytest tests/unit/architecture/test_platform_router_delegation.py tests/contract/test_platform_api.py -q
8 passed in 3.93s

.\.venv\Scripts\python.exe -m pytest tests/unit/architecture/test_phase_b_facades.py tests/unit/layer_gates/ tests/unit/governance/test_s017_planning_docs.py tests/unit/governance/test_adr_lifecycle_status.py -q
106 passed, 2 skipped, 1 warning in 1.62s
```

The warning is the existing `doge.core.services.composition` deprecation
coverage.

## Residual Gaps

- Capability registry route audit remains in the router because its execution
  path is a separate use case rather than Workspace/Workflow orchestration.
- Service classes still sit in a facade-first target package while the broader
  source tree remains mixed during ADR-0022.
- Web navigation consolidation is still pending.
- RuntimeKernel service extraction is still pending.

## Phase D Close Criteria

| Criterion | Result |
|-----------|--------|
| Platform router no longer directly calls platform repository methods | Passed |
| Workspace/Project/Case/Workflow orchestration lives in services | Passed |
| Case-to-run and template-to-run behavior remains contract-compatible | Passed |
| Enterprise ACL filtering still works | Passed |
| Audit writes still happen through governance port | Passed |
| Platform/API contracts pass | Passed |
| Router delegation guard exists | Passed |
