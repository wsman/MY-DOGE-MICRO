# Structure Convergence Report Response

Date: 2026-07-02

Source prompt: external structure/modularization report reviewed against source
HEAD `59f6e4f` (`chore(governance): close Sprint M compatibility registry`).

## Verdict

The external report is useful as a convergence prompt, but several findings are
stale after Sprint M. The remaining local structure-convergence work is now
closed: docs reconciliation, tool-service split, API app factory extraction, and
SDK/web run typing are implemented and locally verified.

This response does not change runtime maturity:

```text
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## Classification

| Recommendation | Current repo finding | Status | Evidence | Follow-up |
|---|---|---|---|---|
| Reconcile stale API auth and route wording | `docs/API.md` now describes `local_demo`, `enterprise`, and remote non-loopback bind gates; route wording uses HTTP routes and preserves 88 = 34 legacy `/api/*` + 54 daemon/v1 and health routes. | done | `docs/API.md`; `src/doge/config/settings.py`; `src/doge/interfaces/api/main.py` | Keep active-doc grep empty for `Auth \| None`, `Neither exists today`, and `88 product routes`. |
| Converge active route terminology outside archive/import snapshots | Active API references, architecture traceability, ADR-0007, registries, TR registry, CDD route notes, and runtime-maturity evidence now use `88 HTTP routes` instead of `88 product routes`. | done | `docs/reference/http-api.md`; `docs/reference/api.md`; `docs/architecture/architecture-traceability.md`; `docs/architecture/adr-0007-api-surface-and-cors.md`; `docs/registry/architecture.yaml`; `docs/registry/entities.yaml`; `docs/architecture/tr-registry.yaml`; `design/cdd/fastapi-service.md`; `docs/progress/runtime-maturity.yaml` | Preserve archive/import historical text. |
| Clarify four product modules versus eight bounded contexts | `docs/architecture/overview.md` now explains that `doge.products.market`, `portfolio`, `research`, and `quant` are source ownership product modules, while the eight bounded contexts are the internal governance map. | done | `docs/architecture/overview.md`; `README.md`; `docs/product/modules.md` | Keep reader docs pointing to the architecture overview for count reconciliation. |
| Compress reader paths to three quick-starts and five user scenarios | README now highlights `doge session`, `doged serve`, and SDK + `/v1`; `docs/index.md` and `docs/product/user-scenarios.md` now expose Local Analyst, Daemon Operator, SDK Integrator, Research Workspace, and Eval/Demo Owner paths. | done | `README.md`; `docs/index.md`; `docs/product/user-scenarios.md`; `docs/start-here/research-workspace.md`; `docs/start-here/eval-demo-owner.md` | Keep demo, uvicorn, Vue, and MCP setup as secondary references rather than primary quick-start commands. |
| Add source layout placement guide without creating a second authority | `docs/architecture/source-layout-map.md` gives a thin placement map and points back to the existing file-structure, module-boundary, and module-ownership authorities. | done | `docs/architecture/source-layout-map.md`; `docs/architecture/index.md`; `docs/index.md` | Keep placement decisions tied to the existing authority docs. |
| Move providers to product owners | Provider compatibility concerns from the report are stale after Sprint M. Tool providers now live under product/governance ownership instead of the retired compatibility locations. | stale | `546ce7f`; `79baad8`; `tests/unit/architecture/test_tool_provider_ownership.py` | Preserve ownership gates; do not reopen removed compatibility paths. |
| Retire obsolete macro/micro and composition roots | The report's warning about legacy roots is stale for the removed Sprint M surfaces. `src/macro`, `src/micro`, `doge.application.composition`, and compatibility shims were retired. | stale | `e14f388`; `0aabae5`; `985bab6`; `59f6e4f` | Use import gates for regressions instead of documenting deleted roots as active architecture. |
| Retire PyQt dashboard as a platform surface | The former PyQt desktop dashboard is no longer an active platform stack. | stale | `5cf5664`; `README.md` | Treat Web, SDK, daemon, CLI, and MCP as current delivery surfaces. |
| Split `ToolApplicationService` into registry factory, execution service, and compatibility facade | `ToolApplicationService` is now a compatibility facade over `ToolExecutionService`; provider-owner imports moved to `registry_factory.py`. | done | `src/doge/application/agent/tool_service.py`; `src/doge/application/tools/execution_service.py`; `src/doge/application/tools/registry_factory.py`; `tests/unit/layer_gates/test_new_code_imports.py` | Keep provider-owner imports out of the facade and preserve the public import path. |
| Split import-time API app assembly from `src/doge/interfaces/api/main.py` | `main.py` is now a compatibility shim over `create_app()`, while auth, lifespan, middleware, errors, routes, and startup gates live in focused modules. | done | `src/doge/interfaces/api/main.py`; `src/doge/interfaces/api/app_factory.py`; `src/doge/interfaces/api/auth.py`; `src/doge/interfaces/api/lifespan.py`; `src/doge/interfaces/api/routes.py`; `src/doge/interfaces/api/startup_gates.py` | Keep `doge.interfaces.api.main:app` and private compatibility exports intact for daemon/tests. |
| Tighten TypeScript SDK run lifecycle types and migrate web client casts | SDK run lifecycle methods now return `AgentRun`; web agent API imports SDK run types and no longer casts through `as unknown as AgentRun`. | done | `packages/doge-sdk-typescript/src/run.ts`; `packages/doge-sdk-typescript/src/client.ts`; `web/src/api/agent.ts`; `web/src/views/ResearchAgentView.spec.ts` | Keep SDK/web types aligned with serialized `AgentRun` fields. |
| Extend import-boundary gates for legacy and demo-only runtime paths | Production code is blocked from importing `doge.interfaces.api_legacy` or `doge.infrastructure.agent.inmemory_runtime` outside explicit allowlists for legacy route mounting/shims, `api_legacy` itself, and gated demo fallback factories. | done | `scripts/validate_import_boundaries.py`; `tests/unit/governance/test_import_boundaries.py`; `docs/architecture/source-layout-map.md` | Keep exceptions explicit and narrow. |
| Close external/operator gates from structure convergence work | Deferred by design. Structure convergence does not close live/provider/release gates or promote runtime maturity. | deferred | S017-003; W3-live; AUTH-prod; S017-007; `docs/progress/runtime-maturity.yaml` | Keep these gates open until operator evidence and strict validators pass. |

## Sprint M SHA Evidence

The reviewed baseline includes the following local Sprint M convergence commits:

| SHA | Evidence |
|---|---|
| `5a52465` | Relocated governance and reader documentation. |
| `6be51db` | Split HTTP API contracts from the route reference. |
| `e14f388` | Removed retired legacy import roots. |
| `546ce7f` | Moved tool providers to product owners. |
| `be18ba2` | Failed closed for non-demo runtime fallback. |
| `87679c5` | Added module ownership and compatibility trend gates. |
| `79baad8` | Removed provider compatibility shims. |
| `5cf5664` | Retired the legacy PyQt dashboard surface. |
| `0aabae5` | Retired `src/macro` and `src/micro`. |
| `985bab6` | Removed bootstrap and tool compatibility shims. |
| `59f6e4f` | Closed the Sprint M compatibility registry. |

## Module And Import Gates

The convergence posture is guarded by existing tests and scripts:

- `tests/unit/architecture/test_tool_provider_ownership.py`
- `tests/unit/layer_gates/test_new_code_imports.py`
- `tests/unit/governance/test_import_boundaries.py`
- `scripts/validate_import_boundaries.py`

These gates should remain the authority for preventing new provider ownership
drift or new imports from retired roots.

## Local Verification

This local response was verified with the focused Structure Convergence gate:

- `py -3 -m pytest tests\unit\interfaces\test_api_auth_startup.py tests\unit\layer_gates\test_new_code_imports.py tests\unit\architecture\test_tool_provider_ownership.py tests\unit\architecture\test_context_dependency_graph.py tests\unit\governance\test_import_boundaries.py tests\unit\layer_gates\test_web_no_legacy_api.py tests\contract\test_api_doc_route_coverage.py -q` -> 47 passed, 2 warnings.
- `py -3 scripts\validate_import_boundaries.py` -> passed.
- `py -3 scripts\validate_alpha_maturity_honesty.py` -> passed.
- `py -3 scripts\validate_governance_yaml_shape.py` -> passed.
- `py -3 scripts\validate_docs_links.py` -> validated 85 markdown files.
- `cd packages\doge-sdk-typescript && npm test -- --run && npm run build` -> 16 tests passed and TypeScript build passed.
- `cd web && npm test -- --run src/views/ResearchAgentView.spec.ts` -> 2 tests passed.
- `git diff --check` -> passed.
- Active-doc grep for `88 product routes`, `Auth | None`, and `Neither exists today` -> empty.

## External Gates Preserved

The following gates remain open or operator-owned. This response must not rename
local evidence as closure evidence for them:

- S017-003: provider approval, license scope, and approved real provider fixture
  storage remain external/operator gated.
- W3-live: analyst benchmark execution still requires real materials, human
  labels, approved thresholds, redacted live observations, and strict validator
  closure.
- AUTH-prod: enterprise production authentication/IdP/JWKS validation remains
  production-environment evidence, not local docs evidence.
- S017-007: SDK registry publication, release approval, and registry-backed
  consumer smoke remain external release gates.
