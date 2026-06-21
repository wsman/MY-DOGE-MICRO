# UX And Accessibility Context

## Current UX Sources

- Product visual direction: analytical command console.
- Design rule: dense but legible market intelligence, with status and evidence close to the decision.
- UX source files:
  - `design/ux/interaction-patterns.md`
  - `design/ux/scanner-flow.md`
  - `design/ux/analysis-flow.md`
  - `design/ux/archive-flow.md`
  - `design/ux/ticker-flow.md`
  - `design/ux/accessibility-requirements.md`
  - `design/art/art-bible.md`

## Accessibility Posture

- Accessibility tier: product baseline documented in `design/ux/accessibility-requirements.md`.
- Current status: documented and partially tested; S015 adds Research Agent accessibility semantics.
- Open risks: screen-reader manual pass remains deferred; Core Web Vitals are N/A for the local app context but documented.

## Surface Map

| Surface | UX source | Status |
|---------|-----------|--------|
| Scanner | `design/ux/scanner-flow.md` | documented |
| Analysis | `design/ux/analysis-flow.md` | documented |
| Archive | `design/ux/archive-flow.md` | documented |
| Ticker | `design/ux/ticker-flow.md` | documented |
| Shared interaction patterns | `design/ux/interaction-patterns.md` | documented |
| Research Agent Web view | `web/src/views/ResearchAgentView.vue`, `production/qa/accessibility-sprint-015.md` | tested, manual SR pass pending |
