import { ref, shallowRef, watch, onUnmounted, type Ref } from 'vue'
import {
  prepare,
  prepareWithSegments,
  layout,
  type PreparedText,
  type PreparedTextWithSegments,
  type LayoutResult,
} from '@pretext'

export interface PretextLayoutOptions {
  /** CSS font string, e.g. '14px "Helvetica Neue", sans-serif' */
  font: string
  /** Line height in pixels */
  lineHeight: number
  /** Use rich variant with segment data (for markdown). Default: false */
  withSegments?: boolean
}

/**
 * Wraps pretext's two-phase prepare/layout cycle in Vue reactivity.
 *
 * Phase 1: prepareAll() — segments text, measures via canvas, caches widths.
 * Phase 2: relayout() — pure arithmetic on cached widths (~0.0002ms/text).
 *
 * ResizeObserver on the container auto-triggers relayout.
 */
export function usePretextLayout(
  containerRef: Ref<HTMLElement | null>,
  options: PretextLayoutOptions,
) {
  const preparedMap = shallowRef<Map<string | number, PreparedText | PreparedTextWithSegments>>(new Map())
  const layoutResults = ref<Map<string | number, LayoutResult>>(new Map())
  const containerWidth = ref(0)

  let resizeObserver: ResizeObserver | null = null
  let rafId: number | null = null

  // Phase 2: layout all prepared texts for current width
  function relayout() {
    const results = new Map<string | number, LayoutResult>()
    const maxWidth = containerWidth.value
    if (maxWidth <= 0) return
    for (const [id, prepared] of preparedMap.value) {
      results.set(id, layout(prepared, maxWidth, options.lineHeight))
    }
    layoutResults.value = results
  }

  // Schedule relayout in next animation frame (debounce rapid resizes)
  function scheduleRelayout() {
    if (rafId != null) return
    rafId = requestAnimationFrame(() => {
      rafId = null
      relayout()
    })
  }

  // Phase 1: prepare one text block
  function prepareText(id: string | number, text: string) {
    const p = options.withSegments
      ? prepareWithSegments(text, options.font)
      : prepare(text, options.font)
    const newMap = new Map(preparedMap.value)
    newMap.set(id, p)
    preparedMap.value = newMap
    scheduleRelayout()
  }

  // Batch prepare: accept an array of { id, text } items
  function prepareAll(items: Array<{ id: string | number; text: string }>) {
    const newMap = new Map<string | number, PreparedText | PreparedTextWithSegments>()
    for (const item of items) {
      const p = options.withSegments
        ? prepareWithSegments(item.text, options.font)
        : prepare(item.text, options.font)
      newMap.set(item.id, p)
    }
    preparedMap.value = newMap
    scheduleRelayout()
  }

  // Get computed font from an element
  function getComputedFont(el: HTMLElement): string {
    const style = getComputedStyle(el)
    return `${style.fontSize} ${style.fontFamily}`
  }

  // Setup resize observation
  function setupResize() {
    if (!containerRef.value) return
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        containerWidth.value = entry.contentRect.width
        scheduleRelayout()
      }
    })
    resizeObserver.observe(containerRef.value)
    containerWidth.value = containerRef.value.clientWidth
    relayout()
  }

  watch(containerRef, (el) => {
    if (el) setupResize()
  }, { immediate: true })

  onUnmounted(() => {
    resizeObserver?.disconnect()
    if (rafId != null) cancelAnimationFrame(rafId)
  })

  return {
    preparedMap,
    layoutResults,
    containerWidth,
    prepareText,
    prepareAll,
    relayout,
    getComputedFont,
  }
}
