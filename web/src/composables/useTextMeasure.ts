/**
 * Canvas text measurement with two-level cache.
 * Inspired by pretext's measurement.ts architecture:
 *   Map<fontString, Map<textString, widthPixels>>
 *
 * Avoids DOM layout reflow by using OffscreenCanvas for measurement.
 */

type Cache = Map<string, Map<string, number>>

// Module-level singleton for shared instances
let sharedCache: Cache | null = null
let sharedCtx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D | null = null

function createContext(): CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D {
  if (sharedCtx) return sharedCtx
  // Prefer OffscreenCanvas (worker-safe, no DOM side effects)
  if (typeof OffscreenCanvas !== 'undefined') {
    sharedCtx = new OffscreenCanvas(1, 1).getContext('2d')!
    return sharedCtx
  }
  // Fallback to DOM canvas
  if (typeof document !== 'undefined') {
    sharedCtx = document.createElement('canvas').getContext('2d')!
    return sharedCtx
  }
  throw new Error('Text measurement requires OffscreenCanvas or DOM canvas')
}

export interface TextMeasureHandle {
  /** Measure a single text string. Returns pixel width. */
  measure: (text: string, font: string) => number
  /** Batch-measure multiple items. Groups by font for efficiency. */
  measureBatch: (items: Array<{ text: string; font: string }>) => Float64Array
  /** Clear the cache. */
  clear: () => void
  /** Total number of cached entries across all fonts. */
  cacheSize: () => number
  /** Get the raw context (for advanced use). */
  context: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D
}

/**
 * Create a text measurement handle.
 * @param shared If true, returns a module-level singleton cache shared across callers.
 *               If false (default), returns an independent cache.
 */
export function useTextMeasure(shared = false): TextMeasureHandle {
  const ctx = createContext()
  const cache: Cache = shared ? (sharedCache ??= new Map()) : new Map()

  function measure(text: string, font: string): number {
    let fontCache = cache.get(font)
    if (!fontCache) {
      fontCache = new Map()
      cache.set(font, fontCache)
    }
    const cached = fontCache.get(text)
    if (cached !== undefined) return cached

    ctx.font = font
    const width = ctx.measureText(text).width
    fontCache.set(text, width)
    return width
  }

  function measureBatch(items: Array<{ text: string; font: string }>): Float64Array {
    const results = new Float64Array(items.length)

    // Group by font to minimize ctx.font assignments
    const groups = new Map<string, Array<{ text: string; idx: number }>>()
    for (let i = 0; i < items.length; i++) {
      const { text, font } = items[i]!
      let group = groups.get(font)
      if (!group) {
        group = []
        groups.set(font, group)
      }
      group.push({ text, idx: i })
    }

    for (const [font, entries] of groups) {
      let fontCache = cache.get(font)
      if (!fontCache) {
        fontCache = new Map()
        cache.set(font, fontCache)
      }
      ctx.font = font
      for (const { text, idx } of entries) {
        const cached = fontCache.get(text)
        if (cached !== undefined) {
          results[idx] = cached
        } else {
          const width = ctx.measureText(text).width
          fontCache.set(text, width)
          results[idx] = width
        }
      }
    }

    return results
  }

  function clear() {
    cache.clear()
  }

  function cacheSize(): number {
    let total = 0
    for (const fontCache of cache.values()) {
      total += fontCache.size
    }
    return total
  }

  return { measure, measureBatch, clear, cacheSize, context: ctx }
}
