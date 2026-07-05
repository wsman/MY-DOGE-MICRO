# Sprint 022 — Approval Explanation Metadata Manifest

> Sprint: 022 (Approval Explanation Metadata)
> Date: 2026-07-05 · Branch: `main`
> Plan: `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`
> Status: Local implementation complete; ready for local acceptance.

## Purpose

This manifest records Sprint 022 local implementation evidence. The selected
deferred item is UX-2 B4: approval explanation fields. The delivered target is
an additive `AgentApproval` metadata expansion with four optional strings:

- `why_needed`
- `impact`
- `deny_consequence`
- `publish_target`

The sprint edits runtime code, persistence, API response models, SDK types,
Web rendering, tests, and governance documents without changing approval
resolution semantics or external-gate posture.

## Scope Register

| Slice | Scope | Files | Status |
|-------|-------|-------|--------|
| 0 | ADR and CDD | `docs/architecture/adr-0029-additive-approval-explanation-fields.md`, `design/cdd/sprint-022-approval-explanation.md` | Complete |
| 1 | Domain, run-stepper, provider content | `agent_models.py`, `run_stepper.py`, `registry.py`, governance providers | Complete |
| 2 | SQLite schema and migration | `agent_schema.sql`, `migration_runner.py`, repositories, runtime transaction | Complete |
| 3 | Gateway response model, SDK parity, TypeScript SDK | `_response_models.py`, `run_queries.py`, `sdk-contract-check.py`, TS SDK run types | Complete |
| 4 | Web approval rows | `ResearchAgentView.vue`, `ResearchAgentView.spec.ts` | Complete |
| 5 | Tests, fixture, reference docs | runtime/API/Web tests, golden fixture, HTTP/runtime docs | Complete |
| 6 | Governance closeout | sprint record, this manifest, active session-state | Complete |

## Contract Decision

The four fields are passive metadata:

| Field | Meaning | Default |
|-------|---------|---------|
| `why_needed` | Why the approval pause exists. | `""` |
| `impact` | What decision area or outcome is affected. | `""` |
| `deny_consequence` | What happens when the approval is denied. | `""` |
| `publish_target` | Destination/audience for publish-style approvals. | `""` |

No existing approval field is removed or renamed. No required field is added.
Approval resolution and entitlement behavior are unchanged.

## Posture Invariants

- `production_ready: false`; `stable_declaration: forbidden`;
  `level_3_sdk_platform: experimental`.
- External/operator gates S017-003 / W3-live / AUTH-prod / S017-007 remain
  open.
- S017-002 and S017-006 remain passed.
- Closure gate remains 4 open / 2 passed.
- No external gate closure and no fabricated live evidence.

## Implementation Evidence

Implemented evidence includes:

- `AgentApproval` fields and `AgentRun.add_approval` keyword metadata.
- Run stepper propagation from `ToolResult.data` to approval object and
  `APPROVAL_REQUESTED` event payload.
- Provider text population for publish/rebalance/generic approval flows.
- Fresh SQLite schema and idempotent migration for legacy approval rows.
- Repository and transaction round-trip persistence.
- OpenAPI `ApprovalResponse` / `ApprovalListResponse`.
- TypeScript SDK optional fields and 13-entry SDK parity gate.
- Web approval detail rows with empty-row hiding and accessible label context.
- Runtime golden fixture update.
- Runtime/API/SDK/Web tests.

## Verification

Local acceptance checks:

```text
py -3 -m pytest tests\unit\agent\test_approval_coordinator.py tests\unit\agent\test_run_stepper.py tests\unit\agent\test_repositories.py tests\unit\infrastructure\test_migration_runner.py tests\unit\gateway\test_response_models_wire.py tests\contract\test_approval_resume.py tests\contract\test_platform_api.py tests\contract\test_golden_runtime_contract.py -q
=> 62 passed

py -3 -m pytest tests\unit\agent\test_tool_service_facade.py tests\unit\agent\test_tool_registry.py tests\contract\test_tool_registry.py -q
=> 34 passed

py -3 tools\ci\sdk-contract-check.py
=> sdk-contract-check passed (13 surfaces, 13 entity parity checks)

cd web && npm run test -- src/views/ResearchAgentView.spec.ts
=> 1 file / 2 tests passed

cd web && npm run build
=> passed

py -3 scripts\validate_docs_authority.py
py -3 scripts\validate_docs_maturity_claims.py
py -3 scripts\validate_alpha_maturity_honesty.py
py -3 scripts\validate_docs_links.py
py -3 scripts\validate_import_boundaries.py
py -3 scripts\validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md
git diff --check
```
