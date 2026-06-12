import { onUnmounted, nextTick, type Ref } from 'vue'
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  ColorType,
} from 'lightweight-charts'
import type { IChartApi, ISeriesApi } from 'lightweight-charts'
import type { KlineData } from '../types/stock'

// ---------------------------------------------------------------------------
// Design-token resolution.
//
// lightweight-charts consumes RAW color strings and cannot read CSS var()
// references, so at chart init time we resolve the dgm-* tokens from the
// computed style on :root and pass the cached strings into the chart options.
// Each resolver carries a fallback that matches the original hardcoded value,
// keeping chart appearance identical even if tokens.css fails to load.
// Token names must stay in sync with web/src/styles/tokens.css.
// ---------------------------------------------------------------------------
function token(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

// Convert a solid #rrggbb / #rgb / rgb() color into an "r, g, b" triplet so we
// can append an alpha channel for translucent series (volume bars) without
// changing the base hue. Returns the input unchanged if it cannot be parsed.
function rgbTriplet(color: string): string {
  if (color.startsWith('#')) {
    let hex = color.slice(1)
    if (hex.length === 3) hex = hex.split('').map(c => c + c).join('')
    const r = parseInt(hex.slice(0, 2), 16)
    const g = parseInt(hex.slice(2, 4), 16)
    const b = parseInt(hex.slice(4, 6), 16)
    if ([r, g, b].every(n => Number.isFinite(n))) return `${r}, ${g}, ${b}`
  }
  const m = color.match(/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/)
  if (m) return `${m[1]}, ${m[2]}, ${m[3]}`
  return color
}

// Volume bars render at 0.3 alpha over the same up/down hues as the candles.
const VOLUME_ALPHA = 0.3

export function useKlineChart(container: Ref<HTMLElement | null>) {
  let chart: IChartApi | null = null
  let candleSeries: ISeriesApi<'Candlestick'> | null = null
  let volumeSeries: ISeriesApi<'Histogram'> | null = null
  let ma5Series: ISeriesApi<'Line'> | null = null
  let ma20Series: ISeriesApi<'Line'> | null = null
  let resizeObserver: ResizeObserver | null = null

  // Palette is resolved from CSS tokens once, when the chart initializes, and
  // cached here so setData() can reuse the translucent volume hues without
  // re-reading computed style on every render.
  let palette = {
    ma5: '#2196f3',
    ma20: '#ff9800',
    upVol: `rgba(${rgbTriplet('#ef5350')}, ${VOLUME_ALPHA})`,
    downVol: `rgba(${rgbTriplet('#26a69a')}, ${VOLUME_ALPHA})`,
  }

  function initChart() {
    if (!container.value || chart) return

    // Resolve palette from CSS tokens once per chart init.
    const bg = token('--dgm-bg', '#1a1a2e')
    const textColor = token('--dgm-chart-text', '#d1d4dc')
    const gridline = token('--dgm-gridline', '#2a2a3e')
    const up = token('--dgm-chart-up', '#ef5350')
    const down = token('--dgm-chart-down', '#26a69a')
    const ma5 = token('--dgm-chart-ma5', '#2196f3')
    const ma20 = token('--dgm-chart-ma20', '#ff9800')
    palette = {
      ma5,
      ma20,
      upVol: `rgba(${rgbTriplet(up)}, ${VOLUME_ALPHA})`,
      downVol: `rgba(${rgbTriplet(down)}, ${VOLUME_ALPHA})`,
    }

    const w = container.value.clientWidth || 400
    const h = container.value.clientHeight || 500
    chart = createChart(container.value, {
      layout: {
        background: { type: ColorType.Solid, color: bg },
        textColor,
      },
      grid: {
        vertLines: { color: gridline },
        horzLines: { color: gridline },
      },
      width: w,
      height: h,
      timeScale: { timeVisible: false },
    })

    // v5 API: chart.addSeries(SeriesType, options)
    candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: up,
      downColor: down,
      borderUpColor: up,
      borderDownColor: down,
      wickUpColor: up,
      wickDownColor: down,
    })

    volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    ma5Series = chart.addSeries(LineSeries, {
      color: palette.ma5,
      lineWidth: 1,
      title: 'MA5',
    })

    ma20Series = chart.addSeries(LineSeries, {
      color: palette.ma20,
      lineWidth: 1,
      title: 'MA20',
    })

    resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        chart?.applyOptions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        })
      }
    })
    resizeObserver.observe(container.value)
  }

  function setData(data: KlineData[]) {
    if (!data.length) return
    initChart()
    if (!chart || !candleSeries) return

    const candleData = data.map(d => ({
      time: d.date,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }))
    candleSeries.setData(candleData)

    const volData = data.map(d => ({
      time: d.date,
      value: d.volume,
      color: d.close >= d.open ? palette.upVol : palette.downVol,
    }))
    volumeSeries?.setData(volData)

    if (data.some(d => d.ma_5 != null)) {
      ma5Series?.setData(
        data.filter(d => d.ma_5 != null).map(d => ({
          time: d.date,
          value: d.ma_5!,
        })),
      )
    }
    if (data.some(d => d.ma_20 != null)) {
      ma20Series?.setData(
        data.filter(d => d.ma_20 != null).map(d => ({
          time: d.date,
          value: d.ma_20!,
        })),
      )
    }

    chart.timeScale().fitContent()

    // Fix width after layout settles
    nextTick(() => {
      if (chart && container.value) {
        chart.applyOptions({ width: container.value.clientWidth })
      }
    })
  }

  function dispose() {
    resizeObserver?.disconnect()
    if (chart) {
      chart.remove()
      chart = null
    }
  }

  onUnmounted(() => dispose())

  return { setData, dispose }
}
