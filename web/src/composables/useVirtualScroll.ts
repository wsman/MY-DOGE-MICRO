/**
 * Virtual scroll composable for fixed-row-height tables.
 * Pure arithmetic visibility calculation — no DOM measurement needed.
 * Uses ResizeObserver for container height + RAF-batched scroll events.
 */
import { ref, computed, watch, onMounted, onUnmounted, type Ref } from 'vue'

export interface VirtualScrollOptions {
  /** Fixed row height in pixels */
  rowHeight: number
  /** Extra rows rendered above/below viewport (default: 5) */
  bufferRows?: number
}

export interface VirtualRange {
  startIdx: number
  endIdx: number
  offsetY: number
}

export function useVirtualScroll(
  containerRef: Ref<HTMLElement | null>,
  itemCount: Ref<number>,
  options: VirtualScrollOptions,
) {
  const { rowHeight, bufferRows = 5 } = options

  const scrollTop = ref(0)
  const containerHeight = ref(0)
  let rafId: number | null = null
  let resizeObserver: ResizeObserver | null = null

  // Total scrollable height
  const totalHeight = computed(() => itemCount.value * rowHeight)

  // Visible range calculation — pure arithmetic
  const visibleRange = computed<VirtualRange>(() => {
    const count = itemCount.value
    if (count === 0) return { startIdx: 0, endIdx: 0, offsetY: 0 }

    const visibleCount = Math.ceil(containerHeight.value / rowHeight)
    const centerIdx = Math.floor(scrollTop.value / rowHeight)

    const startIdx = Math.max(0, centerIdx - bufferRows)
    const endIdx = Math.min(count, centerIdx + visibleCount + bufferRows + 1)

    return {
      startIdx,
      endIdx,
      offsetY: startIdx * rowHeight,
    }
  })

  // Batch scroll events via RAF (pattern from VirtualMasonry)
  function onScroll() {
    if (rafId !== null) return
    rafId = requestAnimationFrame(() => {
      const el = containerRef.value
      if (el) scrollTop.value = el.scrollTop
      rafId = null
    })
  }

  // Sync scrollTop when container appears
  function syncScrollTop() {
    const el = containerRef.value
    if (el) {
      scrollTop.value = el.scrollTop
      containerHeight.value = el.clientHeight
    }
  }

  // Watch for container mount
  watch(containerRef, (el) => {
    if (resizeObserver) resizeObserver.disconnect()
    if (!el) return

    containerHeight.value = el.clientHeight
    scrollTop.value = el.scrollTop

    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        containerHeight.value = entry.contentRect.height
      }
    })
    resizeObserver.observe(el)
  }, { immediate: true })

  return {
    totalHeight,
    visibleRange,
    onScroll,
    syncScrollTop,
  }
}
