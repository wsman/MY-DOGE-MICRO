<template>
  <div class="portfolio-importer">
    <input
      ref="input"
      class="file-input"
      type="file"
      accept=".csv,text/csv"
      @change="onChange"
    >
    <n-space size="small" align="center">
      <n-button size="small" :loading="loading" @click="input?.click()">Import CSV</n-button>
      <n-tag v-if="portfolio?.portfolio_id" size="small" type="success">{{ portfolio.portfolio_id }}</n-tag>
      <n-tag v-else size="small">No portfolio</n-tag>
    </n-space>
    <n-alert v-if="error" type="error" :show-icon="false">{{ error.message }}</n-alert>
    <div v-if="previewRows.length" class="preview" aria-label="Portfolio preview">
      <div v-for="(row, index) in previewRows" :key="index" class="preview-row">
        {{ row }}
      </div>
    </div>
    <div v-if="summary" class="summary" aria-label="Portfolio summary">
      <div class="summary-metrics">
        <div>
          <span>Holdings</span>
          <strong>{{ summary.holdings_count }}</strong>
        </div>
        <div>
          <span>Market Value</span>
          <strong>{{ formatMoney(summary.total_market_value) }}</strong>
        </div>
      </div>
      <div class="summary-block">
        <h4>Top Concentration</h4>
        <div v-for="row in summary.top_concentration" :key="row.symbol" class="summary-row">
          <span>{{ row.symbol }}</span>
          <span>{{ formatPercent(row.weight) }}</span>
          <span>{{ formatMoney(row.market_value) }}</span>
        </div>
      </div>
      <div class="summary-block">
        <h4>Sector Exposure</h4>
        <div v-for="row in summary.by_sector" :key="row.name" class="summary-row">
          <span>{{ row.name }}</span>
          <span>{{ formatPercent(row.weight) }}</span>
          <span>{{ formatMoney(row.market_value) }}</span>
        </div>
      </div>
      <div class="summary-block">
        <h4>Missing Prices</h4>
        <div v-if="summary.missing_prices.length === 0" class="muted">None</div>
        <template v-else>
          <div v-for="row in summary.missing_prices" :key="row.symbol" class="summary-row two-col">
            <span>{{ row.symbol }}</span>
            <span>{{ row.reason }}</span>
          </div>
        </template>
      </div>
      <div class="suggested-run">
        <span>Suggested run</span>
        <strong>{{ summary.suggested_run.question }}</strong>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NAlert, NButton, NSpace, NTag } from 'naive-ui'
import { uploadPortfolioCsv, type ImportedPortfolio } from '../../api/portfolio'
import { toFetchError, type FetchError } from '../../utils/fetchError'

const emit = defineEmits<{
  imported: [portfolio: ImportedPortfolio]
}>()

const input = ref<HTMLInputElement | null>(null)
const loading = ref(false)
const error = ref<FetchError | null>(null)
const previewRows = ref<string[]>([])
const portfolio = ref<ImportedPortfolio | null>(null)
const summary = computed(() => portfolio.value?.summary ?? null)

async function onChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file) return
  loading.value = true
  error.value = null
  try {
    previewRows.value = await previewCsv(file)
    portfolio.value = await uploadPortfolioCsv(file, { name: file.name.replace(/\.csv$/i, '') })
    emit('imported', portfolio.value)
  } catch (e) {
    error.value = toFetchError(e)
  } finally {
    loading.value = false
  }
}

async function previewCsv(file: File): Promise<string[]> {
  const text = await file.text()
  return text.split(/\r?\n/).filter(Boolean).slice(0, 6)
}

function formatMoney(value: number) {
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPercent(value: number) {
  return `${Math.round(value * 1000) / 10}%`
}
</script>

<style scoped>
.portfolio-importer {
  display: grid;
  gap: 8px;
}

.file-input {
  display: none;
}

.preview {
  display: grid;
  gap: 3px;
  max-height: 90px;
  overflow: auto;
  padding: 6px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  color: var(--dgm-text-faint);
  font-family: var(--dgm-font-mono);
  font-size: 11px;
}

.preview-row {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary {
  display: grid;
  gap: 10px;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface-hover);
}

.summary-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.summary-metrics > div,
.suggested-run {
  display: grid;
  gap: 2px;
}

.summary-metrics span,
.suggested-run span,
.summary-block h4 {
  margin: 0;
  color: var(--dgm-text-faint);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.summary-metrics strong,
.suggested-run strong {
  color: var(--dgm-text);
  font-size: 12px;
}

.summary-block {
  display: grid;
  gap: 4px;
}

.summary-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 54px 74px;
  gap: 6px;
  align-items: center;
  color: var(--dgm-text-muted);
  font-size: 11px;
}

.summary-row.two-col {
  grid-template-columns: 64px minmax(0, 1fr);
}

.summary-row span,
.suggested-run strong {
  overflow-wrap: anywhere;
}

.summary-row span:nth-child(2),
.summary-row span:nth-child(3) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.summary-row.two-col span:nth-child(2) {
  text-align: left;
  font-variant-numeric: normal;
}

.muted {
  color: var(--dgm-text-faint);
  font-size: 11px;
}
</style>
