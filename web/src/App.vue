<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { darkTheme } from 'naive-ui'
import {
  NConfigProvider, NMessageProvider, NButton, NSpace, NText, NTooltip,
} from 'naive-ui'
import { useSplitTree } from './composables/useSplitTree'
import SplitPane from './components/SplitPane.vue'
import type { SplitLayout } from './types/splitTree'

const splitTree = useSplitTree()

// ---------------------------------------------------------------------------
// Layout presets
// ---------------------------------------------------------------------------

function preset(p: 'single' | 'h-split' | 'v-split' | 'quad') {
  splitTree.applyPreset(p)
}

// ---------------------------------------------------------------------------
// Keyboard shortcuts
// ---------------------------------------------------------------------------

function onKeyDown(e: KeyboardEvent) {
  // Ctrl+Shift+% → split horizontal (using % key which is Shift+5)
  // Ctrl+Shift+" → split vertical (using " key which is Shift+')
  // We use simpler shortcuts:
  //   Ctrl+Shift+H → horizontal split
  //   Ctrl+Shift+V → vertical split
  //   Ctrl+W       → close panel
  //   Ctrl+Enter   → toggle zoom
  //   Alt+Arrow    → spatial navigation

  if (e.ctrlKey && e.shiftKey && e.key === 'H') {
    e.preventDefault()
    if (splitTree.activeHandle.value) {
      splitTree.split(splitTree.activeHandle.value, 'horizontal', 'scanner')
    }
    return
  }

  if (e.ctrlKey && e.shiftKey && e.key === 'V') {
    e.preventDefault()
    if (splitTree.activeHandle.value) {
      splitTree.split(splitTree.activeHandle.value, 'vertical', 'scanner')
    }
    return
  }

  if (e.ctrlKey && !e.shiftKey && e.key === 'w') {
    e.preventDefault()
    if (splitTree.canClose()) {
      splitTree.remove(splitTree.activeHandle.value)
    }
    return
  }

  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault()
    if (splitTree.activeHandle.value) {
      splitTree.toggleZoom(splitTree.activeHandle.value)
    }
    return
  }

  if (e.altKey && ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
    e.preventDefault()
    const dirMap: Record<string, string> = {
      ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down',
    }
    splitTree.gotoSpatial(dirMap[e.key] as any)
    return
  }
}

onMounted(() => window.addEventListener('keydown', onKeyDown))
onUnmounted(() => window.removeEventListener('keydown', onKeyDown))
</script>

<template>
  <n-config-provider :theme="darkTheme">
    <n-message-provider>
      <div class="app-root">
        <!-- Top toolbar -->
        <div class="toolbar">
          <n-text strong class="app-title">MY-DOGE</n-text>
          <n-space size="small" align="center">
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button size="tiny" quaternary @click="preset('single')">1</n-button>
              </template>
              Single panel
            </n-tooltip>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button size="tiny" quaternary @click="preset('h-split')">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="1" y="1" width="12" height="12" rx="1" />
                    <line x1="7" y1="1" x2="7" y2="13" />
                  </svg>
                </n-button>
              </template>
              Side by side (Ctrl+Shift+H)
            </n-tooltip>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button size="tiny" quaternary @click="preset('v-split')">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="1" y="1" width="12" height="12" rx="1" />
                    <line x1="1" y1="7" x2="13" y2="7" />
                  </svg>
                </n-button>
              </template>
              Stacked (Ctrl+Shift+V)
            </n-tooltip>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button size="tiny" quaternary @click="preset('quad')">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="1" y="1" width="12" height="12" rx="1" />
                    <line x1="7" y1="1" x2="7" y2="13" />
                    <line x1="1" y1="7" x2="13" y2="7" />
                  </svg>
                </n-button>
              </template>
              Quad split
            </n-tooltip>
            <span class="toolbar-sep">|</span>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button size="tiny" quaternary @click="splitTree.equalize()">Equalize</n-button>
              </template>
              Equalize all splits
            </n-tooltip>
          </n-space>
        </div>
        <!-- Split tree fills remaining space -->
        <div class="split-root">
          <SplitPane :node="splitTree.visibleRoot.value" />
        </div>
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<style>
body { margin: 0; background: #1a1a2e; }
a { text-decoration: none; color: inherit; }
* { box-sizing: border-box; }
</style>

<style scoped>
.app-root {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.toolbar {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
  flex-shrink: 0;
}

.app-title {
  font-size: 14px;
  letter-spacing: 1px;
  background: linear-gradient(135deg, #63e2b7, #2196f3);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.toolbar-sep {
  color: rgba(255, 255, 255, 0.15);
  font-size: 12px;
}

.split-root {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
</style>
