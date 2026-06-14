<template>
  <div class="panel-chrome">
    <div class="chrome-left">
      <n-select
        :value="node.viewId"
        :options="viewOptions"
        size="tiny"
        style="width: 130px"
        @update:value="onViewChange"
      />
    </div>
    <div class="chrome-right">
      <n-button quaternary size="tiny" title="Split Horizontal" @click="splitH">
        <template #icon>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="1" y="1" width="12" height="12" rx="1" />
            <line x1="7" y1="1" x2="7" y2="13" />
          </svg>
        </template>
      </n-button>
      <n-button quaternary size="tiny" title="Split Vertical" @click="splitV">
        <template #icon>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="1" y="1" width="12" height="12" rx="1" />
            <line x1="1" y1="7" x2="13" y2="7" />
          </svg>
        </template>
      </n-button>
      <n-button
        quaternary size="tiny"
        :type="isZoomed ? 'primary' : 'default'"
        title="Zoom"
        @click="toggleZoom"
      >
        <template #icon>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M2 5V2h3M12 5V2H9M2 9v3h3M12 9v3H9" />
          </svg>
        </template>
      </n-button>
      <n-button quaternary size="tiny" title="Close" :disabled="!canClosePanel" @click="closePanel">
        <template #icon>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
            <line x1="3" y1="3" x2="11" y2="11" />
            <line x1="11" y1="3" x2="3" y2="11" />
          </svg>
        </template>
      </n-button>
    </div>
  </div>
  <div class="panel-content">
    <component :is="viewComponent" v-if="viewComponent" :key="node.handle" />
    <div v-else class="panel-empty">
      <n-text depth="3">Select a view</n-text>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { NSelect, NButton, NText } from 'naive-ui'
import type { LeafNode, ViewId } from '../types/splitTree'
import { VIEW_REGISTRY, VIEW_SELECT_OPTIONS } from '../views/registry'
import { useSplitTree } from '../composables/useSplitTree'

const props = defineProps<{ node: LeafNode }>()
const splitTree = useSplitTree()

const viewOptions = VIEW_SELECT_OPTIONS
const canClosePanel = computed(() => splitTree.canClose())
const isZoomed = computed(() => splitTree.zoomedHandle.value === props.node.handle)

// Lazy-load the view component
const viewComponent = computed(() => {
  const entry = VIEW_REGISTRY[props.node.viewId]
  if (!entry) return null
  return defineAsyncComponent(entry.loader)
})

function onViewChange(viewId: ViewId) {
  splitTree.setView(props.node.handle, viewId)
}

function splitH() {
  splitTree.split(props.node.handle, 'horizontal', 'scanner')
}

function splitV() {
  splitTree.split(props.node.handle, 'vertical', 'scanner')
}

function toggleZoom() {
  splitTree.toggleZoom(props.node.handle)
}

function closePanel() {
  splitTree.remove(props.node.handle)
}
</script>

<style scoped>
.panel-chrome {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 32px;
  padding: 0 6px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
  gap: 4px;
}

.chrome-left {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.chrome-right {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.panel-content {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.panel-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>
