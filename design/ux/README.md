# UX Specs — Operator Journey View

> **Status**: Seed (Wave 2 docs, 2026-06-12)
> **Scope**: Local operator journeys across the Vue Web Console (Module #11) and
> the PyQt Desktop Dashboard (Module #10). This directory is the *operator-journey*
> companion to the technical-contract CDDs in `design/cdd/`.

## Purpose of this directory

Per `design/CLAUDE.md` ("UX Specs"), `design/ux/` holds the operator-facing
journey and interaction specifications. Where a CDD answers *"what does this
module contractually do?"*, a UX spec answers *"how does a single local operator
move through this surface to get their job done, and what do they see at each
step?"*.

MY-DOGE-MICRO has **two** operator surfaces, and this directory specs both:

| Surface | Implementation | Primary input |
|---|---|---|
| **Web Console** | `web/src/` — Vue 3 + Vite + Pinia + Naive UI | Keyboard + mouse (full shortcut map) |
| **Desktop Dashboard** | `src/interface/` — PyQt6 `CommandCenter` | Mouse + Tab/Enter (Qt widgets) |

The web console is the richer, keyboard-first surface (Ghostty-style split-tree
panels, six registered views, three virtualized components). The desktop is the
mouse-driven fallback that works without a browser. Both are local-first: the
operator is the only user, on Windows, against local SQLite/DuckDB stores.

## UX specs vs. CDDs — which to read

| You want to know… | Read |
|---|---|
| What a module *contracts* (API, schema, errors, config knobs, acceptance) | `design/cdd/*.md` (the technical-contract view) |
| How the *operator moves* through a surface, what they see, what goes wrong | `design/ux/*.md` (the operator-journey view) |

UX specs **cite** CDDs for the contract and add the journey: entry points,
step-by-step flow, the loading/empty/error triad, and the keyboard path. UX specs
must never redefine a contract — if a contract is wrong, fix the CDD and let the
UX spec reference the corrected one.

- The web console's technical contract: [`design/cdd/vue-web-console.md`](../cdd/vue-web-console.md) (Module #11).
- The desktop dashboard's technical contract: [`design/cdd/pyqt-desktop-dashboard.md`](../cdd/pyqt-desktop-dashboard.md) (Module #10).

## Index of specs

### Cross-cutting (apply to every web view)

| Spec | What it defines |
|---|---|
| [`interaction-patterns.md`](./interaction-patterns.md) | Web interaction library: split-tree panel model, virtualization patterns, keyboard shortcut map, SSE progress pattern, the loading/empty/error triad requirement. **Web-only** — desktop interaction is mouse-driven Qt. |
| [`accessibility-requirements.md`](./accessibility-requirements.md) | Baseline a11y: target audience, declared `browserslist`, keyboard accessibility per view, color/contrast, CJK support, reduced-motion/screen-reader status. |

### Per-flow specs

| Spec | Surface | Status |
|---|---|---|
| [`scanner-flow.md`](./scanner-flow.md) | Web `ScannerView` + Desktop `ScannerWidget` (tab 1) | Seed (this wave) |
| [`ticker-flow.md`](./ticker-flow.md) | Web `TickerView` (panel-only, no router route) | Published |
| [`archive-flow.md`](./archive-flow.md) | Web `CnArchiveView`/`UsArchiveView` + Desktop editors (tabs 2–4) | Published |
| [`analysis-flow.md`](./analysis-flow.md) | Web `InsightsView`/`AnalysisView` + Desktop `AnalysisWidget` (tab 5) | Published |

> **Note on the desktop "Insights" tab**: the desktop tab 4 (`🧠 研报智库`,
> `dashboard.py:76-79`) is a `DBEditorWidget` bound to `research_insights.db` —
> a raw SQLite table editor, *not* the report-masonry surface the web `InsightsView`
> provides. The two are not the same journey; the desktop has no masonry/report
> reader. See [`analysis-flow.md`](./analysis-flow.md) §5 for the divergence.

## How UX specs relate to the registered views

The web console registers exactly six views (`web/src/views/registry.ts:18-61`,
`web/src/types/splitTree.ts:22`): `scanner`, `cn-archive`, `us-archive`,
`ticker`, `insights`, `analysis`. The intent is one per-flow UX spec per view.
This wave ships the cross-cutting framework + the scanner flow (the most
critical, SSE-driven, watchdog-gated flow); the remaining three per-flow specs
(`ticker-flow.md`, `archive-flow.md`, `analysis-flow.md`) are now published,
derived from the cross-cutting patterns established here.

## Validation

Author with `/ux-design`. Validate a finished spec with `/ux-review` before
passing it to `/team-ui`. The docs-consistency gate
`tests/unit/ux/test_ux_doc_coverage.py` asserts the seed files exist and that
`accessibility-requirements.md` declares a `browserslist`.
