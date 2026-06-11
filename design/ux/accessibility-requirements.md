# Accessibility Requirements — Web Console & Desktop Baseline

> **Status**: Seed (Wave 2 docs, 2026-06-12)
> **Surfaces**: Vue Web Console (primary) + PyQt Desktop Dashboard.
> **Authoritative contracts**: [`design/cdd/vue-web-console.md`](../cdd/vue-web-console.md) §9.4–9.5; [`design/cdd/pyqt-desktop-dashboard.md`](../cdd/pyqt-desktop-dashboard.md) §3.2.

This document establishes the **baseline** accessibility expectations for the
local operator. Several sub-areas (contrast ratio, reduced-motion, screen-reader
semantics) are **not yet addressed** in code and are flagged OPEN below; they are
advisory today and become acceptance criteria when the corresponding code task
lands.

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

## 2. Browser target — declared `browserslist`

> This section **declares** the project `browserslist` (closing `vue-web-console.md`
> §9.4 Open Question 6 at the spec level; the code change to add the key to
> `web/package.json` is a follow-on).

**browserslist** (to be added to `web/package.json`):

```json
"browserslist": [
  "Chrome >= 110",
  "Edge >= 110",
  "Firefox >= 115",
  "Safari >= 16.4"
]
```

**Rationale** — the runtime relies on two features with a hard floor:

| Feature | Used by | Floor | Below the floor |
|---|---|---|---|
| `Intl.Segmenter` | `useFuzzySearch.ts:16-28` (CJK-aware fuzzy, **no fallback**) | Node 16+ / all evergreen | ticker search throws |
| `OffscreenCanvas` | `useTextMeasure.ts:15-28` (pretext measurement, DOM-canvas fallback) | Chrome/Edge/Firefox; **Safari 16.4+** | pretext may assume OffscreenCanvas (`vue-web-console.md` §9.4) |
| `ResizeObserver` | split-tree resize | all evergreen | (not a risk) |

Safari **< 16.4** is the only realistic loss: canvas measurement degrades to the
DOM-canvas fallback (`useTextMeasure.ts:23-26`), but pretext's own assumptions
are not guaranteed. **Safari < 16.4 is not a supported target.** `EventSource`
is intentionally NOT used — the console streams via raw `fetch` (`useSSE.ts`).

The realistic in-practice target is **the operator's local Chrome/Edge/Firefox
on Windows** (`vue-web-console.md` §9.4).

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

> VirtualTable keyboard row navigation is **OPEN** — flag for the archive-flow
> follow-on. The split-tree shortcuts themselves are bound/unbound cleanly, which
> the docs-consistency test could pin.

### 3.3 Desktop dashboard

PyQt6 widgets are keyboard-navigable by default (`Tab` to move focus, `Enter` to
activate). The five tabs (`dashboard.py:58-82`) are reachable via `Ctrl+Tab` /
the tab bar. The DB editor's in-place edit, add, delete, and single-column LIKE
search (`db_editor.py:339-363`) are standard Qt controls. No custom desktop
shortcuts are defined today.

---

## 4. Color and contrast

- **Theme**: Naive UI `darkTheme` is the default and only shipped theme
  ([`web/src/App.vue:81`](../../web/src/App.vue): `<n-config-provider :theme="darkTheme">`).
  The desktop applies `Microsoft YaHei 9` globally (`dashboard.py:133-134`) on
  the native Qt palette.
- **Contrast baseline**: **NONE documented.** There is no measured contrast
  ratio, no project-wide color tokens, and no `prefers-color-scheme` handling.
  Status colors are inline (`ScannerView.vue:234,297-298`):
  `ok=#63e2b7` (green), `failed=#ef5350` (red), untested=`rgba(255,255,255,0.3)`.
- **OPEN (advisory)**: establish a minimum contrast ratio for status colors and
  a token set. May warrant a future ADR if it becomes a project-wide standard.

---

## 5. Loading / empty / error triad — closing the §9.5 gaps

The triad is a **per-view acceptance criterion** (see
[`interaction-patterns.md`](./interaction-patterns.md) §5 for the full table).
The gaps from `vue-web-console.md` §9.5 (Open Question 9) are tracked here so
each follow-on per-flow spec inherits a concrete checklist:

| View | Gap to close |
|---|---|
| Scanner | **CLOSED (S002-010)** — `n-alert` + Retry now ships (`ScannerView.vue:115-131`) |
| Ticker | kline-fetch errors uncaught — add an error surface |
| CnArchive / UsArchive | no explicit empty message; `loadAllRows` errors uncaught |
| Insights | research tab has no empty state |
| Analysis | no explicit empty state; fetch errors uncaught |

These remain ADVISORY per `coding-standards.md` ("Web/App Workflow" gate) until
the corresponding code task lands; this spec records them so they are not lost.

---

## 6. CJK support

CJK (Chinese) ticker names and report content are first-class — the operator is
on a CN-market stack.

- **Fuzzy search**: `Intl.Segmenter` with `granularity: 'word'` and `'grapheme'`,
  locale `'zh-CN'` (`useFuzzySearch.ts:16-28`). Supports partial CJK queries
  (e.g. `"贵茅"` matching `"贵州茅台"`) via grapheme-subsequence scoring
  (`useFuzzySearch.ts:51-58`). **No fallback** — requires the browserslist floor
  in §2.
- **Font**: desktop uses `Microsoft YaHei` (`dashboard.py:133-134`). Web relies
  on the browser default CJK fallback; no web font is shipped.

> OPEN: declare a web CJK font stack consistent with the desktop YaHei choice.

---

## 7. Reduced motion and screen-reader support

**Current state: NOT addressed.** There is:

- No `prefers-reduced-motion` handling (the `processing` `n-progress`
  (`ScannerView.vue:109`) and Naive UI transitions are always animated).
- No ARIA live region for SSE progress/error (the watchdog's terminal
  `stream_stalled` error appears in an `n-alert`, but is not announced).
- No documented screen-reader testing (the operator is sighted + mouse/keyboard;
  SR support is not a stated need).

These are flagged **OPEN** and are advisory. If a future operator requires SR
support, the SSE progress pattern and the terminal-error banner are the first
candidates for `aria-live` regions.
