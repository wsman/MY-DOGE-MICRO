<template>
  <div class="insights-view">
    <!--
      View-level status triad (S003-009). `derived` folds loading + error into
      the StatusView lifecycle: only `idle` yields the slot, so a loading
      skeleton or error result replaces the tabs wholesale instead of rendering
      stale content behind them. The modal/report-detail error path below is a
      separate concern and is left as-is.
    -->
    <StatusView
      :status="derivedStatus"
      :error="error"
      :on-retry="reload"
      :skeleton-rows="6"
    >
      <n-tabs type="line" animated>
      <n-tab-pane name="macro" tab="Macro Reports">
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
              <n-card size="small" hoverable @click="showMacroReport(asMacro(item.raw))">
                <template #header>{{ asMacro(item.raw).date }} {{ asMacro(item.raw).timestamp }}</template>
                <template #header-extra>
                  <n-tag :type="riskTagType(asMacro(item.raw).risk_signal)" size="small">
                    {{ asMacro(item.raw).risk_signal }}
                  </n-tag>
                </template>
                <n-text depth="3">{{ asMacro(item.raw).analyst }} | Vol: {{ asMacro(item.raw).volatility }}</n-text>
              </n-card>
            </template>
          </VirtualMasonry>
          <n-empty v-else description="No reports" />
        </div>
      </n-tab-pane>

      <n-tab-pane name="research" tab="Research Reports">
        <div class="masonry-container">
          <!--
            Research-tab empty state (S003-009). The view-level StatusView above
            only knows about the aggregate fetch; once idle, an individual tab
            can still have zero items, so we surface a scoped empty status here
            rather than leaving the pane blank.
          -->
          <StatusView
            v-if="!researchMasonryItems.length"
            status="empty"
            empty-description="No research reports"
          />
          <VirtualMasonry
            v-else
            :items="researchMasonryItems"
            font="14px -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
            :lineHeight="20"
            :gap="12"
            :bufferPx="200"
            :maxColWidth="400"
          >
            <template #card="{ item }">
              <n-card size="small" hoverable @click="showResearchReport(asResearch(item.raw))">
                <template #header>{{ asResearch(item.raw).title || 'Untitled' }}</template>
                <n-text depth="3">{{ asResearch(item.raw).date }} | {{ asResearch(item.raw).analyst }}</n-text>
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
    </StatusView>

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
import StatusView from '../components/common/StatusView.vue'
import { toFetchError, type FetchError } from '../utils/fetchError'
import type { MacroReport, ResearchReport } from '../types/report'
import type { MasonryItem } from '../components/VirtualMasonry.vue'

const md = new MarkdownIt()

// MasonryItem.raw is typed `unknown` (it is a generic payload slot). These
// narrow it back to the concrete report type the template renders. The raw
// value is set from a typed source in the computed masonry items above, so
// the cast is sound.
const asMacro = (raw: unknown): MacroReport => raw as MacroReport
const asResearch = (raw: unknown): ResearchReport => raw as ResearchReport

const loading = ref(false)
// Structured fetch error surfaced through the view-level StatusView (S003-009).
// Null while loading/idle; populated by the onMounted catch via toFetchError so
// REST rejections render the same { code, message } shape the SSE path uses.
const error = ref<FetchError | null>(null)
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

/**
 * Fold loading + error into the StatusView lifecycle for the view-level wrapper.
 * Only `idle` yields the slot (the tabs), so a loading skeleton or error result
 * replaces the tabs wholesale instead of rendering stale content behind them.
 */
const derivedStatus = computed<'loading' | 'error' | 'idle'>(() => {
  if (loading.value) return 'loading'
  if (error.value) return 'error'
  return 'idle'
})

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

/**
 * Load the three report feeds in parallel. Previously the onMounted Promise.all
 * only had a `finally`, so a rejection was swallowed and the panels silently
 * blanked. Now any thrown value is normalized via toFetchError into the shared
 * { code, message } shape and surfaced through the view-level StatusView.
 *
 * `reload` is the same body wired to StatusView's Retry button so the operator
 * can re-attempt a failed fetch without reloading the page.
 */
async function reload() {
  loading.value = true
  error.value = null
  try {
    const [macroRes, researchRes, trackedRes] = await Promise.all([
      api.get('/macro/reports'),
      api.get('/analysis/reports'),
      api.get('/notes/tracked'),
    ])
    macroReports.value = macroRes.data.reports
    researchReports.value = researchRes.data.reports
    trackedTickers.value = trackedRes.data.tickers || []
  } catch (e) {
    error.value = toFetchError(e)
  } finally {
    loading.value = false
  }
}

onMounted(reload)
</script>

<style scoped>
.insights-view { padding: 8px; height: 100%; display: flex; flex-direction: column; }
.masonry-container { flex: 1; min-height: 0; }

.modal-markdown-body {
  padding: 12px 16px;
  color: var(--dgm-text-muted);
}
.modal-markdown-body :deep(h1),
.modal-markdown-body :deep(h2),
.modal-markdown-body :deep(h3) {
  margin: 16px 0 8px;
  color: var(--dgm-text);
}
.modal-markdown-body :deep(p) {
  margin: 8px 0;
  line-height: 1.6;
}
.modal-markdown-body :deep(code) {
  background: var(--dgm-border);
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
  border: 1px solid var(--dgm-table-border);
  padding: 6px 10px;
  text-align: left;
}
</style>
