# Architecture And Enterprise Closure

Generated: 2026-06-21

## Wave 4-A Scope

This note records the first Wave 4 architecture cleanup pass from
`C:\Users\Aby\.claude\plans\9b77f9c-kimi-twinkly-map.md`.

## Service Locator Removal

`ToolApplicationService` no longer imports `doge.application.composition`
inside tool methods. Tool dependencies are now constructor-injected, and the
composition root owns the default wiring.

Changed boundary:

- `src/doge/application/agent/tool_service.py` contains only application tool
  orchestration and dependency accessors.
- `src/doge/application/composition.py` owns
  `build_tool_application_service()` and `build_default_tool_registry()`.
- `src/doge/application/agent/tools.py` accepts an injected
  `ToolApplicationService` while preserving the existing registry/schema
  surface.
- API, CLI, and MCP paths use composition-owned tool-service wiring.

## Verification

| Check | Result | Notes |
|---|---:|---|
| `.\.venv\Scripts\python.exe -m py_compile src\doge\application\agent\tool_service.py src\doge\application\agent\tools.py src\doge\application\composition.py src\doge\interfaces\api\routers\v1\tools.py` | PASS | Tool service, registry, composition, and v1 tools route compile. |
| `.\.venv\Scripts\python.exe -m pytest tests\unit\agent\test_tool_service.py tests\unit\agent\test_tool_registry.py -q` | PASS | `14 passed`; tests cover injection, connector delegation, registry schema, and no composition import in `tool_service.py`. |
| `.\.venv\Scripts\python.exe -m pytest tests\unit\agent\test_tool_service.py tests\unit\agent\test_tool_registry.py tests\test_mcp_tools.py tests\unit\layer_gates\test_composition_root_location.py tests\unit\layer_gates\test_api_layer_gate.py -q` | PASS | `97 passed`; covers the broader tool/MCP/layer-gate surface after injection. |
| `rg -n "from doge\.application import composition\|doge\.application\.composition\|application\.composition" src\doge\application\agent\tool_service.py` | PASS | No matches. |

## TDX Helper Migration

`TDXDataSource` no longer imports server-download helpers from the legacy
downloader. The infrastructure layer now owns the helper functions it needs:

- `src/doge/infrastructure/data_source/tdx_helpers.py`
- `find_working_server`
- `ticker_to_market_code`
- `bars_to_df`
- `get_latest_market_date`

`tests/unit/layer_gates/test_no_micro_under_doge.py` no longer allowlists
`infrastructure/data_source/tdx.py`; the only remaining `micro.*` allowlist
entry under `src/doge` is the SQLite storage bridge.

Verification:

| Check | Result | Notes |
|---|---:|---|
| `.\.venv\Scripts\python.exe -m py_compile src\doge\infrastructure\data_source\tdx.py src\doge\infrastructure\data_source\tdx_helpers.py tests\test_tdx_adapter.py tests\unit\infrastructure\test_tdx_helpers.py tests\unit\layer_gates\test_no_micro_under_doge.py` | PASS | Adapter, helpers, and migration gates compile. |
| `.\.venv\Scripts\python.exe -m pytest tests\test_tdx_adapter.py tests\unit\infrastructure\test_tdx_helpers.py tests\unit\layer_gates\test_no_micro_under_doge.py tests\unit\layer_gates\test_forbidden_pattern_grep_gate.py tests\unit\infrastructure\test_tdx_server_list.py -q` | PASS | `52 passed`; covers TDX adapter behavior, helper behavior, optional opentdx degradation, server-list adapter, and micro-import gate. |

## Research Path Boundary

Macro and industry research paths are now labeled explicitly:

- `GenerateMacroReportUseCase`: `compatibility_text_llm_report`
- `GenerateIndustryReportUseCase`: `compatibility_report_tool`
- `MacroStrategistAgentUseCase`: `runtime_research_copilot`
- `IndustryAnalyzerAgentUseCase`: `runtime_research_copilot`

Call graph and ownership notes are captured in
`docs/progress/research-use-case-call-graph.md`.

## Kimi Agent SDK Semantic Adapter

The non-direct backend path now passes runtime routing context into
`IAgentBackend` instead of reducing the SDK call to a plain prompt only.
`KimiAgentSdkBackend` builds a structured prompt request containing:

- serialized MY-DOGE messages, including multimodal content parts;
- visible tool schemas, tool choice, max token budget, and selected model;
- request metadata such as run/session/profile context and prompt cache key;
- SDK event metadata for raw trace preservation.

The adapter also maps SDK-style events back into provider-neutral
`AgentResponse` records with richer semantics:

- approval requests become the existing `request_approval` tool call shape;
- tool call IDs, function names, and arguments are preserved when exposed;
- reasoning content, usage, finish reason, and `tool_call_id` are retained;
- unsupported SDK prompt kwargs are filtered by inspecting the installed SDK
  `prompt` signature.

This is still not a live production certification of the Kimi Agent SDK. The
remaining external verification is a real SDK smoke run covering native
session state, tool execution, approvals, and multimodal file events.

Verification:

| Check | Result | Notes |
|---|---:|---|
| `.\.venv\Scripts\python.exe -m py_compile src\doge\core\ports\agent_backend.py src\doge\application\agent\runtime_kernel.py src\doge\infrastructure\agent\backends.py src\doge\infrastructure\agent\kimi_sdk_adapter.py tests\unit\agent\test_backends.py` | PASS | Backend port, runtime handoff, SDK backend, adapter, and tests compile. |
| `.\.venv\Scripts\python.exe -m pytest tests\unit\agent\test_backends.py -q` | PASS | `8 passed`; covers structured prompt kwargs, approval mapping, tool call IDs, reasoning, usage, and finish reason. |
| `.\.venv\Scripts\python.exe -m pytest tests\unit\agent\test_backends.py tests\unit\agent\test_kimi_sdk_adapter.py tests\unit\agent\test_runtime_kernel.py tests\unit\agent\test_inmemory_runtime.py tests\unit\agent\test_model_router.py tests\contract\test_agent_router.py tests\integration\test_agent_sse_stream.py -q` | PASS | `37 passed`; covers broader backend/runtime/router/SSE behavior after the port signature change. |

## Enterprise Identity Design Coverage

ADR/CDD coverage now exists for the enterprise identity gap without promoting
the implementation to production-ready:

- `docs/architecture/adr-0015-enterprise-identity-and-access.md` defines the
  local demo versus enterprise auth boundary.
- `design/cdd/fastapi-service.md` now requires OIDC/JWT validation before
  trusting tenant/user headers in enterprise mode.
- `design/cdd/research-copilot-agent-runtime.md` requires trusted
  `EnterpriseContext` propagation into runs, tools, approvals, model metadata,
  and audit events.
- `design/cdd/document-evidence-pipeline.md` requires tenant ACL filtering for
  document APIs, RAG, evidence lookup, and citation drill-down.
- `design/cdd/sdk-daemon-client-interfaces.md` requires bearer-token
  pass-through, request correlation, auth error handling, and token redaction.
- `docs/architecture/tr-registry.yaml` adds TR-055 through TR-058 for these
  enterprise identity requirements.

This remains a design gate only. OIDC/JWT middleware, persistent ACLs,
approval/audit actor storage, secrets handling, and remote-bind auth tests are
still implementation blockers.

Verification:

| Check | Result | Notes |
|---|---:|---|
| `.\.venv\Scripts\python.exe -m pytest tests\unit\governance\test_adr_lifecycle_status.py -q` | PASS | `3 passed, 2 skipped`; ADR-0015 uses a legal Proposed status. |
| YAML shape check for `docs/progress/runtime-maturity.yaml`, `production/sprint-status.yaml`, `docs/registry/architecture.yaml`, and `docs/architecture/tr-registry.yaml` | PASS | No tabs or odd indentation detected. Full YAML parse was not run because `PyYAML` is not installed in this venv. |
| `.\.venv\Scripts\python.exe -m pytest tests\contract\test_v1_api.py tests\unit\infrastructure\test_financial_connectors.py tests\unit\agent\test_tool_service.py tests\unit\agent\test_tool_registry.py tests\unit\test_portfolio_service.py tests\eval\test_gold_eval.py tests\eval\test_run_eval.py tests\eval\test_failure_injection.py tests\test_tdx_adapter.py tests\unit\infrastructure\test_tdx_helpers.py tests\unit\layer_gates\test_no_micro_under_doge.py tests\unit\application\test_research_path_boundaries.py tests\unit\agent\test_backends.py tests\unit\agent\test_kimi_sdk_adapter.py tests\unit\agent\test_runtime_kernel.py tests\unit\agent\test_inmemory_runtime.py tests\unit\agent\test_model_router.py tests\contract\test_agent_router.py tests\integration\test_agent_sse_stream.py tests\unit\governance\test_adr_lifecycle_status.py -q` | PASS | `106 passed, 2 skipped`; cross-wave backend/runtime/eval/governance regression. |

## Sprint 016 Closure Update

Sprint 016 is closed for local implementation. Browser/Node verification,
live Kimi execution, real provider fixture approval, and enterprise auth
implementation are transferred to
`production/sprints/sprint-017-external-validation-and-provider-hardening.md`.

Additional closure evidence:

| Check | Result | Notes |
|---|---:|---|
| `.\.venv\Scripts\python.exe -m pytest tests\live\test_kimi_live_smoke.py tests\unit\infrastructure\test_financial_provider_fixture_contract.py -q` | PASS | `1 passed, 4 skipped`; live Kimi tests skipped by env gates. |
| S016 targeted cross-wave regression including live-smoke skips | PASS | `120 passed, 6 skipped in 25.32s`. |
| `git diff --check` | PASS | No whitespace errors; LF/CRLF warnings only. |
| Governance YAML shape check | PASS | No tabs or CR-only lines in runtime maturity, sprint status, architecture registry, or TR registry. Full parse was not run because `PyYAML` is not installed in this venv. |

## Still Open In Wave 4

- Kimi Agent SDK adapter still needs a live SDK smoke run for native
  session/tool/approval/multimodal behavior.
- Enterprise auth still needs implementation of OIDC/JWT, tenant isolation,
  persistent ACL, approval actor, audit actor, and secrets handling.
- Governance files have been synchronized to Sprint 016/runtime maturity/module
  index scope, but a fresh independent architecture review remains required
  before promotion.
