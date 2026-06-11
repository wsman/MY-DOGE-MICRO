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

export function useKlineChart(container: Ref<HTMLElement | null>) {
  let chart: IChartApi | null = null
  let candleSeries: ISeriesApi<'Candlestick'> | null = null
  let volumeSeries: ISeriesApi<'Histogram'> | null = null
  let ma5Series: ISeriesApi<'Line'> | null = null
  let ma20Series: ISeriesApi<'Line'> | null = null
  let resizeObserver: ResizeObserver | null = null

  function initChart() {
    if (!container.value || chart) return
    const w = container.value.clientWidth || 400
    const h = container.value.clientHeight || 500
    chart = createChart(container.value, {
      layout: {
        background: { type: ColorType.Solid, color: '#1a1a2e' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2a2a3e' },
        horzLines: { color: '#2a2a3e' },
      },
      width: w,
      height: h,
      timeScale: { timeVisible: false },
    })

    // v5 API: chart.addSeries(SeriesType, options)
    candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#ef5350',
      downColor: '#26a69a',
      borderUpColor: '#ef5350',
      borderDownColor: '#26a69a',
      wickUpColor: '#ef5350',
      wickDownColor: '#26a69a',
    })

    volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    ma5Series = chart.addSeries(LineSeries, {
      color: '#2196f3',
      lineWidth: 1,
      title: 'MA5',
    })

    ma20Series = chart.addSeries(LineSeries, {
      color: '#ff9800',
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
      color: d.close >= d.open
        ? 'rgba(239,83,80,0.3)'
        : 'rgba(38,166,154,0.3)',
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
