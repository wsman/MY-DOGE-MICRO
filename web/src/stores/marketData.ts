import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { listTables, queryTable, fetchTickerNames } from '../api/data'
import type { KlineData } from '../types/stock'

export const useMarketDataStore = defineStore('marketData', () => {
  const tables = ref<string[]>([])
  const currentTable = ref('stock_prices')
  const rows = ref<Record<string, unknown>[]>([])
  const columns = ref<string[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(50)
  const searchQuery = ref('')
  const loading = ref(false)
  const selectedTicker = ref<string | null>(null)
  const selectedMarket = ref<'cn' | 'us' | null>(null)
  const klineData = ref<KlineData[]>([])

  // Ticker name mapping
  const tickerNames = ref<Record<string, string>>({})
  const showNames = ref(false)
  const _namesLoaded = ref<Set<string>>(new Set())

  // -- Infinite scroll accumulator --
  const allRows = ref<Record<string, unknown>[]>([])
  const hasMore = ref(true)
  const fetchPageSize = ref(500) // larger page for infinite scroll

  async function loadTickerNames(market: string) {
    if (_namesLoaded.value.has(market)) return
    try {
      tickerNames.value = await fetchTickerNames(market)
      _namesLoaded.value.add(market)
    } catch {
      // Silently fail — names are optional
    }
  }

  function getTickerDisplayName(ticker: string): string {
    if (showNames.value && tickerNames.value[ticker]) {
      return tickerNames.value[ticker]
    }
    return ticker
  }

  async function loadTables(market: string) {
    tables.value = await listTables(market)
  }

  async function loadPage(market: string) {
    loading.value = true
    try {
      const result = await queryTable(
        market, currentTable.value,
        page.value, pageSize.value,
        searchQuery.value || undefined
      )
      columns.value = result.columns
      rows.value = result.rows
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  // -- Infinite scroll: load all data progressively --
  async function loadAllRows(market: string) {
    loading.value = true
    allRows.value = []
    page.value = 1
    hasMore.value = true
    try {
      const result = await queryTable(
        market, currentTable.value,
        1, fetchPageSize.value,
        searchQuery.value || undefined
      )
      columns.value = result.columns
      allRows.value = result.rows
      total.value = result.total
      hasMore.value = allRows.value.length < total.value
      page.value = 1
    } finally {
      loading.value = false
    }
  }

  async function loadMoreRows(market: string) {
    if (loading.value || !hasMore.value) return
    loading.value = true
    try {
      const nextPage = Math.floor(allRows.value.length / fetchPageSize.value) + 1
      const result = await queryTable(
        market, currentTable.value,
        nextPage, fetchPageSize.value,
        searchQuery.value || undefined
      )
      columns.value = result.columns
      allRows.value = allRows.value.concat(result.rows)
      total.value = result.total
      hasMore.value = allRows.value.length < total.value
    } finally {
      loading.value = false
    }
  }

  return {
    tables, currentTable, rows, columns, total, page, pageSize,
    searchQuery, loading, selectedTicker, selectedMarket, klineData,
    tickerNames, showNames,
    allRows, hasMore, fetchPageSize,
    loadTables, loadPage, loadTickerNames, getTickerDisplayName,
    loadAllRows, loadMoreRows,
  }
})
