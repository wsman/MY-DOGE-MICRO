# Research Agent Accessibility Tree Smoke

Date: 2026-06-22
Scope: S017-006 browser-level accessibility preflight for Research Agent
Result: PASS

## Environment

| Check | Result |
|---|---|
| Browser | Local Chrome via headless CDP |
| Web | Vite dev server on local loopback |
| API fixture | Local fake `/v1/documents` response to avoid backend/proxy noise |
| View | Split layout forced to `research-agent` via `my-doge-split-layout` |

Evidence files:

- `production/qa/evidence/manual/research-agent-ax-tree-2026-06-22.json`
- `production/qa/evidence/manual/research-agent-ax-tree-2026-06-22.png`

## Checks

The script uses Chrome `Accessibility.getFullAXTree` against the rendered
Research Agent view and verifies:

- `Research Agent workspace` is present in the accessibility tree.
- `Agent status idle; tokens 0` is exposed as a `status` live region.
- `Approval requests` is exposed as a named group/generic region.
- `Agent event timeline` is exposed as a `list`.
- `Run` is exposed as a button.
- `Research question` is exposed as a named input/generic control.

Observed result:

```json
{
  "workspace_region": true,
  "status_live_region": true,
  "approval_group_label": true,
  "timeline_list": true,
  "run_button": true,
  "research_question": true
}
```

## Limitation

This is real Chrome accessibility-tree evidence, not a human NVDA, VoiceOver,
or Narrator session. It strengthens S017-006 preflight evidence but does not
close the manual screen-reader pass.
