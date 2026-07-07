# Sprint 036 - Slot Discovery Surfaces Manifest

> Sprint: 036 (Slot Discovery Surfaces)
> Date: 2026-07-07
> Status: Local implementation complete; final verification passed.

## Scope

This manifest records local evidence for the read-only slot discovery sprint:
built-in slots can be inspected through `/v1/slots`, one-slot health reads, and
`doged slots` without resolving slot contributions or adding mutation/bundle
activation semantics.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0045-slot-discovery-surfaces.md` records the discovery-surface decision. |
| CDD | `design/cdd/sprint-036-slot-discovery-surfaces.md` records behavior, contracts, and acceptance criteria. |
| Shared status rows | `src/doge/bootstrap/runtime_factories/slots.py` adds `build_slot_status_rows()` and keeps it manifest-only. |
| CLI slot list | `src/doge/interfaces/cli/commands/slots.py` reuses shared rows for `doge slots list`. |
| Slot API router | `src/doge/interfaces/gateway/routers/slots.py` adds read-only `/v1/slots` endpoints. |
| API route registration | `src/doge/interfaces/api/routes.py` mounts the slots router under `/v1`. |
| Daemon operator command | `src/doge/interfaces/daemon/main.py` adds `doged slots [--json]`. |
| Slot API tests | `tests/contract/test_slot_api.py` covers feature gate, status rows, one-slot reads, health, unknown IDs, and no bundle route. |
| doged tests | `tests/cli/test_doged_cli.py` covers text and JSON `doged slots` output. |
| CLI slot tests | `tests/cli/test_cli_slots.py` continues covering `doge slots` flag posture. |
| Route authority | `docs/reference/http-api.md`, `docs/API.md`, `docs/reference/api.md`, `docs/registry/entities.yaml`, `design/cdd/fastapi-service.md`, `docs/architecture/tr-registry.yaml`, `docs/registry/architecture.yaml`, `docs/architecture/architecture-traceability.md`, and `docs/architecture/adr-0007-api-surface-and-cors.md` now track 93 HTTP routes. |
| Session state | `production/session-state/active.md` records Sprint 036 as the current local implementation. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` adds the slot discovery surfaces evidence record. |

## Verification Commands

```bash
py -3 -m pytest tests/contract/test_slot_api.py tests/cli/test_doged_cli.py tests/cli/test_cli_slots.py -q
py -3 -m pytest tests/contract/test_api_doc_route_coverage.py tests/unit/governance/test_s017_planning_docs.py -q
py -3 -m pytest tests/unit/platform/slots tests/contract/test_workflow_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_tool_registry_slot_parity.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0045-slot-discovery-surfaces.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-036-slot-discovery-surfaces.md
py -3 scripts/validate_no_stale_counts.py
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## Verification Results

| Gate | Result |
|---|---|
| Focused slot API / doged / CLI suite | Passed: 37 tests, 2 existing FastAPI deprecation warnings. |
| Route coverage and S017 governance route sync | Passed: 39 tests, 2 existing FastAPI deprecation warnings. |
| Combined Sprint 036 focused + slot regression suite | Passed: 148 tests, 2 existing FastAPI deprecation warnings. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 103 markdown files. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0045 and Sprint 036 CDD. |
| Stale counts / ADR index / governance YAML | Passed. |
| Plan closure | Passed with controlled open posture: 4 open / 2 passed. |
| Whitespace | Passed with `git diff --check` and `cmd.exe /c git diff --check`. |

## Posture

- Production posture unchanged: `production_ready: false`,
  `stable_declaration: forbidden`, `level_3_sdk_platform: experimental`.
- No external/operator gates are closed by this sprint.
- No SDK package source, Web source, persistence schema, ModelRouter,
  ProfileRegistry, runtime dispatch, watcher middleware, lifecycle hook
  invocation, runtime permission/health enforcement, bundle activation,
  third-party slot install, signing, or enterprise allowlist is part of this
  sprint.
- Slot Platform remains experimental and feature-flagged off by default.
- Sprint 036 completes read-only built-in slot discovery only; it does not
  complete the full OpenClaw-like Slot Platform.
