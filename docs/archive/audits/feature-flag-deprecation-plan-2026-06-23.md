# Feature Flag Deprecation Plan - 2026-06-23

## Verdict

The four backend platformization feature flags remain default-off in this
phase. The Web platform shell flag was defaultized separately on 2026-06-24
after case-workspace browser and accessibility-tree evidence was captured.

This plan records lifecycle metadata, target defaultization order, rollback
criteria, and removal gates. It does not remove compatibility routes, SDK
methods, CLI commands, MCP tools, or the direct `/research-agent` route.

Required maturity posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## Lifecycle Table

| Order | Flag | Current default | Target default-on | Target removal | Gating conditions | Rollback criteria | Consumer impact |
|---|---|---:|---|---|---|---|---|
| 1 | `DOGE_FEATURE_CAPABILITY_REGISTRY` / `settings.features.capability_registry` | `False` | First defaultization candidate after ADR-0019 review and capability regressions are green. | One release cycle after default-on with approved provider-registry compatibility removal story. | `tests/unit/use_cases/test_capability_registry.py`, `tests/contract/test_platform_api.py`, and `tests/unit/capabilities/` pass; capability metadata remains redacted; provider-backed execution parity remains green. | Restore default `False` if capability discovery, redaction, or provider parity regresses. | `/v1/capabilities` becomes always available after default-on; callers no longer need the opt-in env var. |
| 2 | `DOGE_FEATURE_PLATFORM_OBJECTS` / `settings.features.platform_objects` | `False` | After ADR-0016 evidence and platform object contract regressions are green. | One release cycle after default-on with approved legacy workspace compatibility removal story. | Workspace, project, research-case, case-run, Python SDK, and TypeScript SDK regressions pass. | Restore default `False` if platform object contracts fail or existing consumers break. | Workspace/project/case APIs become always available after default-on. |
| 3 | `DOGE_FEATURE_WORKFLOW_TEMPLATES` / `settings.features.workflow_templates` | `False` | After ADR-0018 preflight and template-created run regressions are green. | One release cycle after default-on with approved workflow-template compatibility removal story. | Workflow template list/create/get and template-created research-case run regressions pass. | Restore default `False` if template APIs or template-created run flows regress. | Workflow template APIs become always available after default-on. |
| 4 | `DOGE_FEATURE_RUN_SUMMARY_API` / `settings.features.run_summary_api` | `False` | After ADR-0017 evidence and citation/eval API regressions are green. | One release cycle after default-on with approved API/SDK compatibility removal story. | Run summary, claims, citations, eval, v1 API, ACL redaction, and SDK regressions pass. | Restore default `False` if run-summary contract tests fail or consumers report API breakage. | `/v1/runs/{run_id}/summary`, `/claims`, `/citations`, and `/eval` become always available after default-on. |
| 5 | `VITE_DOGE_FEATURE_PLATFORM_SHELL` | `True` | Completed locally on 2026-06-24 after ADR-0020 review, case-workspace browser smoke, AX-tree preflight, and Web navigation regressions passed. | One release cycle after default-on with approved legacy route compatibility removal story. | `web/src/config/features.spec.ts`, `web/src/router/productNavigation.spec.ts`, `web/src/stores/platform.spec.ts`, full `npm test`, and `npm run build` pass; `/research-agent` compatibility remains tested; `production/qa/evidence/manual/platform-shell-default-entry-smoke-2026-06-24.json` verifies default-on and rollback routes. | Set `VITE_DOGE_FEATURE_PLATFORM_SHELL=0` or restore default `False` if product navigation, accessibility evidence, or legacy deep links regress. | Product-domain shell is the default Web entry while `/research-agent` remains a compatibility route until a separate approved removal story. |

## Code Metadata

Lifecycle metadata is represented in code so it can be audited alongside the
feature flags:

- Python: `src/doge/config/settings.py`
  - `FeatureLifecycle`
  - `FEATURE_LIFECYCLES`
  - Four backend feature entries keyed by `run_summary_api`,
    `platform_objects`, `workflow_templates`, and `capability_registry`.
- Capability API: `src/doge/application/capabilities/registry.py`
  - Feature capability records expose lifecycle metadata under
    `metadata.lifecycle`.
- Web: `web/src/config/features.ts`
  - `platformShellLifecycle`
  - `featureLifecycles`
  - `isPlatformShellEnabled(value)`, defaulting on for unset/empty values and
    preserving explicit rollback values such as `'0'`, `'false'`, and `'off'`.

## Defaultization Rules

1. Do not flip a default in the same change that introduces lifecycle metadata.
2. Default-on changes require a separate story with:
   - target flag;
   - CDD/ADR reference;
   - expected consumer impact;
   - rollback command or patch;
   - targeted regression results;
   - external consumer risk assessment.
3. A flag can be removed only after:
   - it has been default-on for at least one release cycle;
   - all callers use the new path unconditionally;
   - rollback evidence exists;
   - legacy route/API/SDK/CLI/MCP compatibility has an approved removal story;
   - no external gate is being implicitly closed by the removal.

## Required Regression Commands

Backend lifecycle and API checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/contract/test_platform_api.py tests/contract/test_run_summary_api.py -q
```

Architecture and contract checks before any default flip:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/governance/test_s017_planning_docs.py tests/unit/governance/test_adr_lifecycle_status.py -q
.\.venv\Scripts\python.exe -m pytest tests/unit/layer_gates/ tests/unit/architecture/ -q
.\.venv\Scripts\python.exe -m pytest tests/contract/test_v1_api.py tests/contract/test_platform_api.py tests/contract/test_run_summary_api.py tests/contract/test_agent_router.py tests/contract/test_enterprise_acl_api.py tests/contract/test_python_sdk.py -q
.\.venv\Scripts\python.exe -m pytest tests/unit/agent/test_runtime_kernel.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_service_facade.py tests/unit/agent/test_tool_registry.py tests/unit/use_cases/test_capability_registry.py tests/unit/capabilities -q
```

Web and TypeScript SDK checks:

```powershell
cd web
npm test -- features.spec.ts productNavigation.spec.ts platform.spec.ts
npm test
npm run build

cd ..\packages\doge-sdk-typescript
npm test
npm run build
```

## Follow-Up Story

First backend defaultization story candidate:

```text
Title: Default-on capability registry discovery
Scope: Flip DOGE_FEATURE_CAPABILITY_REGISTRY default to True only after ADR-0019 review confirms acceptance criteria.
Required evidence: capability lifecycle metadata, redaction tests, /v1/capabilities contract tests, provider parity tests, exact-SHA remote CI.
Rollback: restore default False in FeatureConfig if capability discovery or provider parity fails.
```

## Boundaries

- Web shell defaultization changed only `VITE_DOGE_FEATURE_PLATFORM_SHELL`.
- No backend feature flag default changed in this phase.
- No legacy route, SDK method, CLI command, MCP tool, or Web route was removed.
- `/research-agent` remains reachable.
- Web root rollback remains available with `VITE_DOGE_FEATURE_PLATFORM_SHELL=0`.
- External gates remain open and tracked in
  `docs/archive/audits/external-gate-next-actions-2026-06-23.md`.
