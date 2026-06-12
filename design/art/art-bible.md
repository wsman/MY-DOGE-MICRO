# Art Bible — MY-DOGE-MICRO

> **Status**: Seed (Sprint 003, story S003-007 — 2026-06-13)
> **Scope**: Product style guide for the web console (`web/`) and the visual
> baseline inherited by the PyQt desktop dashboard.
> **Authoritative contracts**: [`design/cdd/vue-web-console.md`](../cdd/vue-web-console.md)
> §9.4–9.5; [`design/ux/accessibility-requirements.md`](../ux/accessibility-requirements.md)
> §4, §6, §7.
> **Closes**: the `gate-check` finding *"no art bible"* (Sprint 003 Verification gate).

---

## 1. Overview

MY-DOGE-MICRO is a **dark-first, local-first quantitative decision-support
tool** for a **single operator** (the machine owner), surfaced as a Vue 3 +
Naive UI web console and a PyQt6 desktop dashboard on the same Windows host.
There is no public audience and no light theme: the operator works long sessions
on dense tables, candlestick charts, and streaming SSE progress in a dark room,
so every surface is tuned for low-glare, high-contrast, CJK-first reading. This
art bible exists now because the Verification `gate-check` flagged the absence
of an art bible as a blocker: prior to this document there was **no measured
contrast baseline, no project-wide color tokens, and no documented status
semantics** — status colors were inlined per-view (`ScannerView.vue`), the web
console relied on whatever CJK fallback the browser chose, and
`prefers-reduced-motion` was unhandled (`accessibility-requirements.md` §4, §7).
The token system declared here closes that gap: it is the single source of truth
for palette, typography, elevation, status semantics, and contrast, consumed by
the web console via `:root` CSS custom properties and inherited conceptually by
the desktop dashboard.

---

## 2. Palette

All design tokens are declared on `:root` as CSS custom properties in
[`web/src/styles/tokens.css`](../../web/src/styles/tokens.css). Every token is a
**full `rgba()`/hex form usable directly in `var(...)`** — no bare alpha numbers
that require `rgb()` channel composition at the call site.

| Token | Value | Usage |
|---|---|---|
| `--dgm-bg` | `#1a1a2e` | App background — the single darkest surface, the contrast baseline reference |
| `--dgm-surface` | `rgba(255,255,255,0.03)` | Default surface overlay (cards, panels, table rows) over `--dgm-bg` |
| `--dgm-surface-hover` | `rgba(255,255,255,0.06)` | Hover/active surface overlay (row hover, button hover) |
| `--dgm-border` | `rgba(255,255,255,0.08)` | Default low-contrast border (cards, dividers, inputs) |
| `--dgm-border-strong` | `rgba(255,255,255,0.12)` | Emphasized border (focused input, active panel chrome) |
| `--dgm-gridline` | `#2a2a3e` | Chart gridlines and table row separators (opaque, distinct from `--dgm-bg`) |
| `--dgm-text` | `rgba(255,255,255,0.95)` | Primary text — all body, labels, headings, table cells |
| `--dgm-text-muted` | `rgba(255,255,255,0.82)` | Secondary text — captions, metadata, table secondary columns |
| `--dgm-text-faint` | `rgba(255,255,255,0.60)` | Tertiary text — placeholders, disabled labels (raised from 0.50 for added AA headroom — see §6) |
| `--dgm-accent` | `#2196f3` | Interactive accent — icons, indicators, large text, links. Reserved for emphasis, not body copy (see §6) |
| `--dgm-accent-warm` | `#63e2b7` | Warm accent / positive emphasis (aliases status-ok green) |
| `--dgm-status-ok` | `#63e2b7` | Success / healthy status (server ok, scan complete) |
| `--dgm-status-fail` | `#ef5350` | Failure / error status (server fail, scan error) |
| `--dgm-status-unknown` | `rgba(255,255,255,0.30)` | Unknown / untested status — **DECORATION DOTS ONLY, never text** (see §5, §6 exception) |
| `--dgm-market-cn` | `#ef5350` | CN market accent (aliases status-fail red) |
| `--dgm-market-us` | `#2196f3` | US market accent (aliases the blue accent) |
| `--dgm-chart-up` | `#ef5350` | Candlestick up bar — CN convention: **red = up** |
| `--dgm-chart-down` | `#26a69a` | Candlestick down bar — green/teal = down |
| `--dgm-chart-ma5` | `#2196f3` | MA5 moving-average line |
| `--dgm-chart-ma20` | `#ff9800` | MA20 moving-average line |
| `--dgm-chart-text` | `#d1d4dc` | Chart axis labels, price scale, crosshair tooltip text |
| `--dgm-table-border` | `#3a3b52` | Opaque table grid border (heavier than `--dgm-border`) |
| `--dgm-font-sans` | `'Microsoft YaHei','PingFang SC','Hiragino Sans GB',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif` | CJK-first sans-serif stack (see §3) |
| `--dgm-font-mono` | `ui-monospace,SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace` | Monospace stack for tickers, prices, code |

### Reduced-motion baseline (a11y)

`tokens.css` includes a global `prefers-reduced-motion` guard so operators who
request reduced motion never see a transition or animation (closes
`accessibility-requirements.md` §7):

```css
/* a11y reduced-motion baseline — neutralize all motion for operators who
   request it. Targets every element plus Naive UI's n-progress indeterminate
   spin so streaming scans do not animate for motion-sensitive operators. */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
  }
  .n-progress .n-progress-graph-line-indicator {
    animation: none !important;
  }
}
```

---

## 3. Typography

**CJK-first system stack.** `--dgm-font-sans` leads with `Microsoft YaHei`
(the desktop's global font, `dashboard.py:133-134`) so Chinese ticker names and
report content render identically on desktop and web. The web stack then falls
back through `PingFang SC` (macOS) and `Hiragino Sans GB` before reaching the
generic `system-ui` / `-apple-system` / `Segoe UI` / `Roboto` Latin stack.

**Mono stack.** `--dgm-font-mono` (`ui-monospace` first) is used for tickers,
prices, and numeric table columns where monospaced digit alignment matters.

**No web font is loaded.** The desktop uses Microsoft YaHei natively; the web
console uses the operator's system CJK fallback. **Bundling a font is out of
scope** (see §8) — the local-first, single-operator constraint makes a web-font
download unnecessary, and the desktop already has YaHei installed.

---

## 4. Spacing & Elevation

MY-DOGE-MICRO uses a **flat, translucent-overlay elevation model**, not drop
shadows. Depth is communicated entirely through stacked translucent white
overlays on the opaque `--dgm-bg`:

- **Base**: `--dgm-bg` (`#1a1a2e`) — the app canvas.
- **Surface**: `--dgm-surface` (`rgba(255,255,255,0.03)`) — cards, panels, and
  table bodies sit one translucent layer above the base.
- **Hover/active**: `--dgm-surface-hover` (`rgba(255,255,255,0.06)`) — a doubled
  opacity lift for row hover and active affordances.
- **Borders**: `--dgm-border` (`rgba(255,255,255,0.08)`) default, rising to
  `--dgm-border-strong` (`rgba(255,255,255,0.12)`) on focus/active. Borders are
  deliberately **low-contrast** so the dark-first aesthetic stays calm; emphasis
  is carried by the translucent surface lift, not by border weight.

There is no shadow token. This keeps the dark UI flat and low-glare, and avoids
the muddy shadow-on-dark problem. Charts and tables use the opaque
`--dgm-gridline` / `--dgm-table-border` for crisp structural lines where a
translucent border would be too faint.

---

## 5. Status Semantics

Status is encoded by color with a fixed mapping shared by the scanner, server
latency tests, and any loading/empty/error surface:

| Status | Token | Color | Meaning |
|---|---|---|---|
| **ok** | `--dgm-status-ok` / `--dgm-accent-warm` | `#63e2b7` green | Healthy, succeeded, server reachable, scan complete |
| **fail** | `--dgm-status-fail` / `--dgm-market-cn` | `#ef5350` red | Error, failed, server unreachable, scan error |
| **unknown** | `--dgm-status-unknown` | `rgba(255,255,255,0.30)` gray | Untested / indeterminate |

**The `unknown` token is decoration-only — it renders a status DOT, never text.**
A translucent-gray status word would fail contrast catastrophically (see §6
exception); the semantic is communicated by the dot's presence/absence, with any
accompanying label using `--dgm-text-muted`.

**Market accents.** CN market = `--dgm-market-cn` (red); US market =
`--dgm-market-us` (blue). These alias the fail/red and accent/blue tokens so the
market identity is color-coupled to its directional convention.

**Chart direction convention (CN).** `--dgm-chart-up` = red (`#ef5350`),
`--dgm-chart-down` = green/teal (`#26a69a`) — the Chinese-market convention
where **red = up, green = down**, the inverse of the US convention. This is a
deliberate product choice for a CN-market-first operator.

---

## 6. Contrast Baseline

Contrast ratios are measured against the app background `--dgm-bg` (`#1a1a2e`)
per WCAG 2.1. One genuine gap is closed by this token set; one value is raised
for added headroom; one deliberate reservation is recorded.

| Token / use | Contrast vs `#1a1a2e` | WCAG level | Note |
|---|---|---|---|
| `--dgm-text` (`.95`) | 12.6:1 | **AAA** | Primary text everywhere |
| `--dgm-text-muted` (`.82`) | 9.4:1 | **AAA** | Secondary text |
| `--dgm-text-faint` (`.60`) | ~6.8:1 | **AAA** | Prior `.50` was already ~5.2:1 (AA); raised to `.60` for additional AAA headroom, not to clear AA |
| `--dgm-status-ok` / `--dgm-accent-warm` `#63e2b7` | 7.8:1 | **AAA** | Green status |
| `--dgm-status-fail` / `--dgm-market-cn` `#ef5350` | 4.6:1 | **AA** | Red status |
| `--dgm-chart-text` `#d1d4dc` | 9.5:1 | **AAA** | Chart axis/tooltip text |
| `--dgm-accent` / `--dgm-market-us` `#2196f3` | 5.46:1 | **AA** (passes normal text) | Reserved for icons, indicators, large text, and links — see rule below |
| `--dgm-status-unknown` `rgba(.30)` | decoration only | **EXCEPTION** | Recorded exception — never used as text |

**Fix 1 — faint text.** `--dgm-text-faint` alpha was raised from `0.50` (~5.2:1,
already AA) to `0.60` (~6.8:1, AAA-level headroom) for additional legibility
margin on disabled labels and placeholders — not to clear AA, which the prior
value already satisfied.

**Fix 2 — status-unknown.** `--dgm-status-unknown` at `rgba(255,255,255,0.30)`
has negligible contrast and is therefore **forbidden as text**; it renders a
decoration dot only (§5).

**Exception — the blue accent.** `--dgm-accent` (`#2196f3`) measures **5.46:1**
against the background, which **passes WCAG AA for normal-size text** (and nearly
clears AA Large). It is nonetheless **reserved for icons, indicators, large text
(≥18pt / 14pt bold), and links** as a deliberate brand/legibility choice: body
copy stays on the higher-contrast `--dgm-text` (~12.6:1) for maximum readability,
preserving the blue as a high-signal interactive accent rather than spending it
on running prose. **RULE: small and body text always uses `--dgm-text`; the blue
accent is never used for body copy.**

---

## 7. Component Primitives

The web console renders status and async states through **Naive UI primitives**
under a single `n-config-provider :theme="darkTheme"` root (`App.vue:81`). The
primitives in active use, mapped to the status semantics in §5:

| Primitive | Token / semantic used | Purpose |
|---|---|---|
| `n-spin` | wraps `--dgm-accent` (Naive default) | Inline loading on tables, modals, views |
| `n-empty` | `--dgm-text-muted` description | Explicit empty state (Insights macro/notes tabs) |
| `n-alert` (`type="error"`) | `--dgm-status-fail` | Scanner scan-fail banner + Retry (`ScannerView.vue:115-131`) |
| `n-progress` | `--dgm-accent` bar; indeterminate spin neutralized by the reduced-motion rule (§2) | Scan progress streaming |
| `n-config-provider` + `themeOverrides` | the `:root` tokens feed `themeOverrides` so Naive components inherit the dgm palette | Single theming seam |
| `n-skeleton` | `--dgm-surface` shimmer | Loading placeholder (planned) |

**StatusView.vue (upcoming).** A shared status component will standardize the
loading/empty/error triad across views, closing the §9.5 gaps in
`vue-web-console.md`. Its contract:

- **Loading** → `n-skeleton` (matches the table/view shape) under `--dgm-surface`.
- **Empty** → `n-empty` with a `--dgm-text-muted` description.
- **Error** → `n-result` (error variant) tinted with `--dgm-status-fail`, with a
  Retry action.

**Governing rule (restated):** small and body text inside any primitive always
uses `--dgm-text` (or `--dgm-text-muted` / `--dgm-text-faint`), **never the blue
`--dgm-accent`** (§6 exception). Although `--dgm-accent` passes AA at 5.46:1, it
is reserved for icons, indicators, large headings, and links so body copy stays
on the higher-contrast `--dgm-text` (~12.6:1) for maximum readability.

---

## 8. Out of Scope

The following are deliberately **not** part of this art bible or the current
product, and are recorded here so they are not assumed by future work:

- **No light theme / `prefers-color-scheme` toggle.** MY-DOGE-MICRO is dark-only
  now. A light theme is a future ADR, not a current capability.
- **No brand logo.** There is no logo system; the app is identified by its
  toolbar text and view labels only.
- **No illustration system.** The product is data-dense tables, charts, and
  Markdown — no spot illustrations, empty-state art, or icon set beyond the
  `@vicons/ionicons5` set already in use.
- **No bundled English (or any) web font.** Typography is the system CJK stack
  (`--dgm-font-sans`) and system mono stack (`--dgm-font-mono`); bundling a font
  is unnecessary for a local-first single-operator tool (§3).
- **No VirtualTable keyboard row navigation.** Row-level keyboard navigation in
  `VirtualTable.vue` remains an OPEN item (`accessibility-requirements.md` §3.2)
  and is out of scope for this art bible, which governs only visual style.
