---
title: Analysis Flow — Insights & Analysis Views (Web)
view: insights, analysis
status: published
---

# Analysis Flow — Insights & Analysis Views (Web)

> **Status**: Published (Wave 3 docs, 2026-06-13).
> **Surfaces**: Web `InsightsView` (view `'insights'`) and `AnalysisView` (view
> `'analysis'`). No desktop equivalent — the PyQt dashboard has no research/notes
> surface today.
> **Authoritative contracts**: [`design/cdd/vue-web-console.md`](../cdd/vue-web-console.md) §3.4–3.5; REST report endpoints in `src/api/routers/`.
> **Cross-cutting patterns**: [`interaction-patterns.md`](./interaction-patterns.md) §2 (virtualization), §5 (triad); [`accessibility-requirements.md`](./accessibility-requirements.md) §3.2 (per-view keyboard path), §5 (triad gaps).

This spec defines the operator journey for reading AI-generated macro and
industry/analysis research reports and tracking ticker notes. The two views
share the same data shape (a `ResearchReport`/`MacroReport` feed + a
Markdown-detail modal) and the same S003-009 loading/empty/error machinery, so
they are documented together.

---

## 1. Overview

The Analysis flow is the **read side** of MY-DOGE-MICRO: it surfaces
AI-produced research and the operator's per-ticker notes for triage. Both views
are REST-backed (no SSE, no watchdog) — each issues one or more `api.get(...)`
calls on mount, and a fetch failure is the only failure mode. S003-009 wired
both views onto the shared `StatusView` triad
([`web/src/components/common/StatusView.vue`](../../web/src/components/common/StatusView.vue))
and the shared `FetchError` vocabulary
([`web/src/utils/fetchError.ts`](../../web/src/utils/fetchError.ts)), so a
rejection renders a structured error + Retry rather than silently blanking the
panel.

## 2. User promise / JTBD

**Operator's job**: "Read the latest AI macro and industry/analysis research
reports, open one in a readable modal, and see which tickers I'm tracking with
notes — without ever landing on a silent empty tab or a spinner that never
clears."

The promise rests on three shipped guarantees:

1. **Every fetch state is visible** — loading skeleton, empty message, or
   structured error + Retry, never a blank pane (`StatusView`, S003-009).
2. **A fetch failure is actionable** — an `n-result` error with a **Retry**
   button bound to `reload`, never a swallowed `catch {}`
   (`InsightsView.vue:10-15,219-236`; `AnalysisView.vue:6-11,82-93`).
3. **The modal report read degrades gracefully** — a per-report detail fetch
   failure shows "Failed to load report content." inside the modal, not a hung
   `n-spin` (`InsightsView.vue:189-193,203-207`).

## 3. Entry points

| Surface | Entry point | Source |
|---|---|---|
| Web Insights | `InsightsView` — registered as view `'insights'` (label "Insights", icon `book`), loaded on demand into any split-tree leaf | `web/src/views/registry.ts:47-53` |
| Web Analysis | `AnalysisView` — registered as view `'analysis'` (label "Analysis", icon `doc`), loaded on demand into any split-tree leaf | `web/src/views/registry.ts:54-60` |

The operator reaches either view by splitting a leaf
(`Ctrl+Shift+H`/`V`, defaulting to `scanner`) and then selecting "Insights" or
"Analysis" in the panel picker (`VIEW_SELECT_OPTIONS`, `registry.ts:66-69`). See
[`interaction-patterns.md`](./interaction-patterns.md) §1 for the split-tree
model and §3 for the keyboard map.

## 4. Detailed behavior — step-by-step (web)

### InsightsView

#### Step 1 — Load the three feeds in parallel

On mount, `reload()` (`InsightsView.vue:219-236`) fires three REST calls in
parallel via `Promise.all`:

- `GET /macro/reports` → `macroReports`
- `GET /analysis/reports` → `researchReports`
- `GET /notes/tracked` → `trackedTickers`

`loading` is true throughout; any thrown value is normalized through
`toFetchError` into the shared `{ code, message }` shape
(`InsightsView.vue:231-232`, [`fetchError.ts`](../../web/src/utils/fetchError.ts))
and surfaced via the view-level `StatusView`. `reload` is also the **Retry**
handler — re-invoking it clears the prior error so the derived status flips back
to `loading` immediately (`InsightsView.vue:220-221`).

#### Step 2 — Browse the tabs

Once `derivedStatus === 'idle'` the `StatusView` yields its slot and the three
`n-tab-pane`s render (`InsightsView.vue:16-87`):

- **Macro Reports** — a `VirtualMasonry` of macro cards (date/timestamp header,
  risk-signal `n-tag`, analyst + volatility). Empty fallback: `n-empty` "No
  reports" (`InsightsView.vue:40`). Masonry uses vendored `@pretext` for height
  prediction — see [`interaction-patterns.md`](./interaction-patterns.md) §2.
- **Research Reports** — a `VirtualMasonry` of research cards. Empty fallback is
  a scoped `StatusView` with `status="empty"` and
  `empty-description="No research reports"` (`InsightsView.vue:52-56`).
- **Stock Notes** — the tracked-ticker list as `n-tag`s (with per-ticker note
  counts). Empty fallback: `n-empty` "No tracked tickers"
  (`InsightsView.vue:79`).

#### Step 3 — Open a report (modal)

Clicking a macro or research card calls `showMacroReport` / `showResearchReport`
(`InsightsView.vue:182-208`), which opens an `n-modal`, sets `modalLoading`,
and fetches the full Markdown body from
`GET /macro/reports/{id}` or `GET /analysis/reports/{id}`. The body is rendered
through `markdown-it` into the modal's `.modal-markdown-body`. See **Edge
cases** §7 for the modal's failure path.

### AnalysisView

#### Step 1 — Load the report list

On mount, `reload()` (`AnalysisView.vue:82-93`) issues `GET /analysis/reports`
→ `reports`. As with Insights, `loading` is true during the fetch and any throw
is normalized via `toFetchError` into `error` (`AnalysisView.vue:88-89`).
`reload` doubles as the Retry handler (`AnalysisView.vue:83-84`).

#### Step 2 — Browse the grid

The derived `status` (`AnalysisView.vue:63-68`) folds loading > error > empty >
idle. Only `idle` yields the `StatusView` slot, which renders an `n-grid`
(responsive `1 s:2 m:3`) of `n-card`s — title header, date + analyst subtext
(`AnalysisView.vue:12-19`). The empty state ("No analysis reports yet") is
declared on the `StatusView` itself (`AnalysisView.vue:10`), so a zero-row idle
result never renders a blank grid.

#### Step 3 — Open a report (modal)

Clicking a card calls `showReport` (`AnalysisView.vue:70-73`), which sets
`modalContent` from the card's already-loaded `report.content` (no second
fetch) and opens the `n-modal`. The Markdown renders through the same
`markdown-it` path as Insights.

## 5. Detailed behavior — desktop divergence

**n/a.** The PyQt desktop dashboard has no Insights/Analysis/notes surface.
Macro reports, research reports, and tracked-ticker notes are web-only today.
A desktop port would be a new CDD; do not assume parity
([`design/cdd/pyqt-desktop-dashboard.md`](../cdd/pyqt-desktop-dashboard.md)).

## 6. States (the S003-009 triad)

Both views are wrapped by the shared `StatusView` and follow
[`interaction-patterns.md`](./interaction-patterns.md) §5. Only `idle` yields
the slot — loading/empty/error replace the content wholesale so no stale cards
render behind a skeleton or banner.

### 6.1 Loading

- **Insights** — view-level `StatusView` with `:skeleton-rows="6"`
  (`InsightsView.vue:10-15`) while `Promise.all` is in flight. The modal also
  shows `n-spin` while a detail fetch runs (`InsightsView.vue:97`).
- **Analysis** — view-level `StatusView` with the default 3 skeleton rows
  (`AnalysisView.vue:6-11`) while `GET /analysis/reports` is in flight.

### 6.2 Empty

- **Insights** — view-level idle is reached once all three feeds resolve; each
  tab then owns its own empty state: Macro `n-empty` "No reports"
  (`InsightsView.vue:40`), Research scoped `StatusView status="empty"`
  "No research reports" (`InsightsView.vue:52-56`), Notes `n-empty` "No tracked
  tickers" (`InsightsView.vue:79`).
- **Analysis** — `status === 'empty'` when `reports.length === 0`
  (`AnalysisView.vue:66-67`); `StatusView` renders "No analysis reports yet"
  (`AnalysisView.vue:10`).

### 6.3 Error

- **Insights** — `derivedStatus === 'error'` when `error` is set
  (`InsightsView.vue:169-173`); `StatusView` renders an `n-result` (role
  `alert`, `aria-live="assertive"`) with the `FetchError.message` and a
  **Retry** button bound to `reload` (`InsightsView.vue:12-14`).
- **Analysis** — `status === 'error'` when `error` is set
  (`AnalysisView.vue:64-65`); same `StatusView` error + Retry path
  (`AnalysisView.vue:8-9`).
- Error codes come from `toFetchError`: `http_<status>` (server non-2xx),
  `network_error` (no response — matches the SSE code so one dialect covers
  both transports), or `fetch_failed` (anything else). See
  [`fetchError.ts`](../../web/src/utils/fetchError.ts).

### 6.4 Complete (idle)

`derivedStatus`/`status === 'idle'` once `loading` is false and no error is
set; `StatusView` yields the slot (tabs / grid). The modal is a separate
lifecycle and does not affect the view-level status.

## 7. Edge cases

| Situation | What happens |
|---|---|
| Aggregate feed fetch rejects (Insights) | `toFetchError` → `error`; view-level `StatusView` shows error + Retry (`reload`). The tabs are replaced wholesale — no stale content behind the banner (`InsightsView.vue:169-173,219-236`). |
| Report-list fetch rejects (Analysis) | Same path: `toFetchError` → `error`; `StatusView` error + Retry (`AnalysisView.vue:63-68,82-93`). |
| Modal detail fetch fails (Insights) | **Separate path** — `showMacroReport`/`showResearchReport` catch sets `modalContent = 'Failed to load report content.'` and the modal renders that string; `modalLoading` clears in `finally`. The view-level status stays `idle`; the tabs remain usable (`InsightsView.vue:189-193,203-207`). |
| Modal has no content after a successful fetch | `n-empty` "No content" renders inside the modal (`InsightsView.vue:103`). |
| A tab's feed is empty while others populated (Insights) | View stays `idle`; the empty tab renders its scoped empty state (e.g. Research `StatusView` "No research reports"). |
| Operator clicks a card while a prior modal fetch is in flight | `modalLoading` gates the body; the modal opens immediately and the `n-spin` shows until the new fetch resolves (`InsightsView.vue:97-104`). |
| `Promise.all` partially rejects (Insights) | `Promise.all` rejects on the first failure — the whole `reload` is treated as failed and the view shows the error + Retry. There is no partial-success render; the operator retries the full set. |
| Operator hits Retry while already loading | `reload` re-enters; `loading` stays true and `error` is cleared first so the status flips back to `loading` (`InsightsView.vue:220-221`; `AnalysisView.vue:83-84`). |

## 8. Dependencies

- **Web Insights**: `InsightsView.vue` (UI + state), `VirtualMasonry.vue`
  (macro + research card layout), `StatusView.vue` (triad wrapper),
  `utils/fetchError.ts` (`toFetchError`), `api/client.ts`; report types in
  `web/src/types/report.ts`.
- **Web Analysis**: `AnalysisView.vue` (UI + state), `StatusView.vue`,
  `utils/fetchError.ts`, `api/client.ts`; `ResearchReport` type shared with
  Insights.
- **REST endpoints**: `GET /macro/reports`, `GET /macro/reports/{id}`,
  `GET /analysis/reports`, `GET /analysis/reports/{id}`, `GET /notes/tracked`
  (see `src/api/routers/`).
- **Cross-cutting**: virtualization and triad patterns in
  [`interaction-patterns.md`](./interaction-patterns.md) §2 and §5; keyboard
  reachability in [`accessibility-requirements.md`](./accessibility-requirements.md)
  §3.2; the triad gap closure tracked in
  [`accessibility-requirements.md`](./accessibility-requirements.md) §5.
- **Markdown rendering**: `markdown-it` for the modal body (no virtualization —
  reports are read in full in the modal, unlike the long-report
  `VirtualMarkdown` pattern in [`interaction-patterns.md`](./interaction-patterns.md)
  §2).

## 9. Configuration knobs

| Knob | Default | Range / values | Owner |
|---|---|---|---|
| `StatusView` skeleton rows (Insights) | `6` | int; `0` renders an `n-spin` instead | view (`InsightsView.vue:14`) |
| `StatusView` skeleton rows (Analysis) | `3` (component default) | int; `0` renders an `n-spin` instead | component (`StatusView.vue:107`) |
| Masonry `font` / `lineHeight` / `gap` / `bufferPx` / `maxColWidth` (Insights) | `14px …`, `20`, `12`, `200`, `400` | see `VirtualMasonry` props | view (`InsightsView.vue:22-26,59-63`) |
| Empty-state copy | "No research reports" / "No analysis reports yet" / "No reports" / "No tracked tickers" | strings | view (hardcoded today) |

> No runtime/env config is hardcoded into either view's implementation module
> (per `standards/coding-standards.md`). The masonry tuning values are layout
> constants, not operator-configurable settings.

## 10. Acceptance criteria

- [ ] On a fresh page load, both views show a loading skeleton (Insights: 6
      rows; Analysis: 3 rows) until their feed(s) resolve.
- [ ] A feed fetch failure renders a structured error (`n-result`, role
      `alert`, `aria-live="assertive"`) with a **Retry** button bound to
      `reload`; the underlying content (tabs/grid) is replaced, not rendered
      behind the banner. `status`/`derivedStatus` is `'error'`, not silently
      `'idle'`.
- [ ] Retry clears the prior error, flips status back to `loading`, and
      re-issues the fetch.
- [ ] Insights: once idle, each tab owns its empty state — Macro "No reports",
      Research "No research reports", Notes "No tracked tickers".
- [ ] Analysis: a zero-row idle result renders "No analysis reports yet", not a
      blank grid.
- [ ] Insights: a macro/research card click opens the modal; if the detail
      fetch fails, the modal body shows "Failed to load report content." and
      `modalLoading` clears (the view-level status stays `idle`).
- [ ] Insights: a successful detail fetch with empty content shows "No content"
      in the modal.
- [ ] Both views are reachable as `'insights'` / `'analysis'` in the split-tree
      panel picker (`registry.ts`); the operator can open one alongside the
      Scanner via a split (no modal-vs-split conflict — see
      [`interaction-patterns.md`](./interaction-patterns.md) §1).
