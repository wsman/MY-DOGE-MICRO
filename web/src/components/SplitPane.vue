<template>
  <!-- ZOOMED MODE: render only the zoomed leaf -->
  <div
    v-if="isZoomedLeaf"
    class="split-pane leaf"
    :class="{ active: isActive }"
    @mousedown="activate"
  >
    <PanelChrome :node="node as LeafNode" />
  </div>

  <!-- LEAF NODE -->
  <div
    v-else-if="node.type === 'leaf'"
    class="split-pane leaf"
    :class="{ active: isActive }"
    @mousedown="activate"
  >
    <PanelChrome :node="node" />
  </div>

  <!-- SPLIT NODE: horizontal (left | divider | right) -->
  <div
    v-else-if="node.type === 'split' && node.layout === 'horizontal'"
    ref="containerEl"
    class="split-pane split horizontal"
  >
    <SplitPane :node="node.left" :style="{ width: leftPercent }" />
    <div
      class="divider vertical-divider"
      @pointerdown.stop="onDividerDown($event, 'horizontal')"
    />
    <SplitPane :node="node.right" :style="{ width: rightPercent }" />
  </div>

  <!-- SPLIT NODE: vertical (top | divider | bottom) -->
  <div
    v-else-if="node.type === 'split'"
    ref="containerEl"
    class="split-pane split vertical"
  >
    <SplitPane :node="node.left" :style="{ height: leftPercent }" />
    <div
      class="divider horizontal-divider"
      @pointerdown.stop="onDividerDown($event, 'vertical')"
    />
    <SplitPane :node="node.right" :style="{ height: rightPercent }" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { SplitTreeNode, SplitLayout, LeafNode } from '../types/splitTree'
import { useSplitTree } from '../composables/useSplitTree'
import { VIEW_REGISTRY } from '../views/registry'
import PanelChrome from './PanelChrome.vue'

const props = defineProps<{ node: SplitTreeNode }>()
const splitTree = useSplitTree()
const containerEl = ref<HTMLElement | null>(null)

const isActive = computed(() => props.node.handle === splitTree.activeHandle.value)
const isZoomedLeaf = computed(() =>
  splitTree.zoomedHandle.value != null && props.node.handle === splitTree.zoomedHandle.value
)

// Computed size percentages for split children
const leftPercent = computed(() => {
  if (props.node.type !== 'split') return '100%'
  return `${(props.node.ratio * 100).toFixed(2)}%`
})
const rightPercent = computed(() => {
  if (props.node.type !== 'split') return '0%'
  return `${((1 - props.node.ratio) * 100).toFixed(2)}%`
})

function activate() {
  if (props.node.type === 'leaf') {
    splitTree.setActive(props.node.handle)
  }
}

// ---------------------------------------------------------------------------
// Drag-to-resize (ghostty: resizeInPlace L483-495)
// ---------------------------------------------------------------------------

const DIVIDER_PX = 4
const DEFAULT_MIN_PX = 300

/**
 * Calculate the minimum width/height a tree node needs.
 * Leaf nodes use the registered minWidth; split nodes sum their children.
 */
function getMinPanelPx(node: SplitTreeNode): number {
  if (node.type === 'leaf') {
    const entry = VIEW_REGISTRY[node.viewId]
    return entry?.minWidth ?? DEFAULT_MIN_PX
  }
  // Split node: both children must fit, plus divider
  return getMinPanelPx(node.left) + DIVIDER_PX + getMinPanelPx(node.right)
}

function onDividerDown(e: PointerEvent, layout: SplitLayout) {
  if (props.node.type !== 'split') return
  e.preventDefault()

  const el = containerEl.value
  if (!el) return

  const startClient = layout === 'horizontal' ? e.clientX : e.clientY
  const containerSize = layout === 'horizontal' ? el.offsetWidth : el.offsetHeight
  const startRatio = props.node.ratio
  const effectiveSize = containerSize - DIVIDER_PX

  // Compute min/max ratio from dynamic minimum panel sizes
  const leftMinPx = getMinPanelPx(props.node.left)
  const rightMinPx = getMinPanelPx(props.node.right)
  const minRatio = Math.max(0.05, leftMinPx / effectiveSize)
  const maxRatio = Math.min(0.95, 1 - rightMinPx / effectiveSize)

  // Guard against impossible constraints (container too small)
  if (minRatio > maxRatio) return

  const onMove = (moveE: PointerEvent) => {
    const currentClient = layout === 'horizontal' ? moveE.clientX : moveE.clientY
    const delta = currentClient - startClient
    const deltaRatio = delta / effectiveSize
    const newRatio = Math.max(minRatio, Math.min(maxRatio, startRatio + deltaRatio))
    splitTree.resize(props.node.handle, newRatio)
  }

  const onUp = () => {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    splitTree.persist()
  }

  document.body.style.cursor = layout === 'horizontal' ? 'col-resize' : 'row-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}
</script>

<style scoped>
.split-pane {
  display: flex;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.split-pane.split.horizontal {
  flex-direction: row;
}

.split-pane.split.vertical {
  flex-direction: column;
}

.split-pane.leaf {
  flex-direction: column;
  position: relative;
}

.split-pane.leaf.active {
  box-shadow: inset 0 0 0 1px rgba(99, 226, 183, 0.3);
}

.divider {
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.06);
  transition: background 0.15s;
  z-index: 1;
}

.divider:hover,
.divider:active {
  background: rgba(99, 226, 183, 0.4);
}

.vertical-divider {
  width: 4px;
  cursor: col-resize;
}

.horizontal-divider {
  height: 4px;
  cursor: row-resize;
}
</style>
