# ADR-0032: Workspace Mode and Memo Export

## Status

Accepted

## Date

2026-07-05

## Decision Makers

wsman (product owner) · Codex implementation agent

## Summary

Sprint UX-5 completes the B2 and B5 local UX items from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`. The Web Research Agent
workspace will default to an analyst-facing mode that hides raw runtime
diagnostics, and it will provide browser-local memo export/copy actions for
investment committee handoff.

This decision is UI-local. It does not add `/v1` export routes, SDK methods,
SDK types, persistence tables, or new runtime events.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10; TypeScript ~6.0.2; Vue 3.5.32; Vite 8.0.10; Pinia 3.0.4; Naive UI 2.44.1 |
| **Domain** | Frontend / Research workspace / Local artifact handoff |
| **Knowledge Risk** | LOW — uses existing Vue component state, Pinia store state, Naive UI buttons/icons, and browser Blob/Clipboard/Print APIs |
| **References Consulted** | `docs/reference/python/VERSION.md`, `standards/technical-preferences.md`, `docs/registry/architecture.yaml`, `design/cdd/platform-shell-ui.md`, `design/cdd/bc-06-agent-runtime.md`, `design/cdd/bc-07-knowledge-evidence.md`, `docs/architecture/adr-0020-platform-shell-ui.md`, `docs/architecture/adr-0031-conclusion-evidence-matrix-interaction.md`, `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Web utility tests for memo export shape; ResearchAgentView tests for Analyst/Developer mode and export/copy actions; store tests for local mode state; Web build; governance validators |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0020 (Platform Shell UI), ADR-0026 (Artifact Citation Assembly), ADR-0031 (Conclusion Evidence Matrix Interaction) |
| **Enables** | Sprint UX-5 workspace modes and artifact handoff |
| **Blocks** | Future server-side/PDF export workflows that would otherwise bypass an explicit export contract decision |
| **Ordering Note** | UX-5 uses the artifact and claim/evidence display state already present after UX-4. Server-side export remains a separate future ADR if needed. |

## Context

### Problem Statement

After UX-4, the Research Agent workspace exposes a useful evidence matrix, but
it still mixes analyst-facing review controls with developer diagnostics such
as raw runtime events, compact JSON payloads, token counts, cost metrics, and
routing tags. This makes the default review surface noisier than the investment
committee workflow requires.

The workspace also renders durable memo artifacts but lacks local handoff
actions. Analysts must manually select text to share a memo, IC questions, or
citations.

### Constraints

- Keep the UI honest about the current local-alpha maturity posture.
- Preserve explicit maturity posture: `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.
- Do not compute authoritative support/eval status in the browser.
- Do not add a server export endpoint or SDK public surface.
- Do not add PDF/headless-render dependencies.
- Keep raw runtime diagnostics available for developer inspection.
- Preserve existing evidence matrix and citation drilldown behavior.

### Requirements

- Default the workspace to Analyst mode.
- Hide raw timeline, compact payload JSON, token tag, cost metrics, and routing
  tags unless Developer mode is selected.
- Keep memo, evidence matrix, citation drilldown, approvals, maturity warning,
  input controls, and next-action hints visible in Analyst mode.
- Add Markdown and JSON memo downloads.
- Add Copy IC Questions and Copy citations actions.
- Provide Print through the browser's print path only.
- Keep export payloads Web-local and self-describing.

## Decision

Add UI-only workspace mode state to the agent store and a compact toolbar in
ResearchAgentView.

### Interaction Model

```text
ResearchAgentView toolbar
  -> Analyst mode (default)
       visible: memo, evidence, approvals, maturity, input, next actions
       hidden: token tag, Cost/Eval panel, routing tags, raw timeline/payload
  -> Developer mode
       visible: Analyst content plus runtime diagnostics

Investment memo artifact
  -> memoExport utilities
  -> Markdown download
  -> JSON download
  -> IC question clipboard text
  -> citation clipboard text
  -> browser print
```

### Key Interfaces

The agent store owns only local UI state:

```typescript
const analystMode = ref(true)
function setAnalystMode(enabled: boolean): void
```

The memo export utility emits a Web-local JSON shape:

```typescript
{
  schema_version: 'doge.web.memo_export.v1',
  export_kind: 'investment_memo',
  generated_at: string,
  run: { run_id, workflow, question, status, market, language, document_ids, portfolio_id, created_at, updated_at },
  artifact: { artifact_id, kind, title, created_at, content_markdown },
  ic_questions: string[],
  claims: StructuredClaimDisplay[],
  citations: CitationRecord[],
  metrics: { usage, citation_precision, numerical_consistency, tool_execution_success, support_status, coverage_ratio, numeric_validation }
}
```

This payload is for browser-local handoff and file download only. It is not a
new public API contract.

## Alternatives Considered

### Alternative 1: Leave all diagnostics visible

- **Description**: Keep the current single-mode workspace.
- **Pros**: No state or test changes.
- **Cons**: Analyst review remains cluttered by runtime diagnostics and raw JSON.
- **Rejection Reason**: It leaves B2 incomplete and weakens the default workflow.

### Alternative 2: Add server-side export endpoints

- **Description**: Add `/v1` export routes and SDK methods for Markdown, JSON,
  and PDF.
- **Pros**: Could centralize export semantics and support future automation.
- **Cons**: Expands public contract, SDK parity, authorization, and test scope.
- **Rejection Reason**: UX-5 only needs local artifact handoff from already-loaded
  memo data.

### Alternative 3: Browser-local exports and print

- **Description**: Use client-side Blob downloads, clipboard writes, and
  `window.print()`.
- **Pros**: Completes B5 without new backend or dependency surface.
- **Cons**: Export payload is not a server-governed artifact contract.
- **Rejection Reason**: Chosen, with the payload explicitly marked Web-local.

## Consequences

### Positive

- Analyst mode becomes a cleaner default review surface.
- Developer diagnostics remain one click away without leaking into default
  accessibility tree.
- Memo, questions, and citations can be handed off without manual selection.
- No backend, SDK, or persistence blast radius.

### Negative

- ResearchAgentView owns more UI coordination state.
- Web-local JSON export must be documented as non-authoritative to prevent
  contract drift.
- Clipboard/download tests need browser API shims under jsdom.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Analyst mode hides useful eval signal | MEDIUM | LOW | Keep evidence matrix, support tags, maturity warning, and next actions visible; Developer mode exposes cost/eval details. |
| JSON export mistaken for `/v1` contract | LOW | MEDIUM | Name schema `doge.web.memo_export.v1` and document it as Web-local only. |
| Clipboard unavailable in a browser | LOW | LOW | Provide a textarea fallback for copy actions. |
| Duplicate citations in export | MEDIUM | LOW | Normalize and dedupe by evidence/citation/chunk/key. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/product-concept.md` | Evidence and status should stay close to the decision. | Keeps evidence matrix and citations visible while removing raw runtime noise from the default view. |
| `design/cdd/platform-shell-ui.md` | The shell must consume run summaries, citations, and eval panels without computing authority client-side. | Exports already-loaded memo/artifact/claim/citation data and does not infer support or eval status. |
| `design/cdd/bc-06-agent-runtime.md` | Operators can observe and inspect agent runs with predictable state transitions. | Preserves raw timeline and payloads behind Developer mode. |
| `design/cdd/bc-07-knowledge-evidence.md` | Operators can trace important claims back to source material. | Copy citations and JSON export include normalized citation records. |

## Performance Implications

- **CPU**: Small client-side mapping over already-loaded artifacts, claims,
  events, and memo text.
- **Memory**: One transient Blob per download action.
- **Load Time**: No route or initial-load change.
- **Network**: None.

## Migration Plan

1. Add agent-store `analystMode` state.
2. Add ResearchAgentView toolbar and `v-if` guards for developer-only details.
3. Add `memoExport.ts` utilities for markdown/json/download/copy handling.
4. Extend Web tests for mode behavior and export actions.
5. Record UX-5 CDD, sprint record, and evidence manifest.

## Validation Criteria

- Analyst mode is default and hides token/cost/routing/timeline/raw payload
  content from the DOM.
- Developer mode reveals the same diagnostics.
- Markdown download contains the exact memo content.
- JSON export contains run, artifact, claims, citations, IC questions, and
  metrics but not raw events.
- Copy IC Questions extracts only the memo question section or generates
  claim-review fallback questions.
- Copy citations includes source/page/snippet text.
- Web build and focused tests pass.

## Related Decisions

- ADR-0020: Platform Shell UI
- ADR-0026: Artifact Citation Assembly
- ADR-0030: Structured Claim Contract
- ADR-0031: Conclusion Evidence Matrix Interaction
