# Sprint 035 CDD: Workflow Slot Consumer

Status: Ready for Acceptance
Date: 2026-07-07

## 1. Overview

Sprint 035 consumes the workflow facet introduced in ADR-0043. It adds a
built-in `workflow.templates` slot that contributes the existing built-in
workflow template definitions, then routes CLI and MCP workflow-template seeding
through a workspace-container seam that can choose the slot-aware definitions
when both slot and workflow-template feature flags are enabled.

The sprint remains local, experimental, and feature-flagged. It does not claim
the full OpenClaw-like Slot Platform is complete.

## 2. User Promise / JTBD

A platform maintainer can now verify that workflow templates are a real slot
contribution, not just a representable contract type. A local operator can keep
using `doge template seed` and MCP `seed_workflow_templates` without behavior
change when feature flags are off, while the slot-aware path produces the same
template set when enabled.

## 3. Detailed Behavior

- `WorkflowTemplatesSlot` lives in `doge.platform.workspace.slot`.
- The slot manifest has:
  - `id=workflow.templates`
  - `type=workflow`
  - `owner=workspace-workflow`
  - `maturity=experimental`
  - `feature_flags=(slot_platform, workflow_templates)`
- The slot contributes one `WorkflowTemplateContribution` per
  `BUILTIN_TEMPLATES` entry.
- Contribution factories return defensive copies of template mappings.
- `build_builtin_slot_registry()` registers `workflow.templates` beside
  `market.core` and `model.kimi_agent_sdk`.
- `build_slot_aware_workflow_templates()` resolves only workflow slots and
  returns template dictionaries.
- Duplicate workflow template slugs raise `SlotConfigurationError`.
- A contribution whose factory returns a mismatched `slug` raises
  `SlotConfigurationError`.
- `seed_workflow_templates()` accepts optional template definitions and defaults
  to `BUILTIN_TEMPLATES`.
- `WorkspaceContainer.build_workflow_template_definitions()` returns slot-aware
  templates only when both `slot_platform` and `workflow_templates` are true.
- CLI `template seed` and MCP `seed_workflow_templates` pass the workspace
  container's template definitions into the seeder.
- `doge slots list` reports per-slot `resolved` / `disabled` status from feature
  flags without resolving slots.

## 4. Contracts / Data Model

`WorkflowTemplateContribution` remains the ADR-0043 contract:

```python
WorkflowTemplateContribution(
    slug: str,
    template_factory: Callable[[SlotContext], Mapping[str, Any]],
    capabilities: tuple[str, ...] = (),
)
```

Seeder contract:

```python
seed_workflow_templates(
    repo,
    *,
    scope=None,
    tenant_id=None,
    dry_run=False,
    templates=None,
)
```

When `templates` is `None`, the seeder uses `BUILTIN_TEMPLATES`.

## 5. Edge Cases

- Only `workflow_templates` on: seeding uses legacy built-in templates.
- Only `slot_platform` on: `workflow.templates` appears disabled in slot list;
  direct slot-aware workflow helper returns no templates.
- Both flags on: seeding can use slot-aware template definitions.
- Duplicate workflow slugs: fail fast before persistence.
- Mismatched factory slug: fail fast before persistence.
- Dry-run seeding: reports inserted slugs but writes nothing.
- Existing seeded templates: idempotent slug check remains unchanged.

## 6. Dependencies

- ADR-0042 Slot Platform Foundation.
- ADR-0043 Slot Contribution Facets.
- Existing `BUILTIN_TEMPLATES` data in `doge.platform.workspace.template_seed`.
- Existing `IPlatformRepository.save_workflow_template`.
- Existing `DOGE_FEATURE_SLOT_PLATFORM` and `DOGE_FEATURE_WORKFLOW_TEMPLATES`.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`.
- `DOGE_FEATURE_WORKFLOW_TEMPLATES`: default `false`.

No new feature flag is introduced.

## 8. Acceptance Criteria

- `workflow.templates` is registered in the built-in slot registry.
- Slot-aware workflow template definitions equal `BUILTIN_TEMPLATES`.
- Direct seeder behavior stays unchanged when no injected templates are passed.
- CLI and MCP seed surfaces route through the workspace-container template seam.
- `doge slots list --json` shows `workflow.templates` disabled unless
  `workflow_templates` is enabled.
- Existing tool and model slot parity tests remain green.
- `/v1` routes, OpenAPI, SDK packages, Web source, daemon command source,
  persistence schema, ModelRouter/ProfileRegistry, and runtime dispatch are
  unchanged.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## 9. Validation Plan

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

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-035-workflow-slot-consumer-manifest.md`.

## 11. Out of Scope

- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, and `SlotLoader`.
- `/v1/slots`, `doged slots`, Web Slot Center, or bundle activation.
- Runtime consumers for data, document, gateway, UI, watcher, eval, or
  governance facets.
- Runtime permission/health enforcement.
- Third-party slot installation, signing, or enterprise allowlist.
- Production readiness declaration or external/operator gate closure.
