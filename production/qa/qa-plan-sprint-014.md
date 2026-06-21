# QA Plan - Sprint 014 Industry Report And Modular Migration

## Scope

Validate the S014 industry-report workflow, claim/citation persistence, agent
tool registration, and canonical scan-router decoupling from direct legacy TDX
downloader imports.

## Automated Evidence

| Area | Evidence | Command |
|---|---|---|
| Industry report workflow | Use case returns structured report, claims, citations, and persists report/claim links | `tests/integration/test_industry_report.py` |
| Claim/citation services | Validation, citation assembly, and SQLite persistence are deterministic | `tests/unit/test_claim_validation.py`, `tests/unit/test_citation_service.py`, `tests/unit/test_claim_repository.py` |
| Agent tool surface | Default registry includes and executes `generate_industry_report` | `tests/unit/agent/test_tool_registry.py` |
| TDX server list adapter | Configured server listing and opentdx-absent degradation are covered | `tests/unit/infrastructure/test_tdx_server_list.py` |
| Scan router boundary | Canonical scan router has no direct legacy downloader import | `tests/contract/test_no_micro_imports_in_interface.py`, `tests/unit/layer_gates/test_no_micro_under_doge.py` |
| API/TDX regression | Existing scan API and TDX adapter behavior remain stable | `tests/test_api_routers.py::TestScanRouter`, `tests/test_tdx_adapter.py` |

## Local Gate

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_citation_service.py tests/unit/test_claim_validation.py tests/unit/test_claim_repository.py tests/integration/test_industry_report.py tests/unit/infrastructure/test_tdx_server_list.py tests/contract/test_no_micro_imports_in_interface.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_registry.py tests/unit/application/contracts/test_dtos.py tests/test_api_routers.py::TestScanRouter tests/unit/interfaces/api/test_scan_local_fallback.py tests/test_tdx_adapter.py tests/unit/layer_gates/test_no_micro_under_doge.py tests/unit/layer_gates/test_api_layer_gate.py tests/unit/layer_gates/test_composition_root_location.py -q
```

Result: `91 passed in 11.83s`.

## Deferred Manual / Live Evidence

- Live Kimi synthesis smoke for the industry report.
- Live TDX server connectivity/download smoke.
- Citation-quality evaluation against a labeled benchmark.
- Legacy TDX helper deletion/parity pass.

## QA Verdict

Automated S014 target gate is adequate for local merge-readiness of the new
workflow and boundary refactor. Release promotion remains blocked by the
deferred live/evaluation gates above.
