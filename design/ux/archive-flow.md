---
title: Archive Flow — CN & US Market Archive (Web + Desktop)
view: cn-archive, us-archive
status: published
---

# Archive Flow — CN & US Market Archive (Web + Desktop)

> **Status**: Published (Wave 3 UX docs, 2026-06-13; triad closed by S003-009).
> **Surfaces**: Web `CnArchiveView` + `UsArchiveView` (primary) + Desktop
> `DBEditorWidget` (tabs 2-4).
> **Authoritative contracts**: [`design/cdd/vue-web-console.md`](../cdd/vue-web-console.md)
> §3.4–3.6, §9.5; [`design/cdd/pyqt-desktop-dashboard.md`](../cdd/pyqt-desktop-dashboard.md)
> §3.2; REST contract in [`design/cdd/fastapi-service.md`](../cdd/fastapi-service.md)
> and `src/api/routers/data.py`.
> **Cross-cutting patterns**: [`interaction-patterns.md`](./interaction-patterns.md)
> §2 (VirtualTable) and §5 (triad); [`accessibility-requirements.md`](./accessibility-requirements.md)
> §3.2 (keyboard row nav — OPEN) and §5 (triad gap closure).

This spec defines the operator journey for browsing the two local market-data
archives (`market_data_cn.db`, `market_data_us.db`): searching, scrolling the
virtualized row stream, and row-clicking a ticker to load its kline. A fetch
failure must **never** leave a silent empty table — S003-009 closed the
`loadAllRows` error and the missing empty state via the shared `StatusView`
triad.

---

## 1. Overview

The Archive flow is how the operator browses the persisted per-ticker rows that
the Scanner wrote. It is **REST-paged** (not SSE): the store calls
`GET /data/{market}/table/stock_prices` for the first 500 rows and appends
further pages on scroll-end (`stores/marketData.ts:loadAllRows`,
`loadMoreRows`). A `VirtualTable` renders a fixed-row-height windowed viewport
over potentially hundreds of thousands of rows. Both `CnArchiveView` and
`UsArchiveView` share the single `marketData` Pinia store, differ only by the
`'cn'` / `'us'` market argument, and are mounted into any split-tree leaf.

The CN view additionally offers a 名称/代码 (name/code) toggle that lazy-loads a
ticker→name map; the US view omits it. Beyond that, the two views are
structurally identical and share the same lifecycle states.

## 2. User promise / JTBD

**Operator's job**: "Browse the full CN or US market archive, search for a
ticker, scroll through thousands of rows without the UI freezing, and click a
row to load that ticker's kline into the Ticker view — and trust that if the
fetch dies I'll see a clear failure with a Retry, not an empty table that looks
like 'no data'."

The promise rests on three shipped guarantees:

1. **The archive is virtualized** — `VirtualTable` windowed viewport keeps
   memory bounded regardless of total row count
   ([`interaction-patterns.md`](./interaction-patterns.md) §2).
2. **A fetch failure surfaces a terminal error with a Retry** (S003-009) —
   `loadAllRows`/`loadMoreRows` rejections are caught, normalized to a
   `FetchError { code, message }`, and routed into `StatusView`'s `n-result`
   + Retry; **never** a silent blank table.
3. **An empty result is distinct from a loading/error state** — a successful
   fetch returning zero rows renders an explicit `n-empty` ("No rows match"),
   not a stale or blank table.

## 3. Entry points

| Surface | Entry point | Source |
|---|---|---|
| Web (CN) | `CnArchiveView` — registered view `'cn-archive'`, loaded on demand into any split-tree leaf | `web/src/views/registry.ts` |
| Web (US) | `UsArchiveView` — registered view `'us-archive'`, loaded on demand | `web/src/views/registry.ts` |
| Desktop | `DBEditorWidget` — tabs 2-4 (raw table editor, see README) | `src/interface/dashboard.py:58-82` |

On the web, an Archive leaf is opened by `Ctrl+Shift+H`/`V` to split and then
selecting the "CN Archive" or "US Archive" entry in the panel picker
([`interaction-patterns.md`](./interaction-patterns.md) §1, §3). The
split-tree default for a freshly split leaf is `'scanner'`; the Archive is an
explicit picker choice.

## 4. Detailed behavior — step-by-step (web)

### Step 1 — Initial load (infinite-scroll seed)

On mount, each view calls `store.loadAllRows(market)`
(`CnArchiveView.vue:110`, `UsArchiveView.vue:79`). The store:

1. Sets `loading = true`, `error = null`, **resets `allRows = []`**, `page = 1`,
   `hasMore = true` (`marketData.ts:79-83`). The reset is deliberate: a Retry
   never reuses a stale partial list.
2. Calls `queryTable(market, 'stock_prices', 1, 500, searchQuery)`
   (`api/data.ts:9-18`) → `GET /data/{market}/table/stock_prices?page=1&page_size=500`.
3. On success, sets `columns`, `allRows` to the first page, and derives
   `hasMore = allRows.length < total` (`marketData.ts:90-94`).
4. On rejection, `toFetchError(e)` (`utils/fetchError.ts`) normalizes the throw
   into `{ code, message }` and stores it; `allRows` stays `[]`
   (`marketData.ts:95-98`).
5. `finally` sets `loading = false`.

### Step 2 — Search

The toolbar `n-input` (`CnArchiveView.vue:9-10`, `UsArchiveView.vue:6-7`) is
bound to `store.searchQuery`. Pressing `Enter` (or clicking **Refresh**) calls
`store.loadAllRows(market)` again, which re-seeds with the new search term as
the `search` query param. Search is server-side LIKE; an empty search restores
the full list.

### Step 3 — Name/Code toggle (CN only)

The CN toolbar has a 名称/代码 `n-button` (`CnArchiveView.vue:6-8`) bound to
`toggleNames` (`CnArchiveView.vue:90-95`). On first switch to names it
lazy-loads `GET /data/cn/ticker-names`
(`store.loadTickerNames('cn')`, `marketData.ts:36-44`). The name fetch is
**fail-soft**: a rejection is swallowed silently (`marketData.ts:41-43`) because
names are a display enhancement, not a data dependency — the column falls back
to the bare ticker code (`getTickerDisplayName`, `marketData.ts:46-51`). The US
view has no name map and no toggle.

### Step 4 — Row-click loads a kline

Clicking a row fires `onRowClick(row)` (`CnArchiveView.vue:97-102`,
`UsArchiveView.vue:66-71`), which:

1. Sets `store.selectedTicker = ticker`, `store.selectedMarket = 'cn'|'us'`.
2. Awaits `getKline(market, ticker, 120)` (`api/data.ts:20-26`) →
   `GET /data/{market}/ticker/{ticker}/kline?days=120`.
3. Stores the result in `store.klineData`.

The shared `selectedTicker` / `selectedMarket` / `klineData` are the contract
the **Ticker view** reads, so the operator can split the Archive next to a
Ticker leaf and have the row-click drive the chart. (The kline fetch itself is
out of this flow's triad scope — see Ticker flow.)

### Step 5 — Infinite scroll

When `VirtualTable` emits `scroll-end`, `onScrollEnd` checks
`store.hasMore && !store.loading` and, if both hold, calls
`store.loadMoreRows(market)` (`CnArchiveView.vue:104-108`,
`UsArchiveView.vue:73-77`). The store computes the next page from the
accumulated row count, appends the new page, and recomputes `hasMore`
(`marketData.ts:104-127`).

> A mid-scroll page failure is handled gracefully: the already-accumulated rows
> stay in place (the operator keeps what loaded), only the failed page is lost,
> and the `StatusView` error banner tells them why the scroll stopped
> (`marketData.ts:119-126`). The banner's Retry re-calls `loadAllRows`, which
> resets and re-seeds.

## 5. Detailed behavior — desktop divergence

The desktop dashboard exposes the archives as the raw `DBEditorWidget` on
**tabs 2-4** (per the project README note): a generic SQLite table editor with
in-place edit/add/delete and a single-column LIKE search
(`db_editor.py:339-363`), not the web's virtualized browse + row-click flow.

Key differences from web:

- **No VirtualTable** — the desktop editor paginates through the table widget's
  own row buffer; there is no infinite-scroll accumulator.
- **No shared Pinia store** — the editor binds directly to the SQLite file
  through `QSqlDatabase`; there is no `selectedTicker`/`klineData` handoff to a
  Ticker view (the desktop has no separate kline surface).
- **No `StatusView` triad** — the editor relies on Qt's native empty-table
  rendering and per-action message boxes; the S003-009 triad is web-only.
- **Cross-tab lock** — a running Scanner scan locks the matching archive editor
  tab and relabels it `写入中…` until completion
  (`dashboard.py:85-117`, see [`scanner-flow.md`](./scanner-flow.md) §5).

The desktop is documented here for completeness; the **triad, search, and
row-click contracts below are web-only.**

## 6. States

The S003-009 work wrapped the `VirtualTable` in `StatusView`
(`components/common/StatusView.vue`) and derived a single status enum from
store state. Both views use the identical derivation, just spelled slightly
differently in source (CN: an explicit `if`-chain `tableStatus`,
`CnArchiveView.vue:57-62`; US: a ternary `derivedStatus`,
`UsArchiveView.vue:48-56`). Order matters and is the same in both:

```text
loading  -> skeleton          (store.loading === true)
error    -> n-result + Retry  (store.error !== null)
empty    -> n-empty           (store.allRows.length === 0)
idle     -> VirtualTable      (default slot, only path that renders the table)
```

### 6.1 Loading

- `store.loading === true` → `StatusView` renders `n-skeleton` rows (default 3)
  with `aria-live="polite"` + `aria-busy="true"` (`StatusView.vue:7-22`).
- The VirtualTable lives in `StatusView`'s default slot, which **only yields
  when status is `idle`** — so a loading state replaces the table wholesale,
  never showing stale rows behind a skeleton.

### 6.2 Error (terminal — SHIPPED via S003-009)

When `store.error` is non-null (a `loadAllRows` or `loadMoreRows` rejection,
normalized by `toFetchError`):

- `tableStatus`/`derivedStatus` becomes `'error'` — **not** `'idle'` with an
  empty table.
- `StatusView` renders an `n-result` (status `error`) with
  `error.message ?? 'Something went wrong'`, wrapped in a `role="alert"`
  `aria-live="assertive"` container (`StatusView.vue:39-53`).
- A **Retry** button renders in the `n-result` footer because both views wire
  `on-retry` (CN: `retry()` → `store.loadAllRows('cn')`,
  `CnArchiveView.vue:65-67`; US: inline `() => store.loadAllRows('us')`,
  `UsArchiveView.vue:15`). Retry re-seeds `allRows` from page 1.
- Error codes overlap the SSE vocabulary where the failure mode is shared
  (`http_<status>`, `network_error`; `utils/fetchError.ts`). REST adds
  `fetch_failed` (catch-all) and SSE adds the server-envelope codes
  (`bad_request`/`not_found`/`conflict`/`internal_error`); all share the
  `{ code, message }` shape so `StatusView` renders both identically
  ([`interaction-patterns.md`](./interaction-patterns.md) §4).
- For a `loadMoreRows` (mid-scroll) failure, the accumulated rows are **left in
  place** — the banner overlays the partial list rather than blanking it
  (`marketData.ts:119-126`).

### 6.3 Empty

- `store.loading === false` AND `store.error === null` AND
  `store.allRows.length === 0` → `StatusView` renders an `n-empty` with
  description **"No rows match"** (`CnArchiveView.vue:23`,
  `UsArchiveView.vue:13`). This is the distinct "successful fetch, zero rows"
  state — a search with no hits lands here, not in the error banner.

### 6.4 Idle (table rendered)

- `store.allRows.length > 0` (and not loading/error) → `StatusView` yields its
  default slot and the `VirtualTable` renders: fixed `row-height: 32`,
  `row-key: "ticker"`, windowed viewport over `store.allRows`
  (`CnArchiveView.vue:26-34`, `UsArchiveView.vue:17-24`).

## 7. Edge cases

| Situation | What happens |
|---|---|
| `loadAllRows` rejects on first load | `error` set, `allRows` stays `[]` from the reset → `StatusView` error banner with Retry; never a blank table (`marketData.ts:79-98`) |
| `loadMoreRows` rejects mid-scroll | Accumulated rows retained; only the failed page lost; error banner overlays the partial list; Retry re-seeds from page 1 (`marketData.ts:104-127`) |
| Search returns zero hits | Empty state (`n-empty` "No rows match") — distinct from loading and from error |
| Operator clicks Refresh while a load is in flight | `loadAllRows` resets `allRows = []` and `error = null`, then re-fetches; the in-flight prior fetch's late resolve is discarded (store overwrite) |
| CN name map fetch fails | Swallowed silently; column falls back to bare ticker code — names are a display enhancement, not a data dependency (`marketData.ts:41-43,46-51`) |
| `scroll-end` fires while `loading` | Guarded: `if (store.hasMore && !store.loading)` skips the tick (`CnArchiveView.vue:104-108`) |
| Row-click kline fetch rejects | **GAP (out of this flow's triad)** — the kline fetch is awaited directly in `onRowClick` with no try/catch; a rejection propagates uncaught. Tracked in [`accessibility-requirements.md`](./accessibility-requirements.md) §5 as the Ticker-view gap. |
| Desktop: scan started while archive editor open | Editor tab locked + relabeled `写入中…`, refreshed + focused on finish (`dashboard.py:85-117`) |

## 8. Dependencies

- **Web**: `stores/marketData.ts` (shared CN+US state, infinite-scroll
  accumulator, `error` ref), `api/data.ts` (`queryTable`, `getKline`,
  `fetchTickerNames`), `components/VirtualTable.vue` (windowed viewport — see
  [`interaction-patterns.md`](./interaction-patterns.md) §2),
  `components/common/StatusView.vue` (triad, S003-009),
  `utils/fetchError.ts` (`toFetchError`, shared `{ code, message }` dialect),
  `api/client.ts` (axios instance).
- **REST contract**: `GET /data/{market}/table/stock_prices` (paged rows),
  `GET /data/{market}/ticker/{ticker}/kline`, `GET /data/{market}/ticker-names`
  (`src/api/routers/data.py`); envelope convention in
  [`design/cdd/fastapi-service.md`](../cdd/fastapi-service.md).
- **Cross-cutting patterns**: the loading/empty/error triad
  ([`interaction-patterns.md`](./interaction-patterns.md) §5; closed for this
  view by S003-009) and the shared `{ code, message }` error dialect (§4).
- **Desktop**: `db_editor.py` (`DBEditorWidget`), `dashboard.py:85-117`
  (cross-tab lock/refresh), `dashboard.py:58-82` (tab order — archives are
  tabs 2-4, raw editor per README).
- **Accessibility**: keyboard row navigation is a **DEFERRED** target — see
  §9.1 below and [`accessibility-requirements.md`](./accessibility-requirements.md)
  §3.2 / §5.

## 9. Configuration knobs

### 9.1 VirtualTable keyboard row navigation — DEFERRED

The Archive views' critical action — **row-click to load a kline** — is today
**mouse-only** at the table level. `VirtualTable` rows are `<div>` elements,
not focusable table cells; there is no arrow-key row navigation and no
`Enter`-to-select binding. The keyboard path today is `Tab` to the table
container only; selecting a specific row requires the mouse. This is recorded
as **DEFERRED** for a follow-on batch and cross-referenced in
[`accessibility-requirements.md`](./accessibility-requirements.md) §3.2
(VirtualTable keyboard row nav — OPEN) and §5 (the triad gap is closed; the
keyboard gap is not). Implementing it will require `VirtualTable` to expose
focusable row elements + arrow-key row movement + `Enter` to emit the
`row-click` payload.

### 9.2 Knobs

| Knob | Default | Range / values | Owner |
|---|---|---|---|
| `fetchPageSize` | `500` | rows per infinite-scroll page | client (`marketData.ts:34`) |
| VirtualTable `row-height` | `32` | px | view (`CnArchiveView.vue:30`, `UsArchiveView.vue:19`) |
| StatusView `skeletonRows` | `3` (default) | int; `0` renders an `n-spin` | `StatusView.vue:107` (archives use the default) |
| `empty-description` | `"No rows match"` | string | view (both archives) |
| `days` (kline) | `120` | int | `onRowClick` (`CnArchiveView.vue:101`, `UsArchiveView.vue:70`) |
| `currentTable` | `'stock_prices'` | table name | store (`marketData.ts:10`) |

## 10. Acceptance criteria

- [ ] On mount, each archive view calls `store.loadAllRows(market)` and renders
      a skeleton (loading) state until the first page resolves.
- [ ] On a successful first page, the `VirtualTable` renders the rows in a
      windowed viewport; scrolling to the bottom appends further pages while
      `store.hasMore` is true.
- [ ] If `loadAllRows` rejects, `StatusView` renders an `n-result` error banner
      with the normalized `error.message` and a **Retry** button; the table is
      **not** shown behind the banner; `tableStatus`/`derivedStatus` is
      `'error'`, not `'idle'`.
- [ ] Retry re-calls `store.loadAllRows(market)`, resets `allRows` from page 1,
      and clears the prior error.
- [ ] A successful fetch returning zero rows renders `n-empty` with description
      "No rows match" — distinct from loading and from error.
- [ ] A `loadMoreRows` (mid-scroll) rejection leaves the accumulated rows in
      place and surfaces the error banner; the operator's prior scroll progress
      is not lost.
- [ ] A search query submitted via Enter or Refresh re-seeds the table with the
      new `search` parameter; an empty search restores the full list.
- [ ] CN only: the 名称/代码 toggle lazy-loads the ticker-name map on first
      switch; a name-map fetch failure is swallowed silently and the column
      falls back to the bare ticker code.
- [ ] A row-click sets `store.selectedTicker`, `store.selectedMarket`, and
      populates `store.klineData` from `getKline(market, ticker, 120)` — the
      contract the Ticker view reads.
- [ ] DEFERRED: `VirtualTable` exposes arrow-key row navigation + `Enter`-to-
      select so the row-click critical action is keyboard-reachable (tracked in
      [`accessibility-requirements.md`](./accessibility-requirements.md) §3.2).
