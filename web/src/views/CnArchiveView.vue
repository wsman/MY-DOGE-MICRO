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
    <VirtualTable
      :columns="vtColumns"
      :items="store.allRows"
      :loading="store.loading"
      :row-height="32"
      row-key="ticker"
      @row-click="onRowClick"
      @scroll-end="onScrollEnd"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { NInput, NButton, NSpace, NH3 } from 'naive-ui'
import { useMarketDataStore } from '../stores/marketData'
import { getKline } from '../api/data'
import VirtualTable from '../components/VirtualTable.vue'
import type { VtColumn } from '../components/VirtualTable.vue'

const store = useMarketDataStore()

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
