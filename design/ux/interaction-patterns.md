# Interaction Patterns — Web Console Library

> **Status**: Seed (Wave 2 docs, 2026-06-12)
> **Surface**: Vue Web Console only (`web/src/`). The PyQt Desktop Dashboard is
> mouse-driven Qt widgets and is out of scope for this library — see
> [`design/cdd/pyqt-desktop-dashboard.md`](../cdd/pyqt-desktop-dashboard.md).
> **Authoritative contract**: [`design/cdd/vue-web-console.md`](../cdd/vue-web-console.md) §3.4–3.6; [`docs/architecture/adr-0008-web-architecture.md`](../../docs/architecture/adr-0008-web-architecture.md).

This document is the cross-cutting **web interaction library**: the patterns
every registered view reuses. Per-flow specs (`scanner-flow.md`, the follow-on
`ticker-flow.md` / `archive-flow.md` / `analysis-flow.md`) derive from these
patterns and must not contradict them.

---

## 1. Split-tree panel model

Implemented in [`web/src/composables/useSplitTree.ts`](../../web/src/composables/useSplitTree.ts)
(a hand-port of Ghostty's Zig `split_tree.zig`, `useSplitTree.ts:1-13`) and wired
in [`web/src/App.vue`](../../web/src/App.vue) (`App.vue:10`, `App.vue:16-77`).

Each leaf panel renders one registered view (`registry.ts:18-61`). The tree
supports:

- **Split** — horizontal or vertical (`useSplitTree.ts` `split()`). New splits
  default `ratio: 0.5` (`useSplitTree.ts:309,480,487,494,497`).
- **Resize** — `setRatio()` mutates the split's `ratio` in place, clamped to
  **`MIN_RATIO = 0.05` … `MAX_RATIO = 0.95`** (`useSplitTree.ts:26-27`,
  enforced at `useSplitTree.ts:382`). A leaf can never be squeezed to zero.
- **Zoom** — `toggleZoom()` collapses siblings to focus one leaf (`App.vue:58-64`).
- **Spatial navigation** — `gotoSpatial('left'|'right'|'up'|'down')` moves the
  active handle between leaves (`useSplitTree.ts`, `App.vue:66-73`).
- **Presets** — single / h-split / v-split / quad (`App.vue:16-18`, toolbar
  buttons `App.vue:90-108`).

**Equalize** rebalances ratios by leaf weight (`useSplitTree.ts:220-225`).

> UX rule: any flow that needs a second surface alongside the primary one (e.g.
> Scanner + Ticker, Archive + Ticker) opens it via a split, not a modal. Modals
> are reserved for transient report reads (`InsightsView.vue` modal).

---

## 2. Virtualization patterns

Three components cover the three data shapes the console renders. All three
appear in `vue-web-console.md` §3.5.

| Component | File | Use case | Windowing |
|---|---|---|---|
| `VirtualTable` | [`web/src/components/VirtualTable.vue`](../../web/src/components/VirtualTable.vue) | Fixed-row archive tables (CN/US market data, hundreds of thousands of rows) | Fixed row height; windowed viewport |
| `VirtualMasonry` | [`web/src/components/VirtualMasonry.vue`](../../web/src/components/VirtualMasonry.vue) | Variable-height cards (Insights report masonry) | Two-phase prepare/layout via **vendored `@pretext`** |
| `VirtualMarkdown` | [`web/src/components/VirtualMarkdown.vue`](../../web/src/components/VirtualMarkdown.vue) | Arbitrarily long Markdown reports (macro/industry reports) | Chunked render |

### The `@pretext` dependency

`VirtualMasonry`'s card-height prediction and two-phase layout use `@pretext`
([`web/src/vendor/pretext/`](../../web/src/vendor/pretext/)). **As of 2026-06-12
(S002-012 / TR-037), `@pretext` is vendored into the repo** — the 5-file import
closure of `layout.ts` (upstream `4e71390` / `v0.0.4`) lives at
`web/src/vendor/pretext/` and the alias in all three configs points at the
relative vendored path. The build is green on a clean checkout with no sibling
project on disk (`vue-web-console.md` Open Question 1, **RESOLVED**).

> UX rule: do **not** treat pretext internals as a stable contract for spec
> purposes. The vendored SHAPE is asserted by
> [`web/src/__tests__/vendor-pretext-regression.spec.ts`](../../web/src/__tests__/vendor-pretext-regression.spec.ts)
> (3 runtime fns + 3 types), but upstream bumps require a hand-sync
> (`web/src/vendor/pretext/README.md`). Per-flow specs that mention masonry
> should reference the *component* (`VirtualMasonry`), not pretext fns.

`@pretext`'s text measurement relies on `OffscreenCanvas` with a DOM-canvas
fallback (`useTextMeasure.ts:15-28`); fuzzy search requires `Intl.Segmenter`
with **no fallback** (`useFuzzySearch.ts:16-28`). Both are browser-target
constraints — see [`accessibility-requirements.md`](./accessibility-requirements.md).

---

## 3. Keyboard shortcut map

All shortcuts are global (`window` `keydown`), bound on mount and unbound on
unmount ([`web/src/App.vue:24-77`](../../web/src/App.vue)). They operate on the
**active** panel handle (`splitTree.activeHandle`).

| Shortcut | Action | Source |
|---|---|---|
| `Ctrl+Shift+H` | Split active panel **horizontally** (new leaf defaults to `scanner`) | `App.vue:34-40` |
| `Ctrl+Shift+V` | Split active panel **vertically** (new leaf defaults to `scanner`) | `App.vue:42-48` |
| `Ctrl+W` | Close the active panel (no-op if it cannot close) | `App.vue:50-56` |
| `Ctrl+Enter` | Toggle zoom on the active panel | `App.vue:58-64` |
| `Alt+←` / `→` / `↑` / `↓` | Spatial-navigate to the neighbor leaf | `App.vue:66-73` |

> UX rule: a per-flow spec must map the flow's **critical action** to a keyboard
> path where one exists (see [`accessibility-requirements.md`](./accessibility-requirements.md)
> §3). The split-tree shortcuts are global; in-view actions (e.g. the scanner
> Scan button) are not keyboard-bound today and are flagged per-flow.

---

## 4. SSE progress pattern

Implemented in [`web/src/composables/useSSE.ts`](../../web/src/composables/useSSE.ts)
and consumed by the scanner store ([`web/src/stores/scanner.ts`](../../web/src/stores/scanner.ts)).

### Status state machine

`useSSE` exposes a single `status: SSEStatus` where
`SSEStatus = 'idle' | 'running' | 'error' | 'complete'` (`useSSE.ts:17-25`).
Every terminal path is idempotent (`surfaceTerminalError` guards on
`watchdogTripped`, `useSSE.ts:88-105`):

| Transition | Trigger | Effect |
|---|---|---|
| `idle → running` | `start()` called | `isRunning=true`, watchdog armed |
| `running → complete` | server sends `progress >= 100`, or stream ends cleanly | watchdog cleared, `isRunning=false`, `onComplete` |
| `running → error` | watchdog trips / HTTP non-ok / fetch rejects / in-band `progress === -1` | watchdog cleared, `isRunning=false`, `onError` with `SSEError` |

### The 30s watchdog (SHIPPED — S002-010)

> **This is the resolution of `vue-web-console.md` Open Question 3** ("SSE
> reconnect — a dropped stream without a terminal event leaves scanner status
> stuck on `running`"). It is shipped; the recon's pre-fix description is stale.

`DEFAULT_STALL_TIMEOUT_MS = 30000` (`useSSE.ts:43`). While `isRunning` is true, a
`setInterval` watchdog compares wall-clock time against `lastEventAt`; if **no
`data:` line (or decoded chunk) arrives within 30s**, the stream is treated as
dropped and a **terminal** `stream_stalled` error is surfaced
(`useSSE.ts:143-151`). The reader is cancelled (`useSSE.ts:97-103`) so the
blocked `await reader.read()` unwinds.

30s is deliberately conservative: a full CN-universe scan can have multi-second
gaps between progress callbacks (`useSSE.ts:33-38`).

### Error code contract

`SSEError = { code: string; message: string }` (`useSSE.ts:12-15`). Codes are a
stable string enum the UI branches on:

| Code | Origin | Meaning |
|---|---|---|
| `stream_stalled` | client watchdog | No data for 30s; stream dropped |
| `network_error` | client fetch/reader | Fetch rejected, reader cancelled, network drop |
| `http_<status>` | client HTTP check | Non-ok response with no parseable envelope |
| `bad_request` / `not_found` / `conflict` / `internal_error` | **server** (S002-009 envelope) | Threaded through `progress === -1` when the server emits `{error:{code,message}}` |

Server error envelopes follow the S002-009 convention `{error:{code,message}}`
with string-enum codes — **no raw `str(e)` leaks**. When a server `code` is
absent the client degrades to `internal_error` (`useSSE.ts:172-180`).

### Operator-facing consequence (no silent stuck-running)

The scanner store sets `cnStatus`/`usStatus` to **`'error'`** on `onError` —
*not* silently back to `'idle'` (`scanner.ts:128-134`, `scanner.ts:146-150`) —
and **stops the auto-scan timer** so the next tick doesn't silently restart into
another stuck stream. The view surfaces an `n-alert` with a **Retry** affordance
([`web/src/views/ScannerView.vue:115-131`](../../web/src/views/ScannerView.vue)).
See [`scanner-flow.md`](./scanner-flow.md) for the full flow.

> UX rule: any flow built on `useSSE` must (a) render a terminal error banner
> with a Retry when `status === 'error'`, (b) never reset to idle on error, and
> (c) never auto-reconnect — a retry is an explicit operator action
> (`scanner.ts:115-117`).

---

## 5. Loading / empty / error triad (cross-cutting requirement)

Every view must render all three states explicitly. `vue-web-console.md` §9.5
audits the current state per view; the **gaps** are tracked there as Open
Question 9 and are an advisory gate today (`coding-standards.md` "Web/App
Workflow"). The triad is the per-view acceptance criterion going forward:

| State | Requirement |
|---|---|
| **Loading** | A visible affordance (`n-progress`, `n-spin`, or component `:loading`) tied to the data-fetch flag |
| **Empty** | An explicit empty message (`n-empty` or placeholder element) — *not* "0 rows rendered silently" |
| **Error** | A visible error surface (`n-alert` + Retry, or in-view error text) — *not* "console-only / uncaught" |

Per-view status (from `vue-web-console.md` §9.5, with the Scanner row updated for
the shipped S002-010 watchdog fix):

| View | Loading | Empty | Error |
|---|---|---|---|
| **Scanner** | `n-progress` while `isRunning` (`ScannerView.vue:105-111`); Scan/Retry buttons `:loading` on `status==='running'` (`ScannerView.vue:32-40,78-86`) | n/a (always shows server lists) | **`n-alert` + Retry on terminal error** (SHIPPED, `ScannerView.vue:115-131`) — no longer log-only |
| **Ticker** | `namesLoading` on autocomplete | `.ticker-empty` placeholder | kline-fetch errors uncaught — **GAP** |
| **CnArchive / UsArchive** | VirtualTable `:loading` | no explicit empty message — **GAP** | `loadAllRows` errors uncaught — **GAP** |
| **Insights** | `n-spin` (list + modal) | `n-empty` in macro/notes tabs; **research tab has no empty** — **GAP** | modal shows "Failed to load report content." |
| **Analysis** | `n-spin` | no explicit empty state — **GAP** | fetch errors uncaught — **GAP** |

Closing the gaps is a follow-on code task (S002-010 closed the Scanner error path;
the rest remain ADVISORY per `coding-standards.md`).
