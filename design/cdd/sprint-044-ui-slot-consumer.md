# Sprint 044 CDD: UI Slot Consumer

Status: Ready for Acceptance / Local Verification Passed
Date: 2026-07-07

## 1. Overview

Sprint 044 consumes the Slot Platform `ui` facet for the Research workspace.

The sprint adds a built-in `ui.research_workspace` slot, a backend
`UIPanelRegistry`, read-only `/v1/ui-panels`, and a frontend
`panelRegistry.ts` used by `ResearchAgentView.vue`.

The sprint does not add Web Slot Center, dynamic component loading, bundle
activation, persistent layout customization, SlotLoader, third-party slot
install, signing, permission enforcement, active health probes, external gate
closure, or production-readiness changes.

## 2. User Promise / JTBD

A platform engineer can inspect the Research workspace panel set as slot
metadata instead of reading `ResearchAgentView.vue`.

A Web integrator can keep the existing static component render while making
panel visibility mode-aware and slot-driven.

An operator can see `ui.research_workspace` status through the existing slot
discovery surfaces and use `/v1/ui-panels` when the UI slot feature is enabled.

## 3. Detailed Behavior

- `DOGE_FEATURE_SLOT_UI` defaults to `false`.
- `FeatureConfig.slot_ui` reads `DOGE_FEATURE_SLOT_UI`.
- Capability discovery exposes `feature.slot_ui`.
- `UIPanelContribution` includes `workspace`, defaulting to
  `research_workspace`.
- `ResearchWorkspaceUISlot` declares:
  - id: `ui.research_workspace`;
  - type: `ui`;
  - owner: `workspace-ui`;
  - flags: `slot_platform`, `slot_ui`;
  - capabilities: `ui.panels`, `ui.research_workspace`.
- The slot contributes the current Research workspace panel IDs across zones:
  `research.input`, `research.memo`, `research.evidence`, `research.quality`,
  and `research.timeline`.
- Developer-only panels are `cost_eval_panel` and `agent_timeline`.
- `UIPanelRegistry` filters panels by workspace, zone, and Analyst/Developer
  mode.
- Duplicate panel IDs within one workspace fail fast.
- `build_slot_aware_ui_panels()` resolves UI contributions through
  `SlotKernel.resolve_contributions(..., slot_type=SlotType.UI)`.
- `GET /v1/ui-panels` returns `{"panels": [...]}` only when both
  `DOGE_FEATURE_SLOT_PLATFORM=1` and `DOGE_FEATURE_SLOT_UI=1`.
- `ResearchAgentView.vue` keeps existing static imports and wraps panels with
  `showPanel(panel_id)`.
- The frontend default registry includes all existing Research workspace
  panels, so no remote metadata is required to preserve current rendering.

## 4. Contracts / Data Model

Backend contribution:

```python
UIPanelContribution(
    panel_id="conclusion_evidence_matrix",
    workspace="research_workspace",
    zone="research.evidence",
    component_module="components/agent/ConclusionEvidenceMatrix.vue",
    order=20,
    modes=("analyst", "developer"),
    required_artifact_fields=("structured_claims",),
    label="Conclusion Evidence Matrix",
)
```

Read-only UI panel route:

```http
GET /v1/ui-panels?workspace=research_workspace&zone=research.evidence&mode=analyst
```

Response shape:

```json
{
  "panels": [
    {
      "panel_id": "conclusion_evidence_matrix",
      "workspace": "research_workspace",
      "zone": "research.evidence",
      "component_module": "components/agent/ConclusionEvidenceMatrix.vue",
      "order": 20,
      "modes": ["analyst", "developer"],
      "required_artifact_fields": ["structured_claims"],
      "label": "Conclusion Evidence Matrix"
    }
  ]
}
```

Feature flags:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_UI=1
```

Maturity posture:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 5. Edge Cases

- Slot platform off: `/v1/ui-panels` returns 404 through the slot-platform gate.
- Slot UI off: `/v1/ui-panels` returns 404 with `slot UI API disabled`.
- Unknown workspace: returns an empty `panels` list.
- Unknown zone or mode: returns an empty `panels` list.
- Remote Web panel metadata omitting known defaults is treated as authoritative
  for the provided list, but an empty or invalid list falls back to the local
  default registry.
- Unknown frontend panel IDs from the backend are ignored by the Web registry.
- `component_module` is metadata only in this sprint; Web does not dynamically
  import from it.

## 6. Dependencies

- ADR-0042 Slot Platform Foundation.
- ADR-0043 Slot Contribution Facets.
- ADR-0045 Slot Discovery Surfaces.
- ADR-0052 Slot Kernel, Bundles, Policy, and Lifecycle.
- Existing ResearchAgentView component set.
- Existing platform store and DogeClient request helper.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; gates slot discovery and slot
  contribution resolution.
- `DOGE_FEATURE_SLOT_UI`: default `false`; gates UI slot contribution
  resolution and `/v1/ui-panels`.

No Vite flag, persistent layout flag, or user-level enable/disable state is
added in this sprint.

## 8. Acceptance Criteria

- `ui.research_workspace` is registered as a built-in UI slot.
- `/v1/slots` lists `ui.research_workspace` and marks it disabled unless
  `DOGE_FEATURE_SLOT_UI=1`.
- `build_slot_aware_ui_panels()` resolves Research workspace panels only when
  both slot flags are enabled.
- `/v1/ui-panels` is read-only and feature-gated.
- `ResearchAgentView.vue` renders through the frontend panel registry while
  preserving existing Analyst/Developer behavior.
- Frontend panel registry tests cover default and remote metadata.
- API route authority is synchronized at 95 HTTP routes.
- No Web Slot Center, dynamic component loading, bundle activation, SlotLoader,
  third-party install, signing, runtime permission enforcement, production
  readiness declaration, or external/operator gate closure is added.

## 9. Validation Plan

```bash
py -3 -m pytest tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/unit/platform/slots/test_builtin_ui_slot.py tests/unit/platform/workspace/test_ui_panel_registry.py tests/contract/test_slot_ui_registry.py tests/contract/test_slot_api.py tests/contract/test_gateway_slot_parity.py tests/cli/test_cli_slots.py tests/cli/test_doged_cli.py -q
cd web && npm run test -- src/views/panelRegistry.spec.ts src/stores/platform.spec.ts src/views/ResearchAgentView.spec.ts
py -3 -m pytest tests/contract/test_api_doc_route_coverage.py tests/unit/governance/test_s017_planning_docs.py -q
cd web && npm run build
py -3 -m pytest tests/unit/architecture/test_slot_boundary.py tests/unit/architecture/test_bootstrap_owns_factories.py -q
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0053-ui-slot-consumer.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-044-ui-slot-consumer.md
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-044-ui-slot-consumer-manifest.md`.

## 11. Out of Scope

- Web Slot Center.
- Dynamic panel/component loading.
- Persistent UI layout state or user customization.
- Bundle activation and persistent enable/disable state.
- SlotLoader, YAML manifests, third-party install, signing, and enterprise
  allowlist.
- Runtime permission enforcement and active health probes.
- SDK slot client.
- Persistence schema, ModelRouter/ProfileRegistry, external auth, worker
  behavior, or production deployment behavior changes.
- Production readiness declaration or external/operator gate closure.
