<template>
  <div class="platform-view" aria-label="Run detail">
    <header class="platform-header">
      <div>
        <div class="eyebrow">Run</div>
        <h1>{{ currentRunId || 'Run Detail' }}</h1>
      </div>
      <n-space size="small">
        <n-input v-model:value="runIdInput" size="small" placeholder="Run ID" />
        <n-button size="small" type="primary" :disabled="!runIdInput.trim()" :loading="store.loading" @click="load">
          Load
        </n-button>
      </n-space>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>

    <n-spin :show="store.loading">
      <section v-if="resources" class="run-grid">
        <article class="summary-section" aria-labelledby="run-summary-title">
          <div id="run-summary-title" class="section-title">Summary</div>
          <p class="summary-text">{{ resources.summary.summary_text || 'No summary text' }}</p>
        </article>

        <aside class="eval-section" aria-labelledby="run-eval-title">
          <div id="run-eval-title" class="section-title">Eval</div>
          <div class="metric-row">
            <span>Coverage</span>
            <n-tag size="small" :type="coverageType">{{ coverageLabel }}</n-tag>
          </div>
          <div class="metric-row">
            <span>Claims</span>
            <n-tag size="small">{{ resources.eval.claim_count }}</n-tag>
          </div>
          <div class="metric-row">
            <span>Citations</span>
            <n-tag size="small">{{ resources.eval.citation_count }}</n-tag>
          </div>
          <div v-for="check in resources.eval.failed_checks" :key="check" class="failed-check">{{ check }}</div>
        </aside>

        <article class="claims-section" aria-labelledby="run-claims-title">
          <div id="run-claims-title" class="section-title">Claims</div>
          <div class="list">
            <div v-for="claim in resources.claims" :key="claim.claim_id" class="row-item">
              <span>{{ claim.claim_text }}</span>
              <n-tag size="small">{{ claim.support_status }}</n-tag>
            </div>
            <div v-if="!resources.claims.length" class="empty-state">No claims</div>
          </div>
        </article>

        <article class="citations-section" aria-labelledby="run-citations-title">
          <div id="run-citations-title" class="section-title">Citations</div>
          <div class="list">
            <div v-for="citation in resources.citations" :key="citation.citation_id" class="citation-item">
              <div class="citation-top">
                <span>{{ citation.source || citation.document_id || citation.citation_id }}</span>
                <n-tag size="small" :type="citation.accessible ? 'success' : 'warning'">
                  {{ citation.accessible ? 'accessible' : 'restricted' }}
                </n-tag>
              </div>
              <p>{{ citation.snippet || 'No snippet' }}</p>
            </div>
            <div v-if="!resources.citations.length" class="empty-state">No citations</div>
          </div>
        </article>
      </section>
      <div v-else class="empty-state">No run loaded</div>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAlert, NButton, NInput, NSpace, NSpin, NTag } from 'naive-ui'
import { usePlatformStore } from '../stores/platform'

const route = useRoute()
const router = useRouter()
const store = usePlatformStore()
const routeRunId = computed(() => String(route.params.runId || ''))
const runIdInput = ref(routeRunId.value)
const currentRunId = computed(() => routeRunId.value || runIdInput.value.trim())
const resources = computed(() => currentRunId.value ? store.runResourcesById[currentRunId.value] : null)
const errorMessage = computed(() => store.error?.message ?? '')
const coverageLabel = computed(() => {
  const value = resources.value?.eval.coverage_ratio ?? 0
  return `${Math.round(value * 100)}%`
})
const coverageType = computed(() => {
  const value = resources.value?.eval.coverage_ratio ?? 0
  return value >= 1 ? 'success' : value > 0 ? 'warning' : 'error'
})

async function load() {
  const runId = runIdInput.value.trim()
  if (!runId) return
  await router.replace(`/runs/${runId}`)
  await store.loadRunSummaryResources(runId).catch(() => undefined)
}

watch(routeRunId, value => {
  runIdInput.value = value
  if (value) store.loadRunSummaryResources(value).catch(() => undefined)
})

onMounted(() => {
  if (routeRunId.value) store.loadRunSummaryResources(routeRunId.value).catch(() => undefined)
})
</script>

<style scoped>
.platform-view {
  min-height: 100%;
  display: grid;
  align-content: start;
  gap: 12px;
  padding: 12px;
  color: var(--dgm-text);
}

.platform-header,
.run-grid,
.metric-row,
.row-item,
.citation-top {
  display: flex;
  gap: 10px;
}

.platform-header,
.metric-row,
.row-item,
.citation-top {
  align-items: center;
  justify-content: space-between;
}

.eyebrow,
.section-title {
  color: var(--dgm-text-faint);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

h1,
p {
  margin: 0;
}

h1 {
  font-size: 20px;
}

.run-grid {
  align-items: start;
  flex-wrap: wrap;
}

.summary-section,
.claims-section,
.citations-section,
.eval-section {
  display: grid;
  gap: 10px;
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.summary-section,
.citations-section {
  flex: 1 1 420px;
}

.claims-section {
  flex: 1 1 320px;
}

.eval-section {
  flex: 0 1 260px;
}

.summary-text,
.citation-item p {
  color: var(--dgm-text-muted);
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.list {
  display: grid;
  gap: 8px;
}

.row-item,
.citation-item {
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
}

.failed-check,
.empty-state {
  color: var(--dgm-text-faint);
  font-size: 13px;
}

@media (max-width: 760px) {
  .run-grid,
  .platform-header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
