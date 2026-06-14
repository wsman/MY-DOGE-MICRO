<template>
  <div class="ticker-view">
    <div class="ticker-toolbar">
      <n-auto-complete
        v-model:value="searchText"
        :options="searchOptions"
        placeholder="Code or name…  e.g. 600519, 贵州茅台, AAPL"
        size="small"
        clearable
        :loading="namesLoading"
        @select="onSelect"
        @update:value="onInput"
        style="flex: 1; min-width: 0"
      />
      <n-select
        v-model:value="activeMarket"
        size="small"
        :options="marketOptions"
        style="width: 110px; flex-shrink: 0"
      />
    </div>

    <!--
      Chart area: the no-selection empty block (.ticker-empty) is kept verbatim
      and short-circuits before any kline state is consulted. Once a ticker is
      selected, StatusView takes over and renders the error / empty / chart
      branches. The chart container is bound via ref to useKlineChart, so it must
      stay mounted whenever real data exists — hence it lives in the idle slot.
    -->
    <StatusView
      v-if="store.selectedTicker"
      :status="chartStatus"
      :error="klineError"
      :on-retry="klineError ? retryGetKline : undefined"
      empty-description="No kline data"
      :skeleton-rows="0"
      class="ticker-chart-wrap"
    >
      <div ref="chartContainer" class="ticker-chart" />
    </StatusView>
    <div v-else class="ticker-empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="1.5">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
      <n-text depth="3" style="margin-top: 8px">No ticker selected</n-text>
      <!-- loadNames is non-blocking (names only power autocomplete); surface its
           failure as a muted inline note rather than a StatusView block. -->
      <n-text v-if="namesError" depth="3" class="ticker-names-note">
        Ticker names unavailable — search limited to codes
      </n-text>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { NAutoComplete, NSelect, NText } from 'naive-ui'
import { useMarketDataStore } from '../stores/marketData'
import { getKline, fetchTickerNames } from '../api/data'
import { useKlineChart } from '../composables/useKlineChart'
import { useFuzzySearch } from '../composables/useFuzzySearch'
import StatusView from '../components/common/StatusView.vue'
import { toFetchError, type FetchError } from '../utils/fetchError'

interface TickerEntry {
  ticker: string
  name: string
  market: 'cn' | 'us'
}

const store = useMarketDataStore()
const chartContainer = ref<HTMLElement | null>(null)
const { setData, dispose } = useKlineChart(chartContainer)
const { search: fuzzySearch } = useFuzzySearch({ maxResults: 30, minScore: 10 })

const searchText = ref('')
const activeMarket = ref<'cn' | 'us'>('cn')
const namesLoading = ref(false)

// Structured kline fetch error. Null while idle/loading; populated by the
// getKline catch blocks so StatusView can surface { code, message } instead of
// silently blanking the chart. Cleared at the start of every fetch attempt.
const klineError = ref<FetchError | null>(null)
// loadNames failure flag — names are non-blocking (autocomplete-only), so a
// failure is surfaced as a muted inline note rather than a StatusView block.
const namesError = ref(false)
// Last fetch params, retained so retryGetKline can re-issue the identical
// request without the caller having to thread them back through.
const lastFetch = ref<{ market: 'cn' | 'us'; ticker: string } | null>(null)

// Ticker data
const allTickers = ref<TickerEntry[]>([])
const cnNames = ref<Record<string, string>>({})
const usNames = ref<Record<string, string>>({})

const marketOptions = [
  { label: 'A-Share (CN)', value: 'cn' },
  { label: 'US Market', value: 'us' },
]

// Load ticker names for both markets. Names are non-blocking — they only
// power the autocomplete, so a failure sets a muted inline-note flag rather
// than a StatusView block. Promise.allSettled keeps one market's failure from
// masking the other's success.
async function loadNames() {
  namesLoading.value = true
  namesError.value = false
  try {
    const [cn, us] = await Promise.allSettled([
      fetchTickerNames('cn'),
      fetchTickerNames('us'),
    ])
    if (cn.status === 'fulfilled') cnNames.value = cn.value
    if (us.status === 'fulfilled') usNames.value = us.value
    // If both legs rejected there are no names to search against — flag it so
    // the operator knows autocomplete is code-only until the next mount.
    if (cn.status === 'rejected' && us.status === 'rejected') {
      namesError.value = true
    }
    rebuildTickerList()
  } catch {
    // Defensive: Promise.allSettled never rejects, but guard the rebuild path.
    namesError.value = true
  } finally {
    namesLoading.value = false
  }
}

/**
 * Fetch kline data for a ticker and route it into the store + chart. Centralizes
 * the try/catch so both onSelect and the external-selection watcher share one
 * error path: a failure sets klineError (surfaced via StatusView) and leaves
 * any prior chart data intact rather than blanking it. Returns the data on
 * success so callers (e.g. retryGetKline) can chain on it.
 */
async function loadKline(market: 'cn' | 'us', ticker: string) {
  klineError.value = null
  lastFetch.value = { market, ticker }
  try {
    const data = await getKline(market, ticker, 120)
    store.klineData = data
    nextTick(() => setData(data))
    return data
  } catch (e) {
    klineError.value = toFetchError(e)
    return null
  }
}

/** Retry the most recent loadKline with the same params (StatusView Retry). */
function retryGetKline() {
  if (!lastFetch.value) return
  void loadKline(lastFetch.value.market, lastFetch.value.ticker)
}

/**
 * Derive the StatusView status for the chart area from the kline refs:
 *   - error   → klineError is set (fetch failed)
 *   - empty   → no error but no rows either (ticker resolved to zero candles)
 *   - idle    → otherwise, yielding the slot so the chart container mounts
 * Loading is intentionally not modeled here: getKline is awaited inline, so the
 * chart simply holds its previous render until new data lands rather than
 * flashing a skeleton. skeleton-rows=0 is passed to StatusView as a no-op.
 */
const chartStatus = computed<'idle' | 'empty' | 'error'>(() => {
  if (klineError.value) return 'error'
  if (store.klineData.length === 0) return 'empty'
  return 'idle'
})

function rebuildTickerList() {
  const list: TickerEntry[] = []
  for (const [ticker, name] of Object.entries(cnNames.value)) {
    list.push({ ticker, name, market: 'cn' })
  }
  for (const [ticker, name] of Object.entries(usNames.value)) {
    list.push({ ticker, name, market: 'us' })
  }
  allTickers.value = list
}

// Search / autocomplete — uses fuzzy search with CJK subsequence matching
const searchOptions = computed(() => {
  const q = searchText.value.trim()
  if (!q || q.length < 1) return []

  // If user already selected a market, only search that
  const pool = allTickers.value.filter(t =>
    activeMarket.value === 'cn' ? t.market === 'cn' : t.market === 'us'
  )

  const results = fuzzySearch(
    q,
    pool,
    (t) => [t.ticker, t.ticker.split('.')[0], t.name],
  )

  return results.map(({ item: entry }) => ({
    label: entry.ticker + (entry.name ? `  ${entry.name}` : ''),
    value: entry.ticker,
    // attach metadata for onSelect
    market: entry.market,
    name: entry.name,
  }))
})

function onInput(val: string) {
  searchText.value = val
}

async function onSelect(value: string) {
  const ticker = value
  const entry = allTickers.value.find(t => t.ticker === ticker)
  const market: 'cn' | 'us' = entry?.market ?? activeMarket.value

  store.selectedTicker = ticker
  store.selectedMarket = market

  // Use nextTick to override v-model's automatic value update
  nextTick(() => {
    searchText.value = entry
      ? (entry.name ? `${entry.ticker}  ${entry.name}` : entry.ticker)
      : ticker
  })

  await loadKline(market, ticker)
}

// Also load chart when selectedTicker is set externally (from archive view)
watch(() => store.selectedTicker, async (ticker) => {
  if (!ticker || !store.selectedMarket) return
  // Update search text to reflect external selection
  const name = store.getTickerDisplayName(ticker)
  searchText.value = name !== ticker ? `${ticker}  ${name}` : ticker
  activeMarket.value = store.selectedMarket

  await loadKline(store.selectedMarket, ticker)
})

// Re-render chart when container mounts
watch(() => chartContainer.value, (el) => {
  if (el && store.klineData.length) {
    nextTick(() => setData(store.klineData))
  }
})

onMounted(() => loadNames())
onUnmounted(() => dispose())
</script>

<style scoped>
.ticker-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.ticker-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  flex-shrink: 0;
}
.ticker-chart-wrap {
  /* StatusView wraps the chart panel; mirror the chart's outer chrome so the
     loading/empty/error primitives occupy the same frame the chart would. */
  flex: 1;
  min-height: 0;
  margin: 0 12px 12px;
}
.ticker-chart {
  height: 100%;
  min-height: 0;
  border: 1px solid var(--dgm-border);
  border-radius: 4px;
}
.ticker-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0.5;
}
.ticker-names-note {
  /* Non-blocking names-load failure: muted, sits beneath the empty icon so it
     never competes with a real status surface. */
  margin-top: 4px;
  font-size: 12px;
}
</style>
