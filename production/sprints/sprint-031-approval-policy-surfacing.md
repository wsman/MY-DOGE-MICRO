# Sprint 031 - Approval Policy Surfacing

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-06

## Summary

Sprint 031 implements the Approval Policy Surfacing plan from
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`.

The sprint makes existing workflow-template approval policy metadata visible in
Web Research and Case approval panels while keeping approval behavior,
authorization, API contracts, SDK contracts, persistence, and maturity posture
unchanged.

## Scope

- Add ADR-0040 and this sprint CDD/governance trail.
- Add `workflowTemplatesBySlug` to the Web platform store.
- Add `approvalPolicy.ts` to narrow `metadata.contract.approval_policy`.
- Extend `ApprovalExplanation.vue` with optional policy rows.
- Wire ResearchAgentView to resolve policy from the current run workflow slug.
- Wire CaseDetailView and CaseApprovalPanel through `policyByRunId`.
- Add focused Web tests for the utility, shared approval component, Research
  surface, Case surface, and platform store slug index.
- Update Research Workspace reader docs and active session state.

## Explicitly Out of Scope

- `/v1` API surface changes.
- SDK package source changes.
- Typed `approval_policy` SDK field.
- Persistence schema migration.
- Approval-resolution behavior changes.
- Entitlement, authorization, or policy-decision engine changes.
- Approver/deadline/delegation/history workflow.
- Production readiness declaration.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the UX/product-acceptance and governance-record sprint precedent where no new
story-status tracking is introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-031-approval-policy-surfacing-manifest.md`.

Verification results:

- Focused approval-policy Web suite passed: 5 files, 20 tests.
- Full Web suite passed: 35 files, 158 tests.
- Web build passed.
- SDK contract passed: 15 surfaces, 15 entity parity checks.
- Docs authority, docs links, docs maturity claims, import boundaries,
  ADR/CDD maturity honesty, plan closure, and WSL/Windows Git whitespace checks
  passed.
- Plan closure posture remains controlled open: 4 open / 2 passed.
