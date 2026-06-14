# Accessibility Requirements — Web Console & Desktop Baseline

> **Status**: Updated (Sprint 003 — 2026-06-13). Baseline a11y items closed by
> S003-007 (design tokens) and S003-009 (`StatusView` triad + `aria-live`).
> **Surfaces**: Vue Web Console (primary) + PyQt Desktop Dashboard.
> **Authoritative contracts**: [`design/cdd/vue-web-console.md`](../cdd/vue-web-console.md) §9.4–9.5; [`design/cdd/pyqt-desktop-dashboard.md`](../cdd/pyqt-desktop-dashboard.md) §3.2; [`design/art/art-bible.md`](../art/art-bible.md) §6 (measured contrast baseline).

This document establishes the **baseline** accessibility expectations for the
local operator. The originally-open sub-areas (contrast ratio, reduced-motion,
`aria-live`, CJK font, loading/empty/error triad) are **closed** below as of
Sprint 003; two items remain advisory (screen-reader testing) or documented-deferred
(VirtualTable keyboard row navigation). The closed items are no longer aspirational
— they are now acceptance criteria backed by shipped code.

---

## 1. Target audience

- **Who**: a **single local operator** (the machine owner). MY-DOGE-MICRO is
  local-first; there is no public/multi-tenant audience.
- **Platform**: **Windows primary** (`standards/technical-preferences.md`:
  "Windows paths and local-first data directories are first-class constraints").
- **Implication**: the a11y bar is "one expert operator can run every workflow
  keyboard-first and read every state." It is *not* a WCAG 2.1 AA public-site
  bar — but keyboard reachability, visible state, and CJK legibility are
  non-negotiable because they directly affect daily operator throughput.

---

## 2. Browser target — declared `browserslist` — CLOSED (S003)

> **CLOSED.** The project `browserslist` now ships in
> [`web/package.json`](../../web/package.json) (added during Sprint 003), closing
> `vue-web-console.md` §9.4 Open Question 6 at both the spec and the code level.

**browserslist** (declared in `web/package.json`):

```json
"browserslist": [
  "Chrome >= 110",
  "Edge >= 110",
  "Firefox >= 115",
  "Safari >= 16.4"
]
```

The realistic in-practice target is **the operator's local Chrome/Edge/Firefox on
Windows**; Safari is the only floor worth flagging (see below). **Rationale** — the
runtime relies on two features with a hard floor:

| Feature | Used by | Floor | Below the floor |
|---|---|---|---|
| `Intl.Segmenter` | `useFuzzySearch.ts:16-28` (CJK-aware fuzzy, **no fallback**) | Node 16+ / all evergreen | ticker search throws |
| `OffscreenCanvas` | `useTextMeasure.ts:15-28` (pretext measurement, DOM-canvas fallback) | Chrome/Edge/Firefox; **Safari 16.4+** | pretext may assume OffscreenCanvas (`vue-web-console.md` §9.4) |
| `ResizeObserver` | split-tree resize | all evergreen | (not a risk) |

Safari **< 16.4** is the only realistic loss: canvas measurement degrades to the
DOM-canvas fallback (`useTextMeasure.ts:23-26`), but pretext's own assumptions
are not guaranteed. **Safari < 16.4 is not a supported target.** `EventSource`
is intentionally NOT used — the console streams via raw `fetch` (`useSSE.ts`).

---

## 3. Keyboard accessibility

### 3.1 Web console — global split-tree shortcuts

All shortcuts operate on the active panel (`App.vue:24-77`, see
[`interaction-patterns.md`](./interaction-patterns.md) §3). Bound on mount,
unbound on unmount (`App.vue:76-77`).

| Shortcut | Action |
|---|---|
| `Ctrl+Shift+H` | Split horizontal |
| `Ctrl+Shift+V` | Split vertical |
| `Ctrl+W` | Close active panel |
| `Ctrl+Enter` | Toggle zoom |
| `Alt+←` `→` `↑` `↓` | Spatial navigate |

### 3.2 Web console — per-view critical-action keyboard path

Each view's critical action should be reachable by keyboard. **Current state:**
in-view actions (e.g. the Scanner Scan/Retry buttons) are Naive UI controls
focusable via `Tab` and activatable via `Enter`/`Space` by default — but **no
in-view shortcut is bound**, so the only keyboard path is `Tab` through the
focus ring. This is acceptable for the single-operator bar but should be
documented per flow.

| View | Critical action | Keyboard path today |
|---|---|---|
| Scanner | Trigger scan / Retry | `Tab` to the Scan/Retry button, `Enter` |
| Ticker | Search + select a ticker | `Tab` to autocomplete, type, `Enter` |
| CnArchive / UsArchive | Row-click loads kline | `Tab` to the table row, `Enter` (depends on VirtualTable focus support — **OPEN**) |
| Insights | Open a report | `Tab` to the masonry card, `Enter` |
| Analysis | Refresh report list | `Tab` to refresh affordance, `Enter` |

> **DOCUMENTED-DEFERRED.** VirtualTable keyboard row navigation is tracked in
> [`archive-flow.md`](./archive-flow.md) (target interaction described but not
> implemented this batch). The split-tree shortcuts themselves are bound/unbound
> cleanly.

### 3.3 Desktop dashboard

PyQt6 widgets are keyboard-navigable by default (`Tab` to move focus, `Enter` to
activate). The five tabs (`dashboard.py:58-82`) are reachable via `Ctrl+Tab` /
the tab bar. The DB editor's in-place edit, add, delete, and single-column LIKE
search (`db_editor.py:339-363`) are standard Qt controls. No custom desktop
shortcuts are defined today.

---

## 4. Color and contrast — CLOSED (S003-007)

- **Theme**: Naive UI `darkTheme` is the default and only shipped theme
  ([`web/src/App.vue:81`](../../web/src/App.vue): `<n-config-provider :theme="darkTheme">`).
  The desktop applies `Microsoft YaHei 9` globally (`dashboard.py:133-134`) on
  the native Qt palette.
- **Token set — CLOSED by S003-007.** Project-wide color tokens now ship in
  [`web/src/styles/tokens.css`](../../web/src/styles/tokens.css) and feed Naive
  UI via `themeOverrides`; status colors are no longer inlined per-view. The
  authoritative token table and the contrast rationale live in
  [`design/art/art-bible.md`](../art/art-bible.md) §2 and §6; the table below is
  the WCAG-correct measured baseline reproduced here so this a11y doc is
  self-contained.

**Measured contrast baseline** (against `--dgm-bg` `#1a1a2e`, per WCAG 2.1):

| Token / use | Contrast vs `#1a1a2e` | WCAG level | Note |
|---|---|---|---|
| `--dgm-text` | 15.5:1 | **AAA** | Primary text everywhere |
| `--dgm-text-muted` | 11.7:1 | **AAA** | Secondary text (captions, table secondary columns) |
| `--dgm-text-faint` | 6.8:1 | **AAA** | Tertiary text (placeholders, disabled labels) |
| `--dgm-status-ok` / `--dgm-accent-warm` (`#63e2b7`) | 10.6:1 | **AAA** | Green status (server ok, scan complete) |
| `--dgm-status-fail` / `--dgm-market-cn` (`#ef5350`) | 4.9:1 | **AA** | Red status (server fail, scan error) |
| `--dgm-chart-text` (`#d1d4dc`) | 11.5:1 | **AAA** | Chart axis/tooltip text |
| `--dgm-accent` / `--dgm-market-us` (`#2196f3`) | 5.46:1 | **AA** (normal text) | Reserved for icons, indicators, large text, and links — see rule below |
| `--dgm-status-unknown` (`rgba(255,255,255,0.30)`) | 2.7:1 | **EXCEPTION** | Decoration dots only — never text |

**Governing rule — the blue accent.** `--dgm-accent` measures 5.46:1, which
passes WCAG AA for normal-size text, but it is **reserved for icons, indicators,
large text (≥18pt / 14pt bold), and links** as a deliberate brand/legibility
choice: body copy stays on the higher-contrast `--dgm-text` (15.5:1) for maximum
readability. **Small and body text always uses `--dgm-text` (or `--dgm-text-muted`
/ `--dgm-text-faint`); the blue accent is never used for body copy.**

**Recorded exception — status-unknown.** `--dgm-status-unknown` (2.7:1) is too
low for text and is therefore **forbidden as text**; it renders a decoration dot
only, with any accompanying label using `--dgm-text-muted`.

**Out of scope — light theme / `prefers-color-scheme` toggle.** MY-DOGE-MICRO is
dark-only for now; a light theme is a future ADR, not a current capability.

---

## 5. Loading / empty / error triad — CLOSED (S003-009)

The triad is a **per-view acceptance criterion** (see
[`interaction-patterns.md`](./interaction-patterns.md) §5 for the full table).

**CLOSED by S003-009.** The 5/6-view triad gap is resolved by
[`web/src/components/common/StatusView.vue`](../../web/src/components/common/StatusView.vue),
a shared loading / empty / error / idle component. The five non-scanner views
(Ticker, CnArchive, UsArchive, Insights, Analysis) now wrap their content area in
`StatusView`, which renders the matching Naive UI primitive (`n-skeleton` /
`n-spin` for loading, `n-empty` for empty, `n-result` error variant for error) and
only yields the default slot when `status === 'idle'` — so a view never shows
stale content behind a skeleton or an error banner.

| View | Triad status |
|---|---|
| Scanner | **CLOSED (S002-010)** — `n-alert` + Retry ships (`ScannerView.vue`); `aria-live` wrappers added (S003-009, §7) |
| Ticker | **CLOSED (S003-009)** — kline-fetch errors surface via `StatusView` |
| CnArchive / UsArchive | **CLOSED (S003-009)** — explicit empty message + `loadAllRows` error surface via `StatusView` |
| Insights | **CLOSED (S003-009)** — research-tab empty state via `StatusView` |
| Analysis | **CLOSED (S003-009)** — explicit empty state + fetch-error surface via `StatusView` |

`StatusView` consumes the shared `{ code, message }` error vocabulary
(`utils/fetchError.ts` `FetchError` / `composables/useSSE.ts` `SSEError`) so one
component renders both REST and SSE failures identically.

---

## 6. CJK support

CJK (Chinese) ticker names and report content are first-class — the operator is
on a CN-market stack.

- **Fuzzy search**: `Intl.Segmenter` with `granularity: 'word'` and `'grapheme'`,
  locale `'zh-CN'` (`useFuzzySearch.ts:16-28`). Supports partial CJK queries
  (e.g. `"贵茅"` matching `"贵州茅台"`) via grapheme-subsequence scoring
  (`useFuzzySearch.ts:51-58`). **No fallback** — requires the browserslist floor
  in §2.
- **Font — CLOSED (S003-007).** Desktop uses `Microsoft YaHei`
  (`dashboard.py:133-134`). Web now declares the CJK-first sans-serif stack
  `--dgm-font-sans` in [`web/src/styles/tokens.css`](../../web/src/styles/tokens.css):
  `'Microsoft YaHei','PingFang SC','Hiragino Sans GB',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif`.
  The web stack leads with `Microsoft YaHei` so Chinese ticker names and report
  content render identically on desktop and web, then falls back through
  `PingFang SC` (macOS) and `Hiragino Sans GB` before the generic Latin stack.
  No web font is bundled (the operator's system CJK fallback is used).

---

## 7. Reduced motion, `aria-live`, and screen-reader support

### 7.1 Reduced motion — CLOSED (S003-007 / S003-009)

**CLOSED.** A global `prefers-reduced-motion` guard ships in
[`web/src/styles/tokens.css`](../../web/src/styles/tokens.css): it collapses
every transition/animation to a near-zero duration (0.01ms) and neutralizes the
Naive UI `n-progress` indeterminate spin, so motion-sensitive operators never see
a transition or animation when they request reduced motion. `StatusView.vue`
mirrors this with a scoped reduced-motion rule that neutralizes its `n-spin`
rotation and `n-skeleton` shimmer.

### 7.2 `aria-live` regions — CLOSED (S003-009)

**CLOSED.** Async progress and terminal errors are now announced to assistive
tech:

- **`StatusView`** ([`web/src/components/common/StatusView.vue`](../../web/src/components/common/StatusView.vue)):
  the **error** branch renders `role="alert"` + `aria-live="assertive"` so
  screen readers announce the failure immediately; the **loading** branch renders
  `aria-live="polite"` + `aria-busy="true"` so a screen reader cues the operator
  that content is arriving.
- **`ScannerView`** ([`web/src/views/ScannerView.vue`](../../web/src/views/ScannerView.vue)):
  the scan `n-progress` is wrapped in a `div aria-live="polite"` (SSE progress),
  and the terminal-error `n-alert` (the watchdog `stream_stalled` banner) is
  wrapped in a `div role="alert" aria-live="assertive"`.

### 7.3 Screen-reader testing — ADVISORY (not a current requirement)

**ADVISORY — not a current requirement.** The single operator is sighted and
works mouse/keyboard; screen-reader (SR) support is not a stated need. The
`aria-live` infrastructure in §7.2 is **forward-compatible plumbing, not a tested
SR contract**: it is correct, well-formed markup that an SR *can* consume, but no
SR (NVDA/VoiceOver) regression test is run today. Formal SR testing is deferred
until there is an operator who needs it; at that point the SSE progress pattern
(§7.2) and the terminal-error banner are the first candidates to verify under a
real SR.
