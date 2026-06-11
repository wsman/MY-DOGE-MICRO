<template>
  <div class="insights-view">
    <n-tabs type="line" animated>
      <n-tab-pane name="macro" tab="Macro Reports">
        <n-spin :show="loading">
          <div class="masonry-container">
            <VirtualMasonry
              v-if="macroMasonryItems.length"
              :items="macroMasonryItems"
              font="14px -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
              :lineHeight="20"
              :gap="12"
              :bufferPx="200"
              :maxColWidth="400"
            >
              <template #card="{ item }">
                <n-card size="small" hoverable @click="showMacroReport(item.raw)">
                  <template #header>{{ item.raw.date }} {{ item.raw.timestamp }}</template>
                  <template #header-extra>
                    <n-tag :type="riskTagType(item.raw.risk_signal)" size="small">
                      {{ item.raw.risk_signal }}
                    </n-tag>
                  </template>
                  <n-text depth="3">{{ item.raw.analyst }} | Vol: {{ item.raw.volatility }}</n-text>
                </n-card>
              </template>
            </VirtualMasonry>
            <n-empty v-else description="No reports" />
          </div>
        </n-spin>
      </n-tab-pane>

      <n-tab-pane name="research" tab="Research Reports">
        <div class="masonry-container">
          <VirtualMasonry
            v-if="researchMasonryItems.length"
            :items="researchMasonryItems"
            font="14px -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
            :lineHeight="20"
            :gap="12"
            :bufferPx="200"
            :maxColWidth="400"
          >
            <template #card="{ item }">
              <n-card size="small" hoverable @click="showResearchReport(item.raw)">
                <template #header>{{ item.raw.title || 'Untitled' }}</template>
                <n-text depth="3">{{ item.raw.date }} | {{ item.raw.analyst }}</n-text>
              </n-card>
            </template>
          </VirtualMasonry>
        </div>
      </n-tab-pane>

      <n-tab-pane name="notes" tab="Stock Notes">
        <n-space vertical>
          <n-h4>Tracked Tickers</n-h4>
          <n-empty v-if="!trackedTickers.length" description="No tracked tickers" />
          <n-space v-else>
            <n-tag v-for="t in trackedTickers" :key="t.ticker" clickable>
              {{ t.ticker }} ({{ t.note_count }})
            </n-tag>
          </n-space>
        </n-space>
      </n-tab-pane>
    </n-tabs>

    <!-- Report Detail Modal -->
    <n-modal
      v-model:show="showModal"
      preset="card"
      style="width: 80%"
      title="Report"
    >
      <n-spin :show="modalLoading">
        <div
          v-if="showModal && modalContent"
          class="modal-markdown-body"
          v-html="renderedModalContent"
        />
        <n-empty v-else-if="!modalLoading" description="No content" />
      </n-spin>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import MarkdownIt from 'markdown-it'
import {
  NTabs, NTabPane, NCard, NTag, NText, NSpace,
  NModal, NH4, NEmpty, NSpin,
} from 'naive-ui'
import api from '../api/client'
import VirtualMasonry from '../components/VirtualMasonry.vue'
import type { MacroReport, ResearchReport } from '../types/report'
import type { MasonryItem } from '../components/VirtualMasonry.vue'

const md = new MarkdownIt()

const loading = ref(false)
const macroReports = ref<MacroReport[]>([])
const researchReports = ref<ResearchReport[]>([])
const trackedTickers = ref<{ ticker: string; note_count: number }[]>([])
const showModal = ref(false)
const modalContent = ref('')
const modalLoading = ref(false)

// Render markdown for modal
const renderedModalContent = computed(() => md.render(modalContent.value))

// Transform reports into masonry items (text for height prediction)
const macroMasonryItems = computed<MasonryItem[]>(() =>
  macroReports.value.map(r => ({
    id: r.id,
    text: `${r.date} ${r.timestamp} ${r.analyst} ${r.risk_signal} ${r.volatility || ''}`,
    raw: r,
  }))
)

const researchMasonryItems = computed<MasonryItem[]>(() =>
  researchReports.value.map(r => ({
    id: r.id,
    text: `${r.title || 'Untitled'} ${r.date} ${r.analyst}`,
    raw: r,
  }))
)

function riskTagType(signal: string) {
  const s = signal?.toLowerCase() || ''
  if (s.includes('high') || s.includes('aggressive')) return 'error'
  if (s.includes('low') || s.includes('caution')) return 'warning'
  return 'success'
}

async function showMacroReport(report: MacroReport) {
  modalContent.value = ''
  modalLoading.value = true
  showModal.value = true
  try {
    const { data } = await api.get(`/macro/reports/${report.id}`)
    modalContent.value = data.content || 'No content available.'
  } catch {
    modalContent.value = 'Failed to load report content.'
  } finally {
    modalLoading.value = false
  }
}

async function showResearchReport(report: ResearchReport) {
  modalContent.value = ''
  modalLoading.value = true
  showModal.value = true
  try {
    const { data } = await api.get(`/analysis/reports/${report.id}`)
    modalContent.value = data.content || 'No content available.'
  } catch {
    modalContent.value = 'Failed to load report content.'
  } finally {
    modalLoading.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const [macroRes, researchRes, trackedRes] = await Promise.all([
      api.get('/macro/reports'),
      api.get('/analysis/reports'),
      api.get('/notes/tracked'),
    ])
    macroReports.value = macroRes.data.reports
    researchReports.value = researchRes.data.reports
    trackedTickers.value = trackedRes.data.tickers || []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.insights-view { padding: 8px; height: 100%; display: flex; flex-direction: column; }
.masonry-container { flex: 1; min-height: 0; }

.modal-markdown-body {
  padding: 12px 16px;
  color: rgba(255, 255, 255, 0.82);
}
.modal-markdown-body :deep(h1),
.modal-markdown-body :deep(h2),
.modal-markdown-body :deep(h3) {
  margin: 16px 0 8px;
  color: rgba(255, 255, 255, 0.95);
}
.modal-markdown-body :deep(p) {
  margin: 8px 0;
  line-height: 1.6;
}
.modal-markdown-body :deep(code) {
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
}
.modal-markdown-body :deep(pre) {
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}
.modal-markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}
.modal-markdown-body :deep(ul),
.modal-markdown-body :deep(ol) {
  padding-left: 20px;
}
.modal-markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
}
.modal-markdown-body :deep(th),
.modal-markdown-body :deep(td) {
  border: 1px solid #3a3b52;
  padding: 6px 10px;
  text-align: left;
}
</style>
