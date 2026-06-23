# Platformization Consolidation Completion Audit

Date: 2026-06-23
Source plan: `C:\Users\Aby\.claude\plans\d91dc3b-python-typescript-sdk-federated-bird.md`

## Verdict

Local architecture consolidation is complete for the approved scope.

This audit does not close external release gates and does not promote runtime
maturity. The project remains:

```text
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## Phase Status

| Phase | Status | Evidence |
| --- | --- | --- |
| Baseline | Complete | `docs/progress/platformization-consolidation-baseline.md` |
| A: Bounded contexts | Complete | `design/cdd/module-index.md`, `design/cdd/bc-*.md`, `docs/architecture/adr-0021-bounded-context-consolidation.md`, `docs/architecture/adr-0022-directory-restructuring.md` |
| B: Facade packages | Complete | `src/doge/platform/*`, `src/doge/products/*`, `src/doge/shared`, `src/doge/adapters`, `src/doge/entrypoints`, `src/doge/bootstrap` |
| C: Tool provider registry | Complete | `src/doge/application/agent/tool_service.py`, `src/doge/application/composition.py`, `tests/unit/agent/test_tool_service_facade.py` |
| D: Platform services | Complete | `src/doge/platform/workspace/service.py`, `src/doge/interfaces/api/routers/v1/platform.py`, `tests/unit/architecture/test_platform_router_delegation.py` |
| E: Runtime split | Complete | `src/doge/platform/runtime/services.py`, `src/doge/application/agent/runtime_kernel.py`, `tests/unit/architecture/test_runtime_kernel_split.py` |
| F: Web navigation | Complete | `docs/progress/platformization-consolidation-phase-f-web-2026-06-23.md`, `web/src/App.vue`, `web/src/router/index.ts`, `web/src/views/DomainLandingView.vue` |
| G: Delivery channels | Complete locally | SDK, CLI, MCP, transport, Web, API, and package checks passed locally; registry publication remains externally blocked |
| H: Governance closure | Complete | This audit plus the governance checks listed below |

## Module Count

The authoritative counted module set is now the eight bounded contexts in
`design/cdd/module-index.md`:

```text
Market Intelligence
Research
Portfolio & Risk
Quant & Data Lab
Workspace & Workflow
Agent Runtime
Knowledge & Evidence
Governance & Evaluation
```

Delivery channels and adapters are no longer counted as product modules:

```text
API, Web, CLI, daemon, SDK, MCP, PyQt, SQLite, DuckDB, Kimi, TDX, yfinance
```

The former 20-module inventory is retained as appendix/historical mapping only.

## Architecture State

- ADR-0015 through ADR-0022 remain Proposed.
- ADR-0021 records the eight-context target boundary.
- ADR-0022 records facade-first restructuring and blocks broad physical moves
  until architecture review accepts or revises the target package layout.
- No ADR was promoted to Accepted in this consolidation pass.
- `docs/architecture/control-manifest.md` records bounded-context import rules,
  compatibility rules, and deprecation requirements.

## TR Registry Policy

TR IDs remain permanent and append-only. Removed requirements must become
`deprecated`; replaced requirements must become `superseded-by: TR-NNN`. This
consolidation did not renumber existing TR IDs.

## Feature Flag Status

Existing platformization feature flags remain explicit compatibility controls:

```text
DOGE_FEATURE_RUN_SUMMARY_API
DOGE_FEATURE_PLATFORM_OBJECTS
DOGE_FEATURE_WORKFLOW_TEMPLATES
DOGE_FEATURE_CAPABILITY_REGISTRY
VITE_DOGE_FEATURE_PLATFORM_SHELL
```

The tool service's `use_capability_providers` constructor argument is retained
for source compatibility, but provider registry execution is now the only local
tool execution path.

Feature flags must not be removed until direct compatibility tests and rollback
criteria are updated in the relevant story.

## Web Navigation Note

Phase F satisfied the behavioral exit criteria by consolidating the existing
App shell around product-domain entries and adding reusable domain landing
views. A dedicated `PlatformShell.vue` / `NavSidebar.vue` extraction was not
introduced because it would be a structural refactor without additional user
behavior in this pass.

Legacy routes remain direct and tested:

```text
/research-agent
/scanner
/cn-archive
/us-archive
/insights
/analysis
```

`/research-agent` remains a compatibility entry and is treated as the Research
Case execution surface, not as a separate product domain.

## Verification

Commands passed locally on 2026-06-23.

```text
web> npm test
web> npm run build
```

Result:

```text
14 Web test files passed, 84 tests passed.
vue-tsc and Vite production build passed.
```

```text
.\.venv\Scripts\python.exe -m pytest tests/unit/architecture tests/unit/layer_gates tests/unit/governance/test_s017_planning_docs.py tests/unit/governance/test_adr_lifecycle_status.py -q
```

Result:

```text
109 passed, 2 skipped, 1 warning.
```

```text
.\.venv\Scripts\python.exe -m pytest tests/unit/agent/test_runtime_kernel.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_service_facade.py tests/unit/agent/test_tool_registry.py tests/unit/capabilities -q
```

Result:

```text
52 passed.
```

```text
.\.venv\Scripts\python.exe -m pytest tests/contract/test_platform_api.py tests/contract/test_run_summary_api.py tests/contract/test_v1_api.py tests/contract/test_agent_router.py tests/contract/test_enterprise_acl_api.py tests/integration/test_multimodal_chat.py -q
```

Result:

```text
37 passed.
```

```text
.\.venv\Scripts\python.exe -m pytest tests/contract/test_python_sdk.py tests/cli tests/test_mcp_tools.py tests/test_transport.py -q
```

Result:

```text
177 passed, 1 skipped, 2 warnings.
```

```text
packages/doge-sdk-typescript> npm test
packages/doge-sdk-typescript> npm run build
packages/doge-sdk-python> ..\..\.venv\Scripts\python.exe -m build
```

Result:

```text
TypeScript SDK: 13 tests passed; build passed.
Python SDK: sdist and wheel built.
```

Environment note: the local `.venv` initially lacked the PEP 517 front-end
package `build`; it was installed into `.venv` before rerunning the Python SDK
package build.

## Residual Risks

- Dedicated Web layout extraction remains optional follow-up work; the current
  shell behavior is centralized but still lives in `App.vue`.
- Physical source moves remain blocked until ADR-0022 is accepted or a specific
  story explicitly scopes compatibility exports and rollback evidence.
- Legacy routes remain intentionally available and must not be removed without a
  deprecation story.
- ADR-0015 enterprise identity is still Proposed; non-loopback or hosted claims
  remain blocked by enterprise validation gates.
- SDK registry publication remains blocked until registry ownership, release
  approval, version/changelog approval, and registry-backed consumer smoke pass.

## External Gates Still Open

This consolidation does not close:

- Live Kimi Text/Files/Vision/Agent SDK verification.
- Formal financial data provider approval and licensed adapter implementation.
- Analyst-labeled benchmark quality baseline and trend history.
- Enterprise production validation against approved IdP, secret store, remote
  bind, SIEM/WORM sink, and data-isolation environment.
- SDK registry publication approval and registry-backed consumer smoke.

## Close Statement

The local target is now in place:

```text
one product object model
eight bounded contexts
one Agent Runtime coordinator with focused execution services
one Capability Provider Registry execution path
multiple delivery channels with compatibility tests
```

Release maturity remains controlled by the external gates above.
