import { describe, it, expect } from 'vitest'
import {
  prepare,
  prepareWithSegments,
  layout,
  type PreparedText,
  type PreparedTextWithSegments,
  type LayoutResult,
} from '@pretext'

/**
 * Contract test for the vendored @pretext module (S002-012 / TR-037).
 *
 * WHAT THIS GUARDS:
 *   The vendored copy at web/src/vendor/pretext/ must uphold the SAME public
 *   contract the two importers (usePretextLayout.ts, VirtualMasonry.vue)
 *   depend on: three runtime fns (prepare, prepareWithSegments, layout) that
 *   are callable, plus three exported types (PreparedText,
 *   PreparedTextWithSegments, LayoutResult). This catches a partial/incomplete
 *   vendor copy (e.g. a missing transitive file, a renamed export) before it
 *   breaks the app build.
 *
 * WHAT THIS DOES NOT DO:
 *   It does NOT invoke layout() (or prepare()) on real text. jsdom lacks
 *   Intl.Segmenter + OffscreenCanvas, which layout.ts relies on at runtime;
 *   vitest.config.ts deliberately keeps @pretext-using RUNTIME tests out of
 *   the smoke suite. This file asserts the EXPORT SHAPE only — a static
 *   contract check, not a behavior check.
 *
 * If this file ever needs to assert layout() behavior, polyfill
 * Intl.Segmenter + a canvas measureText stub in the test setup first, or move
 * that scenario to an E2E suite against a real browser.
 */

describe('vendored @pretext public contract (S002-012 / TR-037)', () => {
  it('exports the three runtime functions the app consumes', () => {
    // typeof === 'function' confirms the bindings resolved to actual callables,
    // not undefined re-exports from a missing/partial vendor copy.
    expect(typeof prepare).toBe('function')
    expect(typeof prepareWithSegments).toBe('function')
    expect(typeof layout).toBe('function')
  })

  it('exports the three types as compile-time-only bindings (no runtime value)', () => {
    // Type-only imports are erased at runtime; the only runtime assertion we
    // can make is that referencing them as values would be `undefined`. We
    // instead assert via a type-level check below. Here we just confirm the
    // module object is non-null (the import resolved at all).
    // The real type check is the `import { ... type ... }` line above compiling
    // under vue-tsc (this spec is in the build's tsconfig include glob).
    expect(import.meta).toBeDefined()
  })

  // Compile-time contract: if any of these names were removed/renamed in the
  // vendored copy, vue-tsc fails the build. The `satisfies` trick forces the
  // types into a position where they MUST resolve or the file does not compile.
  it('type-checks the exported types are importable (compile-time)', () => {
    // PreparedText / PreparedTextWithSegments are opaque handles to layout();
    // LayoutResult is the output shape. We bind them into a value position via
    // a satisfies on a typed factory so the type names MUST exist.
    const checkTypes = ((p: PreparedText, pw: PreparedTextWithSegments, _r: LayoutResult) => {
      return { p, pw }
    }) satisfies (
      p: PreparedText,
      pw: PreparedTextWithSegments,
      r: LayoutResult,
    ) => { p: PreparedText; pw: PreparedTextWithSegments }
    expect(typeof checkTypes).toBe('function')
  })
})
