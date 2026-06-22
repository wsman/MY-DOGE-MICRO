# Research Agent Wave 1 Evidence - 2026-06-21

## Scope

This evidence records the first Wave 1 implementation pass for the Research
Agent Web workspace business loop:

- TypeScript SDK multipart document upload API.
- `/v1/portfolios/import` CSV import API.
- Web document upload/list/select controls.
- Execution profile selector using real backend profile IDs.
- Portfolio CSV import UI binding `portfolio_id` into runs.
- Evidence/Citation drill-down panel.
- Cost/Eval/Routing quality panel.
- Four-pane workspace layout: Input, Research Memo, Evidence, Quality, with
  Timeline spanning the bottom.

## Automated Evidence

| Check | Result | Notes |
|---|---:|---|
| `.\.venv\Scripts\python.exe -m pytest tests/contract/test_v1_api.py tests/unit/test_portfolio_service.py -q` | PASS | `12 passed`; covers existing v1 runtime contracts plus multipart document upload and portfolio CSV import contract tests. |
| `.\.venv\Scripts\python.exe -m py_compile src\doge\application\services\portfolio_import_service.py src\doge\interfaces\api\routers\v1\portfolios.py` | PASS | New backend files compile. |
| `git diff --check` | PASS | No whitespace errors; line-ending warnings only. |

## Web / SDK Test Status

Not executed in this shell: `node` and `npm` are not available on PATH.

Commands still required once Node is available:

```powershell
cd packages/doge-sdk-typescript; npm test; npm run build
cd web; npm test; npm run build
cd web; npx vue-tsc --noEmit
```

Targeted Web/SDK tests added or updated:

- `packages/doge-sdk-typescript/src/__tests__/client.spec.ts`
- `web/src/__tests__/agentApi.spec.ts`
- `web/src/__tests__/agentStore.spec.ts`
- `web/src/stores/documents.spec.ts`
- `web/src/views/ResearchAgentView.spec.ts`

## Manual Browser Walkthrough

Status: **NOT EXECUTED** in this environment because the local shell cannot
start the Vite dev server without `node`/`npm`.

Required walkthrough when Node is restored:

1. Start the API/daemon and open `/research-agent`.
2. Upload a PDF or text document.
3. Confirm the document appears with filename, MIME type, size, and parse state.
4. Select/unselect documents and confirm the next run payload includes checked
   `document_ids`.
5. Select `financial_research`, then `web_research`, and confirm
   `model_policy.execution_profile` is sent.
6. Import a portfolio CSV and confirm returned `portfolio_id` is sent with the
   next run.
7. Run a research question.
8. Verify SSE status, approvals, memo, timeline, evidence/citation candidates,
   and Cost/Eval/Routing metrics.

## Remaining Wave 1 Evidence Gaps

- Browser manual walkthrough evidence.
- Browser SSE reconnect evidence with `Last-Event-ID`.
- Web and TypeScript SDK tests/build/typecheck in a Node-enabled shell.
- Live operator screenshot or recording of the four-pane workspace.

## Verdict

Backend contract evidence is green for the new document/portfolio primitives.
The Web implementation is present in code and has targeted tests authored, but
Wave 1 cannot be closed until the Node/Web verification and manual browser
walkthrough are executed.
