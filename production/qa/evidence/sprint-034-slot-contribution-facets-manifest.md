# Sprint 034 - Slot Contribution Facets Manifest

> Sprint: 034 (Slot Contribution Facets)
> Date: 2026-07-07
> Status: Local implementation complete; final verification passed.

## Scope

This manifest records local evidence for the Slot Contribution Facets sprint:
all planned non-tool facets are representable in the pure slot contract, and one
model backend (`kimi_agent_sdk`) is assembled through a built-in model slot behind
`DOGE_FEATURE_SLOT_PLATFORM`.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0043-slot-contribution-facets.md` records the facet contract and model-slot proof decision. |
| CDD | `design/cdd/sprint-034-slot-contribution-facets.md` records behavior, contracts, and acceptance criteria. |
| Facet contract | `src/doge/platform/slots/facets.py` defines model, workflow, data, document, gateway, UI, watcher, eval, and governance contribution dataclasses. |
| Slot contribution widening | `src/doge/platform/slots/contracts.py` adds facet fields, optional tool service, service-id constants, and lifecycle hooks. |
| Contract exports | `src/doge/platform/slots/__init__.py` re-exports facet and service-id symbols. |
| Market slot guard | `src/doge/products/market/slot.py` raises `SlotConfigurationError` when resolved without a tool service. |
| Built-in model slot | `src/doge/bootstrap/runtime_factories/builtin_model_slot.py` defines `ModelKimiAgentSdkSlot`. |
| Bootstrap wiring | `src/doge/bootstrap/runtime_factories/slots.py` registers built-in tool/model slots and adds `build_slot_aware_agent_backends`. |
| Runtime factory branch | `src/doge/bootstrap/runtime_factories/runtime_kernel.py` delegates `build_agent_backends` to the slot-aware path when `slot_platform` is enabled. |
| Facet tests | `tests/unit/platform/slots/test_slot_facets.py` covers all 9 non-tool facets and multi-facet contribution carrying. |
| Model slot tests | `tests/unit/platform/slots/test_builtin_model_slot.py` covers manifest fields, contribution shape, and secret-provider lookup. |
| Agent-backend parity | `tests/contract/test_agent_backends_slot_parity.py` proves public flag-on/off backend equivalence and duplicate-id fail-fast. |
| Tool parity hardening | `tests/contract/test_tool_registry_slot_parity.py` keeps `/v1/tools` parity and tool-executor fail-fast coverage. |
| Context and market tests | `tests/unit/platform/slots/test_slot_context.py` and `tests/unit/platform/slots/test_market_core_slot.py` cover optional tool service and fail-fast behavior. |
| Boundary ratchet | `tests/unit/architecture/test_slot_boundary.py` scans the new `facets.py` package surface. |
| Session state | `production/session-state/active.md` records Sprint 034 as the current local implementation. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` adds the `slot_contribution_facets_2026_07_07` evidence record. |

## Verification Commands

```bash
py -3 -m pytest tests/unit/platform/slots tests/unit/architecture/test_slot_boundary.py \
  tests/contract/test_agent_backends_slot_parity.py tests/contract/test_tool_registry_slot_parity.py -q
py -3 -m pytest tests/test_settings.py tests/unit/agent tests/contract/test_tool_registry.py \
  tests/contract/test_golden_runtime_contract.py tests/unit/architecture -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0043-slot-contribution-facets.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-034-slot-contribution-facets.md
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
| Focused slot/model suite | Passed: 72 tests (slot facets, boundary ratchet, agent-backend parity, and tool-registry slot parity). |
| Settings/agent/tool/runtime/architecture regression | Passed: 408 tests, 108 existing deprecation warnings. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 101 markdown files. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0043 and Sprint 034 CDD. |
| Stale counts / ADR index / governance YAML | Passed. |
| Plan closure | Passed with controlled open posture: 4 open / 2 passed. |
| Whitespace | Passed with `git diff --check` and `cmd.exe /c git diff --check`. |

## Posture

- Production posture unchanged: `production_ready: false`,
  `stable_declaration: forbidden`, `level_3_sdk_platform: experimental`.
- No external/operator gates are closed by this sprint.
- No `/v1` route, OpenAPI schema, SDK source, Web source, daemon command source,
  persistence schema, ModelRouter, ProfileRegistry, runtime dispatch, or
  production readiness declaration is part of this sprint.
- Slot Platform remains experimental and feature-flagged off by default.
- Sprint 034 completes contribution facets plus the model-backend slot proof; it
  does not complete the full OpenClaw-like Slot Platform.
