/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// Mirrors the @pretext alias in vite.config.ts so the resolver works in tests.
// @pretext is vendored into web/src/vendor/pretext/ (S002-012 / TR-037) — the
// alias no longer points at a sibling-project checkout. See ADR-0008 §Alternatives
// and web/src/vendor/pretext/README.md. Tests that touch @pretext transitively
// (usePretextLayout, VirtualMasonry) are still skipped in the smoke suite because
// jsdom lacks OffscreenCanvas + Intl.Segmenter (see web/src/__tests__/ README comments).

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@pretext': resolve(__dirname, 'src/vendor/pretext/layout.ts'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.spec.ts', 'src/**/*.test.ts'],
    // jsdom lacks OffscreenCanvas + Intl.Segmenter support varies; keep the
    // smoke suite to pure-arithmetic and store-logic tests.
    coverage: {
      reporter: ['text', 'html'],
    },
  },
})
