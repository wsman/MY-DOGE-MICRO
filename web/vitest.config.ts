/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// Mirrors the @pretext alias in vite.config.ts so the resolver works in tests.
// @pretext points at the sibling project at ../../pretext/src/layout.ts (see
// design/cdd/vue-web-console.md §9 "Integration Requirements"). Tests that
// touch @pretext transitively (usePretextLayout, VirtualMasonry) are skipped
// in the smoke suite — see web/src/__tests__/README comments.
const pretextSrc = resolve('D:/Users/WSMAN/Desktop/Coding Task/pretext/src')

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@pretext': resolve(pretextSrc, 'layout.ts'),
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
