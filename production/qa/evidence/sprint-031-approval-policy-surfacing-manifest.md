# Sprint 031 - Approval Policy Surfacing Manifest

> Sprint: 031 (Approval Policy Surfacing)
> Date: 2026-07-06
> Status: Local implementation complete; final verification passed.

## Scope

This manifest records local evidence for surfacing existing workflow-template
approval policy metadata in Web approval panels.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0040-approval-policy-surfacing.md` records the display-only decision. |
| CDD | `design/cdd/sprint-031-approval-policy-surfacing.md` records acceptance criteria. |
| Policy source | `WorkflowTemplate.metadata.contract.approval_policy` remains the read-side source. |
| Store lookup | `web/src/stores/platform.ts` exposes `workflowTemplatesBySlug`. |
| Policy utility | `web/src/utils/approvalPolicy.ts` narrows and formats scalar policy metadata. |
| Shared approval display | `web/src/components/approval/ApprovalExplanation.vue` appends optional policy rows. |
| Research surface | `web/src/views/ResearchAgentView.vue` resolves policy from the current run workflow slug. |
| Case surface | `web/src/views/CaseDetailView.vue` and `web/src/components/case/CaseApprovalPanel.vue` resolve policy by run id. |
| Focused tests | `approvalPolicy.spec.ts`, `ApprovalExplanation.spec.ts`, `CaseApprovalPanel.spec.ts`, `ResearchAgentView.spec.ts`, and `platform.spec.ts`. |
| Reader docs | `docs/start-here/research-workspace.md` describes approval policy rows as template metadata. |
| Session state | `production/session-state/active.md` records Sprint 031 as the current local implementation. |

## Verification Commands

```bash
cd web && npm run test -- --run src/utils/approvalPolicy.spec.ts src/components/approval/ApprovalExplanation.spec.ts src/components/case/CaseApprovalPanel.spec.ts src/views/ResearchAgentView.spec.ts src/stores/platform.spec.ts
cd web && npm run test
cd web && npm run build
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0040-approval-policy-surfacing.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-031-approval-policy-surfacing.md
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/a038a698-harmonic-mango.md
git diff --check
```

## Verification Results

| Gate | Result |
|---|---|
| Focused approval-policy Web suite | Passed: 5 files, 20 tests. |
| Full Web suite | Passed: 35 files, 158 tests. |
| Web build | Passed. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Docs authority | Passed. |
| Docs links | Passed: 98 markdown files validated. |
| Docs maturity claims | Passed. |
| Import boundaries | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0040 and Sprint 031 CDD. |
| Plan closure | Passed with controlled open posture: 4 open / 2 passed. |
| Whitespace | Passed with WSL and Windows Git `diff --check`. |

## Posture

- Production posture unchanged.
- No external/operator gates are closed by this sprint.
- No `/v1` route, SDK package source, persistence schema, approval-resolution
  behavior, authorization behavior, or production readiness declaration is part
  of this sprint.
