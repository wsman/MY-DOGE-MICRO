<template>
  <div class="archive-view">
    <div class="archive-toolbar">
      <n-h3 style="margin: 0">A-Share Archive</n-h3>
      <n-space>
        <n-button size="small" :type="store.showNames ? 'primary' : 'default'" @click="toggleNames">
          {{ store.showNames ? '名称' : '代码' }}
        </n-button>
        <n-input v-model:value="store.searchQuery" placeholder="Search ticker..." size="small"
                 @keyup.enter="store.loadAllRows('cn')" style="width: 200px" />
        <n-button size="small" @click="store.loadAllRows('cn')">Refresh</n-button>
      </n-space>
    </div>
    <!--
      StatusView triad (S003-009): replace the bare VirtualTable so fetch failures
      surface via store.error instead of silently blanking. Derived status maps
      loading -> skeleton, error -> retryable n-result, empty -> "No rows match",
      idle -> the real VirtualTable (default slot, only rendered when idle).
    -->
    <StatusView
      :status="tableStatus"
      :error="store.error"
      empty-description="No rows match"
      :on-retry="retry"
    >
      <VirtualTable
        :columns="vtColumns"
        :items="store.allRows"
        :loading="false"
        :row-height="32"
        row-key="ticker"
        @row-click="onRowClick"
        @scroll-end="onScrollEnd"
      />
    </StatusView>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { NInput, NButton, NSpace, NH3 } from 'naive-ui'
import { useMarketDataStore } from '../stores/marketData'
import { getKline } from '../api/data'
import VirtualTable from '../components/VirtualTable.vue'
import type { VtColumn } from '../components/VirtualTable.vue'
import StatusView from '../components/common/StatusView.vue'

const store = useMarketDataStore()

/**
 * Lifecycle status for the table area. StatusView only yields its default slot
 * (the VirtualTable) when this is `idle`, so a loading/error/empty state always
 * replaces the table wholesale — no stale rows behind a skeleton or error.
 * Order matters: loading wins over error (an in-flight retry clears the prior
 * failure) and an explicit error wins over an empty result set.
 */
const tableStatus = computed<'idle' | 'loading' | 'empty' | 'error'>(() => {
  if (store.loading) return 'loading'
  if (store.error) return 'error'
  if (store.allRows.length === 0) return 'empty'
  return 'idle'
})

/** Retry a failed fetch via the store action bound by StatusView's Retry button. */
function retry() {
  store.loadAllRows('cn')
}

const vtColumns = computed<VtColumn[]>(() =>
  store.columns.map(col => {
    if (col === 'ticker') {
      return {
        title: store.showNames ? '名称' : 'ticker',
        key: col,
        width: '130px',
        render: (row: Record<string, unknown>) => {
          const ticker = String(row.ticker)
          return store.getTickerDisplayName(ticker)
        },
      }
    }
    return {
      title: col,
      key: col,
      width: col === 'date' ? '110px' : col === 'volume' ? '120px' : undefined,
    }
  })
)

async function toggleNames() {
  if (!store.showNames && !Object.keys(store.tickerNames).length) {
    await store.loadTickerNames('cn')
  }
  store.showNames = !store.showNames
}

async function onRowClick(row: Record<string, unknown>) {
  const ticker = String(row.ticker)
  store.selectedTicker = ticker
  store.selectedMarket = 'cn'
  store.klineData = await getKline('cn', ticker, 120)
}

function onScrollEnd() {
  if (store.hasMore && !store.loading) {
    store.loadMoreRows('cn')
  }
}

onMounted(() => store.loadAllRows('cn'))
</script>

<style scoped>
.archive-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.archive-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  flex-shrink: 0;
}
</style>
