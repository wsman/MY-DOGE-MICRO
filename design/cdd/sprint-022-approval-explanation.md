# Sprint 022 CDD: Approval Explanation Metadata

> **Status**: Ready for Acceptance / Local implementation complete
> **Author**: Codex documentation/governance agent
> **Last Updated**: 2026-07-05
> **Governing ADRs**: ADR-0007, ADR-0011, ADR-0024, ADR-0028, ADR-0029
> **Runtime Posture**: `production_ready: false`, `stable_declaration: forbidden`, `level_3_sdk_platform: experimental` — unchanged
> **Plan**: `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`

## Overview

Sprint 022 adds structured explanation metadata to approval prompts. The user
should be able to understand why an approval is requested, what it affects,
what denial does, and where a publish action would go before resolving it.

This file records the product and contract target implemented by Sprint 022.
Runtime code, database migration, API response models, SDK type changes, Web UI,
tests, and governance records are included in local acceptance scope.

## User Promise / JTBD

As a local analyst, SDK integrator, or demo owner, I can inspect a pending
approval and see enough context to make a deliberate approve/deny decision
without reconstructing intent from surrounding event history.

## Detailed Behavior

### Approval Fields

`AgentApproval` gains four optional string fields:

| Field | Default | Behavior |
|-------|---------|----------|
| `why_needed` | `""` | Explains why this approval pause exists. |
| `impact` | `""` | Names the affected decision area or outcome. |
| `deny_consequence` | `""` | Explains what happens if the approval is denied. |
| `publish_target` | `""` | Names the destination or audience for publish-style approvals. |

Empty string means no explanation was supplied. Renderers should hide empty
rows instead of showing placeholder text.

### Producer Intent

Approval-producing governance providers should populate the fields where they
already know the context. Publishing flows should set `publish_target` from the
known distribution target when available. Compliance or generic approval flows
may leave `publish_target` empty.

### Consumer Intent

API and SDK consumers should treat the fields as passive metadata. They do not
change approval status, authorization, entitlement checks, retry behavior, or
run continuation rules.

## Contracts / Data Model

- Additive `AgentApproval` fields: `why_needed`, `impact`,
  `deny_consequence`, `publish_target`.
- All four fields are optional for clients and default to empty string on the
  runtime object after implementation.
- `/v1/runs/{run_id}/approvals` should expose an `ApprovalResponse` schema
  containing the existing approval fields plus the four new fields.
- Full `AgentRun` responses that embed approvals should include the same fields
  after implementation.
- TypeScript SDK `AgentApproval` fields should be optional to tolerate older
  daemon snapshots.
- Python SDK remains dict-shaped for approvals; documentation may describe the
  new keys, but no typed Python approval class is required.

## Edge Cases

- Older approval rows: explanation fields default to empty string after
  migration.
- Provider omits one or more fields: omitted fields become empty strings.
- Denied approval: explanation fields remain attached to the approval record.
- Legacy compatibility reads: additive fields may appear, but no legacy
  endpoint gains continuation semantics.

## Dependencies

- `docs/architecture/adr-0029-additive-approval-explanation-fields.md`
- `docs/architecture/runtime-contracts.md`
- `docs/reference/http-api.md`
- `src/doge/core/domain/agent_models.py`
- `src/doge/application/agent/run_stepper.py`
- `src/doge/infrastructure/database/agent_schema.sql`
- `src/doge/interfaces/gateway/routers/_response_models.py`
- `packages/doge-sdk-typescript/src/run.ts`
- `web/src/views/ResearchAgentView.vue`
- `tests/fixtures/runtime_contracts/agent_runtime_contract_v1.json`

## Acceptance Criteria

- ADR-0029 is accepted and linked from this CDD.
- Runtime contract prose lists the four optional `AgentApproval` explanation
  fields.
- HTTP API reference documents the fields on approval reads.
- Implementation slices add the fields without removing or renaming existing
  approval fields.
- Approval resolution and entitlement behavior remain unchanged.
- Runtime golden contract, repository/migration tests, OpenAPI checks, SDK
  parity, and Web rendering tests pass for local acceptance.
- Plan closure remains controlled-open at 4 open / 2 passed.

## Non-Goals

- No approval-resolution behavior change.
- No entitlement or governance policy decision change.
- No external/operator gate closure.
- No platform-wide `CaseReview` / home-queue type promotion in this slice.
- No conclusion-evidence matrix, artifact export, or run comparison feature.
- No production posture promotion.

## Verification Plan

Local acceptance:

```text
py -3 -m pytest tests/unit/agent/test_approval_coordinator.py tests/unit/agent/test_run_stepper.py tests/unit/agent/test_repositories.py tests/unit/infrastructure/test_migration_runner.py tests/unit/gateway/test_response_models_wire.py tests/contract/test_approval_resume.py tests/contract/test_platform_api.py tests/contract/test_golden_runtime_contract.py -q
py -3 tools/ci/sdk-contract-check.py
cd web && npm run test -- src/views/ResearchAgentView.spec.ts
cd web && npm run build
py -3 scripts\validate_docs_authority.py
py -3 scripts\validate_docs_maturity_claims.py
py -3 scripts\validate_alpha_maturity_honesty.py
py -3 scripts\validate_docs_links.py
py -3 scripts\validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md
```
