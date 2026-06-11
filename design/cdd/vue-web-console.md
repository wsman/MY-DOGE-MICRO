# CDD: Vue Web Console (Module #11)

> **Module #11** — Category: **Presentation**
> **Slug**: `vue-web-console`
> **Status**: Reverse-documented (brownfield) — 2026-06-12; vitest smoke suite added 2026-06-12 (useFuzzySearch + useVirtualScroll + scanner store)
> **Depends on**: #9 `fastapi-service` (HTTP JSON + SSE), #2 `market-data-storage` (transitively, via the API)
> **Depended on by**: (terminal Presentation surface — nothing depends on this module)
> **Source files reverse-documented**: `web/src/{App,main}.vue?`, `web/src/router/index.ts`, `web/src/views/{registry,ScannerView,TickerView,AnalysisView,InsightsView,CnArchiveView,UsArchiveView}.{ts,vue}`, `web/src/components/{SplitPane,PanelChrome,VirtualTable,VirtualMasonry,VirtualMarkdown}.vue`, `web/src/composables/{useFuzzySearch,useVirtualScroll,useKlineChart,useSSE,useSplitTree,usePretextLayout,useTextMeasure}.ts`, `web/src/stores/{marketData,scanner}.ts`, `web/src/api/{client,config,data,scanner}.ts`, `web/src/types/{report,splitTree,stock}.ts`, `web/vite.config.ts`, `web/vitest.config.ts`, `web/tsconfig*.json`, `web/package.json`
> **Related ADRs**: [ADR-0008](../../docs/architecture/adr-0008-web-architecture.md) (**this module's** decision — Vue3 + Vite8 + Pinia + Naive UI + SSE + virtual-scroll + the external `@pretext` sibling-project alias). [ADR-0007](../../docs/architecture/adr-0007-api-surface-and-cors.md) (the upstream API contract + CORS the dev-server proxy relies on). No ADR-0001 forbidden-pattern remediation is owned here — this module consumes the API over HTTP and owns no DB/`_PROJECT_ROOT` code; its tracked debt is the external `@pretext` path-portability question (§6, §7, §9).

---

## 1. Overview

The Vue Web Console is the browser-facing operator surface of MY-DOGE-MICRO: a single-page Vue 3 application (`web/src/App.vue`, `web/src/main.ts:1-9`) that mounts a Ghostty-style resizable split-tree of panels (`App.vue:10,138-139`; `composables/useSplitTree.ts`) and lets the operator drive the whole platform from a tab. Each leaf panel renders one of six registered views (`views/registry.ts:18-61`) — Scanner, Ticker, A-Share Archive, US Market Archive, Insights, Analysis — and the operator can split, zoom, resize, and spatially navigate panels exactly like terminal multiplexer panes (`App.vue:16-77`). The console consumes the FastAPI Service (Module #9) over a JSON API for reads and Server-Sent Events for scan progress (`composables/useSSE.ts`; `api/scanner.ts:3-11`), renders hundreds of thousands of table rows and arbitrarily long Markdown reports through three virtualized components (`VirtualTable`, `VirtualMasonry`, `VirtualMarkdown`), and uses an external sibling-project text-layout library — `@pretext`, aliased at `../../pretext/src/layout.ts` — for canvas-measured, two-phase masonry layout (`composables/usePretextLayout.ts:1-9`; `vite.config.ts:5-12`). It is a brownfield UI: the split-tree is a hand-ported port of Ghostty's Zig `split_tree.zig` algorithms (`useSplitTree.ts:1-13`), the fuzzy search is `Intl.Segmenter`-based CJK-aware matching inspired by pretext's `analysis.ts` (`useFuzzySearch.ts:1-5`), and the k-line chart uses the lightweight-charts v5 series-registration API (`useKlineChart.ts:38-66`). Build is green (`vue-tsc -b && vite build`); a vitest smoke suite covers the pure-arithmetic composables and one Pinia store.

## 2. User Promise / JTBD

**Operator JTBD**: "From my browser, on one screen, see everything MY-DOGE-MICRO is doing at once — kick off a CN/US scan and watch its progress stream in, browse the price archive I just downloaded, search for a ticker by code or Chinese name and pull its candlestick chart, and read the latest macro and research reports — in any combination of side-by-side panels I can split, resize, zoom, and keyboard-navigate, all talking to one local API and never blocking the UI on a huge table or a long report."

**The module must reliably**:
- Render the split-tree layout from persisted state on load (`useSplitTree.ts:242-249,75-85`), restore the active panel, and survive a reload (localStorage key `my-doge-split-layout`, `useSplitTree.ts:25,284`).
- Stream scan progress over SSE without freezing the UI, surface the in-progress bar, and return the panel to idle on completion or error (`composables/useSSE.ts:15-76`; `stores/scanner.ts:114-138`).
- Virtualize arbitrarily long tables (`VirtualTable.vue`) and Markdown (`VirtualMarkdown.vue`), and masonry-layout variable-height cards (`VirtualMasonry.vue`), so the DOM node count stays bounded regardless of dataset size.
- Let the operator search tickers with Latin or CJK partial queries ("贵茅" → "贵州茅台") and return ranked results (`useFuzzySearch.ts:30-95`; `views/TickerView.vue:93-116`).
- Keep the API base URL, SSE endpoint, and the external `@pretext` alias configurable without source edits to view or store code (§7).
- Never make the tests depend on a live FastAPI process: the vitest suite mocks/stubs the API layer and exercises only pure logic (§8, §9).

**The module does NOT yet keep** (open questions, §9): a configurable `@pretext` path (it is hard-absolute-pathed to a sibling checkout), an explicit loading/empty/error triad on every view (Analysis/Insights/CnArchive/UsArchive render `n-spin`/`n-empty` inconsistently), an automated SSE-reconnect strategy (a dropped stream leaves `isRunning=true` until the worker thread closes — §5), or end-to-end/interaction tests (only the pure-logic smoke suite exists).

## 3. Detailed Behavior

### 3.1 Application bootstrap (`web/src/main.ts`, `web/src/App.vue`)

- `main.ts:6-9` creates the app, installs Pinia (`createPinia()`) and the router, and mounts to `#app`. Pinia is therefore the global state owner before any view mounts.
- `App.vue` is a single full-viewport flex column: a 36px toolbar (`App.vue:84-136`) over a split-tree root (`App.vue:137-141`). It wraps everything in `n-config-provider :theme="darkTheme"` + `n-message-provider` (`App.vue:81-83`).
- Layout presets are exposed as toolbar buttons (1 / h-split / v-split / quad) that call `splitTree.applyPreset(p)` (`App.vue:16-18`; `useSplitTree.ts:469-507`). The `quad` preset hard-codes a scanner→ticker→us-archive→insights four-leaf tree (`useSplitTree.ts:493-501`).
- Global keyboard shortcuts are bound on `window` in `onMounted`/`onUnmounted` (`App.vue:76-77`): `Ctrl+Shift+H`/`V` split the active panel, `Ctrl+W` closes it (guarded by `canClose()`), `Ctrl+Enter` toggles zoom, `Alt+Arrows` does spatial navigation (`App.vue:24-74`). The split/zoom/close all delegate to `useSplitTree()`.

### 3.2 The view registry and router (`web/src/views/registry.ts`, `web/src/router/index.ts`)

There are **two** view registries in this module — they overlap but are NOT identical, and this is intentional:

- **`VIEW_REGISTRY`** (`registry.ts:18-61`) is the *panel* registry: the source of truth for what a split-tree leaf can display. It is a `Record<ViewId, ViewRegistryEntry>` keyed by the six `ViewId` literals defined in `types/splitTree.ts:22`. Each entry has `{id, label, icon, loader, minWidth}`. `loader` is a dynamic `import()` so only mounted views are bundled (`registry.ts:23,30,37,44,52,59`). `minWidth` (420/350/350/380/300/300 px) drives the SplitPane drag-resize floor (`SplitPane.vue:94-101`).
- The six registered views are: `scanner`, `cn-archive`, `us-archive`, `ticker`, `insights`, `analysis` (`registry.ts:19-60`).
- `ALL_VIEW_IDS` (`registry.ts:63`) and `VIEW_SELECT_OPTIONS` (`registry.ts:66-69`) are derived for the panel-chrome view switcher (`PanelChrome.vue:69,74-78`).
- **The vue-router** (`router/index.ts:3-13`) is a *separate, smaller* registry using `createWebHashHistory()`. It maps five top-level hash routes (`/scanner`, `/cn-archive`, `/us-archive`, `/insights`, `/analysis`) and redirects `/` → `/scanner` (`router/index.ts:6-12`). **Note**: `ticker` has NO router route — it is reachable only as a panel inside the split tree, not as a standalone URL. The router is mounted (`main.ts:8`) but the split tree is the primary navigation surface; the router exists for deep-linking/bookmarkability of the five non-ticker views and is not the operator's main entry point.

### 3.3 The six views

| View | File | Job | Key dependencies |
|---|---|---|---|
| **Scanner** | `views/ScannerView.vue` | CN/US TDX data-source manager: server dropdown + latency test + scan trigger + auto-scan toggle/interval + shared progress bar + log | `stores/scanner.ts`, `n-progress`/`n-log` |
| **Ticker** | `views/TickerView.vue` | Ticker search (code or CN/EN name) → candlestick + volume + MA5/MA20 chart | `stores/marketData.ts`, `composables/useKlineChart.ts`, `composables/useFuzzySearch.ts`, `api/data.ts` |
| **A-Share Archive** | `views/CnArchiveView.vue` | Virtualized table of the CN price archive, ticker-name toggle, infinite scroll, row-click → loads kline | `stores/marketData.ts`, `VirtualTable.vue` |
| **US Market Archive** | `views/UsArchiveView.vue` | Same as CnArchive for the US market (no name toggle) | `stores/marketData.ts`, `VirtualTable.vue` |
| **Insights** | `views/InsightsView.vue` | Three tabs: Macro reports (masonry), Research reports (masonry), Stock notes (tracked tickers); modal renders Markdown | `VirtualMasonry.vue`, `api/client.ts`, `types/report.ts` |
| **Analysis** | `views/AnalysisView.vue` | Research-report grid + Markdown modal (simpler/older variant of Insights' research tab) | `api/client.ts`, `types/report.ts` |

Per-view specifics worth citing:
- ScannerView sorts servers ok-first by latency asc, prepends an "Auto (fastest)" option, and renders custom label/tag slots via `h()` (`ScannerView.vue:129-187`). Auto-scan uses `setInterval` at `interval * 60 * 1000` ms (`scanner.ts:146-148`).
- TickerView loads both markets' ticker-name maps with `Promise.allSettled` (`TickerView.vue:67-80`), pools them, and filters by the selected market before fuzzy search (`TickerView.vue:99-101`). It also reacts to *external* selection (a row click in an Archive view sets `store.selectedTicker`, which TickerView watches) (`TickerView.vue:143-153`).
- CnArchiveView builds `VirtualTable` columns from the store's `columns` array, special-casing the `ticker` column to render either the code or the CN name depending on `store.showNames` (`CnArchiveView.vue:36-55,57-62`). Infinite scroll is `@scroll-end` → `store.loadMoreRows('cn')` (`CnArchiveView.vue:71-75`).
- InsightsView transforms reports into `MasonryItem[]` whose `text` field is the height-prediction input, and carries the raw report in `item.raw` (`InsightsView.vue:119-133`). The `asMacro`/`asResearch` casts (`InsightsView.vue:104-105`) narrow the generic `raw: unknown` slot back to the typed report.

### 3.4 The split-tree layout (Ghostty-style)

- `composables/useSplitTree.ts` is a hand-port of Ghostty's `split_tree.zig`. The file header (`useSplitTree.ts:1-13`) cites the source line ranges: `split()` L505-569, `remove()` L576-613, `resizeInPlace` L483-495, `equalize()` L759-795, `spatial()` L968-1048, `nearest()` L390-474.
- The tree is a binary tree of `LeafNode` (`{type:'leaf', handle, viewId}`) and `SplitNode` (`{type:'split', handle, layout:'horizontal'|'vertical', ratio, left, right}`) (`types/splitTree.ts:32-53`). `ratio` is clamped to `[0.05, 0.95]` (`useSplitTree.ts:26-27,382`).
- State is a **module-level singleton** `reactive<SplitTreeState>` (`useSplitTree.ts:242-249`) hydrated from `localStorage['my-doge-split-layout']` on import (`useSplitTree.ts:75-85`), defaulting to a single `scanner` leaf. This means every `useSplitTree()` caller shares the same tree — there is exactly one split tree per page.
- Operations: `split` (replace leaf with a split containing the old leaf + a new leaf, `useSplitTree.ts:299-330`), `remove` (replace parent with sibling, refuse on last panel / root, `useSplitTree.ts:336-373`), `resize` (clamp ratio, `useSplitTree.ts:379-384`), `equalize` (recursive per-layout leaf weighting, `useSplitTree.ts:221-235,390-393`), `zoom`/`toggleZoom` (`useSplitTree.ts:396-404`), spatial nav with wrap-around (`useSplitTree.ts:134-197,429-433`), linear nav with wrap (`useSplitTree.ts:436-465`), and four presets (`useSplitTree.ts:469-507`).
- `SplitPane.vue` renders the tree recursively. Leaf nodes get `PanelChrome`; split nodes render two child `SplitPane`s plus a 4px divider (`SplitPane.vue:87,22-48`). The divider drag handler (`SplitPane.vue:103-144`) computes dynamic min ratios from each subtree's `minWidth` sum and refuses to start a drag if constraints are unsatisfiable (`SplitPane.vue:118-122`). Zoom mode renders only the zoomed leaf (`SplitPane.vue:2-10`).
- `PanelChrome.vue` is the leaf header: a view `<n-select>` switcher (`PanelChrome.vue:3-11`) and four buttons (split H, split V, zoom, close) (`PanelChrome.vue:12-49`). The view body is lazy-loaded via `defineAsyncComponent(entry.loader)` keyed by `node.handle` so the same view in two panels gets independent state (`PanelChrome.vue:52,74-78`).
- Persistence is debounced 300ms (`useSplitTree.ts:281-286`); presets use `forcePersist()` (`useSplitTree.ts:288-291,506`).

### 3.5 Virtualized components

| Component | File | Virtualization strategy | Height source |
|---|---|---|---|
| **VirtualTable** | `components/VirtualTable.vue` | Fixed-row-height windowing via `useVirtualScroll` (`VirtualTable.vue:80-84`); translateY offset on the row container (`VirtualTable.vue:18`); emits `scrollEnd` near the bottom for infinite scroll (`VirtualTable.vue:92-101`) | Fixed `rowHeight` (default 32, `VirtualTable.vue:67`) |
| **VirtualMasonry** | `components/VirtualMasonry.vue` | Variable-height masonry: prepare all texts once, compute column layout + per-card height via pretext `layout()`, position absolutely, then cull by viewport+buffer (`VirtualMasonry.vue:84-148,151-155`) | pretext `layout(prepared, textWidth, lineHeight).height` + padding (`VirtualMasonry.vue:124-127`) |
| **VirtualMarkdown** | `components/VirtualMarkdown.vue` | Chunked Markdown: split source into `linesPerChunk`-line chunks, render each with `markdown-it`, predict height (`lines × lineHeight`), measure actual height after mount and correct (`VirtualMarkdown.vue:52-84,143-159`), cull chunks outside viewport±300px (`VirtualMarkdown.vue:117-135`) | `actualHeight ?? predictedHeight` (`VirtualMarkdown.vue:138-140`) |

All three batch scroll/resize work through `requestAnimationFrame` to avoid per-event reflow (`useVirtualScroll.ts:54-62`; `VirtualMasonry.vue:158-167`; `VirtualMarkdown.vue:161-171`) and observe container size with `ResizeObserver` (`useVirtualScroll.ts:74-87`; `VirtualMasonry.vue:173-188`; `VirtualMarkdown.vue:176-188`).

### 3.6 Composables

| Composable | File | Responsibility |
|---|---|---|
| `useFuzzySearch` | `composables/useFuzzySearch.ts` | CJK-aware fuzzy ranking: exact(100)/prefix(80)/contains(60)/grapheme-subsequence(40)/token(≤95) scoring with `Intl.Segmenter` (`useFuzzySearch.ts:65-95,97-129`). Exports `tokenize`, `scoreMatch`, `graphemeSubsetMatch` for direct unit testing (`useFuzzySearch.ts:34,51,65`). |
| `useVirtualScroll` | `composables/useVirtualScroll.ts` | Pure-arithmetic fixed-row-height windowing (`useVirtualScroll.ts:37-52`). Returns `{totalHeight, visibleRange, onScroll, syncScrollTop}`. The `visibleRange` computed is the unit-testable seam. |
| `useKlineChart` | `composables/useKlineChart.ts` | lightweight-charts v5 candlestick + volume histogram + MA5/MA20 line series (`useKlineChart.ts:38-66`); resize-aware (`useKlineChart.ts:68-77`); disposes on unmount (`useKlineChart.ts:129-137`). |
| `useSSE` | `composables/useSSE.ts` | Manual `fetch`-based SSE reader: streams `data:` lines, parses `{progress, message}`, treats `progress === -1` as error and `progress >= 100` as complete (`useSSE.ts:36-69`). Returns `{progress, messages, isRunning, error, start}`. |
| `useSplitTree` | `composables/useSplitTree.ts` | The split-tree singleton + all mutation/navigation/preset ops (§3.4). |
| `usePretextLayout` | `composables/usePretextLayout.ts` | Wraps pretext's two-phase `prepare`/`prepareWithSegments` + `layout` cycle in Vue reactivity (`usePretextLayout.ts:28-121`). Imports from `@pretext` (`usePretextLayout.ts:3-9`). |
| `useTextMeasure` | `composables/useTextMeasure.ts` | Two-level canvas text-measurement cache (`Map<font, Map<text, width>>`); prefers `OffscreenCanvas`, falls back to DOM canvas (`useTextMeasure.ts:15-28`). `shared` flag returns a module singleton (`useTextMeasure.ts:48-50`). |

### 3.7 Pinia stores

| Store | File | Owns |
|---|---|---|
| `marketData` | `stores/marketData.ts` | Archive table state: `tables`, `currentTable`, `rows`/`columns`/`total`, paginated + infinite-scroll (`allRows`, `hasMore`, `fetchPageSize=500`) loaders (`marketData.ts:51-106`); ticker-name map + `showNames` toggle + `getTickerDisplayName` (`marketData.ts:30-45`); `selectedTicker`/`selectedMarket`/`klineData` shared selection state that TickerView and the Archive views read/write (`marketData.ts:16-18`). |
| `scanner` | `stores/scanner.ts` | CN/US server lists + selection + test state (`scanner.ts:42-47`); auto-scan enable/interval + `setInterval` timer handles (`scanner.ts:49-61,141-160`); scan status + last-scan timestamp (`scanner.ts:54-57`); wraps `useSSE()` for progress/messages/isRunning/error (`scanner.ts:39`); persists settings to `localStorage['my-doge-scanner-settings']` (`scanner.ts:7,26-36,64-84`). Restores settings and restarts auto timers on store init (`scanner.ts:182-186`). |

### 3.8 Typed API client (`web/src/api/`)

- `api/client.ts` creates a single shared axios instance: `baseURL: '/api'`, `timeout: 30000` (`client.ts:3-6`). The `/api` prefix is proxied to the FastAPI service in dev (`vite.config.ts:14-17`, §7).
- `api/data.ts` (`data.ts:4-33`): `listTables(market)`, `queryTable(market, table, page, pageSize, search?)`, `getKline(market, ticker, days=120)`, `fetchTickerNames(market)`. All return typed payloads (`PaginatedResponse`, `KlineData`).
- `api/config.ts` (`config.ts:3-46`): `getConfig`, `getSettings`, `updateSettings`, `validateTdx`, plus server management (`getServers`, `testServers`) with typed `ServerInfo`/`ServerTestResult` interfaces (`config.ts:25-36`).
- `api/scanner.ts` (`scanner.ts:3-16`): `startScan` bypasses axios and uses raw `fetch` for the SSE stream (`scanner.ts:5-10`); `getScanStatus` is a normal axios GET. **Note**: the scanner store does NOT call `startScan` — it calls `useSSE().start('/api/scan/...', body, opts)` directly with its own body shape including the selected server (`scanner.ts:117-124`). `api/scanner.ts:3-11` is therefore partially dead/parallel code (open question, §9).

## 4. Contracts / Data Model

### 4.1 TypeScript types (`web/src/types/`)

**`types/stock.ts`** (`stock.ts:1-22`):
```ts
interface KlineData {
  date: string; open: number; high: number; low: number; close: number;
  volume: number; amount?: number;
  ma_5?: number; ma_10?: number; ma_20?: number; ma_60?: number; atr_14?: number;
}
interface PaginatedResponse {
  columns: string[]; rows: Record<string, unknown>[];
  total: number; page: number; page_size: number;
}
```

**`types/report.ts`** (`report.ts:1-31`): `MacroReport` (`{id, date, timestamp, tags, analyst, risk_signal, volatility, content?}`), `ResearchReport` (`{id, date, timestamp, tags, analyst, title, content?}`), `StockNote` (`{id, ticker, market, created_at, note_type, title|null, content, tags|null}`).

**`types/splitTree.ts`** (`splitTree.ts:1-60`): the split-tree algebra.
- `SplitHandle = string`, `SplitLayout = 'horizontal' | 'vertical'`, `SpatialDirection = 'left'|'right'|'up'|'down'` (`splitTree.ts:13-19`).
- `ViewId = 'scanner' | 'cn-archive' | 'us-archive' | 'ticker' | 'insights' | 'analysis'` (`splitTree.ts:22`) — the canonical six-view enumeration.
- `LeafNode`, `SplitNode` (with `ratio: number` in `[0.05, 0.95]`), `SplitTreeNode` union, `SplitTreeState` (`{root, zoomedHandle, activeHandle}`) (`splitTree.ts:32-60`).

### 4.2 API client method shapes

| Method | HTTP | Returns | Source |
|---|---|---|---|
| `listTables(market)` | GET `/api/data/{market}/tables` | `string[]` (unwrapped from `{tables}`) | `data.ts:4-7` |
| `queryTable(market, table, page=1, pageSize=50, search?)` | GET `/api/data/{market}/table/{table}` | `PaginatedResponse` | `data.ts:9-18` |
| `getKline(market, ticker, days=120)` | GET `/api/data/{market}/ticker/{ticker}/kline` | `KlineData[]` (unwrapped from `{data}`) | `data.ts:20-26` |
| `fetchTickerNames(market)` | GET `/api/data/{market}/ticker-names` | `Record<string, string>` (unwrapped from `{names}`) | `data.ts:28-33` |
| `getConfig()`, `getSettings()`, `updateSettings({tdx_path?})`, `validateTdx(path)` | GET/GET/PUT/POST `/api/config[...]` | untyped (`any`) | `config.ts:3-21` |
| `getServers()` | GET `/api/scan/servers` | `{cn: ServerInfo[]; us: ServerInfo[]}` | `config.ts:38-41` |
| `testServers(market)` | POST `/api/scan/servers/test` | `{results: ServerTestResult[]}` | `config.ts:43-46` |
| `startScan(market, tdxPath)` | POST `/api/scan/{market}` (raw `fetch`) | `Response` (caller reads the stream) | `scanner.ts:3-11` |
| `getScanStatus()` | GET `/api/scan/status` | untyped (`any`) | `scanner.ts:13-16` |
| (direct `api.get` calls in views) | GET `/api/macro/reports[/{id}]`, `/api/analysis/reports[/{id}]`, `/api/notes/tracked` | untyped — views cast `.data.reports` / `.data.content` / `.data.tickers` | `AnalysisView.vue:58`; `InsightsView.vue:147,161,173-180` |

### 4.3 SSE event contract

The web console reads SSE manually (NOT via `EventSource`): `useSSE.start(url, body, opts)` does a `fetch(url, {method:'POST', body: JSON.stringify(body)})`, reads `response.body.getReader()`, decodes, and splits on `\n` (`useSSE.ts:22-44`). For each line starting with `data:` it JSON-parses the remainder and inspects `payload.progress` / `payload.message` (`useSSE.ts:45-68`):

| `progress` value | Meaning | Side effect |
|---|---|---|
| `-1` | Error | `error.value = msg`; `opts.onError?.(msg)` (`useSSE.ts:52-54`) |
| `0..99` | In progress | `progress.value = pct`; push `msg` to `messages`; `opts.onProgress?.(pct, msg)` (`useSSE.ts:55-58`) |
| `>= 100` | Complete | same as in-progress, plus `opts.onComplete?.()` (`useSSE.ts:59-62`) |

Malformed `data:` lines are silently skipped (`useSSE.ts:64-66`). This contract must match the FastAPI service's SSE payload shape (`{"progress": int, "message": str}` per the `scan.py`/`macro.py` workers documented in Module #9 §4.3 / §9.1).

### 4.4 MasonryItem / split-tree contracts

- **`MasonryItem`** (`VirtualMasonry.vue:30-34`): `{id: string|number; text: string; [key: string]: unknown}`. The `text` field is the layout-input string (pretext measures it to predict card height); the `[key: string]: unknown` index signature is the slot for arbitrary payload (InsightsView stores the raw report in `raw`, `InsightsView.vue:119-133`).
- **`PositionedCard`** (`VirtualMasonry.vue:36-42`, internal): `{item, x, y, width, height}` — the absolute-positioned render descriptor.
- **`VtColumn`** (`VirtualTable.vue:52-57`): `{key, title, width?, render?}` where `render` is an optional cell formatter `(row) => string`.
- **`Chunk`** (`VirtualMarkdown.vue:41-47`, internal): `{index, source, html, predictedHeight, actualHeight | null}` — the virtual-markdown unit, with a measured-height override slot.

## 5. Edge Cases

| Situation | What happens (Current State) | file:line |
|---|---|---|
| **Empty ticker / no selection in TickerView** | Renders the `.ticker-empty` placeholder with a placeholder SVG + "No ticker selected" text; the chart container is `v-if`-gated out | `TickerView.vue:23-29` |
| **Empty query in fuzzy search** | `search()` returns `[]` for `''` and whitespace-only queries before scoring anything | `useFuzzySearch.ts:144-145`; covered by `useFuzzySearch.spec.ts:27-32` |
| **0 items in VirtualTable / useVirtualScroll** | `visibleRange` short-circuits to `{startIdx:0, endIdx:0, offsetY:0}`; `totalHeight = 0`; no rows rendered | `useVirtualScroll.ts:39,34` |
| **0 items in VirtualMasonry** | `computePositions` early-returns with empty `positionedCards` and `contentHeight = 0` | `VirtualMasonry.vue:86-90` |
| **Huge list (10k+ rows) in VirtualTable** | Only the viewport window + `bufferRows` (default 8) is rendered; DOM node count stays bounded by `ceil(containerHeight / rowHeight) + 2*buffer + 1` | `useVirtualScroll.ts:41-45`; `VirtualTable.vue:67` |
| **Container not yet mounted** | `useVirtualScroll` watches `containerRef` and reads `clientHeight`/`scrollTop` only when the element exists; `ResizeObserver` is set up in the same watch (`immediate: true`) | `useVirtualScroll.ts:74-87` |
| **API unreachable (local-first degraded)** | axios `timeout: 30000` (`client.ts:5`) throws on timeout; callers vary: marketData store lets `loadTables` throw (uncaught, surfaces as a console error + the VirtualTable `loading` flag stuck), while `loadTickerNames` and the scanner store's `fetchServers`/`doTestServers` swallow errors silently | `client.ts:5`; `marketData.ts:47-49` vs `marketData.ts:35-37`; `scanner.ts:88-93,108-110` |
| **SSE stream disconnects mid-scan** | `useSSE`'s `while` loop exits on `done`; the `finally` sets `isRunning=false` (`useSSE.ts:37-75`). **Gap**: there is no automatic reconnect — if the network drops, `onComplete`/`onError` may never fire and the scanner store's `cnStatus`/`usStatus` is reset only because `start()`'s `finally` runs (the `onComplete`/`onError` callbacks set status to idle, but they fire only on a clean `progress>=100` or `progress===-1` payload). A raw socket close without a terminal event leaves the scanner's `onComplete`/`onError` uninvoked — see Open Question §9. | `useSSE.ts:70-75`; `scanner.ts:122-124,134-136` |
| **Malformed SSE `data:` line** | Silently skipped (catch block, no rethrow) | `useSSE.ts:64-66` |
| **Pretext alias unresolved at build time** | `vite build` / `vue-tsc` fail to resolve `@pretext`; build is RED. The alias points at an absolute sibling path — moving/deleting the sibling checkout breaks the build (§6, §7) | `vite.config.ts:5-12`; `tsconfig.app.json:6-8` |
| **Persisted split-tree state corrupt / missing** | `loadFromStorage` returns `null` on JSON parse failure or missing `root`/`activeHandle`; the singleton falls back to a single `scanner` leaf | `useSplitTree.ts:75-85,242-246` |
| **Close the last panel** | Refused: `remove()` returns early when `state.root.type === 'leaf'` or the handle is the root; `canClose()` returns `countLeaves > 1` and the PanelChrome close button is `:disabled` accordingly | `useSplitTree.ts:338-340,422-424`; `PanelChrome.vue:41` |
| **Resize below minimum panel width** | The divider drag computes `minRatio`/`maxRatio` from subtree `minWidth` sums and refuses to start (or clamps) when constraints are unsatisfiable | `SplitPane.vue:116-122` |
| **OffscreenCanvas / Intl.Segmenter unavailable** | `useTextMeasure` falls back to a DOM `<canvas>` context, or throws if neither exists (`useTextMeasure.ts:15-28`). `useFuzzySearch` requires `Intl.Segmenter` (no fallback) — jsdom-based tests that exercise it depend on Node's segmentation support | `useTextMeasure.ts:15-28`; `useFuzzySearch.ts:16-28` |
| **Same ticker selected in two TickerView panels** | Each panel is `defineAsyncComponent` keyed by `node.handle` (`PanelChrome.vue:52`), but BOTH read/write the **singleton** `marketData` store's `selectedTicker`/`klineData` (`marketData.ts:16-18`). Selecting a ticker in one panel overwrites the other's chart data — known shared-state coupling | `PanelChrome.vue:52,74-78`; `marketData.ts:16-18` |
| **Concurrent scan on same market** | The web console does NOT pre-check; it POSTs and the FastAPI service returns `409` (Module #9 §4.4). `useSSE` throws on `!resp.ok` and sets `error.value` (`useSSE.ts:28-31`); the scanner store's `onError` resets status to idle | `useSSE.ts:28-31`; `scanner.ts:122-124` |

## 6. Dependencies

**Upstream (this module depends on):**
- **#9 `fastapi-service`** — every read goes through `api/client.ts` (axios, `/api` prefix, 30s timeout, `client.ts:3-6`); scan progress is the SSE contract documented in §4.3 and Module #9 §9.1. The web console is the primary downstream consumer named in the fastapi-service CDD (#9 §6, "Depended on by"). The CORS-`*` + dev-proxy setup (§7) is what makes `localhost`-origin requests work.
- **#2 `market-data-storage`** (transitively, via #9) — the archive/kline/ticker-names endpoints read SQLite/DuckDB that Module #2 owns. The web console never touches a DB file directly.

**Downstream (depend on this module):**
- None. This is a terminal Presentation surface (consistent with `module-index.md` row 11 and the pyqt-desktop-dashboard CDD's framing of Presentation modules).

**Bidirectional notes (per design-docs rule):**
- The `fastapi-service` CDD (#9 §2, §6) names `vue-web-console` as the primary consumer of its API and SSE streams. This CDD is the matching half of that edge.
- The `pyqt-desktop-dashboard` CDD (#10) is a sibling Presentation surface; the two are independent (different tech: PyQt6 vs Vue3) but share the same upstream API.

**External packages** (`web/package.json`):
- Runtime: `vue` ^3.5.32, `vue-router` ^4.6.4, `pinia` ^3.0.4, `naive-ui` ^2.44.1, `axios` ^1.16.0, `lightweight-charts` ^5.2.0, `markdown-it` ^14.1.1, `@types/markdown-it` (dev), `highlight.js` ^11.11.1, `@vicons/ionicons5` ^0.13.0.
- Build/test: `vite` ^8.0.10, `@vitejs/plugin-vue` ^6.0.6, `typescript` ~6.0.2, `vue-tsc` ^3.2.7, `@vue/tsconfig` ^0.9.1, `vitest` ^2.1.9, `@vue/test-utils` ^2.4.6, `jsdom` ^25.0.1, `@types/node` ^24.12.2.

**External sibling-project dependency — `@pretext` (VENDORED 2026-06-12, S002-012 / TR-037):**
- `usePretextLayout.ts` and `VirtualMasonry.vue` import `{prepare, prepareWithSegments, layout, ...}` from `@pretext` (`usePretextLayout.ts:3-9`; `VirtualMasonry.vue:28`). `@pretext` is **not an npm package** — it is a path alias that resolves to a **vendored** copy of the sibling pretext text-layout library at `web/src/vendor/pretext/layout.ts` (`vite.config.ts`, mirrored in `vitest.config.ts` and `tsconfig.app.json`).
- pretext is a text-layout library: it segments text (word + grapheme, via `Intl.Segmenter`), measures glyph widths on a canvas, caches them, and lays out wrapped lines as pure arithmetic on cached widths. The web console uses it for masonry card-height prediction and the two-phase prepare/layout cycle.
- **Build prerequisite (RESOLVED)**: the sibling `../pretext` checkout is NO LONGER required. The 5-file import closure of `layout.ts` (`layout.ts`, `analysis.ts`, `line-break.ts`, `measurement.ts`, `bidi.ts`) is vendored into `web/src/vendor/pretext/` (upstream commit `4e71390` / tag `v0.0.4`). The alias points at the relative vendored path; `npm run build` / `npm test` are green on a clean checkout without the sibling repo.
- **Portability** (RESOLVED via vendoring, S002-012): the prior absolute Windows path was replaced by the vendored copy. The fork must be hand-synced on upstream pretext bumps — see `web/src/vendor/pretext/README.md` for the re-sync procedure. See ADR-0008 §Alternatives (Alternative 3) and Open Question §9.

**Docs / ADRs:**
- [ADR-0008](../../docs/architecture/adr-0008-web-architecture.md) — **this module's** decision: Vue3 + Vite8 + Pinia + Naive UI + manual-SSE + virtual-scroll + the `@pretext` alias, and the alternatives rejected.
- [ADR-0007](../../docs/architecture/adr-0007-api-surface-and-cors.md) — the upstream API surface and CORS stance this module's dev-proxy relies on (§7).

## 7. Configuration Knobs

| Knob | Default | Valid range / type | Owner (Current) | Env ownership | Operational risk |
|---|---|---|---|---|---|
| `api.baseURL` | `'/api'` | URL path prefix | **hardcoded** in `api/client.ts:4` | (not env) | LOW — the `/api` prefix MUST match the dev-proxy and the FastAPI router prefixes. Changing it requires updating `vite.config.ts` and the raw-`fetch` URLs in `useSSE`/`api/scanner.ts`. |
| `api.timeout` | `30000` (ms) | int > 0 | **hardcoded** in `api/client.ts:5` | (not env) | LOW — bounds how long a hung read waits before throwing. SSE streams are NOT subject to this (they use raw `fetch`, `useSSE.ts:22`). |
| `server.proxy./api` | `http://localhost:8901` | origin URL | **hardcoded** in `vite.config.ts:14-17` | (not env) | **MEDIUM** — couples the dev server to the FastAPI bind port (Module #9 §7 `bind_port=8901`). If the API moves ports, the proxy breaks in dev. Production builds do not use the proxy (the deployed origin serves both). |
| `@pretext` alias path | `web/src/vendor/pretext/layout.ts` (relative, vendored) | relative file path | **hardcoded** in `vite.config.ts`, `vitest.config.ts`, `tsconfig.app.json` | (not env) | **LOW (was HIGH, resolved 2026-06-12 by S002-012)** — vendored into the repo, so the build no longer depends on a sibling checkout. The residual cost is a hand-sync of the fork on upstream pretext bumps (`web/src/vendor/pretext/README.md`). |
| SSE endpoint URLs | `/api/scan/cn`, `/api/scan/us` | URL paths | **hardcoded** in `stores/scanner.ts:117,130` (and `api/scanner.ts:5` parallel) | (not env) | LOW — must match Module #9's `POST /api/scan/{market}` route. |
| `splitTree.storageKey` | `'my-doge-split-layout'` | localStorage key | **hardcoded** in `useSplitTree.ts:25` | (not env) | LOW — collisions with another app's localStorage key would corrupt layout. |
| `scanner.storageKey` | `'my-doge-scanner-settings'` | localStorage key | **hardcoded** in `scanner.ts:7` | (not env) | LOW. |
| `splitTree.ratio clamp` | `[0.05, 0.95]` | float | **hardcoded** in `useSplitTree.ts:26-27` | (not env) | LOW — prevents degenerate zero-width panels. |
| `virtualScroll.rowHeight` (VirtualTable) | `32` (px) | int > 0 | prop default `VirtualTable.vue:67` | per-call site | LOW — must match the CSS row height or windowing misaligns. |
| `virtualScroll.bufferRows` (VirtualTable) | `8` | int >= 0 | prop default `VirtualTable.vue:68` | per-call site | LOW — larger = smoother fast scroll, more DOM nodes. |
| `virtualMarkdown.linesPerChunk` | `40` | int > 0 | prop default `VirtualMarkdown.vue:31` | per-call site | LOW — chunk granularity for culling. |
| `kline.days` | `120` | int 1..365 | **hardcoded** in `data.ts:20`, `TickerView.vue:137,150`, archive views | (not env) | LOW — must stay within Module #9's `Query(120, ge=1, le=365)` or the API returns 422. |
| `scanner.autoScan.interval` (default) | `30` (min) | int > 0 | **hardcoded** in `scanner.ts:52-53`, `loadSettings()` default `scanner.ts:33-34` | per-user (persisted) | LOW — operator-tunable via the ScannerView interval dropdown (`ScannerView.vue:120-126`). |

**Migration target (vs Current State):**
- *Current State*: every knob is hardcoded; the `@pretext` path is an absolute Windows path; nothing is env-driven.
- *Target (Migration)*: `api.baseURL`, `api.timeout`, the dev-proxy target sourced from `import.meta.env` / a `.env` file with safe local defaults; the `@pretext` dependency is **vendored into `web/src/vendor/pretext/` (DONE 2026-06-12, S002-012)** so the absolute sibling path is gone (the `@pretext` alias is retained, pointing at the relative vendored copy).

## 8. Acceptance Criteria

**Build / toolchain (RESOLVED — green as of 2026-06-12):**
- [x] `cd web && npm run build` is green (`vue-tsc -b && vite build` — `package.json:8`). Typecheck + Vite production build pass.
- [x] `cd web && npm test` is green (vitest, jsdom env, `package.json:10`). Smoke suite covers `useFuzzySearch`, `useVirtualScroll`, and one Pinia store (`scanner`).
- [x] The `@pretext` alias resolves in both `vite build` and `vitest` (mirrored in `vite.config.ts:9-13` and `vitest.config.ts:15-19`).
- [x] **Clean-checkout portability (RESOLVED 2026-06-12, S002-012 / TR-037)**: `@pretext` is vendored into `web/src/vendor/pretext/` (5-file import closure, upstream `4e71390` / `v0.0.4`); `cd web && npm run build` and `cd web && npm test` are green with the alias resolved to the vendored copy, no sibling-project checkout required. `grep -rn 'pretext/src' web/` returns only the vendor README provenance rows.

**Pure-logic unit coverage (RESOLVED):**
- [x] `useFuzzySearch.spec.ts` covers exact/prefix/contains/grapheme-subsequence/token scoring, empty-query, no-match, CJK subsequence, and `maxResults`/`minScore` options (8 cases).
- [x] `useVirtualScroll.spec.ts` covers the `visibleRange` computed window for a populated list, the empty-list short-circuit, and the buffer/offset arithmetic.
- [x] A Pinia store spec (`scanner.spec.ts`) covers at least one state mutation and one getter/computed against `setActivePinia(createPinia())`, with the API layer stubbed (no live FastAPI).

**View render / behavior (PARTIAL — advisory per testing standards; UI is ADVISORY gate):**
- [x] All six views mount without console errors in dev (manual smoke — the split-tree registry + lazy loaders resolve).
- [x] The split-tree singleton restores from `localStorage` and defaults to a single scanner leaf on corrupt/missing state (`useSplitTree.ts:75-85,242-246`).
- [ ] **OPEN**: automated mount/render tests for the six views (currently manual only — jsdom lacks full Naive UI/lightweight-charts/OffscreenCanvas support; tracked in §9).
- [ ] **OPEN**: automated SSE reconnect test (the manual-`fetch` reader has no reconnect path — §5; tracked in §9).

**Contracts / data model:**
- [x] The six `ViewId` literals in `types/splitTree.ts:22` exactly match the keys of `VIEW_REGISTRY` (`registry.ts:18-61`).
- [x] The SSE reader's `{progress, message}` parse matches Module #9's SSE payload (`useSSE.ts:48-63` vs fastapi-service §4.3).
- [x] `api.timeout=30000` and `kline.days=120` stay within the upstream API's accepted ranges (Module #9 §7).

**Docs / observability:**
- [x] This CDD cites real `file:line` for every claim (auditable).
- [x] ADR-0008 records the Vue3+Vite8+Pinia+SSE+virtual-scroll+`@pretext` composition decision and the `@pretext` portability stance.
- [ ] **OPEN**: registry proposals (browser target, alias path, proxy target) queued for Phase 5 entry approval (§9).

**Determinism / isolation (per coding-standards):**
- [x] All vitest specs are deterministic (no random seeds, no time-dependent assertions, no live network — the API layer is stubbed).
- [x] Each spec sets up its own Pinia / state; no cross-spec ordering dependency.

## 9. Integration Requirements

> Appended per the assignment brief for interface/integration modules. Also satisfies the testing standards' "Web/App Workflow" gate.

### 9.1 FastAPI / SSE contract

- The web console is a pure client of Module #9. It issues:
  - **JSON reads** via the shared axios instance (`api/client.ts:3-6`, `/api` prefix, 30s timeout) for tables, kline, ticker-names, config, servers, macro/analysis reports, notes.
  - **SSE streams** via raw `fetch` POST (`useSSE.ts:22-26`) for `POST /api/scan/{cn,us}`. The scanner store builds the body `{tdx_path:'', use_server:true, server: selectedServer}` (`scanner.ts:118-120,131-133`) — note `tdx_path` is sent empty because the web flow always uses the server download path, never local `.day` files.
- The SSE payload contract is `data: {"progress": int, "message": str}\n` per Module #9 §9.1; `progress === -1` is the error sentinel, `progress >= 100` is completion (`useSSE.ts:52-62`).
- **No auth** — consistent with Module #9's local-first, no-remote-clients stance (#9 §9.1). The web console sends no credentials.
- **No retry** at the HTTP layer; the web console does not retry failed reads or SSE disconnects (matches #9 §9.3 "the API itself performs no retry"). Operators re-trigger manually.

### 9.2 Build / test toolchain

- **Typecheck + build**: `npm run build` = `vue-tsc -b && vite build` (`package.json:8`). `vue-tsc -b` uses the project-references setup (`tsconfig.json:1-7` → `tsconfig.app.json` + `tsconfig.node.json`). The app config extends `@vue/tsconfig/tsconfig.dom.json`, sets `noUnusedLocals`/`noUnusedParameters`/`erasableSyntaxOnly`/`noFallthroughCasesInSwitch` (`tsconfig.app.json:2-15`), and declares the `@pretext` path alias (`tsconfig.app.json:6-8`).
- **Test**: `npm test` = `vitest run` (`package.json:10`), jsdom environment, globals enabled, include `src/**/*.spec.ts` + `src/**/*.test.ts` (`vitest.config.ts:21-23`). The vitest config mirrors the `@pretext` alias so the resolver works in tests (`vitest.config.ts:15-19`).
- **Constraints honored**: `tsconfig.app.json` and `vite.config.ts` were NOT modified by this module's reverse-documentation/test work (per the assignment rules). New specs live under `web/src/__tests__/` and follow the existing `useFuzzySearch.spec.ts` pattern.

### 9.3 The external `@pretext` dependency

- `@pretext` is a text-layout library **vendored into `web/src/vendor/pretext/`** (the 5-file import closure of `layout.ts`: `layout.ts`, `analysis.ts`, `line-break.ts`, `measurement.ts`, `bidi.ts`; upstream commit `4e71390` / tag `v0.0.4`). It is NO LONGER a build prerequisite on a sibling checkout — `npm run build` and `npm test` resolve the `@pretext` alias to the relative vendored copy. Vendored by S002-012 / TR-037 (2026-06-12).
- The vitest smoke suite deliberately avoids specs that transitively execute `@pretext` at runtime (i.e. no `usePretextLayout` or `VirtualMasonry` mount tests that call `layout()` on real text) because jsdom lacks `OffscreenCanvas` and `Intl.Segmenter` support is uneven — the smoke suite sticks to pure-arithmetic composables (`useVirtualScroll`) and store logic (`scanner`) that do not exercise the canvas/Segmenter path (`vitest.config.ts` comment). The vendored export SHAPE is nonetheless asserted by `web/src/__tests__/vendor-pretext-regression.spec.ts` (a contract test that imports the 3 runtime fns + 3 types and asserts the fns are callable, without invoking `layout()`).
- **Portability stance** (RESOLVED via vendoring, S002-012): the prior absolute Windows path was replaced by the vendored copy. The fork must be hand-synced on upstream pretext bumps — see `web/src/vendor/pretext/README.md` for the re-sync procedure. Tracked in ADR-0008 §Alternatives (Alternative 3).

### 9.4 Browser target

- **Current State**: no explicit `browserslist` is declared in `package.json` or a `.browserslistrc`; Vite 8's default build target applies. The runtime relies on `Intl.Segmenter` (Node 16+/all evergreen browsers), `OffscreenCanvas` (Chrome/Edge/Firefox; Safari 16.4+), `ResizeObserver` (all evergreen), `EventSource` is NOT used (raw `fetch` streaming is), and `lightweight-charts` v5 (evergreen). The realistic target is **the operator's local Chrome/Edge/Firefox on Windows** (the desktop where MY-DOGE-MICRO runs).
- **Risk**: older Safari (< 16.4) would lose canvas measurement (`useTextMeasure` falls back to DOM canvas, `useTextMeasure.ts:23-26`, but pretext itself may assume `OffscreenCanvas`). Not a stated target — flagged for Phase 5.

### 9.5 Error / loading / empty states (per view)

| View | Loading | Empty | Error |
|---|---|---|---|
| Scanner | `n-progress` while `store.isRunning` (`ScannerView.vue:93-99`); buttons show `:loading` on `cnStatus==='running'` (`ScannerView.vue:32`) | n/a (always shows server lists) | `store.error` is surfaced only via the `n-log`; `cnStatus`/`usStatus` reset to idle on `onError` (`scanner.ts:122-124`) |
| Ticker | `namesLoading` on the autocomplete (`TickerView.vue:10`) | `.ticker-empty` placeholder when no ticker selected (`TickerView.vue:23-29`) | kline fetch errors are uncaught (console only) |
| CnArchive | VirtualTable `:loading="store.loading"` (`CnArchiveView.vue:16`) | VirtualTable renders 0 rows if `allRows` empty (no explicit empty message) | `loadAllRows` errors uncaught |
| UsArchive | same as CnArchive (`UsArchiveView.vue:13`) | same | same |
| Insights | `n-spin :show="loading"` (`InsightsView.vue:5`); modal `n-spin :show="modalLoading"` (`InsightsView.vue:74`) | `n-empty` in macro tab (`InsightsView.vue:28`) and notes tab (`InsightsView.vue:57`); research tab has no empty state | report-fetch catch sets "Failed to load report content." in the modal (`InsightsView.vue:149-151,165-167`) |
| Analysis | `n-spin :show="loading"` (`AnalysisView.vue:6`) | no explicit empty state | fetch errors uncaught (the `try`/`finally` only resets `loading`) |

**Target (advisory)**: every view should render an explicit loading / empty / error triad. Insights and Scanner are closest; the Archive and Analysis views have gaps (§8 OPEN).

---

## Open Questions (flagged for Phase 5 reconciliation)

1. **`@pretext` portability** — **RESOLVED 2026-06-12 (S002-012 / TR-037):** vendored the 5-file import closure of `layout.ts` into `web/src/vendor/pretext/` (upstream `4e71390` / `v0.0.4`) and repointed the alias in all 3 configs to the relative vendored path. The build no longer depends on an absolute Windows path or a sibling checkout. Residual: hand-sync the fork on upstream pretext bumps (`web/src/vendor/pretext/README.md`). (§6, §7, §9.3, ADR-0008 Alternative 3.)
2. **`api/scanner.ts` parallel code** — `startScan` (`scanner.ts:3-11`) is not called by the scanner store (which uses `useSSE().start` directly with its own body, `scanner.ts:117-124`). Is `api/scanner.ts` dead code, or the intended future seam? Delete or wire it in.
3. **SSE reconnect** — `useSSE` has no reconnect on a dropped stream without a terminal event; the scanner status can stick on `running`. Add a watchdog (e.g. `isRunning=true` with no message for N seconds → force idle) or an explicit reconnect with resume. (§5.)
4. **View-level automated tests** — mount tests for the six views are blocked by jsdom's missing `OffscreenCanvas`/full Naive UI/lightweight-charts support. Consider a happy-path E2E (Playwright/Cypress) against a running dev server + mocked API, or lift the heaviest composables out of jsdom-incompatible dependencies. (§8 OPEN.)
5. **Shared single-ticker state** — two TickerView panels both bind to the singleton `marketData.selectedTicker`/`klineData` (`marketData.ts:16-18`); selecting in one overwrites the other. Per-panel ticker state (scoped to the leaf handle) would decouple them. (§5.)
6. **`browserslist`** — declare an explicit browser target so Vite's build target and the `OffscreenCanvas`/`Intl.Segmenter` runtime requirements are documented and enforced. (§9.4.)
7. **Untyped API responses in views** — AnalysisView/InsightsView call `api.get(...)` directly and cast `.data.reports`/`.data.content` without typed wrappers (`AnalysisView.vue:58`; `InsightsView.vue:147,161,173-180`). Promote these to typed `api/reports.ts` functions returning `MacroReport`/`ResearchReport`. (§4.2.)
8. **`ticker` has no router route** — intentional (ticker is panel-only), but worth confirming the operator never needs a deep-linkable ticker URL. If they do, add `/ticker/:market/:code` to `router/index.ts`. (§3.2.)
9. **Error/loading/empty triad gaps** — Analysis and the Archive views lack explicit empty/error UI; the testing-standards "Web/App Workflow" gate expects a critical-path interaction + accessibility check. Close the triad on every view before the next release. (§9.5, §8 OPEN.)
10. **CORS / proxy in production** — the dev proxy (`vite.config.ts:14-17`) only runs under `vite dev`. In production the deployed origin must serve both the static bundle and the API (or the API must enable CORS for the bundle's origin). Document the production topology. (§7, ADR-0007.)
