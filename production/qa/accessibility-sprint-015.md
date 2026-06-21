# Accessibility Review - Sprint 015 Research Agent

Generated: 2026-06-21

## Scope

- `web/src/views/ResearchAgentView.vue`
- Existing baseline: `design/ux/accessibility-requirements.md`
- Existing pattern library: `design/ux/interaction-patterns.md`
- Regression test: `web/src/views/ResearchAgentView.spec.ts`

## Findings

| Check | Result | Evidence |
|---|---|---|
| Keyboard path for primary action | Pass | Naive UI `n-button`, `n-select`, and `n-input` are focusable; Run/Approve/Deny remain text buttons |
| Status announcement | Pass | Evidence pane status row now has `role="status"` and `aria-live="polite"` |
| Approval semantics | Pass | Each approval item is a `role="group"` with a risk/status/action label |
| Timeline semantics | Pass | Agent event timeline now exposes `role="list"` and `role="listitem"` |
| Error announcement | Pass | Memo error alert has `role="alert"` and `aria-live="assertive"` |
| Reduced motion / contrast baseline | Pass by inherited baseline | `design/ux/accessibility-requirements.md` Sprint 003 baseline remains applicable |
| Screen-reader manual pass | Deferred | No NVDA/VoiceOver manual session was run in S015 |

## Automated Check

```powershell
cd web
npm test -- --run src/views/ResearchAgentView.spec.ts
```

Result: `1 passed`.

## Core Web Vitals Applicability

Core Web Vitals are scoped **not applicable** for Sprint 015 promotion because
MY-DOGE-MICRO is currently a local loopback operator SPA, not a public hosted
site with SEO, ad conversion, or multi-user browser traffic goals. The practical
gate remains:

- production build succeeds;
- local web tests pass;
- primary workflow screens remain keyboard reachable and announce async status;
- no new layout or rendering regressions are introduced.

If the web console is later hosted or bound beyond loopback, add Lighthouse/Core
Web Vitals evidence to the release checklist before any production-readiness
claim.

## Verdict

Research Agent accessibility passes the S015 local review with one deferred
manual item: screen-reader session evidence. This is adequate for local release
polish but not enough for a public accessibility conformance claim.
