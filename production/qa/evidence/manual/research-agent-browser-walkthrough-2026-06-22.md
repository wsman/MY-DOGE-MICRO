# Research Agent Browser Walkthrough

Date: 2026-06-22
Scope: S017-001 browser verification for the Research Agent business loop
Result: PASS

## Environment

| Check | Result |
|---|---|
| API | Local FastAPI served on `127.0.0.1:8901`; `/api/health` returned `ok`. |
| Web | Vite served on `127.0.0.1:5173`. |
| Node/npm | Temporary Node `v24.17.0`, npm `11.13.0`. |
| Browser | Local Chrome launched headless through Playwright. |

## Browser Workflow Evidence

Evidence files:

- `production/qa/evidence/manual/research-agent-browser-walkthrough-2026-06-22.json`
- `production/qa/evidence/manual/research-agent-browser-walkthrough-2026-06-22.png`
- `production/qa/evidence/manual/research-agent-browser-citation-drilldown-2026-06-22.json`
- `production/qa/evidence/manual/research-agent-browser-citation-drilldown-2026-06-22.png`

The primary browser walkthrough used the real local API and Vite app. Because
the application is a split-pane workspace rather than route-driven, the browser
set `my-doge-split-layout` to open the Research Agent panel directly.

Verified:

- Text document upload renders in the document selector.
- Uploaded document is selected and included in the run payload.
- Execution profile selection sends `model_policy.execution_profile:
  vision_analysis`.
- Portfolio CSV import persists a generated `portfolio-*` id and sends it in
  the next run payload.
- Run creation, SSE completion, approval resolution, event timeline, status,
  and cost/eval panel render without failed HTTP responses.
- Approval button path resolves the pending high-risk approval.

Observed primary payload:

```json
{
  "document_ids_count": 1,
  "portfolio_id": "portfolio-3d761615f907",
  "execution_profile": "vision_analysis"
}
```

## Citation Drill-Down Evidence

The real scripted/local run produced the citation empty state, so a second
browser fixture run intercepted API responses with a populated citation artifact
and verified the UI drill-down behavior in Chrome.

Verified:

- `Citation evidence` list renders a populated row.
- Clicking the row opens the drawer.
- Drawer displays source document `doc-browser`, page `5`, evidence id
  `evd-browser-click`, and snippet `Operating cash flow covered net income.`.

## Notes

- The real backend run did not emit source citations for the local scripted
  fallback, so populated citation drill-down is browser-fixture evidence plus
  component-level coverage, not live-Kimi evidence.
- No failed HTTP responses or browser console errors were recorded in either
  browser pass.
- Playwright Chromium cache was incomplete, so the run used installed local
  Chrome via explicit `executablePath`.
