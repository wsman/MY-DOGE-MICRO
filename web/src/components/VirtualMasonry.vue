<template>
  <div ref="scrollContainer" class="virtual-masonry" @scroll="onScroll">
    <div class="masonry-content" :style="{ height: contentHeight + 'px', position: 'relative' }">
      <div
        v-for="pos in visibleCards"
        :key="pos.item.id"
        class="masonry-card"
        :style="{
          position: 'absolute',
          left: pos.x + 'px',
          top: pos.y + 'px',
          width: pos.width + 'px',
          height: pos.height + 'px',
        }"
      >
        <slot name="card" :item="pos.item" :width="pos.width" :height="pos.height">
          <div class="card-default" :style="{ padding: cardPadding + 'px', fontSize: '14px', lineHeight: lineHeight + 'px' }">
            {{ pos.item.text }}
          </div>
        </slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { prepare, layout, type PreparedText } from '@pretext'

export interface MasonryItem {
  id: string | number
  text: string
  [key: string]: unknown
}

interface PositionedCard {
  item: MasonryItem
  x: number
  y: number
  width: number
  height: number
}

const props = withDefaults(defineProps<{
  items: MasonryItem[]
  font?: string
  lineHeight?: number
  cardPadding?: number
  gap?: number
  bufferPx?: number
  maxColWidth?: number
}>(), {
  font: '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  lineHeight: 20,
  cardPadding: 16,
  gap: 12,
  bufferPx: 200,
  maxColWidth: 400,
})

const scrollContainer = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const containerWidth = ref(0)
const containerHeight = ref(0)

// Prepared texts cache (not reactive — opaque objects)
let preparedTexts = new Map<string | number, PreparedText>()

// All positioned cards (recomputed on resize/items change)
const positionedCards = ref<PositionedCard[]>([])
const contentHeight = ref(0)

// Re-prepare all texts when items change
watch(() => props.items, (items) => {
  const newPrepared = new Map<string | number, PreparedText>()
  for (const item of items) {
    newPrepared.set(item.id, prepare(item.text, props.font))
  }
  preparedTexts = newPrepared
  computePositions()
}, { immediate: false })

// Recompute positions when container width or items change
function computePositions() {
  const w = containerWidth.value
  if (w <= 0 || props.items.length === 0) {
    positionedCards.value = []
    contentHeight.value = 0
    return
  }

  // Compute responsive column layout
  let colCount: number
  let colWidth: number
  const minColWidth = 100 + w * 0.1

  if (w <= 520) {
    colCount = 1
    colWidth = Math.min(props.maxColWidth, w - props.gap * 2)
  } else {
    colCount = Math.max(2, Math.floor((w + props.gap) / (minColWidth + props.gap)))
    colWidth = Math.min(props.maxColWidth, (w - (colCount + 1) * props.gap) / colCount)
  }

  const textWidth = colWidth - props.cardPadding * 2
  const contentWidth = colCount * colWidth + (colCount - 1) * props.gap
  const offsetLeft = (w - contentWidth) / 2

  // Track column heights with Float64Array (from pretext demo)
  const colHeights = new Float64Array(colCount)
  for (let c = 0; c < colCount; c++) colHeights[c] = props.gap

  const cards: PositionedCard[] = []

  for (const item of props.items) {
    // Find shortest column
    let shortest = 0
    for (let c = 1; c < colCount; c++) {
      if (colHeights[c]! < colHeights[shortest]!) shortest = c
    }

    // Get text height from pretext (pure arithmetic on cached widths)
    const prepared = preparedTexts.get(item.id)
    const { height: textH } = prepared
      ? layout(prepared, textWidth, props.lineHeight)
      : { height: props.lineHeight }
    const totalH = textH + props.cardPadding * 2

    cards.push({
      item,
      x: offsetLeft + shortest * (colWidth + props.gap),
      y: colHeights[shortest]!,
      width: colWidth,
      height: totalH,
    })

    colHeights[shortest]! += totalH + props.gap
  }

  // Find max column height
  let maxH = 0
  for (let c = 0; c < colCount; c++) {
    if (colHeights[c]! > maxH) maxH = colHeights[c]!
  }

  positionedCards.value = cards
  contentHeight.value = maxH
}

// Visibility culling: only cards in viewport + buffer
const visibleCards = computed(() => {
  const top = scrollTop.value - props.bufferPx
  const bottom = scrollTop.value + containerHeight.value + props.bufferPx
  return positionedCards.value.filter(p => p.y + p.height > top && p.y < bottom)
})

// RAF-batched scroll handler (from pretext demo)
let scrollRaf: number | null = null
function onScroll() {
  if (scrollRaf != null) return
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = null
    if (scrollContainer.value) {
      scrollTop.value = scrollContainer.value.scrollTop
    }
  })
}

// ResizeObserver
let resizeObserver: ResizeObserver | null = null
let resizeRaf: number | null = null

function setupObserver() {
  if (!scrollContainer.value) return
  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      if (resizeRaf != null) cancelAnimationFrame(resizeRaf)
      resizeRaf = requestAnimationFrame(() => {
        containerWidth.value = entry.contentRect.width
        containerHeight.value = entry.contentRect.height
        computePositions()
      })
    }
  })
  resizeObserver.observe(scrollContainer.value)
  containerWidth.value = scrollContainer.value.clientWidth
  containerHeight.value = scrollContainer.value.clientHeight
}

onMounted(() => {
  // Initial prepare + layout
  const newPrepared = new Map<string | number, PreparedText>()
  for (const item of props.items) {
    newPrepared.set(item.id, prepare(item.text, props.font))
  }
  preparedTexts = newPrepared

  nextTick(() => {
    setupObserver()
    computePositions()
  })
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  if (scrollRaf != null) cancelAnimationFrame(scrollRaf)
  if (resizeRaf != null) cancelAnimationFrame(resizeRaf)
})

// Watch for external container width changes
watch(containerWidth, () => computePositions())
</script>

<style scoped>
.virtual-masonry {
  overflow-y: auto;
  height: 100%;
  position: relative;
}
.masonry-card {
  background: #24253a;
  border: 1px solid #3a3b52;
  border-radius: 8px;
  box-sizing: border-box;
  overflow: hidden;
}
.card-default {
  color: rgba(255, 255, 255, 0.82);
}
</style>
