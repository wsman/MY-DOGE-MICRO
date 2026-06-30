# Sprint G QA Plan - Architecture Consolidation

Date: 2026-06-30

Sprint G is local architecture consolidation only. It does not close external
gates and does not promote runtime maturity.

## QA Cases

| WP | Area | Evidence Command |
|----|------|------------------|
| WP0 | Current-head governance honesty | `py -3 scripts\validate_alpha_maturity_honesty.py` |
| WP1 | API/gateway shim parity and boundary guards | `py -3 -m pytest tests\unit\architecture -q` |
| WP2 | Direct RuntimeKernel lifecycle integration | `py -3 -m pytest tests\integration\test_runtime_kernel_lifecycle.py tests\integration\test_daemon_worker.py -q` |
| WP3 | Scripted scenario config | `py -3 -m pytest tests\unit\agent\test_scripted_agent_model.py tests\unit\infrastructure\test_scripted_model.py -q` |
| WP4 | Eval runner cleanup and metrics | `py -3 -m pytest tests\eval\test_run_eval.py tests\eval\test_gold_eval.py tests\eval\test_failure_injection.py tests\eval\test_run_eval_metrics.py -q` |
| WP5 | CLI batch mode | `py -3 -m pytest tests\cli\test_cli_batch.py -q` |
| WP6 | Worker metrics | `py -3 -m pytest tests\unit\agent\test_worker.py tests\unit\agent\test_worker_metrics.py tests\contract\test_v1_api.py::test_health_ready_reports_daemon_subsystems -q` |
| WP7 | Streaming document upload | `py -3 -m pytest tests\unit\test_file_upload_service.py tests\unit\test_file_upload_large.py tests\contract\test_document_store.py tests\contract\test_document_large_upload.py -q` |
| WP8 | Docs/evidence closure | `py -3 scripts\validate_docs_links.py`; `py -3 scripts\validate_plan_closure_gate.py --allow-open` |

## Maturity Guard

- `production_ready: false` must remain unchanged.
- `stable_declaration: forbidden` must remain unchanged.
- `level_3_sdk_platform: experimental` must remain unchanged.
- Strict closure gate must remain open until `S017-003`, `W3-live`,
  `AUTH-prod`, and `S017-007` have real completed evidence.
