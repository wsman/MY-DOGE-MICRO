---
title: Compatibility Surfaces Registry
status: active
last_verified: 2026-07-01
governing_adr: docs/architecture/adr-0027-shim-sunset-policy.md
runtime_maturity_impact: none
external_gates_changed: false
---

# Compatibility Surfaces Registry

This registry is the detailed compatibility-surface inventory governed by
[ADR-0027](adr-0027-shim-sunset-policy.md),
[file-structure-policy.md](file-structure-policy.md), and
[module-boundaries.md](module-boundaries.md). It does not create a new policy
source. If this file conflicts with those architecture documents, the ADR and
policy files win and this registry must be corrected.

Sprint H records the current compatibility, legacy, and demo/test surfaces so
new work has a visible canonical destination. This does not remove any brownfield
code, close external gates, update the latest remotely verified SHA, or promote
runtime maturity.

## Surface Registry

| surface | type | owner | canonical_replacement | allowed_behavior | forbidden_behavior | parity_tests | earliest_removal | migration_status | current_count |
|---|---|---|---|---|---|---|---|---|---|
| `doge.application.composition` | `import-shim` | bootstrap | `doge.bootstrap.processes`, `RuntimeContainer`, `GatewayContainer`, `WorkspaceContainer` | Delegate to bootstrap containers, emit tested deprecation warnings, preserve docstrings, keep `refresh_views` as documented legacy utility. | Direct infrastructure adapter imports, new public factories or utilities outside this allowlist, inline SQL/DB construction, `RuntimeKernel` instantiation, tool registration, approval/worker/model-routing behavior. | `test_bootstrap_owns_factories.py`, `test_no_container_cross_build.py`, `test_composition_allowlist.py` | After process-root migration, import parity, migration notes, and rollback plan. | Compatibility facade retained for brownfield imports. | 73 public callables: 72 `build_*` plus `refresh_views`, verified 2026-07-01. |
| `doge.application.agent.tools` | `import-shim` | runtime | `doge.application.tools` | Re-export `ToolRegistry`, `ToolResult`, and `build_default_tool_registry`. | New classes/functions, tool registration, or tool behavior. | `test_runtime_tool_boundary_guards.py`, `test_shim_behavior_guards.py` | After runtime and test import parity evidence. | Thin import compatibility shim. | 3 public symbols, verified 2026-07-01. |
| `doge.interfaces.api.routers` | `import-shim` | gateway | `doge.interfaces.api_legacy.routers` | Re-export legacy local router modules. | Route definitions or endpoint handlers. | Import tests, `test_shim_behavior_guards.py` | After internal and third-party imports migrate. | Legacy router package shim. | 8 legacy router module exports, verified 2026-07-01. |
| `doge.interfaces.api.routers.v1` | `import-shim` | gateway | `doge.interfaces.gateway.routers` | Re-export gateway router modules; `run_stream.py` may additionally re-export `RunStreamHandler`. | APIRouter behavior, route implementations, middleware, models, worker/model/approval logic. | `test_gateway_router_shim_parity.py`, `test_shim_behavior_guards.py` | After gateway import migration and `run_stream.py` exception retirement or documentation. | `/v1` implementation moved to gateway; old module path retained. | 22 Python files: 18 route shims, 3 `_common` helper shims, `__init__.py`, verified 2026-07-01. |
| `doge.interfaces.api_legacy.routers` | `legacy` | gateway | `doge.interfaces.gateway.routers` | Serve legacy `/api/*` routes with deprecation headers. | New platform-only features or default new-work ownership. | Route parity and contract tests. | Not before 2026-09-30 and only after route parity, migration notes, and rollback plan. | Active local loopback compatibility implementation. | 8 router modules, about 32 route decorators, verified 2026-07-01. |
| `src/macro/` | `legacy` | product | `doge.products.research` | Local-first macro analysis modules. | Direct imports from new platform work. | Existing GUI smoke and import guards. | Separate product migration story. | Legacy-maintained local surface. | 6 Python files including `__init__.py`, verified 2026-07-01. |
| `src/micro/` | `legacy` | product | `doge.products.market`, `doge.infrastructure.data_source.tdx_file_scanner` | Local-first market data modules. | Direct imports from new platform work. | Existing import guards. | Separate product migration story. | Legacy-maintained local surface. | 7 Python files including `__init__.py`, verified 2026-07-01. |
| `src/interface/` | `legacy` | ux | Web, SDK, and `/v1` paths | Local PyQt dashboard. | Preferred platform UX ownership. | Manual smoke tests. | Separate support/removal story. | Legacy-maintained local surface. | 5 Python files including `__init__.py`, verified 2026-07-01. |
| `doge.infrastructure.agent.inmemory_runtime` | `demo-test` | runtime | Persisted runtime repositories, durable queue, `PersistedResearchAgentRuntime` | Zero-key demo and deterministic tests without live keys. | Production-facing default or platform path dependency. | `test_inmemory_runtime.py` | After deterministic alternatives exist or a separate support story keeps it. | Demo/test-only runtime adapter. | 1 public runtime class, verified 2026-07-01. |
| `doge.infrastructure.agent.scripted_model` | `demo-test` | runtime | Live model adapters such as `KimiAgentModel` | Offline deterministic tests and demos. | Production default or live path replacement. | Eval and failure-injection tests. | Separate support/removal story. | Demo/test-only scripted model adapter. | 4 public classes, verified 2026-07-01. |

## Composition Allowlist

`doge.application.composition` remains a compatibility facade for brownfield
imports. New platform work should use the relevant bootstrap/process root
instead. Any new public callable in this module must be deliberately added here
and to `tests/unit/architecture/test_composition_allowlist.py`.

### Gateway-backed

- `build_view_repository`
- `build_view_service`
- `build_stock_repository`
- `build_stock_service`
- `build_report_repository`
- `build_schema_browser`
- `build_note_repository`
- `build_stock_name_repository`
- `build_metadata_source`
- `build_ranking_service`
- `build_breadth_service`
- `build_anomaly_service`
- `refresh_views`
- `build_storage_repository`
- `build_tdx_data_source`
- `build_tdx_server_list`
- `build_scan_market_use_case`
- `build_generate_macro_report_use_case`
- `build_secret_provider`
- `build_kimi_agent_model`
- `build_default_text_llm_client`
- `build_file_upload_service`
- `build_page_extraction_service`
- `build_rag_service`
- `build_claim_repository`
- `build_financial_statement_repository`
- `build_company_announcement_repository`
- `build_consensus_estimate_repository`
- `build_industry_classification_source`
- `build_risk_factor_source`
- `build_tool_application_service`
- `build_python_analysis_executor`
- `build_portfolio_service`
- `build_risk_service`
- `build_scenario_service`
- `build_manage_notes_use_case`
- `build_query_ticker_use_case`
- `build_generate_market_overview_use_case`
- `build_generate_anomaly_report_use_case`
- `build_catalog_use_case`
- `build_populate_stock_names_use_case`
- `build_industry_report_use_case`
- `build_generate_industry_report_use_case`

### Runtime-backed

- `build_agent_repositories`
- `build_agent_runtime_kernel`
- `build_runtime_outbox_repository`
- `build_event_subscriber`
- `build_model_router`
- `build_agent_backends`
- `build_research_agent_runtime`
- `build_persisted_research_agent_runtime`
- `build_macro_strategist_agent_use_case`
- `build_industry_analyzer_agent_use_case`
- `build_agent_document_repository`
- `build_agent_evidence_repository`
- `build_agent_run_queue`
- `build_agent_idempotency_store`
- `build_agent_unit_of_work`
- `build_create_session_use_case`
- `build_resume_session_use_case`
- `build_list_sessions_use_case`
- `build_append_turn_use_case`
- `build_default_tool_registry`
- `build_execute_run_use_case`
- `build_resume_run_use_case`
- `build_get_run_snapshot_use_case`
- `build_run_summary_use_case`
- `build_capability_registry_use_case`

### Workspace-backed

- `build_portfolio_repository`
- `build_platform_repository`
- `build_enterprise_governance_repository`
- `build_research_case_service`
- `build_workflow_service`

## Maturity Posture

Sprint H does not change runtime maturity:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

External/operator gates remain open unless separate completed evidence closes
them:

- `S017-003`
- `W3-live`
- `AUTH-prod`
- `S017-007`
