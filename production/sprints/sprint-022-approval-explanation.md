# Sprint 022 — Approval Explanation Metadata

> Status: **Local Implementation Complete / Ready for Local Acceptance**
> Branch: `main` · Date: 2026-07-05
> Plan: `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`
> CDD: [design/cdd/sprint-022-approval-explanation.md](../../design/cdd/sprint-022-approval-explanation.md)
> Manifest: [production/qa/evidence/sprint-022-approval-explanation-manifest.md](../qa/evidence/sprint-022-approval-explanation-manifest.md)
> Predecessor: [Sprint UX-2](sprint-ux-2-scenario-completion-and-run-readiness.md)

## Context

UX-2 explicitly deferred approval explanation fields because they require
coordinated domain, persistence, API, SDK, and Web changes. Sprint 022 closes
that local scope with an additive approval metadata contract and implementation.

The target is an additive `AgentApproval` expansion with four optional fields:
`why_needed`, `impact`, `deny_consequence`, and `publish_target`.

## Delivered

### Slice 0 — ADR and CDD

- ADR-0029 records the additive approval explanation fields, field semantics,
  non-goals, migration outline, and validation criteria.
- The Sprint 022 CDD records user promise, contract target, edge cases,
  dependencies, and acceptance criteria.

### Slice 1 — Domain, Stepper, and Provider Content

- `AgentApproval` now carries optional `why_needed`, `impact`,
  `deny_consequence`, and `publish_target` strings.
- `AgentRun.add_approval` accepts the fields as keyword-only metadata while
  preserving existing positional call sites.
- Run stepper copies the fields from `ToolResult.data` and includes them in
  `APPROVAL_REQUESTED` event payloads.
- Governance providers populate explanation text for publish, rebalance, and
  generic approval flows.

### Slice 2 — Persistence

- Fresh SQLite schemas include the four approval explanation columns.
- Legacy local databases get an idempotent runtime migration.
- Runtime repositories and transaction writes round-trip the fields.

### Slice 3 — API and SDK Contract

- `/v1/runs/{run_id}/approvals` has an `ApprovalListResponse` response model
  backed by `ApprovalResponse`.
- `tools/ci/sdk-contract-check.py` now includes `ApprovalResponse` ↔
  TypeScript `AgentApproval` parity.
- TypeScript SDK `AgentApproval` exposes the fields as optional metadata.
- Python and TypeScript SDK READMEs document the optional keys.

### Slice 4 — Web Approval Detail Rows

- ResearchAgentView approval cards render populated explanation rows and hide
  empty rows.
- Approval accessible labels include `why_needed` when present.

### Slice 5 — Tests and Reference Alignment

- `docs/architecture/runtime-contracts.md` lists the four optional
  `AgentApproval` explanation fields as additive contract metadata.
- `docs/reference/http-api.md` documents the fields on `/v1` approval reads and
  legacy approval reads.
- Runtime, migration, repository, OpenAPI, SDK parity, golden contract, and Web
  tests cover the new fields.

### Slice 6 — Governance Closeout

- The Sprint 022 manifest records scope, implementation evidence, posture
  invariants, and validators.
- `production/session-state/active.md` records Sprint 022 as local
  implementation complete.
- Sprint 022 is not registered in `production/sprint-status.yaml`, following
  the UX/product-acceptance precedent.

## Posture

- `production_ready: false`; `stable_declaration: forbidden`;
  `level_3_sdk_platform: experimental`.
- External/operator gates S017-003 / W3-live / AUTH-prod / S017-007 remain
  open.
- S017-002 and S017-006 remain passed.
- Closure gate remains controlled-open at 4 open / 2 passed.
- No external evidence was fabricated.

## Verification

Focused verification completed:

- Python/API/runtime: `62 passed`.
- Governance/tool provider regression: `34 passed`.
- SDK contract: `sdk-contract-check passed (13 surfaces, 13 entity parity checks)`.
- Web focused test: `ResearchAgentView.spec.ts` passed.
- Web build passed.
- Docs authority, docs maturity claims, alpha maturity honesty, docs links,
  import boundaries, and plan closure gate passed; closure posture remains
  4 open / 2 passed.

## Non-Goals

- No approval-resolution behavior change.
- No entitlement or governance policy decision change.
- No external/operator gate closure.
- No maturity promotion.
- No conclusion-evidence matrix, artifact export, run comparison, or SDK
  cookbook scope.
