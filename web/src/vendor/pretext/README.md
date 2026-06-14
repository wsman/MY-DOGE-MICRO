# Vendored `@pretext`

This directory is a **vendored fork** of [`@chenglou/pretext`](https://github.com/chenglou/text-layout) — a canvas-measured text-layout library. It is vendored (not consumed from npm) so that `web/` builds on a clean checkout of MY-DOGE-MICRO without a sibling-project checkout. See [ADR-0008](../../../../docs/architecture/adr-0008-web-architecture.md) (Alternative 3) and story [S002-012](../../../../docs/architecture/tr-registry.yaml) (TR-037) for the decision.

## Provenance

| Field | Value |
|-------|-------|
| **Upstream repo** | `D:/Users/WSMAN/Desktop/Coding Task/pretext` (sibling project, separate git repo) |
| **Upstream source path** | `pretext/src/` |
| **Vendored commit** | `4e71390` ("Release 0.0.4") |
| **Upstream tag** | `v0.0.4` |
| **Vendored date** | 2026-06-12 |
| **Vendored by** | S002-012 (TR-037) |

## Vendored files (the import closure of `layout.ts`)

| File | Upstream | Purpose |
|------|----------|---------|
| `layout.ts` | `pretext/src/layout.ts` | Public entry: `prepare`, `prepareWithSegments`, `layout`, `PreparedText`, `PreparedTextWithSegments`, `LayoutResult`. Has a one-line provenance header above the original comment. |
| `analysis.ts` | `pretext/src/analysis.ts` | Text analysis (CJK/kinsoku/punctuation), imported by `layout.ts`. |
| `line-break.ts` | `pretext/src/line-break.ts` | Line-wrapping walk over prepared widths, imported by `layout.ts`. |
| `measurement.ts` | `pretext/src/measurement.ts` | Canvas `measureText` + emoji correction, imported by `layout.ts`. |
| `bidi.ts` | `pretext/src/bidi.ts` | Simplified bidi segment levels, imported by `layout.ts`. |

**Deliberately NOT copied** (not in the runtime import closure): `layout.test.ts`, `test-data.ts`, `text-modules.d.ts`.

The relative `./bidi.js`-style import specifiers inside these files resolve within this vendor directory under `moduleResolution: bundler` (vue-tsc) and Vite. Do **not** rewrite them.

## How it is consumed

The `@pretext` path alias (`web/vite.config.ts`, `web/vitest.config.ts`, `web/tsconfig.app.json`) points at `web/src/vendor/pretext/layout.ts`. The two importers are unchanged:
- `web/src/composables/usePretextLayout.ts`
- `web/src/components/VirtualMasonry.vue`

The regression contract is enforced by `web/src/__tests__/vendor-pretext-regression.spec.ts` (export shape only — `prepare`, `prepareWithSegments`, `layout` are callable; jsdom lacks `Intl.Segmenter` + `OffscreenCanvas`, so `layout()` is not invoked on real text in the smoke suite).

## Re-sync procedure (hand-sync on upstream bumps)

> Vendoring forks the library: upstream fixes do **not** flow automatically. This is the accepted cost per ADR-0008 §Consequences. Re-sync is a manual, documented step.

**To upgrade:**

1. `cd` to the sibling pretext repo and `git checkout <new-tag-or-commit>` (record the new commit/tag below).
2. Diff the 5 source files against this directory:
   ```bash
   diff -u web/src/vendor/pretext/layout.ts     <pretext-repo>/src/layout.ts
   diff -u web/src/vendor/pretext/analysis.ts    <pretext-repo>/src/analysis.ts
   diff -u web/src/vendor/pretext/line-break.ts  <pretext-repo>/src/line-break.ts
   diff -u web/src/vendor/pretext/measurement.ts <pretext-repo>/src/measurement.ts
   diff -u web/src/vendor/pretext/bidi.ts        <pretext-repo>/src/bidi.ts
   ```
3. Re-copy any changed file(s) **verbatim** (preserve the one-line provenance header on `layout.ts` — re-apply it after copying, since the upstream copy does not have it).
4. Update the **Vendored commit** / **Upstream tag** / **Vendored date** rows in the Provenance table above to the new values.
5. Re-run: `cd web && npm run build && npm test` — both MUST stay green.
6. Confirm `grep -rn 'pretext/src' web/` returns only the Provenance rows in this README (no live absolute import has crept back in).

**Upgrade history:**

| Date | Commit | Tag | Notes |
|------|--------|-----|-------|
| 2026-06-12 | `4e71390` | `v0.0.4` | Initial vendor (S002-012). |
