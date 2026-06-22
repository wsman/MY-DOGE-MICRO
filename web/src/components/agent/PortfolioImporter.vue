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
      <n-tag v-else size="small">portfolio-demo</n-tag>
    </n-space>
    <n-alert v-if="error" type="error" :show-icon="false">{{ error.message }}</n-alert>
    <div v-if="previewRows.length" class="preview" aria-label="Portfolio preview">
      <div v-for="(row, index) in previewRows" :key="index" class="preview-row">
        {{ row }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
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
</style>
