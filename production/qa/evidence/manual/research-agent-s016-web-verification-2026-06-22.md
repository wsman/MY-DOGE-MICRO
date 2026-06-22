# Research Agent S016 Web Verification

Date: 2026-06-22
Scope: Sprint 016 Web Research business loop closure
Result: AUTOMATED WEB/SDK VERIFICATION COMPLETE; BROWSER MANUAL WALKTHROUGH TRANSFERRED TO S017

## Environment Check

| Check | Result |
|---|---|
| `Get-Command node,npm` | Not available on default PATH. |
| Temporary Node/npm | Found at `C:\Users\Aby\AppData\Local\Temp\codex-node-v24.17.0\node-v24.17.0-win-x64`; Node `v24.17.0`, npm `11.13.0`. |
| `web/package-lock.json` | Present; `npm ci` executed successfully. |
| Web implementation files | Present in `web/src/views/ResearchAgentView.vue`, `web/src/components/agent/*`, `web/src/api/documents.ts`, `web/src/api/portfolio.ts`, and stores/tests. |

## Local Verification Performed

| Check | Result |
|---|---|
| `cd web; npm ci` | PASS; follow-up `npm audit` and `npm audit --omit=dev` now report 0 vulnerabilities after lockfile refresh and Vitest `4.1.9` upgrade. |
| Targeted Web vitest | PASS: 4 files, 8 tests. |
| Full Web vitest | PASS: 12 files, 78 tests under Vitest `4.1.9`. |
| `cd web; npm run build` | PASS after normalizing SDK document payloads in `web/src/api/documents.ts`. |
| `cd web; npx vue-tsc --noEmit` | PASS. |
| TypeScript SDK `npm test` | PASS: 1 file, 11 tests under Vitest `4.1.9`. |
| TypeScript SDK `npm run build` | PASS. |
| Browser walkthrough | PASS: `research-agent-browser-walkthrough-2026-06-22.json` and screenshot captured upload, document selection, profile, portfolio import, run, approval, timeline, and cost/eval panel. |
| Browser citation drill-down fixture | PASS: `research-agent-browser-citation-drilldown-2026-06-22.json` and screenshot captured populated citation drawer with source/page/snippet. |
| Sprint 016 targeted Python regression including live-smoke skips | PASS: `120 passed, 6 skipped in 25.32s`. |
| S016 live smoke and provider fixture contract target | PASS: `1 passed, 4 skipped`; live Kimi tests skipped because env gates are unset. |
| `git diff --check` | PASS: no whitespace errors; LF/CRLF warnings only. |
| YAML shape check for governance files | PASS: no tabs or CR-only lines detected. |
| Full YAML parse | NOT RUN: `PyYAML` is not installed in this venv. |

## Required Commands For S017

```powershell
cd web
npm ci
npm test -- --run src/views/ResearchAgentView.spec.ts src/__tests__/agentApi.spec.ts src/__tests__/agentStore.spec.ts src/stores/documents.spec.ts
npm test
npm run build

cd ..\packages\doge-sdk-typescript
npm test
npm run build
```

## Required Browser Scenarios For S017

- Upload one non-sensitive text/PDF-like fixture and one tiny generated image.
- Select documents and run `financial_research` and `vision_analysis` profiles.
- Import a small portfolio CSV.
- Start a run, interrupt/reconnect SSE, and confirm no duplicate terminal event.
- Open citation drill-down and verify source/page/snippet display.
- Confirm cost/eval/routing metadata appears without overlapping UI.

## Closure Decision

Sprint 016 implementation work is complete. S017-001 automated and browser
evidence now exists. Live Kimi and real provider approval remain separate S017
external items.
