# Sprint 043 - Slot Kernel, Bundles, Policy, and Lifecycle Manifest

> Sprint: 043 (Slot Kernel, Bundles, Policy, and Lifecycle)
> Date: 2026-07-07
> Status: Local implementation complete; verification passed.

## Scope

This manifest records local evidence for the first-class SlotKernel sprint:
the Slot Platform now has pure contracts for policy, bundles, lifecycle, and
kernel orchestration; existing slot-aware consumers resolve through the kernel;
and `/v1/slot-bundles` exposes read-only built-in bundle status behind
`DOGE_FEATURE_SLOT_PLATFORM`.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0052-slot-kernel-bundles-policy.md` records the kernel/bundle/policy decision. |
| CDD | `design/cdd/sprint-043-slot-kernel-bundles-policy.md` records behavior, contracts, and acceptance criteria. |
| Policy contract | `src/doge/platform/slots/policy.py` adds `SlotPolicy`. |
| Bundle contract | `src/doge/platform/slots/bundles.py` adds `SlotBundle` and `SlotBundleStatus`. |
| Lifecycle contract | `src/doge/platform/slots/lifecycle.py` adds `SlotLifecycle`. |
| Kernel contract | `src/doge/platform/slots/kernel.py` adds `SlotKernel`. |
| Public exports | `src/doge/platform/slots/__init__.py` exports the new contracts. |
| Built-in kernel | `src/doge/bootstrap/runtime_factories/slots.py` adds built-in bundle definitions and `build_builtin_slot_kernel()`. |
| Consumer refactor | `src/doge/bootstrap/runtime_factories/slots.py` routes existing slot-aware consumers through `SlotKernel.resolve_contributions()`. |
| Bundle rows | `src/doge/bootstrap/runtime_factories/slots.py` adds `build_slot_bundle_rows()`. |
| API dependency | `src/doge/interfaces/api/deps.py` exposes bundle rows through the API dependency layer. |
| API route | `src/doge/interfaces/gateway/routers/slots.py` adds `GET /v1/slot-bundles`. |
| Gateway manifest | `src/doge/interfaces/gateway/slot.py` declares `/v1/slot-bundles`. |
| Route authority | `docs/API.md`, `docs/reference/http-api.md`, `design/cdd/fastapi-service.md`, `docs/registry/entities.yaml`, and route governance tests now track 94 HTTP routes. |
| Unit tests | `tests/unit/platform/slots/test_slot_policy.py`, `test_slot_bundle.py`, and `test_slot_kernel.py` cover policy, bundle, kernel, and lifecycle behavior. |
| Contract tests | `tests/contract/test_slot_kernel_bundle_rows.py` and `tests/contract/test_slot_api.py` cover built-in bundle rows and `/v1/slot-bundles`. |
| Session state | `production/session-state/active.md` records Sprint 043 as the current local implementation. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` adds the SlotKernel evidence record. |

## Verification Commands

```bash
py -3 -m pytest tests/unit/platform/slots/test_slot_policy.py tests/unit/platform/slots/test_slot_bundle.py tests/unit/platform/slots/test_slot_kernel.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_api.py -q
py -3 -m pytest tests/unit/platform/slots tests/unit/eval tests/contract/test_tool_registry_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_gateway_slot_parity.py tests/contract/test_eval_slot_parity.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_api.py tests/cli/test_cli_slots.py tests/cli/test_doged_cli.py -q
py -3 -m pytest tests/contract/test_api_doc_route_coverage.py tests/unit/governance/test_s017_planning_docs.py -q
py -3 -m pytest tests/unit/architecture/test_slot_boundary.py tests/unit/architecture/test_bootstrap_owns_factories.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0052-slot-kernel-bundles-policy.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-043-slot-kernel-bundles-policy.md
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
| Slot kernel / bundle / API focused suite | Passed: 28 tests, 2 existing FastAPI deprecation warnings. |
| Broader slot consumer parity suite | Passed: 182 tests, 2 existing FastAPI deprecation warnings. |
| API route coverage and governance route sync | Passed: 51 tests, 2 existing FastAPI deprecation warnings. |
| Architecture boundary gates | Passed: 28 tests. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 110 markdown files. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0052 and Sprint 043 CDD. |
| Stale counts / ADR index / governance YAML | Passed. |
| Plan closure | Acceptable controlled-open: 4 open gates, 2 passed gates. |
| Whitespace | Passed in WSL Git and Windows Git. |

## Posture

- Production posture unchanged: `production_ready: false`,
  `stable_declaration: forbidden`, `level_3_sdk_platform: experimental`.
- No external/operator gates are closed by this sprint.
- No SDK package source, Web source, persistence schema, ModelRouter,
  ProfileRegistry, bundle activation, SlotLoader, third-party slot install,
  signing, runtime permission enforcement, active health probe, or enterprise
  allowlist is part of this sprint.
- Slot Platform remains experimental and feature-flagged off by default.
- Sprint 043 completes the first-class kernel/bundle/policy proof only; it does
  not complete the full OpenClaw-like Slot Platform.
