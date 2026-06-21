# Sprint 014 - Industry Report And Modular Migration

> Stage: Release follow-up
> Duration: 2026-06-21 -> 2026-06-21
> Status: done
> Source roadmap: `C:\Users\Aby\.claude\plans\replicated-nibbling-pine.md`
> QA plan: `production/qa/qa-plan-sprint-014.md`

## Sprint Goal

Complete the representative industry-report workflow and remove the canonical
scan router's direct legacy TDX downloader coupling.

## Must Have

| ID | Task | Status | Acceptance Evidence |
|---|---|---|---|
| S014-001 | Implement `GenerateIndustryReportUseCase` | done | `src/doge/application/use_cases/generate_industry_report.py`, `tests/integration/test_industry_report.py` |
| S014-002 | Add claim/citation domain, port, repository, and services | done | `src/doge/core/domain/claim_models.py`, `src/doge/core/ports/claim_repository.py`, `src/doge/infrastructure/database/claim_repository.py`, `tests/unit/test_claim_repository.py`, `tests/unit/test_citation_service.py`, `tests/unit/test_claim_validation.py` |
| S014-003 | Add `generate_industry_report` agent tool | done | `src/doge/application/agent/tools.py`, `src/doge/application/agent/tool_service.py`, `tests/unit/agent/test_tool_registry.py` |
| S014-004 | Move TDX server listing/testing behind port/adapter | done | `src/doge/core/ports/tdx_server_list.py`, `src/doge/infrastructure/data_source/tdx_server_list.py`, `tests/unit/infrastructure/test_tdx_server_list.py` |
| S014-005 | Remove direct legacy downloader import from canonical scan router | done | `src/doge/interfaces/api/routers/scan.py`, `tests/contract/test_no_micro_imports_in_interface.py`, `tests/unit/layer_gates/test_no_micro_under_doge.py` |
| S014-006 | ADR/CDD/progress governance update | done | `docs/architecture/adr-0004-data-source-adapter-contract.md`, `design/cdd/clean-architecture-migration.md`, `docs/progress/industry-report-modular-migration-notes.md` |

## Deferred

| ID | Task | Status | Notes |
|---|---|---|---|
| S014-007 | Real fundamentals and announcement connectors | deferred | Use case accepts injected stock/RAG seams; provider-grade fundamentals/announcements need fixtures and provider choice. |
| S014-008 | Full legacy TDX helper deletion | deferred | Canonical scan router is decoupled; compatibility helper deletion needs a separate parity/deletion pass. |
| S014-009 | Citation-quality evaluation | deferred | Claim/citation objects exist; measured citation precision remains a release-quality gate. |
| S014-010 | Live Kimi synthesis smoke | deferred | Offline fallback and mocked/injected seams are tested; live smoke remains operator-environment-dependent. |

## Definition of Done

- [x] "Generate a semiconductor industry report" returns rankings, fundamentals, research evidence, claims, and citations.
- [x] `generate_industry_report` is available in the default agent tool registry.
- [x] Canonical scan router has zero direct legacy downloader imports.
- [x] TDX server list/testing behavior is behind a port/adapter.
- [x] ADR/CDD docs reflect the new modular boundary.
- [x] Full Python suite green after final verification.
- [ ] Remote CI green after push.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_citation_service.py tests/unit/test_claim_validation.py tests/unit/test_claim_repository.py tests/integration/test_industry_report.py tests/unit/infrastructure/test_tdx_server_list.py tests/contract/test_no_micro_imports_in_interface.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_registry.py tests/unit/application/contracts/test_dtos.py tests/test_api_routers.py::TestScanRouter tests/unit/interfaces/api/test_scan_local_fallback.py tests/test_tdx_adapter.py tests/unit/layer_gates/test_no_micro_under_doge.py tests/unit/layer_gates/test_api_layer_gate.py tests/unit/layer_gates/test_composition_root_location.py -q` -> `91 passed in 11.83s`.
- `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `828 passed, 5 skipped, 11 warnings in 63.48s`.

## Stable Declaration

Stable declaration remains forbidden. Sprint 014 adds report-level
claim/citation assembly and removes canonical scan-router legacy coupling, but
it does not provide citation-quality scoring, real fundamentals/announcement
connectors, live Kimi smoke evidence, or release-quality gates.
