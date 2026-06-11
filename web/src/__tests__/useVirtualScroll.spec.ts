import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { ref, nextTick } from 'vue'
import { useVirtualScroll } from '../composables/useVirtualScroll'

/**
 * useVirtualScroll reads container geometry from a DOM element via a Vue
 * `watch(containerRef, …, { immediate: true })` and instantiates a
 * ResizeObserver (useVirtualScroll.ts:74-87). jsdom provides neither a real
 * layout nor a ResizeObserver, so we:
 *   1. stub `globalThis.ResizeObserver` with a no-op class, and
 *   2. drive geometry through a minimal fake element whose `scrollTop` and
 *      `clientHeight` we control, then call `syncScrollTop()` to copy those
 *      values into the composable's internal refs.
 *
 * The `visibleRange` computed (useVirtualScroll.ts:37-52) is the unit-testable
 * seam — pure arithmetic on itemCount + containerHeight + scrollTop + rowHeight
 * + bufferRows.
 */

// Minimal fake of the subset of HTMLElement useVirtualScroll touches.
interface FakeEl {
  scrollTop: number
  clientHeight: number
}
function makeEl(height: number, scrollTop = 0): FakeEl {
  return { scrollTop, clientHeight: height }
}

// jsdom has no ResizeObserver — install a no-op stand-in.
class FakeResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

let prevRO: typeof globalThis.ResizeObserver | undefined
beforeEach(() => {
  prevRO = globalThis.ResizeObserver
  globalThis.ResizeObserver = FakeResizeObserver as unknown as typeof globalThis.ResizeObserver
})
afterEach(() => {
  if (prevRO === undefined) {
    delete (globalThis as { ResizeObserver?: unknown }).ResizeObserver
  } else {
    globalThis.ResizeObserver = prevRO
  }
  vi.restoreAllMocks()
})

describe('useVirtualScroll', () => {
  it('totalHeight = itemCount * rowHeight', async () => {
    const el = ref<HTMLElement | null>(null)
    const itemCount = ref(100)
    const { totalHeight } = useVirtualScroll(el, itemCount, { rowHeight: 32 })
    el.value = makeEl(600) as unknown as HTMLElement
    await nextTick()
    expect(totalHeight.value).toBe(100 * 32)
  })

  it('empty list: visibleRange is the zero sentinel', async () => {
    const el = ref<HTMLElement | null>(null)
    const itemCount = ref(0)
    const { visibleRange } = useVirtualScroll(el, itemCount, { rowHeight: 32 })
    el.value = makeEl(600) as unknown as HTMLElement
    await nextTick()
    expect(visibleRange.value).toEqual({ startIdx: 0, endIdx: 0, offsetY: 0 })
  })

  it('computes a correct window at the top (scrollTop=0)', async () => {
    const el = ref<HTMLElement | null>(null)
    const itemCount = ref(1000)
    const { visibleRange } = useVirtualScroll(el, itemCount, {
      rowHeight: 32,
      bufferRows: 5,
    })
    // 600px viewport / 32px row = ceil(18.75) = 19 visible rows
    el.value = makeEl(600, 0) as unknown as HTMLElement
    await nextTick()

    const range = visibleRange.value
    // startIdx clamped to >= 0; centerIdx = floor(0/32) = 0 → startIdx = max(0, 0-5) = 0
    expect(range.startIdx).toBe(0)
    // endIdx = min(1000, 0 + 19 + 5 + 1) = 25
    expect(range.endIdx).toBe(25)
    // offsetY = startIdx * rowHeight = 0
    expect(range.offsetY).toBe(0)
  })

  it('computes a correct window after scrolling down', async () => {
    const el = ref<HTMLElement | null>(null)
    const itemCount = ref(1000)
    const { visibleRange, syncScrollTop } = useVirtualScroll(el, itemCount, {
      rowHeight: 32,
      bufferRows: 5,
    })
    el.value = makeEl(640, 0) as unknown as HTMLElement
    await nextTick()

    // Scroll so the top row is at index 10 (scrollTop = 320).
    ;(el.value as unknown as FakeEl).scrollTop = 320
    syncScrollTop()
    await nextTick()

    const range = visibleRange.value
    // visibleCount = ceil(640/32) = 20; centerIdx = floor(320/32) = 10
    // startIdx = max(0, 10-5) = 5
    expect(range.startIdx).toBe(5)
    // endIdx = min(1000, 10 + 20 + 5 + 1) = 36
    expect(range.endIdx).toBe(36)
    // offsetY = 5 * 32 = 160
    expect(range.offsetY).toBe(160)
  })

  it('endIdx is clamped to itemCount near the bottom', async () => {
    const el = ref<HTMLElement | null>(null)
    const itemCount = ref(50)
    const { visibleRange, syncScrollTop } = useVirtualScroll(el, itemCount, {
      rowHeight: 32,
      bufferRows: 5,
    })
    el.value = makeEl(640, 0) as unknown as HTMLElement
    await nextTick()

    // Scroll past the end (50*32 = 1600 total; scroll to 1500).
    ;(el.value as unknown as FakeEl).scrollTop = 1500
    syncScrollTop()
    await nextTick()

    const range = visibleRange.value
    // centerIdx = floor(1500/32) = 46; visibleCount = 20
    // startIdx = max(0, 46-5) = 41
    expect(range.startIdx).toBe(41)
    // endIdx = min(50, 46 + 20 + 5 + 1) = min(50, 72) = 50 (clamped)
    expect(range.endIdx).toBe(50)
    expect(range.offsetY).toBe(41 * 32)
  })

  it('respects a custom bufferRows', async () => {
    const el = ref<HTMLElement | null>(null)
    const itemCount = ref(1000)
    const { visibleRange } = useVirtualScroll(el, itemCount, {
      rowHeight: 32,
      bufferRows: 20,
    })
    el.value = makeEl(320, 0) as unknown as HTMLElement
    await nextTick()

    const range = visibleRange.value
    // visibleCount = ceil(320/32) = 10; centerIdx = 0
    // startIdx = max(0, 0-20) = 0
    // endIdx = min(1000, 0 + 10 + 20 + 1) = 31
    expect(range.startIdx).toBe(0)
    expect(range.endIdx).toBe(31)
  })

  it('default bufferRows is 5', async () => {
    const el = ref<HTMLElement | null>(null)
    const itemCount = ref(1000)
    // Omit bufferRows → default 5 (useVirtualScroll.ts:26)
    const { visibleRange } = useVirtualScroll(el, itemCount, { rowHeight: 32 })
    el.value = makeEl(320, 0) as unknown as HTMLElement
    await nextTick()

    const range = visibleRange.value
    // visibleCount = 10; centerIdx = 0; endIdx = 0 + 10 + 5 + 1 = 16
    expect(range.endIdx).toBe(16)
  })

  it('reacts to itemCount changes', async () => {
    const el = ref<HTMLElement | null>(null)
    const itemCount = ref(10)
    const { totalHeight, visibleRange } = useVirtualScroll(el, itemCount, {
      rowHeight: 32,
      bufferRows: 5,
    })
    el.value = makeEl(320, 0) as unknown as HTMLElement
    await nextTick()
    expect(totalHeight.value).toBe(320)
    // 10 items, viewport 320 (10 visible), scrollTop 0 → endIdx = min(10, 0+10+5+1)=10
    expect(visibleRange.value.endIdx).toBe(10)

    itemCount.value = 1000
    await nextTick()
    expect(totalHeight.value).toBe(32000)
    expect(visibleRange.value.endIdx).toBe(16)
  })

  it('reacts to container height changes (resize)', async () => {
    const el = ref<HTMLElement | null>(null)
    const itemCount = ref(1000)
    const { visibleRange, syncScrollTop } = useVirtualScroll(el, itemCount, {
      rowHeight: 32,
      bufferRows: 5,
    })
    el.value = makeEl(320, 0) as unknown as HTMLElement
    await nextTick()
    // 320px viewport → 10 visible → endIdx = 16
    expect(visibleRange.value.endIdx).toBe(16)

    // Resize: taller container exposes more rows.
    ;(el.value as unknown as FakeEl).clientHeight = 640
    syncScrollTop()
    await nextTick()
    // 640px → 20 visible → endIdx = 0 + 20 + 5 + 1 = 26
    expect(visibleRange.value.endIdx).toBe(26)
  })

  it('handles a single-item list', async () => {
    const el = ref<HTMLElement | null>(null)
    const itemCount = ref(1)
    const { visibleRange, totalHeight } = useVirtualScroll(el, itemCount, {
      rowHeight: 32,
      bufferRows: 5,
    })
    el.value = makeEl(600, 0) as unknown as HTMLElement
    await nextTick()
    expect(totalHeight.value).toBe(32)
    // centerIdx = 0; startIdx = 0; endIdx = min(1, 0+19+5+1) = 1
    expect(visibleRange.value.startIdx).toBe(0)
    expect(visibleRange.value.endIdx).toBe(1)
    expect(visibleRange.value.offsetY).toBe(0)
  })

  it('offsetY always equals startIdx * rowHeight', async () => {
    const el = ref<HTMLElement | null>(null)
    const itemCount = ref(1000)
    const { visibleRange, syncScrollTop } = useVirtualScroll(el, itemCount, {
      rowHeight: 40,
      bufferRows: 3,
    })
    el.value = makeEl(500, 0) as unknown as HTMLElement
    await nextTick()

    for (const scrollTop of [0, 80, 400, 1200, 5000]) {
      ;(el.value as unknown as FakeEl).scrollTop = scrollTop
      syncScrollTop()
      await nextTick()
      expect(visibleRange.value.offsetY).toBe(
        visibleRange.value.startIdx * 40,
      )
      // Invariants
      expect(visibleRange.value.startIdx).toBeGreaterThanOrEqual(0)
      expect(visibleRange.value.endIdx).toBeLessThanOrEqual(1000)
      expect(visibleRange.value.endIdx).toBeGreaterThanOrEqual(
        visibleRange.value.startIdx,
      )
    }
  })
})
