# Sprint 035 - Workflow Slot Consumer Manifest

> Sprint: 035 (Workflow Slot Consumer)
> Date: 2026-07-07
> Status: Local implementation complete; final verification passed.

## Scope

This manifest records local evidence for the workflow-facet consumer sprint:
the existing built-in workflow template set can be contributed by a
`workflow.templates` slot and consumed by the CLI/MCP seeding path through the
workspace container when both `DOGE_FEATURE_SLOT_PLATFORM` and
`DOGE_FEATURE_WORKFLOW_TEMPLATES` are enabled.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0044-workflow-slot-consumer.md` records the workflow slot consumer decision. |
| CDD | `design/cdd/sprint-035-workflow-slot-consumer.md` records behavior, contracts, and acceptance criteria. |
| Workflow slot | `src/doge/platform/workspace/slot.py` defines `WorkflowTemplatesSlot`. |
| Seeder seam | `src/doge/platform/workspace/template_seed.py` accepts injected template definitions while preserving `BUILTIN_TEMPLATES`. |
| Bootstrap wiring | `src/doge/bootstrap/runtime_factories/slots.py` registers `workflow.templates` and adds `build_slot_aware_workflow_templates()`. |
| Workspace container | `src/doge/bootstrap/workspace.py` adds `build_workflow_template_definitions()` as the feature posture seam. |
| CLI seed surface | `src/doge/interfaces/cli/commands/template.py` passes workspace-container template definitions to the seeder. |
| MCP seed surface | `src/doge/interfaces/mcp/server.py` passes workspace-container template definitions to the seeder. |
| Slot CLI status | `src/doge/interfaces/cli/commands/slots.py` reports manifest feature-flag status without resolving slots. |
| Workflow slot tests | `tests/unit/platform/slots/test_builtin_workflow_slot.py` covers manifest fields, contribution shape, and defensive copy behavior. |
| Workflow parity tests | `tests/contract/test_workflow_slot_parity.py` covers built-in parity plus duplicate/mismatched slug fail-fast. |
| Seeder/container tests | `tests/unit/workspace_workflow/test_template_seed.py` covers injected definitions and container feature posture. |
| CLI status tests | `tests/cli/test_cli_slots.py` covers `workflow.templates` disabled/resolved status. |
| Session state | `production/session-state/active.md` records Sprint 035 as the current local implementation. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` adds the `workflow_slot_consumer_2026_07_07` evidence record. |

## Verification Commands

```bash
py -3 -m pytest tests/unit/platform/slots tests/unit/workspace_workflow/test_template_seed.py \
  tests/cli/test_cli_slots.py tests/contract/test_workflow_slot_parity.py \
  tests/contract/test_agent_backends_slot_parity.py tests/contract/test_tool_registry_slot_parity.py -q
py -3 -m pytest tests/cli/test_cli_platform_workflow.py tests/test_mcp_tools.py \
  tests/contract/test_platform_api.py tests/unit/architecture -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0044-workflow-slot-consumer.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-035-workflow-slot-consumer.md
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
| Focused workflow-slot suite | Passed: 88 tests (slot provider, seeder, CLI status, workflow parity, agent-backend parity, tool-registry slot parity). |
| Platform workflow/MCP/API/architecture regression | Passed: 195 tests, 2 existing FastAPI deprecation warnings. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 102 markdown files. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0044 and Sprint 035 CDD. |
| Stale counts / ADR index / governance YAML | Passed. |
| Plan closure | Passed with controlled open posture: 4 open / 2 passed. |
| Whitespace | Passed with `git diff --check` and `cmd.exe /c git diff --check`. |

## Posture

- Production posture unchanged: `production_ready: false`,
  `stable_declaration: forbidden`, `level_3_sdk_platform: experimental`.
- No external/operator gates are closed by this sprint.
- No `/v1` route, OpenAPI schema, SDK source, Web source, daemon command source,
  persistence schema, ModelRouter, ProfileRegistry, runtime dispatch, lifecycle
  invocation, or runtime permission/health enforcement is part of this sprint.
- Slot Platform remains experimental and feature-flagged off by default.
- Sprint 035 completes the workflow-facet consumer proof only; it does not
  complete the full OpenClaw-like Slot Platform.
