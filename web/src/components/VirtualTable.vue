<template>
  <div class="vt-root">
    <!-- Header row — fixed -->
    <div class="vt-header">
      <div
        v-for="col in columns"
        :key="col.key"
        class="vt-cell vt-header-cell"
        :style="cellStyle(col)"
      >
        {{ col.title }}
      </div>
    </div>

    <!-- Scrollable body -->
    <div ref="scrollEl" class="vt-body" @scroll="onScroll">
      <div :style="{ height: totalHeight + 'px', position: 'relative' }">
        <div :style="{ transform: `translateY(${visibleRange.offsetY}px)` }">
          <div
            v-for="(row, idx) in visibleRows"
            :key="rowKey ? row[rowKey] : visibleRange.startIdx + idx"
            class="vt-row"
            :class="{ 'vt-row-striped': (visibleRange.startIdx + idx) % 2 === 1 }"
            :style="{ height: rowHeight + 'px' }"
            @click="$emit('rowClick', row)"
          >
            <div
              v-for="col in columns"
              :key="col.key"
              class="vt-cell"
              :style="cellStyle(col)"
            >
              <template v-if="col.render">{{ col.render(row) }}</template>
              <template v-else>{{ row[col.key] }}</template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading indicator -->
    <div v-if="loading" class="vt-loading">
      <span class="vt-loading-text">Loading...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useVirtualScroll } from '../composables/useVirtualScroll'

export interface VtColumn {
  key: string
  title: string
  width?: string
  render?: (row: Record<string, unknown>) => string
}

const props = withDefaults(defineProps<{
  columns: VtColumn[]
  items: Record<string, unknown>[]
  rowHeight?: number
  bufferRows?: number
  rowKey?: string
  loading?: boolean
}>(), {
  rowHeight: 32,
  bufferRows: 8,
  loading: false,
})

const emit = defineEmits<{
  rowClick: [row: Record<string, unknown>]
  scrollEnd: []
}>()

// Template ref — attached to the scrollable body element
const scrollEl = ref<HTMLElement | null>(null)

const { totalHeight, visibleRange, onScroll: onVirtualScroll } = useVirtualScroll(
  scrollEl,
  computed(() => props.items.length),
  { rowHeight: props.rowHeight, bufferRows: props.bufferRows },
)

const visibleRows = computed(() => {
  const { startIdx, endIdx } = visibleRange.value
  return props.items.slice(startIdx, endIdx)
})

// Scroll handler: virtual scroll update + scroll-end detection
function onScroll() {
  onVirtualScroll()
  // Detect near-bottom scroll to emit scrollEnd
  const el = scrollEl.value
  if (!el) return
  const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
  if (distanceFromBottom < props.rowHeight * props.bufferRows * 2) {
    emit('scrollEnd')
  }
}

function cellStyle(col: VtColumn) {
  if (col.width) return { width: col.width, flexShrink: '0' }
  return { flex: '1 1 0', minWidth: '0' }
}
</script>

<style scoped>
.vt-root {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.vt-header {
  display: flex;
  flex-shrink: 0;
  height: 30px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
}

.vt-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.vt-header-cell {
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  opacity: 0.7;
}

.vt-row {
  display: flex;
  cursor: pointer;
  transition: background-color 0.1s;
}

.vt-row:hover {
  background: rgba(255, 255, 255, 0.06);
}

.vt-row-striped {
  background: rgba(255, 255, 255, 0.02);
}

.vt-cell {
  padding: 0 8px;
  display: flex;
  align-items: center;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.vt-loading {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
}

.vt-loading-text {
  font-size: 12px;
  opacity: 0.7;
}
</style>
