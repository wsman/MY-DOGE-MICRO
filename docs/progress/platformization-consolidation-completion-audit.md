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
| F: Web navigation | Complete | `docs/archive/audits/platformization-consolidation-phase-f-web-2026-06-23.md`, `web/src/App.vue`, `web/src/router/index.ts`, `web/src/views/DomainLandingView.vue` |
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

- ADR-0015 through ADR-0020 remain Proposed.
- ADR-0021 is Accepted and records the eight-context target boundary.
- ADR-0022 is Accepted and records facade-first restructuring while blocking broad physical moves
  until story-level compatibility, rollback, and removal gates pass.
- ADR-0021 and ADR-0022 were promoted to Accepted in the governance closure
  pass recorded at `docs/archive/audits/adr-0021-0022-review-2026-06-23.md`.
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

## Governance Closure - 2026-06-23

The follow-up governance closure plan
`C:\Users\Aby\.claude\plans\alpha-foamy-bird.md` closed the local
architecture-governance gaps for ADR-0021/0022 and recorded exact-SHA remote CI
evidence for baseline HEAD `0058c5c`.

| Item | Status | Evidence |
|---|---|---|
| ADR-0021 disposition | Accepted | `docs/archive/audits/adr-0021-0022-review-2026-06-23.md`, `docs/architecture/adr-0021-bounded-context-consolidation.md` |
| ADR-0022 disposition | Accepted | `docs/archive/audits/adr-0021-0022-review-2026-06-23.md`, `docs/architecture/adr-0022-directory-restructuring.md` |
| Remote CI for `0058c5c` | Passed | `production/qa/evidence/ci/remote-ci-0058c5c.json`, `docs/progress/remote-ci-evidence-0058c5c.md`, GitHub Actions run `28016915874` |
| Feature flag lifecycle plan | Complete | `docs/archive/audits/feature-flag-deprecation-plan-2026-06-23.md`, `src/doge/config/settings.py`, `web/src/config/features.ts` |
| Feature defaults | Updated after this audit | The four backend platformization feature flags remain default-off. `VITE_DOGE_FEATURE_PLATFORM_SHELL` was defaultized in `docs/archive/audits/platform-shell-defaultization-2026-06-24.md` with rollback via `VITE_DOGE_FEATURE_PLATFORM_SHELL=0`. |
| External gates | Still open | `docs/archive/audits/external-gate-next-actions-2026-06-23.md` remains 5 open / 1 passed. |

Additional local verification from the governance closure pass:

```text
governance ADR tests: 33 passed, 2 skipped
layer and architecture tests: 76 passed, 1 warning
contract tests: 51 passed
runtime/tool/capability tests: 57 passed
feature lifecycle/API tests: 38 passed
web targeted tests: 3 files / 9 tests passed
web full tests: 15 files / 87 tests passed
web build: passed
TypeScript SDK tests/build: 13 passed; build passed
full Python regression: 1340 passed, 9 skipped, 11 warnings
eval smoke: 7 passed
```

This closure does not claim Beta, GA, Stable, enterprise production readiness,
or external gate completion. Any post-closure commit requires its own exact-SHA
remote CI evidence before that newer SHA can be called remotely verified.

## Post-Closure SHA Probe - 2026-06-24

The follow-on remediation plan
`C:\Users\Aby\.claude\plans\my-doge-micro-2026-swift-frost.md` checked the
newer main-branch target SHA:

```text
625285f067b21a4ee8aa36e83b4565a5fa57bac6
```

Remote CI evidence was fetched to:

```text
production/qa/evidence/ci/remote-ci-625285f.json
```

This evidence does **not** close the remote-CI gate for `625285f`. GitHub
Actions run `28089385791` completed with conclusion `failure` in the Python
checks job. The failing job was caused by the
`validate_piped_donut_pre_remote_ci_package.py` validator attempting to read an
operator-local plan path that is absent in Linux CI:

```text
C:\Users\Aby\.claude\plans\my-doge-micro-main-2ffdb66-piped-donut.md
```

This is tracked as a Phase 0 remediation item. The project still must capture a
future exact-SHA successful remote CI run before any newer SHA is called
remotely verified.

## Swift-Frost Local Remediation Pass - 2026-06-24

The same follow-on plan applied local remediation for the failed CI root cause,
the first boundary-hardening items, and the first physical-modularization
slices. This section is local evidence only; it does not convert the failed
`625285f` remote CI run into a pass.

Implemented locally:

- `scripts/validate_piped_donut_pre_remote_ci_package.py` now has a repository
  fallback for the external operator-local piped-donut plan path that is absent
  on Linux CI workers.
- `doged status` now reads the configured daemon port and also accepts a
  `--port` override, matching `doged serve` behavior.
- README secrets/config documentation now reflects the Kimi default path
  (`DOGE_TEXT_LLM_PROVIDER=kimi`, `MOONSHOT_API_KEY`) and the retained DeepSeek
  fallback.
- `IResearchAgentRuntime`, `RuntimeKernel`, the persisted runtime adapter, v1
  run routes, workspace services, worker user-triggered operations, run summary,
  in-memory repositories, and `ModelRouter` now propagate first-class
  `TenantScope` through tenant-scoped run/event/artifact/approval/document reads
  and mutations. Legacy runtime call signatures remain as temporary migration
  shims.
- Tool and runtime failures now use `SafeError` event payloads with stable
  public code/message/reference fields; legacy public `error`/`message` strings
  are retained for SDK and SSE compatibility, but raw provider/runtime exception
  text no longer enters persisted runtime events.
- `tests/unit/architecture/test_context_dependency_graph.py` adds an AST-level
  dependency gate for platform-runtime/product/entrypoint import boundaries.
- `RuntimeContainer` now owns runtime persistence leaf factories; the former
  `doge.application.composition` compatibility functions were removed in
  Sprint M after consumers migrated to bootstrap containers.
- `RuntimeContainer` now also owns session use-case factories, and the
  migrated `session`/`run` CLI runtime paths plus `/v1/tools` registry lookup use
  bootstrap containers instead of direct legacy composition imports.
- `doge.application.__init__` now lazily resolves compatibility factory
  re-exports so application submodule imports no longer eagerly import the
  legacy mega composition root, which Sprint M later removed.
- `WorkspaceContainer` now owns portfolio/platform/governance repository
  wiring and case/workflow service wiring; `case` and `template` CLI commands
  use that workspace container.
- `GatewayContainer` now owns read-side service/repository wiring, secret
  providers, macro/industry compatibility report wiring, scan/file-upload
  factories, local RAG, and claim repositories; the former legacy composition
  functions were removed in Sprint M after callers migrated.
- Stock/RSRS/breadth/anomaly/macro/demo CLI commands, scan API helpers, and MCP
  query/workspace tools now use bootstrap containers rather than direct legacy
  composition imports.
- `CaseAssetService` and `CaseDecisionService` now own asset-link and
  decision behavior directly; `ResearchCaseService` delegates those operations
  while retaining the public facade.
- `AgentRun.workflow_context` is now first-class and persisted in SQLite;
  workflow-template run requests populate it directly while old
  `ModelPolicy.extra` template metadata remains a compatibility fallback.
- Default tool descriptors now live on the market, portfolio, research,
  fundamental, quant, compliance, and publishing providers; the root default
  registry only aggregates provider-owned descriptors through
  `ToolApplicationService`.
- `DOGE_PROCESS_ROLE` now supports `api`, `worker`, and `all`; `doged serve`
  respects the role, `doged-api`/`doged-worker` console scripts are exposed,
  independent workers poll the durable SQLite queue, and `/health/ready`
  reports database, migration, queue, worker, outbox, document-storage, and
  model-provider checks.
- Python SDK resources now live in `session.py`, `run.py`, `document.py`, and
  `platform.py`; `DogeClient` and `AsyncDogeClient` remain thin aggregators.
- TypeScript SDK resources now live in `session.ts`, `run.ts`, `document.ts`,
  and `platform.ts`; Web imports the `doge-sdk` package and no longer aliases
  or includes `packages/doge-sdk-typescript/src` directly.
- The frontend CI job now tests/builds the TypeScript SDK before Web
  tests/build so package `dist` exists before Web consumes `doge-sdk`.

Local verification:

```text
runtime/use-case TenantScope regression: 42 passed
API/CLI TenantScope contract regression: 40 passed
runtime/tool SafeError regression: 47 passed
architecture and layer gates: 92 passed, 1 warning
contract/API/CLI regression: 48 passed
bootstrap ownership slice: 14 passed
workspace asset/decision split: 33 passed
workflow context independence: 36 passed
workflow/template/platform compatibility: 132 passed
tool provider registration split: 39 passed
daemon role/readiness split: 52 passed
daemon SSE/CLI compatibility: 15 passed
Python SDK resource split: 16 passed
gateway/API/CLI bootstrap migration slice: 107 passed, 1 skipped
MCP bootstrap migration slice: 92 passed, 1 skipped
application lazy composition compatibility slice: 117 passed
full Python regression: 1477 passed, 9 skipped, 11 warnings
Web SDK source-coupling scan: no relative SDK source imports or source aliases
TypeScript SDK tests/build: 14 passed; tsc build passed using temporary Node v24.16.0 / npm 11.13.0 from nodejs-wheel
Web tests/build: 15 files / 91 tests passed; vue-tsc and Vite build passed using temporary Node v24.16.0 / npm 11.13.0 from nodejs-wheel
governance YAML shape: passed (5 files, 0 findings)
git diff --check: no whitespace errors
plan closure gate --allow-open: open as expected (5 controlled external gates, 1 passed)
```

Remote-CI status remains open. The next commit that contains these local fixes
must receive its own successful exact-SHA GitHub Actions evidence before the
remote-CI release gate can be closed.
