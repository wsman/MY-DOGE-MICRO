# ADR-0008: Vue Web Console Architecture (Vue3 + Vite8 + Pinia + Naive UI + Manual SSE + Virtual Scroll + @pretext Alias)

## Status

Accepted (brownfield — reverse-documented 2026-06-12; the composition is already shipped and build-green)

## Date

2026-06-12

## Last Verified

2026-06-12 — verified against the working tree on branch `cdd-adoption-2026-06-11`: `cd web && npm run build` green, `cd web && npm test` green (3 spec files).

## Decision Makers

Reverse-documented from the existing implementation. Original decisions attributed to the MY-DOGE-MICRO web author; this ADR records the composition as-shipped and the open `@pretext` portability question for future maintainers.

## Summary

The Vue Web Console (Module #11) is a single-page Vue 3 app that renders a Ghostty-style resizable split-tree of panels and consumes the FastAPI Service (Module #9) over JSON + a manual-`fetch` SSE reader. This ADR records the architectural stance that the web console is built on Vue 3.5 + Vite 8 + Pinia 3 + Naive UI 2.44 + lightweight-charts v5, uses three hand-written virtualized components (not a table/grid library), reads SSE via raw `fetch` streaming (not `EventSource`), and resolves a text-layout library (`@pretext`) from a **sibling-project checkout via an absolute path alias** rather than from npm — a portability trade-off that is the headline open risk.

## Engine Compatibility

> This ADR template's "Engine Compatibility" section is engine/game-oriented. For a Product web module, the equivalent fields are the framework/runtime compatibility matrix.

| Field | Value |
|-------|-------|
| **Framework** | Vue 3.5.32 + Vite 8.0.10 + TypeScript ~6.0.2 (`web/package.json:14-35`) |
| **Domain** | Presentation (web SPA) |
| **Knowledge Risk** | LOW — Vue 3 Composition API, Vite, Pinia, Naive UI are all in training data and stable. MEDIUM for lightweight-charts **v5** series-registration API (`useKlineChart.ts:38-66`) which changed from v4. |
| **References Consulted** | `web/src/composables/useKlineChart.ts` (v5 `chart.addSeries(CandlestickSeries, …)`), `web/vite.config.ts` (alias + proxy), `web/tsconfig.app.json` (path alias + lint flags) |
| **Post-Cutoff APIs Used** | `lightweight-charts` v5 `addSeries(SeriesDefinition, options)` (v4 used `addCandlestickSeries(options)` directly) — confirmed against the installed `^5.2.0`. |
| **Verification Required** | Re-validate the `@pretext` alias resolution if the sibling project is moved or if Vite 8's alias semantics change. Re-validate lightweight-charts API if upgrading past v5. |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | [ADR-0007](adr-0007-api-surface-and-cors.md) — the web console is a client of the API surface and CORS stance ADR-0007 establishes. Must be Accepted (it is, as Proposed→tracked) for the dev-proxy + CORS-`*` flow to be sound. |
| **Enables** | None (terminal Presentation module — nothing downstream). |
| **Blocks** | None — but the `@pretext` portability open question blocks any non-original-machine / CI build until resolved. |
| **Ordering Note** | This is the last of the per-module ADRs (0001–0008). ADR-0001 (clean architecture) does NOT directly govern this module because it owns no DB/`_PROJECT_ROOT` code — it is a pure HTTP/SSE client. |

## Context

### Problem Statement

MY-DOGE-MICRO needs a browser-based operator surface that can (a) display multiple data views side-by-side in resizable panels, (b) stream long-running scan progress without blocking the UI, (c) render hundreds of thousands of table rows and arbitrarily long Markdown reports, and (d) reuse a fast canvas-measured text-layout library that already exists in a sibling project (`pretext`). The architecture must be recorded so future maintainers understand why specific non-obvious choices were made — especially the sibling-project path alias and the hand-rolled virtualization.

### Current State

The web console is shipped and build-green. It is a brownfield reverse-documentation target: the composition was chosen before this ADR was written. Notable existing facts:
- Six views, two overlapping registries (`VIEW_REGISTRY` for panels, vue-router for deep links — `views/registry.ts:18-61` vs `router/index.ts:3-13`).
- A hand-ported Ghostty split-tree (`composables/useSplitTree.ts:1-13` cites the Zig source line ranges).
- Three hand-written virtualized components (`VirtualTable`, `VirtualMasonry`, `VirtualMarkdown`) — no `vue-virtual-scroller`/`ag-grid`/TanStack Table dependency.
- SSE read via raw `fetch` + `getReader()`, NOT `EventSource` (`composables/useSSE.ts:22-44`).
- `@pretext` resolved from `D:/Users/WSMAN/Desktop/Coding Task/pretext/src/layout.ts` (`vite.config.ts:5,11`).

### Constraints

- **Local-first**: the API binds to `127.0.0.1:8901` (Module #9 §7); the web console is served from the same machine. No remote clients, no auth.
- **Windows host**: the operator's machine is Windows; the `@pretext` absolute path is Windows-style.
- **Sibling-project reuse**: pretext already exists and is mature; re-implementing or waiting for an npm publish was not the original path of least resistance.
- **No backend coupling**: the web console must not open SQLite/DuckDB or recompute `_PROJECT_ROOT` — it is a pure client (ADR-0001 does not apply here).
- **Large datasets**: CN/US archives can be tens of thousands of rows; reports can be long Markdown. DOM node count must stay bounded.

### Requirements

- Render 6 views in any combination of split panels, restorable across reloads.
- Stream scan progress (SSE) without UI freeze.
- Virtualize tables (fixed row height), masonry (variable height), and Markdown (chunked).
- CJK-aware ticker search ("贵茅" → "贵州茅台").
- Keep build + a deterministic smoke test green with no live API dependency.

## Decision

Adopt the shipped composition as the architectural stance for Module #11, and document its non-obvious choices and their trade-offs:

1. **Vue 3.5 + Vite 8 + Pinia 3 + Naive UI 2.44** as the SPA stack. Pinia owns global state (split-tree singleton, marketData archive state, scanner/SSE state); Naive UI provides the dark-theme component library; Vite 8 provides the dev server (with the `/api` proxy) and the production build.
2. **Two overlapping view registries**: `VIEW_REGISTRY` (panel source of truth, six views incl. `ticker`) and vue-router (five deep-link routes, `ticker` excluded). The split tree is the primary navigation surface; the router is for bookmarkability.
3. **Hand-ported Ghostty split-tree** (`useSplitTree.ts`) over any existing Vue split-pane library, because the Ghostty algorithms (spatial navigation with wrap, equalize-by-leaf-weight, dynamic min-ratio resize) are richer than off-the-shelf options and the port was already done.
4. **Three hand-written virtualized components** over a table/grid library, because the three virtualization strategies differ (fixed-row windowing, variable-height masonry, chunked Markdown with measured-height correction) and pretext already provided the masonry height-prediction primitive.
5. **Manual `fetch`-based SSE reader** (`useSSE.ts`) over `EventSource`, because the scan endpoint is a **POST** (`POST /api/scan/{market}`, Module #9 §4.1) and `EventSource` only supports GET. The reader parses `data:` lines and treats `progress === -1` as error / `progress >= 100` as complete.
6. **`@pretext` sibling-project alias** at an absolute path (`vite.config.ts:5,11`, mirrored in `vitest.config.ts:11,17` and `tsconfig.app.json:6-8`), accepting the portability cost in exchange for reusing the mature sibling text-layout library without an npm publish step.

### Architecture

```
+-----------------------------------------------------------------------+
|  Browser (localhost)                                                  |
|                                                                       |
|  App.vue  ──┬── Naive UI ConfigProvider (darkTheme) + MessageProvider |
|             │                                                         |
|             ├── Toolbar (presets, equalize)                           |
|             └── SplitPane (recursive split-tree root)                 |
|                   └── PanelChrome per leaf                            |
|                         └── <AsyncComponent> = one of 6 views         |
|                                                                       |
|  Pinia stores:  marketData (archive/kline/selection)                  |
|                 scanner    (servers, auto-scan, wraps useSSE)         |
|                                                                       |
|  Composables: useSplitTree (Ghostty port, singleton, localStorage)    |
|               useSSE (raw fetch stream reader)                        |
|               useFuzzySearch / useVirtualScroll / useKlineChart       |
|               usePretextLayout / useTextMeasure  ─┐                   |
|                                                   │ @pretext alias   |
|  Components: VirtualTable / VirtualMasonry / VirtualMarkdown          |
|                                                                       |
+----------------------------------┬------------------------------------+
                                   │ axios (/api prefix, 30s) + raw fetch (SSE)
                                   ▼
+-----------------------------------------------------------------------+
|  FastAPI Service (Module #9) — 127.0.0.1:8901                         |
|  (JSON reads + SSE scan/macro streams; see ADR-0007)                  |
+-----------------------------------------------------------------------+

         @pretext  ──>  D:/.../pretext/src/layout.ts   (SIBLING PROJECT, absolute alias)
                          (prepare / layout / Intl.Segmenter / canvas measure)
```

### Key Interfaces

```
// The SSE contract this module assumes (must match Module #9 §9.1):
//   POST /api/scan/{market}  body: {tdx_path, use_server, server?}
//   response: text/event-stream
//   each event: data: {"progress": int, "message": str}\n
//   progress === -1  -> error sentinel
//   progress >= 100  -> completion

// The alias contract (build-time):
//   '@pretext' -> <absolute>/pretext/src/layout.ts
//   must export: prepare, prepareWithSegments, layout,
//                PreparedText, PreparedTextWithSegments, LayoutResult
//   (consumed at usePretextLayout.ts:3-9 and VirtualMasonry.vue:28)
```

### Implementation Guidelines

- Keep the split-tree as a module-level singleton (`useSplitTree.ts:242-249`) — multiple `useSplitTree()` callers MUST share state.
- Keep SSE as raw `fetch` — do not migrate to `EventSource`; the POST requirement is load-bearing.
- Any new view MUST be added to BOTH `VIEW_REGISTRY` (`views/registry.ts`) and, if it should be deep-linkable, `router/index.ts`. The `ViewId` union (`types/splitTree.ts:22`) is the canonical enumeration.
- Any new composable that transitively imports `@pretext` is NOT unit-testable under jsdom — keep the vitest smoke suite to pure-logic composables and store logic.

## Alternatives Considered

### Alternative 1: Use a virtual-table library (TanStack Table / vue-virtual-scroller / ag-grid)

- **Description**: Replace `VirtualTable` (and possibly `VirtualMasonry`) with an off-the-shelf virtualization library.
- **Pros**: Less hand-maintained code; battle-tested; built-in sorting/filtering.
- **Cons**: None of them do pretext-driven variable-height masonry; TanStack Table virtualizes rows but not the masonry card layout; ag-grid is heavy and license-encumbered for commercial-feel features.
- **Estimated Effort**: Medium (rewrite VirtualTable; still need VirtualMasonry).
- **Rejection Reason**: The three virtualization strategies are genuinely different; a single library would not cover all three, and pretext's height-prediction is the masonry differentiator.

### Alternative 2: Use `EventSource` for SSE

- **Description**: Replace the manual `fetch` reader with the browser's `EventSource` API.
- **Pros**: Built-in auto-reconnect; simpler parsing; standard.
- **Cons**: `EventSource` only supports GET with no request body. The scan endpoint is `POST /api/scan/{market}` with a JSON body (`{tdx_path, use_server, server}`, Module #9 §4.2). Migrating would require either changing the API to GET-with-query-params (a Module #9 contract change) or adding a separate GET SSE endpoint.
- **Estimated Effort**: Large (API contract change downstream).
- **Rejection Reason**: The POST requirement is load-bearing and matches Module #9. Keep raw `fetch`.

### Alternative 3: Publish `@pretext` to npm / vendor it / workspace-alias it

- **Description**: Remove the absolute-path sibling alias by (a) publishing pretext to npm, (b) vendoring `layout.ts` into `web/src/vendor/pretext/`, or (c) using a workspace/relative alias.
- **Pros**: Portability — the build no longer depends on a sibling checkout at an absolute Windows path; CI and other machines work; `package.json` becomes the source of truth.
- **Cons**: (a) npm publish requires a publish pipeline and version-sync discipline; (b) vendoring forks the library and loses upstream fixes; (c) a relative alias still requires the sibling to be checked out, just not at an absolute path.
- **Estimated Effort**: Small (vendoring), Medium (workspace alias), Large (npm publish pipeline).
- **Rejection Reason (for now)**: NOT rejected — this is the headline **open question** (CDD §9 Q1). The current absolute alias was the fastest path to reuse; the portability remediation is tracked as future work, not a permanent stance. Preferred order: vendor → npm publish.

### Alternative 4: Use a split-pane library (e.g. `vue-split-panel`, `allotment`)

- **Description**: Replace the hand-ported Ghostty split-tree with an off-the-shelf split-pane library.
- **Pros**: Less code; community-maintained.
- **Cons**: None provide Ghostty's spatial navigation with wrap-around, equalize-by-leaf-weight, or dynamic min-ratio resize from subtree `minWidth` sums — all of which are implemented (`useSplitTree.ts:134-197,221-235`; `SplitPane.vue:94-122`). The port was already done and is the operator's expected UX.
- **Estimated Effort**: Medium (lose features or re-implement them on top).
- **Rejection Reason**: The Ghostty algorithms are richer than off-the-shelf options and already shipped.

## Consequences

### Positive

- A single, coherent SPA stack (Vue3 + Vite + Pinia + Naive UI) with one dark theme and one state model.
- Rich multiplexer-style panel UX (split/zoom/spatial-nav/equalize) that off-the-shelf libraries do not provide.
- Three virtualization strategies tuned to their content (fixed-row table, variable-height masonry, chunked Markdown) with bounded DOM node counts at any dataset size.
- Reuse of the mature pretext text-layout library without an npm publish step.
- A deterministic, API-mocked vitest smoke suite that runs anywhere (no live FastAPI, no `@pretext` in the test graph).

### Negative

- **`@pretext` absolute-path coupling**: the build breaks if the sibling checkout moves/disappears; non-portable to CI or other machines. (Headline risk; tracked open question.)
- **No SSE reconnect**: a dropped stream without a terminal event can leave the scanner status stuck on `running`. (CDD §5, §9 Q3.)
- **Hand-maintained virtualization**: three components to maintain vs. one library; bug surface is owned, not outsourced.
- **Two overlapping view registries**: a new view must be added in up to three places (`ViewId` union, `VIEW_REGISTRY`, optionally router) — easy to forget.
- **Singleton shared state**: two TickerView panels share `marketData.selectedTicker`/`klineData`; selecting in one overwrites the other (CDD §5, §9 Q5).

### Neutral

- The split-tree is a module-level singleton, not per-route — there is exactly one tree per page load, which matches the multiplexer mental model but differs from a typical multi-route SPA.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Sibling `pretext` checkout moved/deleted → build red | MEDIUM (any machine/CI migration) | HIGH (blocks all builds) | Vendor or npm-publish pretext (CDD §9 Q1); add a build precheck that asserts the alias target exists with a clear error. |
| lightweight-charts v5 API changes on upgrade | LOW (v5 is current) | MEDIUM (chart breaks) | Pin `lightweight-charts` minor version; re-validate `useKlineChart.ts:38-66` on upgrade. |
| SSE stream drops without terminal event → stuck `running` | MEDIUM (network blips on localhost are rare but possible) | LOW (operator can re-trigger) | Add a watchdog in `useSSE` (CDD §9 Q3). |
| jsdom limitations block view-level tests | HIGH (already the case) | LOW (smoke suite still covers pure logic) | Add a Playwright/Cypress E2E against dev server + mocked API for critical paths (CDD §9 Q4). |
| Two TickerView panels share ticker state | MEDIUM (operator splits two ticker panels) | LOW (confusing but recoverable) | Scope ticker state to the leaf handle (CDD §9 Q5). |

## Performance Implications

| Metric | Before (n/a — greenfield web module) | Expected After (current shipped) | Budget |
|--------|--------|---------------|--------|
| DOM nodes (10k-row archive) | n/a | ~`ceil(viewport/32) + 2*8 + 1` rows ≈ 20-40 row nodes | < 1000 nodes |
| Initial bundle (gzip) | n/a | one lazy chunk per view; only mounted views loaded | < 300KB gzip per view |
| SSE scan UI freeze | n/a | none — stream parsed off the render thread; progress via reactive `ref` | 0 main-thread jank |
| Markdown render (long report) | n/a | chunked + measured-height correction; only viewport±300px chunks in DOM | < 100 chunks rendered |

## Migration Plan

This ADR reverse-documents an already-shipped architecture; there is no migration FROM an alternative. The forward migration it implies is the `@pretext` portability remediation:

1. **Decide pretext sourcing** — vendor vs. npm-publish vs. workspace-alias (CDD §9 Q1). Vendoring is lowest-effort.
2. **If vendoring**: copy `pretext/src/layout.ts` (+ its `Intl.Segmenter`/canvas-measure deps) into `web/src/vendor/pretext/`, update the alias to a relative path, remove the sibling-checkout build precondition.
3. **If npm-publish**: publish pretext, add it to `web/package.json` `dependencies`, remove the alias from `vite.config.ts` / `vitest.config.ts` / `tsconfig.app.json`.
4. **Verify**: `npm run build` + `npm test` green on a clean machine without the sibling checkout; add a CI check.

**Rollback plan**: revert the alias changes in `vite.config.ts` / `vitest.config.ts` / `tsconfig.app.json` to the absolute path; the sibling-checkout precondition returns.

## Validation Criteria

- [x] `cd web && npm run build` is green (vue-tsc + vite build).
- [x] `cd web && npm test` is green (vitest, 3 spec files: useFuzzySearch, useVirtualScroll, scanner store).
- [x] The `@pretext` alias resolves in both build and test (mirrored in both configs).
- [x] The six `ViewId` literals match `VIEW_REGISTRY` keys.
- [x] The SSE reader's `{progress, message}` parse matches Module #9's payload.
- [ ] **OPEN**: the `@pretext` dependency is portable (vendored or npm-published) — build green on a machine without the sibling checkout. (CDD §9 Q1.)
- [ ] **OPEN**: explicit `browserslist` declares the browser target. (CDD §9 Q4.)

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|-------------|--------|-------------|--------------------------|
| `design/cdd/vue-web-console.md` | Vue Web Console (Module #11) | "The module must reliably render the split-tree layout, stream scan progress over SSE without freezing the UI, virtualize arbitrarily long tables/Markdown/masonry, and keep the API base URL / SSE endpoint / `@pretext` alias configurable." | Records the stack choice (Vue3+Vite+Pinia+Naive UI), the manual-SSE decision (Alternative 2), the hand-virtualization decision (Alternative 1), and the `@pretext` alias stance (Alternative 3) as the architectural stance with traceable alternatives. |
| `design/cdd/fastapi-service.md` | FastAPI Service (Module #9) | "Depended on by: #11 vue-web-console (the web UI consumes this API)" | This ADR's client-side SSE/JSON contract (§Key Interfaces) is the matching half of the Module #9 §9.1 transport contract. |

## Related

- [ADR-0007](adr-0007-api-surface-and-cors.md) — the upstream API surface and CORS stance this module's dev-proxy + localhost requests rely on.
- [ADR-0001](adr-0001-brownfield-clean-architecture.md) — does NOT directly govern this module (pure HTTP/SSE client, no DB/`_PROJECT_ROOT` code), but governs the upstream modules it consumes.
- `design/cdd/vue-web-console.md` — the Module #11 CDD (this ADR's companion).
- `web/vite.config.ts`, `web/vitest.config.ts`, `web/tsconfig.app.json` — the alias declarations.
- `web/src/composables/useSSE.ts`, `web/src/composables/useSplitTree.ts`, `web/src/composables/usePretextLayout.ts`, `web/src/components/VirtualMasonry.vue` — the load-bearing implementation files.
