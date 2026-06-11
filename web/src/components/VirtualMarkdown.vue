<template>
  <div ref="container" class="virtual-markdown" @scroll="onScroll">
    <div :style="{ height: totalHeight + 'px', position: 'relative' }">
      <!-- Spacer above viewport -->
      <div v-if="firstVisibleIdx > 0" :style="{ height: spacerAbove + 'px' }" />
      <!-- Visible chunks -->
      <div
        v-for="chunk in visibleChunks"
        :key="chunk.index"
        :ref="(el) => setChunkRef(chunk.index, el as HTMLElement | null)"
        class="markdown-body"
        :style="{ position: 'relative' }"
        v-html="chunk.html"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'

const props = withDefaults(defineProps<{
  content: string
  font?: string
  lineHeight?: number
  linesPerChunk?: number
}>(), {
  font: '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  lineHeight: 22,
  linesPerChunk: 40,
})

const container = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const containerHeight = ref(0)
const containerWidth = ref(0)

const md = new MarkdownIt()

interface Chunk {
  index: number
  source: string
  html: string
  predictedHeight: number
  actualHeight: number | null
}

const chunks = ref<Chunk[]>([])

// Compute chunks from markdown content
function computeChunks() {
  if (!props.content || containerWidth.value <= 0) {
    chunks.value = []
    return
  }

  // Split source text into chunks by line count
  const sourceLines = props.content.split('\n')
  const result: Chunk[] = []
  let lineOffset = 0

  while (lineOffset < sourceLines.length) {
    const endLine = Math.min(lineOffset + props.linesPerChunk, sourceLines.length)
    const chunkLines = sourceLines.slice(lineOffset, endLine)
    const source = chunkLines.join('\n')

    // Predict height: lines * lineHeight (rough estimate, corrected after render)
    const predictedLineCount = Math.min(props.linesPerChunk, endLine - lineOffset)
    const predictedHeight = predictedLineCount * props.lineHeight

    result.push({
      index: result.length,
      source,
      html: md.render(source),
      predictedHeight,
      actualHeight: null,
    })

    lineOffset = endLine
  }

  chunks.value = result
}

// Total height
const totalHeight = computed(() => {
  let h = 0
  for (const chunk of chunks.value) {
    h += chunk.actualHeight ?? chunk.predictedHeight
  }
  return h
})

// Spacer above viewport
const firstVisibleIdx = computed(() => {
  const top = scrollTop.value - 300
  let accH = 0
  for (let i = 0; i < chunks.value.length; i++) {
    const chunk = chunks.value[i]
    const h = getChunkHeight(chunk)
    if (accH + h > top) return i
    accH += h
  }
  return chunks.value.length
})

const spacerAbove = computed(() => {
  let h = 0
  for (let i = 0; i < firstVisibleIdx.value; i++) {
    h += getChunkHeight(chunks.value[i], i)
  }
  return h
})

// Visible chunks (viewport + buffer)
const visibleChunks = computed(() => {
  const top = scrollTop.value - 300
  const bottom = scrollTop.value + containerHeight.value + 300
  let accH = 0
  const visible: Chunk[] = []

  for (let i = 0; i < chunks.value.length; i++) {
    const chunk = chunks.value[i]
    const h = getChunkHeight(chunk)

    if (accH + h > top && accH < bottom) {
      visible.push(chunk)
    }
    accH += h

    if (accH > bottom + 300) break
  }
  return visible
})

// Helper: get effective height for a chunk
function getChunkHeight(chunk: Chunk): number {
  return chunk.actualHeight ?? chunk.predictedHeight
}

// Measure actual chunk heights and apply corrections
const chunkRefs = new Map<number, HTMLElement>()
function setChunkRef(index: number, el: HTMLElement | null) {
  if (el) {
    chunkRefs.set(index, el)
    // Only measure chunks that haven't been measured yet
    if (chunks.value[index]?.actualHeight != null) return
    // Measure actual height after render
    requestAnimationFrame(() => {
      const actualH = el.offsetHeight
      if (actualH > 0 && chunks.value[index]) {
        chunks.value[index].actualHeight = actualH
      }
    })
  } else {
    chunkRefs.delete(index)
  }
}

// Scroll handler with RAF batching
let scrollRaf: number | null = null
function onScroll() {
  if (scrollRaf != null) return
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = null
    if (container.value) {
      scrollTop.value = container.value.scrollTop
    }
  })
}

// ResizeObserver
let resizeObserver: ResizeObserver | null = null

function setupObserver() {
  if (!container.value) return
  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      containerWidth.value = entry.contentRect.width
      containerHeight.value = entry.contentRect.height
      computeChunks()
    }
  })
  resizeObserver.observe(container.value)
  containerWidth.value = container.value.clientWidth
  containerHeight.value = container.value.clientHeight
}

// Re-chunk when content changes
watch(() => props.content, () => {
  computeChunks()
})

onMounted(() => {
  nextTick(() => {
    setupObserver()
    computeChunks()
  })
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  if (scrollRaf != null) cancelAnimationFrame(scrollRaf)
})
</script>

<style scoped>
.virtual-markdown {
  overflow-y: auto;
  height: 100%;
  min-height: 0;
}
.markdown-body {
  padding: 12px 16px;
  color: rgba(255, 255, 255, 0.82);
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 16px 0 8px;
  color: rgba(255, 255, 255, 0.95);
}
.markdown-body :deep(p) {
  margin: 8px 0;
  line-height: 1.6;
}
.markdown-body :deep(code) {
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
}
.markdown-body :deep(pre) {
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #3a3b52;
  padding: 6px 10px;
  text-align: left;
}
</style>
