import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const pretextSrc = resolve('D:/Users/WSMAN/Desktop/Coding Task/pretext/src')

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@pretext': resolve(pretextSrc, 'layout.ts'),
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8901'
    }
  },
  build: {
    outDir: 'dist'
  }
})
