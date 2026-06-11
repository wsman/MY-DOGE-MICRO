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

    <div v-if="store.selectedTicker" ref="chartContainer" class="ticker-chart" />
    <div v-else class="ticker-empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="1.5">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
      <n-text depth="3" style="margin-top: 8px">No ticker selected</n-text>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { NAutoComplete, NSelect, NText, type SelectOption } from 'naive-ui'
import { useMarketDataStore } from '../stores/marketData'
import { getKline, fetchTickerNames } from '../api/data'
import { useKlineChart } from '../composables/useKlineChart'
import { useFuzzySearch } from '../composables/useFuzzySearch'

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

// Ticker data
const allTickers = ref<TickerEntry[]>([])
const cnNames = ref<Record<string, string>>({})
const usNames = ref<Record<string, string>>({})

const marketOptions = [
  { label: 'A-Share (CN)', value: 'cn' },
  { label: 'US Market', value: 'us' },
]

// Load ticker names for both markets
async function loadNames() {
  namesLoading.value = true
  try {
    const [cn, us] = await Promise.allSettled([
      fetchTickerNames('cn'),
      fetchTickerNames('us'),
    ])
    if (cn.status === 'fulfilled') cnNames.value = cn.value
    if (us.status === 'fulfilled') usNames.value = us.value
    rebuildTickerList()
  } finally {
    namesLoading.value = false
  }
}

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

  const data = await getKline(market, ticker, 120)
  store.klineData = data
  nextTick(() => setData(data))
}

// Also load chart when selectedTicker is set externally (from archive view)
watch(() => store.selectedTicker, async (ticker) => {
  if (!ticker || !store.selectedMarket) return
  // Update search text to reflect external selection
  const name = store.getTickerDisplayName(ticker)
  searchText.value = name !== ticker ? `${ticker}  ${name}` : ticker
  activeMarket.value = store.selectedMarket

  const data = await getKline(store.selectedMarket, ticker, 120)
  store.klineData = data
  nextTick(() => setData(data))
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
.ticker-chart {
  flex: 1;
  min-height: 0;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  margin: 0 12px 12px;
}
.ticker-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0.5;
}
</style>
