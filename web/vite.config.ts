import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// @pretext is vendored into web/src/vendor/pretext/ (S002-012 / TR-037) so the
// build no longer depends on a sibling-project checkout. See ADR-0008 §Alternatives
// and web/src/vendor/pretext/README.md for the re-sync procedure.
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@pretext': resolve(__dirname, 'src/vendor/pretext/layout.ts'),
      'doge-sdk': resolve(__dirname, '../packages/doge-sdk-typescript/src/index.ts'),
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8901',
      '/v1': 'http://localhost:8901',
      '/health': 'http://localhost:8901',
    }
  },
  build: {
    outDir: 'dist'
  }
})
