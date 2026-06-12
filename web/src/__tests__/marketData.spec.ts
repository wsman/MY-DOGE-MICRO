import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useMarketDataStore } from '../stores/marketData'

/**
 * marketData store spec. Follows the useFuzzySearch.spec.ts pattern:
 * deterministic, no live network. The API layer (api/data.ts) is stubbed with
 * vi.mock so no real axios call escapes — the store is tested in isolation.
 *
 * Covers: initial state, a state mutation, a getter (getTickerDisplayName),
 * and the loadTickerNames action (success + silent-failure paths).
 */

// Stub the entire api/data module. Only the symbols the store imports need to
// resolve; we provide sensible default mocks and override per-test.
vi.mock('../api/data', () => ({
  listTables: vi.fn().mockResolvedValue([]),
  queryTable: vi.fn().mockResolvedValue({
    columns: [], rows: [], total: 0, page: 1, page_size: 50,
  }),
  getKline: vi.fn().mockResolvedValue([]),
  fetchTickerNames: vi.fn().mockResolvedValue({}),
}))

// Import AFTER vi.mock so the store picks up the stubbed module.
import { fetchTickerNames } from '../api/data'

beforeEach(() => {
  // Each test gets a fresh Pinia instance → isolated store state.
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('useMarketDataStore', () => {
  describe('initial state', () => {
    it('starts with empty tables/rows and sensible defaults', () => {
      const store = useMarketDataStore()
      expect(store.tables).toEqual([])
      expect(store.currentTable).toBe('stock_prices')
      expect(store.rows).toEqual([])
      expect(store.columns).toEqual([])
      expect(store.total).toBe(0)
      expect(store.page).toBe(1)
      expect(store.pageSize).toBe(50)
      expect(store.loading).toBe(false)
      expect(store.selectedTicker).toBeNull()
      expect(store.selectedMarket).toBeNull()
      expect(store.klineData).toEqual([])
      expect(store.tickerNames).toEqual({})
      expect(store.showNames).toBe(false)
      expect(store.allRows).toEqual([])
      expect(store.hasMore).toBe(true)
      expect(store.fetchPageSize).toBe(500)
    })
  })

  describe('state mutations (direct ref writes)', () => {
    it('selectedTicker / selectedMarket are writable selection state', () => {
      const store = useMarketDataStore()
      store.selectedTicker = '600519'
      store.selectedMarket = 'cn'
      expect(store.selectedTicker).toBe('600519')
      expect(store.selectedMarket).toBe('cn')
    })

    it('searchQuery and currentTable are writable', () => {
      const store = useMarketDataStore()
      store.searchQuery = '茅台'
      store.currentTable = 'stock_indicators'
      expect(store.searchQuery).toBe('茅台')
      expect(store.currentTable).toBe('stock_indicators')
    })

    it('showNames toggle flips the display-mode flag', () => {
      const store = useMarketDataStore()
      expect(store.showNames).toBe(false)
      store.showNames = true
      expect(store.showNames).toBe(true)
    })
  })

  describe('getter: getTickerDisplayName', () => {
    it('returns the raw ticker when showNames is false', () => {
      const store = useMarketDataStore()
      store.tickerNames = { '600519': '贵州茅台' }
      store.showNames = false
      expect(store.getTickerDisplayName('600519')).toBe('600519')
    })

    it('returns the mapped name when showNames is true and a name exists', () => {
      const store = useMarketDataStore()
      store.tickerNames = { '600519': '贵州茅台', '000858': '五粮液' }
      store.showNames = true
      expect(store.getTickerDisplayName('600519')).toBe('贵州茅台')
      expect(store.getTickerDisplayName('000858')).toBe('五粮液')
    })

    it('falls back to the raw ticker when showNames is true but no mapping', () => {
      const store = useMarketDataStore()
      store.tickerNames = {}
      store.showNames = true
      expect(store.getTickerDisplayName('AAPL')).toBe('AAPL')
    })

    it('falls back to the raw ticker when the ticker is not in the map', () => {
      const store = useMarketDataStore()
      store.tickerNames = { '600519': '贵州茅台' }
      store.showNames = true
      expect(store.getTickerDisplayName('999999')).toBe('999999')
    })
  })

  describe('action: loadTickerNames', () => {
    it('populates tickerNames from the API and caches per-market', async () => {
      const mocked = vi.mocked(fetchTickerNames)
      mocked.mockResolvedValueOnce({ '600519': '贵州茅台', '000858': '五粮液' })

      const store = useMarketDataStore()
      await store.loadTickerNames('cn')

      expect(fetchTickerNames).toHaveBeenCalledWith('cn')
      expect(store.tickerNames).toEqual({
        '600519': '贵州茅台',
        '000858': '五粮液',
      })
    })

    it('does NOT re-fetch a market that has already been loaded (per-market cache)', async () => {
      const mocked = vi.mocked(fetchTickerNames)
      const store = useMarketDataStore()

      await store.loadTickerNames('cn')
      await store.loadTickerNames('cn')

      // Only the first call hits the API; the second is a cache hit.
      expect(mocked).toHaveBeenCalledTimes(1)
    })

    it('swallows fetch errors silently (names are optional)', async () => {
      const mocked = vi.mocked(fetchTickerNames)
      mocked.mockRejectedValueOnce(new Error('network down'))

      const store = useMarketDataStore()
      // Must NOT throw — the catch in marketData.ts:35-37 swallows.
      await expect(store.loadTickerNames('us')).resolves.toBeUndefined()
      // tickerNames stays empty (no partial state).
      expect(store.tickerNames).toEqual({})
    })
  })

  describe('action: loadTables', () => {
    it('stores the table list from the API', async () => {
      const { listTables } = await import('../api/data')
      vi.mocked(listTables).mockResolvedValueOnce([
        'stock_prices', 'stock_indicators',
      ])

      const store = useMarketDataStore()
      await store.loadTables('cn')

      expect(listTables).toHaveBeenCalledWith('cn')
      expect(store.tables).toEqual(['stock_prices', 'stock_indicators'])
    })
  })

  /**
   * S003-009 — error exposure. The store used to swallow fetch rejections
   * (try/finally with no catch), silently blanking the table. These tests pin
   * the new contract: a rejection is surfaced on `store.error` as a
   * { code, message } object, `loading` returns to false, and a successful
   * load clears any prior error.
   */
  describe('error exposure', () => {
    it('loadAllRows surfaces a queryTable rejection on store.error and leaves allRows empty', async () => {
      const { queryTable } = await import('../api/data')
      vi.mocked(queryTable).mockRejectedValueOnce(new Error('network down'))

      const store = useMarketDataStore()
      // Must NOT throw — the catch surfaces it on store.error instead.
      await expect(store.loadAllRows('cn')).resolves.toBeUndefined()

      // error is a structured { code, message }, not the raw Error.
      expect(store.error).not.toBeNull()
      expect(typeof store.error!.code).toBe('string')
      expect(store.error!.message).toBe('network down')
      // loading is back to false (finally ran).
      expect(store.loading).toBe(false)
      // allRows stays empty (reset at the start, never repopulated).
      expect(store.allRows).toEqual([])
    })

    it('loadAllRows clears store.error on a successful load', async () => {
      const { queryTable } = await import('../api/data')
      const store = useMarketDataStore()

      // First, prime an error so we can prove the success path nulls it.
      vi.mocked(queryTable).mockRejectedValueOnce(new Error('boom'))
      await store.loadAllRows('cn')
      expect(store.error).not.toBeNull()

      // Second call succeeds — error must be cleared.
      vi.mocked(queryTable).mockResolvedValueOnce({
        columns: ['ticker'], rows: [{ ticker: '600519' }], total: 1,
        page: 1, page_size: 50,
      })
      await store.loadAllRows('cn')

      expect(store.error).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.allRows).toEqual([{ ticker: '600519' }])
    })

    it('loadMoreRows surfaces a queryTable rejection on store.error (regression guard)', async () => {
      const { queryTable } = await import('../api/data')
      const store = useMarketDataStore()

      // Prime state so loadMoreRows doesn't early-return on !hasMore: load a
      // first page successfully (total > page size → hasMore stays true).
      vi.mocked(queryTable).mockResolvedValueOnce({
        columns: ['ticker'], rows: [{ ticker: 'A' }], total: 5,
        page: 1, page_size: 50,
      })
      await store.loadAllRows('cn')
      expect(store.hasMore).toBe(true)
      expect(store.error).toBeNull()

      // The next page rejects — must surface on store.error, not swallow.
      vi.mocked(queryTable).mockRejectedValueOnce(new Error('page 2 dropped'))
      await expect(store.loadMoreRows('cn')).resolves.toBeUndefined()

      expect(store.error).not.toBeNull()
      expect(store.error!.message).toBe('page 2 dropped')
      expect(store.loading).toBe(false)
    })

    it('loadPage surfaces a queryTable rejection on store.error (regression guard)', async () => {
      const { queryTable } = await import('../api/data')
      // Axios-shaped rejection: server answered 503. Proves the structured
      // { code: 'http_<status>', message } path is surfaced end-to-end.
      vi.mocked(queryTable).mockRejectedValueOnce({
        isAxiosError: true,
        response: { status: 503, data: { error: { message: 'upstream busy' } } },
        message: 'Request failed with status code 503',
      })

      const store = useMarketDataStore()
      await expect(store.loadPage('cn')).resolves.toBeUndefined()

      expect(store.error).not.toBeNull()
      expect(store.error!.code).toBe('http_503')
      expect(store.error!.message).toBe('upstream busy')
      expect(store.loading).toBe(false)
    })
  })
})
