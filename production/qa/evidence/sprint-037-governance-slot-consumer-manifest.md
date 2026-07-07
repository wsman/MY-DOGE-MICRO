# Sprint 037 - Governance Slot Consumer Manifest

> Sprint: 037 (Governance Slot Consumer)
> Date: 2026-07-07
> Status: Local implementation complete; final verification passed.

## Scope

This manifest records local evidence for the governance slot consumer sprint:
`governance.tool_policy` contributes the default tool entitlement and approval
policy, and the slot-aware tool registry composes governance checkers behind
`DOGE_FEATURE_SLOT_PLATFORM` + `DOGE_FEATURE_SLOT_GOVERNANCE`.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0046-governance-slot-consumer.md` records the governance-consumer decision. |
| CDD | `design/cdd/sprint-037-governance-slot-consumer.md` records behavior, contracts, and acceptance criteria. |
| Built-in governance slot | `src/doge/platform/governance/slot.py` adds `ToolGovernancePolicySlot`, `DefaultToolGovernanceChecker`, and `CompositeToolEntitlementChecker`. |
| Governance facade | `src/doge/platform/governance/__init__.py` exports the slot/checker types. |
| Built-in registry | `src/doge/bootstrap/runtime_factories/slots.py` registers `ToolGovernancePolicySlot`. |
| Entitlement consumer | `src/doge/bootstrap/runtime_factories/slots.py` adds `build_slot_aware_entitlement_checker()` and wires it into `build_slot_aware_tool_registry()`. |
| Feature lifecycle | `src/doge/config/settings.py` adds `DOGE_FEATURE_SLOT_GOVERNANCE`. |
| Capability discovery | `src/doge/application/capabilities/registry.py` exposes `feature.slot_platform` and `feature.slot_governance`. |
| Unit tests | `tests/unit/platform/slots/test_builtin_governance_slot.py` covers manifest, contribution, and composite behavior. |
| Contract tests | `tests/contract/test_governance_slot_parity.py` covers default parity, restrictive policy behavior, and duplicate policy fail-fast. |
| Slot discovery tests | `tests/cli/test_cli_slots.py`, `tests/cli/test_doged_cli.py`, and `tests/contract/test_slot_api.py` cover `governance.tool_policy` status. |
| Session state | `production/session-state/active.md` records Sprint 037 as the current local implementation. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` adds the governance slot consumer evidence record. |

## Verification Commands

```bash
py -3 -m pytest tests/unit/platform/slots/test_builtin_governance_slot.py tests/contract/test_governance_slot_parity.py tests/contract/test_tool_registry_slot_parity.py tests/cli/test_cli_slots.py tests/contract/test_slot_api.py tests/cli/test_doged_cli.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py -q
py -3 -m pytest tests/unit/platform/slots tests/contract/test_workflow_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_tool_registry_slot_parity.py tests/contract/test_governance_slot_parity.py -q
py -3 -m pytest tests/contract/test_tool_registry.py tests/unit/agent/test_tool_registry.py tests/unit/agent/test_tool_service_facade.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0046-governance-slot-consumer.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-037-governance-slot-consumer.md
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
| Focused governance slot / parity / CLI / API / doged / settings / capability suite | Passed: 84 tests, 2 existing FastAPI deprecation warnings. |
| Broader slot/governance regression suite | Passed: 78 tests. |
| Tool-registry regression suite | Passed: 34 tests. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 104 markdown files. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0046 and Sprint 037 CDD. |
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
- Sprint 037 completes the governance-facet consumer proof only; it does not
  complete the full OpenClaw-like Slot Platform.
