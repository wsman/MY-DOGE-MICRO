# Sprint 031 CDD: Approval Policy Surfacing

Status: Ready for Acceptance
Date: 2026-07-06

## User Promise

A Web analyst or case reviewer can inspect an approval and, when the workflow
template provides policy metadata, see the relevant policy requirements next to
the existing business explanation rows.

## Delivered Contract

Sprint 031 implements the Approval Policy Surfacing plan in
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`:

- `WorkflowTemplate.metadata.contract.approval_policy` remains the read-side
  policy source.
- `web/src/stores/platform.ts` exposes `workflowTemplatesBySlug` for existing
  loaded templates.
- `web/src/utils/approvalPolicy.ts` defensively narrows and formats policy
  metadata.
- `ApprovalExplanation.vue` accepts optional policy metadata and appends policy
  rows after the existing `why_needed`, `impact`, `deny_consequence`, and
  `publish_target` rows.
- `ResearchAgentView.vue` resolves policy from `store.run?.workflow` and the
  platform template slug index.
- `CaseDetailView.vue` builds `policyByRunId` from `review.executions`;
  `CaseApprovalPanel.vue` passes the matching policy to `ApprovalExplanation`.
- Focused Web tests cover utility behavior, shared approval rendering,
  Research approval policy display, Case approval policy display, and platform
  slug indexing.

## Non-Goals

- No `/v1` route, field, route-count, or response-model change.
- No SDK package source or public-surface change.
- No typed `approval_policy` field on `WorkflowTemplate`.
- No persistence migration or new runtime dependency.
- No approval-resolution behavior change.
- No entitlement, authorization, or policy-decision engine change.
- No approver/deadline/delegation/history workflow.
- No external/operator gate closure.
- Current maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.

## Detailed Behavior

### Policy Source

The only policy source for this sprint is:

```text
WorkflowTemplate.metadata.contract.approval_policy
```

The value is treated as optional JSON metadata. Renderers should show no policy
row when the template, contract, approval policy object, run workflow slug, or
case execution link is missing.

### Policy Rows

Scalar policy entries are rendered as detail rows:

| Source key | Label | Value |
|------------|-------|-------|
| `publish` | `Policy · publish` | Stringified scalar value |
| `trade_action` | `Policy · trade_action` | Stringified scalar value |

Nested objects and arrays are ignored because the UI does not have a canonical
way to render them as honest policy text.

### Research Surface

The Research workspace resolves the policy from the current run workflow slug.
It reuses templates that ScenarioPicker loads best-effort and does not issue a
second unconditional template fetch.

### Case Surface

The Case workspace resolves policy by `run_id`:

```text
approval.run_id
  -> review.executions[].run_id
  -> execution.template_slug
  -> workflowTemplatesBySlug[template_slug]
  -> metadata.contract.approval_policy
```

Any missing link degrades to no policy row.

## Dependencies

- `docs/architecture/adr-0040-approval-policy-surfacing.md`
- `docs/architecture/adr-0029-additive-approval-explanation-fields.md`
- `web/src/stores/platform.ts`
- `web/src/utils/approvalPolicy.ts`
- `web/src/components/approval/ApprovalExplanation.vue`
- `web/src/views/ResearchAgentView.vue`
- `web/src/components/case/CaseApprovalPanel.vue`
- `web/src/views/CaseDetailView.vue`

## Acceptance Criteria

- `workflowTemplatesBySlug` indexes loaded templates by `slug`.
- `readTemplatePolicy` returns `undefined` for absent, non-object, or empty
  policy data.
- `readTemplatePolicy` accepts string, number, and boolean policy values and
  ignores nested objects or arrays.
- `formatPolicyRows` returns deterministic `policy-*` keys and `Policy · <key>` labels.
- `ApprovalExplanation` renders no policy rows unless a policy prop is supplied.
- Existing no-policy approval rendering remains unchanged.
- Research approval cards show policy rows when the current run workflow slug
  matches a loaded template policy.
- Case approval cards show policy rows when `policyByRunId` contains the
  approval `run_id`.
- Full Web test and build pass.
- SDK contract remains 15 surfaces / 15 parity checks.
- Docs and maturity validators preserve Local Alpha honesty.

## Validation Plan

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

## Local Verification Result

Final local verification passed. Focused approval-policy Web tests, full Web
tests, Web build, SDK contract parity, docs authority/links/maturity validators,
import boundaries, ADR/CDD honesty checks, plan closure, and WSL/Windows Git
whitespace checks all passed. Evidence is recorded in
`production/qa/evidence/sprint-031-approval-policy-surfacing-manifest.md`.

## Out of Scope

- SDK high-level `client.research.create_memo` helper.
- Python typed result model expansion.
- Web memo editor/version history.
- Operator TUI or support-bundle changes.
- Approval approver/deadline/delegation/history persistence.
- New API routes or production readiness work.
