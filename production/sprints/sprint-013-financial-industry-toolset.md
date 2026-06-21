# Sprint 013 - Financial Industry Toolset

> Stage: Release follow-up
> Duration: 2026-06-21 -> 2026-06-21
> Status: done
> Source roadmap: `C:\Users\Aby\.claude\plans\replicated-nibbling-pine.md`
> QA plan: `production/qa/qa-plan-sprint-013.md`

## Sprint Goal

Replace the most visible financial tool stub with deterministic portfolio,
risk, scenario, and evidence-aware claim-validation tools.

## Must Have

| ID | Task | Status | Acceptance Evidence |
|---|---|---|---|
| S013-001 | Portfolio domain model, port, and SQLite repository | done | `src/doge/core/domain/portfolio_models.py`, `src/doge/core/ports/portfolio_repository.py`, `src/doge/infrastructure/database/portfolio_repository.py`, `tests/unit/test_portfolio_service.py` |
| S013-002 | Portfolio exposure service and demo portfolio seed | done | `src/doge/application/services/portfolio_service.py`, `src/doge/application/composition.py`, `tests/unit/test_portfolio_service.py` |
| S013-003 | Risk and scenario services | done | `src/doge/application/services/portfolio_service.py`, `tests/unit/test_portfolio_service.py` |
| S013-004 | Agent tool registry exposes portfolio/risk/scenario tools | done | `src/doge/application/agent/tools.py`, `tests/unit/agent/test_tool_registry.py` |
| S013-005 | Claim validation returns evidence-aware statuses | done | `src/doge/application/agent/tool_service.py`, `tests/unit/agent/test_tool_service.py` |
| S013-006 | Calculation definitions and progress governance | done | `docs/progress/financial-tool-definitions.md`, `docs/progress/runtime-maturity.yaml`, `docs/progress/runtime-stability-followup-plan.md` |

## Deferred

| ID | Task | Status | Notes |
|---|---|---|---|
| S013-007 | Real fundamentals/announcement connectors | deferred | Requires additional data providers and fixtures. |
| S013-008 | Portfolio CSV/XLSX import workflow | deferred | Portfolio persistence exists; import UX/parser remains future work. |

## Definition of Done

- [x] `get_portfolio_exposure` no longer raises `NotImplementedError`.
- [x] Risk/scenario tools return deterministic documented approximations.
- [x] Claim validation statuses include `supported`, `contradicted`, `insufficient_evidence`, and `data_unavailable` paths.
- [x] Tool registry tests cover new tool names.
- [x] Full Python suite green after final verification.
- [ ] Remote CI green after push.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_portfolio_service.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_registry.py -q` -> `14 passed in 1.58s`.
- `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `817 passed, 5 skipped, 11 warnings in 63.65s`.

## Stable Declaration

Stable declaration remains forbidden. Sprint 013 improves deterministic finance
tools, but it does not provide production risk modeling, real fundamentals
connectors, or regulated investment advice.
