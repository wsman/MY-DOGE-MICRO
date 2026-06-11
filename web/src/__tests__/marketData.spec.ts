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
})
