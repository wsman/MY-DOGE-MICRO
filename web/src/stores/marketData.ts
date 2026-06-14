import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listTables, queryTable, fetchTickerNames } from '../api/data'
import { toFetchError } from '../utils/fetchError'
import type { FetchError } from '../utils/fetchError'
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
  // Surfaced fetch failure (null = no error). Reuses the SSE { code, message }
  // vocabulary so views render one shape across streaming + one-shot fetches.
  // null'd at the start of every fetch so a Retry clears the stale banner.
  const error = ref<FetchError | null>(null)

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
    error.value = null
    try {
      const result = await queryTable(
        market, currentTable.value,
        page.value, pageSize.value,
        searchQuery.value || undefined
      )
      columns.value = result.columns
      rows.value = result.rows
      total.value = result.total
    } catch (e: unknown) {
      // Surface the rejection instead of silently blanking the table.
      error.value = toFetchError(e)
    } finally {
      loading.value = false
    }
  }

  // -- Infinite scroll: load all data progressively --
  async function loadAllRows(market: string) {
    loading.value = true
    error.value = null
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
    } catch (e: unknown) {
      // Surface the rejection — allRows stays [] from the reset above so the
      // view can render the error banner without a stale partial list.
      error.value = toFetchError(e)
    } finally {
      loading.value = false
    }
  }

  async function loadMoreRows(market: string) {
    if (loading.value || !hasMore.value) return
    loading.value = true
    error.value = null
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
    } catch (e: unknown) {
      // Surface the rejection. The already-accumulated rows are left in place
      // (the user keeps what loaded); only the failed page is lost, and the
      // banner tells them why the scroll stopped.
      error.value = toFetchError(e)
    } finally {
      loading.value = false
    }
  }

  return {
    tables, currentTable, rows, columns, total, page, pageSize,
    searchQuery, loading, error, selectedTicker, selectedMarket, klineData,
    tickerNames, showNames,
    allRows, hasMore, fetchPageSize,
    loadTables, loadPage, loadTickerNames, getTickerDisplayName,
    loadAllRows, loadMoreRows,
  }
})
