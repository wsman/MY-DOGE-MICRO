---
title: Ticker Flow — Single-Name Kline Reader
view: ticker
status: published
---

# Ticker Flow — Single-Name Kline Reader (Web)

> **Status**: Published (Wave 2 docs, 2026-06-13)
> **Surface**: Web `TickerView` (panel-only — no top-level route).
> **Authoritative contracts**: [`design/cdd/vue-web-console.md`](../cdd/vue-web-console.md) §3.4, §9.5; kline contract in [`design/cdd/fastapi-service.md`](../cdd/fastapi-service.md) and `src/api/routers/data.py`.
> **Cross-cutting patterns**: [`interaction-patterns.md`](./interaction-patterns.md) §2 (fuzzy/virtualization), §5 (triad); [`accessibility-requirements.md`](./accessibility-requirements.md) §3.2 (keyboard path), §6 (CJK search).

This spec defines the operator journey for the **panel-only** ticker view:
search a ticker by code or CJK name, read its 120-day kline with MA5/MA20
overlays, and never have a fetch failure blank the chart.

---

## 1. Overview

The Ticker flow is how the operator inspects a single name. Unlike the Scanner,
it is **not a top-level route** — it is registered as the `'ticker'` view in the
split-tree registry and lives inside a leaf panel. It is entered in two ways:
the operator picks it from the panel picker (or via a split), or the **Archive
flow hands a selection off** by writing `store.selectedTicker` +
`store.selectedMarket`. The view renders a 120-day candlestick chart with MA5 /
MA20 overlays via `lightweight-charts` (`useKlineChart`), fronted by a
code-or-name autocomplete backed by `Intl.Segmenter`-based CJK fuzzy search. A
fetch failure must **never** blank the chart — prior data is retained and the
failure surfaces through the `StatusView` error branch.

## 2. User promise / JTBD

**Operator's job**: "Type a code (`600519`, `AAPL`) or a Chinese name
(`贵州茅台`), pick the right one from the dropdown, and read the 120-day kline
with MA5/MA20. If the fetch fails, tell me clearly with a Retry — and leave the
last chart I had on screen, don't blank it. Let me jump here from the archive by
clicking a row."

The promise rests on three shipped guarantees (post-S003-009):

1. **Search is CJK-aware** — `Intl.Segmenter` fuzzy search matches partial codes
   and grapheme-subsequence CJK queries
   ([`accessibility-requirements.md`](./accessibility-requirements.md) §6).
2. **A fetch failure is surfaced, never silent** — `klineError` drives the
   `StatusView` error branch with a **Retry**, and the prior `klineData` is left
   intact (`TickerView.vue:136-148`).
3. **A dropped names load degrades, never blocks** — `loadNames` is
   `Promise.allSettled` and non-blocking; its failure is a muted inline note, not
   a `StatusView` block (`TickerView.vue:105-127`, `48-50`).

## 3. Entry points

| Surface | Entry point | Source |
|---|---|---|
| Web | `TickerView` — registered as view `'ticker'`, loaded into any split-tree leaf | `web/src/views/registry.ts` |
| Web | **Archive row-click handoff** — `CnArchive`/`UsArchive` set `store.selectedTicker` + `store.selectedMarket`, then a split opens the ticker leaf | `stores/marketData.ts`; archive-flow follow-on |

Because it is panel-only, the operator reaches it by `Ctrl+Shift+H`/`V` to split
and selecting "Ticker" in the panel picker, **or** by clicking an archive row
which drives `selectedTicker` (the `watch` at `TickerView.vue:230-238` reacts to
the external selection and loads the kline).

## 4. Detailed behavior — step-by-step (web)

### Step 1 — Load names (background)

On mount, `TickerView` calls `loadNames()` (`TickerView.vue:247`), which fires
two `fetchTickerNames('cn'|'us')` requests via **`Promise.allSettled`**
(`TickerView.vue:109-112`). Each fulfilled leg populates `cnNames` / `usNames`;
`rebuildTickerList()` (`TickerView.vue:171-180`) flattens them into
`allTickers`. This is **non-blocking** — the chart area renders the no-selection
empty block immediately; the autocomplete populates when names land.

### Step 2 — Search (autocomplete)

The `n-auto-complete` (`TickerView.vue:4-14`) is bound to `searchOptions`
(`TickerView.vue:183-205`), which runs `useFuzzySearch` over the active-market
slice of `allTickers`, scoring against `[ticker, ticker-without-suffix, name]`.
CJK matching is `Intl.Segmenter`-based with **no fallback**
([`accessibility-requirements.md`](./accessibility-requirements.md) §6). The
market `n-select` (`TickerView.vue:15-20`) filters the pool (CN default).

### Step 3 — Select → fetch kline

`onSelect(value)` (`TickerView.vue:211-227`):

1. Resolves the entry's `market` (falls back to `activeMarket`).
2. Writes `store.selectedTicker` + `store.selectedMarket` (the trigger for the
   archive-handoff path).
3. Sets the search text to `"<code>  <name>"`.
4. `await loadKline(market, ticker)`.

`loadKline` (`TickerView.vue:136-148`) clears `klineError`, records `lastFetch`
(for retry), calls `getKline(market, ticker, 120)`, assigns `store.klineData`,
and pushes data into the chart via `setData` on `nextTick`. On throw it captures
`toFetchError(e)` into `klineError` and **returns without touching**
`store.klineData` — the prior chart stays.

### Step 4 — Render chart (idle)

When `chartStatus === 'idle'`, `StatusView` yields its slot and the
`ref="chartContainer"` div mounts; `useKlineChart` renders the candlestick +
MA5/MA20 series (`TickerView.vue:39`). A watcher re-paints when the container
re-mounts with existing data (`TickerView.vue:241-245`).

### Step 5 — External selection (archive handoff)

The `watch(() => store.selectedTicker)` (`TickerView.vue:230-238`) mirrors the
internal `onSelect` path: it updates the search text + market, then calls
`loadKline`. This is the single integration seam with the Archive flow.

## 5. Desktop divergence

**None.** The ticker flow is web-only. The PyQt desktop dashboard has no
equivalent single-name kline reader (see
[`design/cdd/pyqt-desktop-dashboard.md`](../cdd/pyqt-desktop-dashboard.md)).

## 6. States

The states triad here is the **post-S003-009** implementation — see
[`interaction-patterns.md`](./interaction-patterns.md) §5 for the cross-cutting
requirement. The chart area delegates to `StatusView`; the no-selection block is
a separate idle-empty.

### 6.1 Loading

`getKline` is awaited **inline**, so the chart holds its previous render until
new data lands rather than flashing a skeleton. `skeleton-rows="0"` is passed to
`StatusView` as a no-op (`TickerView.vue:37`). The only explicit loading
affordance is the autocomplete `:loading="namesLoading"` spinner
(`TickerView.vue:10`) during the background names fetch.

### 6.2 Error (terminal — SHIPPED via S003-009)

When `loadKline` catches a fetch failure, `klineError` is populated
(`TickerView.vue:144-146`) and `chartStatus` computes to `'error'`
(`TickerView.vue:165-169`). `StatusView` renders its error branch with the
`FetchError` message and a **Retry** affordance bound to `retryGetKline`
(`TickerView.vue:34`, `151-154`), which re-issues `loadKline` with the retained
`lastFetch` params. **Prior `klineData` is untouched** — a retry that succeeds
replaces it; a retry that fails again re-arms the error branch.

The error follows the `FetchError = { code, message }` shape (`utils/fetchError.ts`)
consistent with the SSE error contract in
[`interaction-patterns.md`](./interaction-patterns.md) §4 — **no raw `str(e)`
leaks**.

### 6.3 Empty

Two distinct empties:

- **No-selection idle-empty** — when `store.selectedTicker` is falsy, the
  `.ticker-empty` block renders (icon + "No ticker selected", `TickerView.vue:41-51`).
  This short-circuits before any kline state is consulted.
- **Chart empty** — when a ticker is selected but `klineData.length === 0` and no
  `klineError` is set, `chartStatus === 'empty'` and `StatusView` renders
  `"No kline data"` (`TickerView.vue:35`).

### 6.4 Complete (idle)

`chartStatus === 'idle'` (ticker selected, data present, no error) → `StatusView`
yields its slot → the chart container mounts and `useKlineChart` paints.

## 7. Edge cases

| Situation | What happens |
|---|---|
| Fetch fails on first selection (no prior data) | `klineError` set → `StatusView` error + Retry; `klineData` stays `[]` → `chartStatus` is `'error'` (error takes priority over empty) |
| Fetch fails on a re-selection (prior data exists) | `klineError` set → error branch; **prior chart data retained** until a successful retry (`TickerView.vue:144-146`) |
| Both `fetchTickerNames` legs reject | `namesError` set → muted inline note "Ticker names unavailable — search limited to codes"; autocomplete falls back to code-only search (`TickerView.vue:117-119`, `48-50`) |
| One names leg rejects | `Promise.allSettled` keeps the other's names; no flag (`TickerView.vue:113-114`) |
| Operator selects a ticker while names still loading | `onSelect` works against the partial `allTickers`; `loadKline` is independent of names |
| Archive sets `selectedTicker` for a ticker not in `allTickers` | `onSelect` not triggered; the watcher path (`TickerView.vue:230-238`) loads kline directly via `store.selectedMarket` |
| Container unmounts mid-render (`Ctrl+W`) | `onUnmounted` calls `dispose()` (`TickerView.vue:248`); `useKlineChart` tears down its series |
| Retry with no prior fetch | `retryGetKline` guards on `lastFetch` being null (`TickerView.vue:152-153`) — no-op |

## 8. Dependencies

- **Web**: `useKlineChart` (lightweight-charts wrapper), `useFuzzySearch`
  (`Intl.Segmenter`, no fallback), `stores/marketData.ts` (`selectedTicker`,
  `selectedMarket`, `klineData`, `getTickerDisplayName`), `api/data.ts`
  (`getKline`, `fetchTickerNames`), `StatusView.vue` (triad), `utils/fetchError.ts`
  (`toFetchError`); server contract in `src/api/routers/data.py`.
- **Cross-cutting**: [`interaction-patterns.md`](./interaction-patterns.md) §2
  (fuzzy search) and §5 (triad);
  [`accessibility-requirements.md`](./accessibility-requirements.md) §6 (CJK).
- **Archive handoff**: shares `marketData` store with the archive views — see
  the archive-flow follow-on.

## 9. Configuration knobs

| Knob | Default | Range / values | Owner |
|---|---|---|---|
| Kline window | `120` days | days (passed to `getKline`, `TickerView.vue:140`) | code constant |
| Default market | `'cn'` | `'cn'` \| `'us'` (`TickerView.vue:77`) | code constant |
| Fuzzy `maxResults` | `30` | int (`useFuzzySearch` init, `TickerView.vue:74`) | code constant |
| Fuzzy `minScore` | `10` | int (`TickerView.vue:74`) | code constant |
| Chart overlays | MA5, MA20 | series rendered by `useKlineChart` | code constant |

## 10. Acceptance criteria

- [ ] On mount, `loadNames` fires for both markets via `Promise.allSettled`; the
      no-selection empty block renders immediately and the autocomplete
      `:loading` spinner shows until names resolve.
- [ ] Typing a code or CJK substring returns fuzzy-matched options scoped to the
      active market; selecting one loads the 120-day kline with MA5/MA20.
- [ ] A kline fetch failure sets `klineError` and renders the `StatusView` error
      branch with a **Retry**; the prior `klineData` is **not**
      blanked (retry-from-error restores or re-arms).
- [ ] `chartStatus === 'empty'` renders `"No kline data"` when a ticker resolves
      to zero candles and no error is set.
- [ ] The no-selection `.ticker-empty` block renders when `store.selectedTicker`
      is falsy, short-circuiting before any kline state.
- [ ] Both `fetchTickerNames` legs rejecting surfaces the muted inline note
      "Ticker names unavailable — search limited to codes" — **not** a
      `StatusView` block; a single leg's rejection is silent.
- [ ] Setting `store.selectedTicker` + `store.selectedMarket` externally (archive
      handoff) loads the kline and updates the search text.
- [ ] `retryGetKline` re-issues the last fetch with identical params; it is a
      no-op when no prior fetch exists.
