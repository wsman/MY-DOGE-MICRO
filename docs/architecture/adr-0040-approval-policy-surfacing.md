# ADR-0040: Approval Policy Surfacing

## Status

Accepted

## Date

2026-07-06

## Decision Makers

wsman (product owner) · Codex implementation agent

## Summary

Sprint 031 implements the Approval Policy Surfacing slice from
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`.

The decision is to surface existing workflow-template approval policy metadata
in Web approval panels. The policy source is the already-on-the-wire
`WorkflowTemplate.metadata.contract.approval_policy` object. No new `/v1` route,
response model, SDK field, approval engine behavior, persistence schema, or
production-readiness claim is introduced.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | TypeScript ~6.0.2; Vue 3.5.32; Pinia 3.0.4; Naive UI 2.44.1 |
| **Domain** | Web Research Workspace / Case workspace / Approval governance display |
| **Knowledge Risk** | LOW - narrows existing `WorkflowTemplate.metadata` JSON at render time |
| **References Consulted** | `docs/architecture/adr-0029-additive-approval-explanation-fields.md`, `docs/architecture/adr-0028-additive-session-turn-workflow-field.md`, `web/src/components/approval/ApprovalExplanation.vue`, `web/src/views/ResearchAgentView.vue`, `web/src/views/CaseDetailView.vue`, `src/doge/platform/workspace/template_seed.py`, `C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Focused approval-policy Web tests, full Web test/build, docs/maturity validators, import boundaries, SDK contract parity, plan closure gate |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0028 (workflow slug threading), ADR-0029 (approval explanation metadata), ADR-0037 (case progress/review workspace), ADR-0039 (Analyst Product Home) |
| **Enables** | Approval cards can explain which template policy requirement is attached to the workflow context. |
| **Blocks** | None |
| **Ordering Note** | This ADR is display-only. Approver identity, deadline, delegation, approval history, and policy enforcement changes require separate persistence/API designs. |

## Context

### Problem Statement

Sprint 022 added approval explanation fields such as `why_needed`, `impact`,
`deny_consequence`, and `publish_target`. Those fields explain the approval
request itself, but they do not show which workflow-template policy requirement
triggered the governance posture.

Built-in workflow templates already carry policy metadata under
`metadata.contract.approval_policy`, for example `{"publish": "required"}`.
Research approvals can resolve the matching workflow through `run.workflow`, and
case approvals can resolve it through review executions (`run_id` ->
`template_slug`). The Web UI can therefore display the policy without changing
the daemon contract.

### Constraints

- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  Level 3 SDK/platform `experimental`.
- Do not add, remove, or rename `/v1` routes or HTTP response fields.
- Do not change SDK package source or the 15-surface SDK contract.
- Do not add a typed `approval_policy` field to `WorkflowTemplate`.
- Do not change approval resolution, entitlement, or policy-decision behavior.
- Do not add persistence migrations or new runtime dependencies.
- Do not close external/operator gates.

### Requirements

- Add a platform-store lookup by workflow template slug.
- Narrow `template.metadata.contract.approval_policy` defensively at render time.
- Ignore nested/array policy values rather than inventing ambiguous copy.
- Show one policy row per scalar policy key, after existing approval explanation
  rows.
- Reuse `ApprovalExplanation.vue` in Research and Case approval surfaces.
- Degrade to no policy row when the template, slug, run id, or policy metadata
  is absent.

## Decision

Implement policy surfacing entirely in the Web client.

`web/src/utils/approvalPolicy.ts` owns the JSON narrowing:

```text
WorkflowTemplate.metadata
  -> contract
  -> approval_policy
  -> Record<string, string> | undefined
```

`ApprovalExplanation.vue` accepts an optional policy map and appends rows such
as `Policy · publish: required`. The whole policy dictionary is shown because
there is no canonical mapping from free-form approval actions such as
`publish memo` or `publish_investment_memo` to policy keys such as `publish` or
`trade_action`.

ResearchAgentView reads the currently loaded template from
`store.run?.workflow` and `platformStore.workflowTemplatesBySlug`. It does not
add a second unconditional workflow-template fetch; ScenarioPicker already
loads templates best-effort.

CaseDetailView builds a `policyByRunId` map from
`review.value?.executions ?? []`, using `run_id` and `template_slug`, then
passes that map to CaseApprovalPanel.

### Key Interfaces

```text
web/src/stores/platform.ts
web/src/utils/approvalPolicy.ts
web/src/components/approval/ApprovalExplanation.vue
web/src/views/ResearchAgentView.vue
web/src/components/case/CaseApprovalPanel.vue
web/src/views/CaseDetailView.vue
```

## Alternatives Considered

### Alternative 1: Add `approval_policy` to approval API responses

- **Description**: Copy template policy onto each approval response.
- **Pros**: Simpler client rendering.
- **Cons**: Expands the wire contract and SDK parity for a display-only row.
- **Rejection Reason**: Existing template metadata is already available to the
  Web surfaces that need it.

### Alternative 2: Add a typed SDK `WorkflowTemplate.approval_policy` field

- **Description**: Promote the metadata field into a first-class SDK property.
- **Pros**: Stronger typed discoverability.
- **Cons**: Changes the SDK public surface and duplicates metadata semantics.
- **Rejection Reason**: Sprint 031 is a Web display slice, not an SDK contract
  expansion.

### Alternative 3: Match policy keys to approval action text

- **Description**: Display only the policy row that appears to match the
  approval action.
- **Pros**: Less visual noise.
- **Cons**: Requires heuristics that can be wrong.
- **Rejection Reason**: Showing the whole policy map is more honest than
  inventing an action-to-policy mapping.

## Consequences

### Positive

- Approval cards can answer "which policy triggered" when template metadata is
  available.
- Research and Case approval surfaces stay consistent through the shared
  `ApprovalExplanation` component.
- The implementation is additive and display-only.
- Missing metadata degrades to the previous approval rows.

### Negative

- User-created templates without `approval_policy` still show no policy row.
- Case policy resolution depends on review executions containing `run_id` and
  `template_slug`.
- Policy rows are descriptive metadata, not proof of a new enforcement engine.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Users infer enforcement changed | MEDIUM | MEDIUM | Docs and ADR state this is display-only and behavior is unchanged. |
| Template metadata is missing | MEDIUM | LOW | Render no policy row and preserve existing approval explanation rows. |
| Long policy labels overflow | LOW | LOW | Approval detail labels use overflow wrapping. |
| Test counts drift | LOW | MEDIUM | Policy rows are strictly gated on policy presence; existing no-policy assertions remain green. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/sprint-031-approval-policy-surfacing.md` | Approval cards should show template policy metadata when available. | Reads existing workflow-template metadata and appends policy rows to approval cards. |
| `design/cdd/sprint-022-approval-explanation.md` | Approval renderers should give reviewers enough context to decide. | Extends the existing explanation component with display-only policy context. |
| `design/cdd/sprint-030-analyst-product-home.md` | Approvals are visible from analyst-facing Web surfaces. | Keeps Research and Case approval displays consistent for Home-to-workspace handoff. |

## Performance Implications

- **CPU**: Small client-side object narrowing and row formatting.
- **Memory**: One computed workflow-template slug index and an optional case
  run-policy map.
- **Network**: No new calls beyond existing template loading.
- **Web Load Time**: Negligible; no new runtime dependency.

## Migration Plan

1. Add `workflowTemplatesBySlug` to the platform store.
2. Add the approval policy utility and focused tests.
3. Add optional policy rows to `ApprovalExplanation.vue`.
4. Wire ResearchAgentView to the current run workflow template.
5. Wire CaseDetailView and CaseApprovalPanel through `policyByRunId`.
6. Update reader and governance docs.
7. Run focused Web tests, full Web test/build, governance validators, SDK
   contract parity, plan closure, and whitespace checks.

## Validation Criteria

- `readTemplatePolicy` returns a scalar policy map only when metadata is present.
- `ApprovalExplanation` appends policy rows only when a policy prop is supplied.
- ResearchAgentView renders a policy row when `run.workflow` matches a loaded
  template policy.
- CaseApprovalPanel renders a policy row when `policyByRunId` contains the
  approval run id.
- Platform store exposes workflow templates by slug.
- Web tests and build pass.
- SDK contract remains 15/15.
- Docs authority, links, maturity claims, alpha honesty, import boundaries,
  plan closure, and whitespace checks pass.

## Related Decisions

- ADR-0028: Additive Session Turn Workflow Field
- ADR-0029: Additive Approval Explanation Fields
- ADR-0037: Case Progress Contract
- ADR-0039: Analyst Product Home
