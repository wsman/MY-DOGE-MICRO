# Sprint 036 CDD: Slot Discovery Surfaces

Status: Ready for Acceptance
Date: 2026-07-07

## 1. Overview

Sprint 036 makes the experimental Slot Platform discoverable through local
operator surfaces without adding mutation or lifecycle semantics.

The sprint adds read-only `/v1/slots` routes and a `doged slots` command backed
by one manifest-only status serializer. Built-in slots remain feature-flagged,
and the full OpenClaw-like Slot Platform remains incomplete.

## 2. User Promise / JTBD

A local daemon operator or platform integrator can inspect which built-in slots
exist, which feature flags gate them, whether they are currently `resolved` or
`disabled`, and what static health/capability/permission metadata they declare.

This enables the next Slot Center and SDK discovery work while keeping slot
activation, bundle management, and third-party installation out of scope.

## 3. Detailed Behavior

- `build_slot_status_rows(settings=None)` lives in
  `doge.bootstrap.runtime_factories.slots`.
- The helper reads only settings, manifests, and `SlotRegistry.status()`.
- The helper does not call `slot.resolve()`.
- Each row includes:
  - identity fields: `id`, `name`, `version`, `type`, `owner`, `maturity`
  - operator fields: `status`, `feature_flags`, `health`
  - contract fields: `provides`, `requires`, `permissions`, `compatibility`
  - count summary fields
- `doge slots list` uses the shared rows for list output.
- `/v1/slots` returns `{"slots": [...]}` when `DOGE_FEATURE_SLOT_PLATFORM=1`.
- `/v1/slots/{slot_id}` returns one slot row.
- `/v1/slots/{slot_id}/health` returns the slot id, status, static health, and
  feature flags.
- Slot API routes return 404 with `slot platform API disabled` when the slot
  platform feature flag is off.
- Unknown slot IDs return 404 with `slot not found`.
- `/v1/slot-bundles` is intentionally not mounted.
- `doged slots` prints compact text rows even when all slots are disabled.
- `doged slots --json` returns the same row shape as the API.
- The canonical HTTP route count is now 93:
  - 34 legacy `/api/*` compatibility routes
  - 59 daemon/v1 and health routes

## 4. Contracts / Data Model

Slot status row:

```python
{
    "id": str,
    "name": str,
    "version": str,
    "type": str,
    "owner": str,
    "maturity": str,
    "description": str,
    "entrypoint": str,
    "status": "resolved" | "disabled",
    "feature_flags": list[str],
    "provides": {
        "tools": list[str],
        "capabilities": list[str],
        "metadata": dict,
    },
    "requires": list[dict],
    "permissions": dict,
    "health": {"status": str, "notes": str},
    "compatibility": dict,
    "counts": {"tools": int, "capabilities": int},
}
```

HTTP contract:

```http
GET /v1/slots
GET /v1/slots/{slot_id}
GET /v1/slots/{slot_id}/health
```

Daemon contract:

```bash
doged slots
doged slots --json
```

## 5. Edge Cases

- Slot platform flag off: API discovery returns 404; `doged slots` still shows
  rows as disabled.
- Workflow templates flag off while slot platform is on:
  `workflow.templates` is listed as disabled.
- Workflow templates flag on with slot platform on:
  `workflow.templates` is listed as resolved.
- Unknown slot id: API returns 404.
- `/v1/slot-bundles`: remains 404 because bundle activation is not implemented.
- `DOGE_API_TOKEN` configured: slot routes use the same bearer dependency as
  other v1 routes.

## 6. Dependencies

- ADR-0042 Slot Platform Foundation.
- ADR-0043 Slot Contribution Facets.
- ADR-0044 Workflow Slot Consumer.
- Existing `DOGE_FEATURE_SLOT_PLATFORM` and `DOGE_FEATURE_WORKFLOW_TEMPLATES`.
- Existing FastAPI route registration and `doged` parser.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; gates `/v1/slots`.
- `DOGE_FEATURE_WORKFLOW_TEMPLATES`: default `false`; affects
  `workflow.templates` status.

No new feature flag is introduced.

## 8. Acceptance Criteria

- Shared status rows are manifest-only and do not resolve slots.
- `/v1/slots` is mounted and feature-gated.
- `/v1/slots/{slot_id}` and `/v1/slots/{slot_id}/health` return one slot's
  status and static health.
- `/v1/slot-bundles` is not mounted.
- `doged slots` and `doged slots --json` work.
- `doge slots list` still preserves the feature-off disabled message and uses
  the shared row shape when enabled.
- HTTP route authority is synchronized at 93 routes.
- SDK package source, Web source, persistence schema, ModelRouter/ProfileRegistry,
  runtime dispatch, watcher middleware, lifecycle hooks, permission enforcement,
  bundle activation, and third-party install remain unchanged.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## 9. Validation Plan

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

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-036-slot-discovery-surfaces-manifest.md`.

## 11. Out of Scope

- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, and `SlotLoader`.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- Runtime consumers for data, document, gateway, UI, watcher, eval, or
  governance facets beyond existing prior proofs.
- Runtime permission/health enforcement or lifecycle hook invocation.
- Production readiness declaration or external/operator gate closure.
