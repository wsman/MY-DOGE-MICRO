# Case Workspace Accessibility Tree Smoke

Date: 2026-06-24
Scope: P0d browser-level accessibility preflight for Case Workspace
Result: PASS

Evidence files:

- `production/qa/evidence/manual/case-workspace-ax-tree-2026-06-24.json`
- `production/qa/evidence/manual/case-workspace-ax-tree-2026-06-24.png`

## Checks

The script uses browser `Accessibility.getFullAXTree` against
`/#/cases/case-ax-smoke` with `VITE_DOGE_FEATURE_PLATFORM_SHELL=1` and verifies
the Case Workspace exposes:

- the named Research case workspace container;
- Case Assets controls, including asset type and asset ID input;
- Template controls, including workflow template, question, JSON inputs,
  Preflight, and Execute;
- Memo, Executions, Preflight, Claims, Citations, Eval, Approval, and Decision
  regions;
- Decision type, rationale, and Record controls;
- no primary manual Run ID or Run Link control.

Observed result:

```json
{
  "asset_id_input": true,
  "approval_region": true,
  "case_assets_region": true,
  "citations_region": true,
  "claims_region": true,
  "decision_rationale_input": true,
  "decision_region": true,
  "decision_type_control": true,
  "eval_region": true,
  "execute_button": true,
  "execution_question_input": true,
  "executions_region": true,
  "manual_run_id_not_primary": true,
  "preflight_button": true,
  "preflight_region": true,
  "record_button": true,
  "template_inputs_textarea": true,
  "template_region": true,
  "workflow_template_control": true,
  "workspace_region": true
}
```

## Limitation

This is automated browser accessibility-tree evidence, not a human NVDA,
VoiceOver, or Narrator session. It is a promotion preflight artifact and does
not by itself close a manual screen-reader gate.
