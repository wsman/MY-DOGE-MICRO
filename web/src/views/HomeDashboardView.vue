<template>
  <div class="home-view" aria-label="Home work queue">
    <header class="home-header">
      <div>
        <div class="eyebrow">Operations</div>
        <h1>Home</h1>
      </div>
      <n-space size="small">
        <n-button size="small" :loading="store.loading" @click="load">Refresh</n-button>
        <n-button size="small" type="primary" @click="router.push('/workspaces')">New Case</n-button>
      </n-space>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>

    <section class="summary-strip" aria-label="Queue summary">
      <div>
        <span>Pending Cases</span>
        <strong>{{ queue?.pending_cases.length ?? 0 }}</strong>
      </div>
      <div>
        <span>Approvals</span>
        <strong>{{ queue?.pending_approvals.length ?? 0 }}</strong>
      </div>
      <div>
        <span>Failed Runs</span>
        <strong>{{ queue?.failed_or_degraded_runs.length ?? 0 }}</strong>
      </div>
      <div>
        <span>Recent Executions</span>
        <strong>{{ queue?.recent_executions.length ?? 0 }}</strong>
      </div>
    </section>

    <section class="queue-grid">
      <article class="queue-panel" aria-labelledby="pending-cases-title">
        <div id="pending-cases-title" class="section-title">Pending Cases</div>
        <div class="list">
          <div v-for="item in pendingCases" :key="item.case.case_id" class="queue-row">
            <div>
              <h2>{{ item.case.title }}</h2>
              <p>{{ item.reason }}</p>
            </div>
            <n-button size="tiny" @click="router.push(`/cases/${item.case.case_id}`)">Open</n-button>
          </div>
          <div v-if="!pendingCases.length" class="empty-state">No pending cases</div>
        </div>
      </article>

      <article class="queue-panel" aria-labelledby="failed-runs-title">
        <div id="failed-runs-title" class="section-title">Failed Or Degraded</div>
        <div class="list">
          <div v-for="item in failedRuns" :key="item.execution.execution_id" class="queue-row">
            <div>
              <h2>{{ item.execution.template_slug || item.execution.template_id }}</h2>
              <p>{{ item.reason }}</p>
            </div>
            <n-button size="tiny" @click="router.push(`/cases/${item.execution.case_id}`)">Inspect</n-button>
          </div>
          <div v-if="!failedRuns.length" class="empty-state">No failed executions</div>
        </div>
      </article>

      <article class="queue-panel" aria-labelledby="recent-executions-title">
        <div id="recent-executions-title" class="section-title">Recent Executions</div>
        <div class="list">
          <div v-for="execution in queue?.recent_executions ?? []" :key="execution.execution_id" class="queue-row">
            <div>
              <h2>{{ execution.template_slug || execution.template_id }}</h2>
              <p>{{ execution.status }} · {{ execution.run_id || 'no run' }}</p>
            </div>
            <n-button size="tiny" @click="router.push(`/cases/${execution.case_id}`)">Open</n-button>
          </div>
          <div v-if="!(queue?.recent_executions.length)" class="empty-state">No executions</div>
        </div>
      </article>

      <aside class="queue-panel" aria-labelledby="warnings-title">
        <div id="warnings-title" class="section-title">Data Freshness</div>
        <div class="list">
          <div v-for="warning in queue?.warnings ?? []" :key="warning" class="warning-row">{{ warning }}</div>
          <div v-if="!(queue?.warnings.length)" class="empty-state">No warnings</div>
        </div>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NAlert, NButton, NSpace } from 'naive-ui'
import { usePlatformStore } from '../stores/platform'
import type { JsonObject, ResearchCase, WorkflowExecution } from '../types/platform'

const router = useRouter()
const store = usePlatformStore()
const queue = computed(() => store.homeQueue)
const errorMessage = computed(() => store.error?.message ?? '')

const pendingCases = computed(() => (
  queue.value?.pending_cases.map(item => ({
    case: item.case as unknown as ResearchCase,
    reason: String(item.reason ?? 'needs_action'),
  })) ?? []
))
const failedRuns = computed(() => (
  queue.value?.failed_or_degraded_runs.map((item: JsonObject) => ({
    execution: item.execution as unknown as WorkflowExecution,
    reason: String(item.reason ?? 'failed'),
  })) ?? []
))

async function load() {
  await store.loadHomeQueue(20).catch(() => undefined)
}

onMounted(load)
</script>

<style scoped>
.home-view {
  min-height: 100%;
  display: grid;
  align-content: start;
  gap: 12px;
  padding: 12px;
  color: var(--dgm-text);
}

.home-header,
.summary-strip,
.queue-grid,
.queue-row {
  display: flex;
  gap: 10px;
}

.home-header,
.queue-row {
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
h2,
p {
  margin: 0;
}

h1 {
  font-size: 20px;
}

h2 {
  font-size: 14px;
}

p,
.empty-state,
.warning-row {
  color: var(--dgm-text-muted);
  font-size: 12px;
}

.summary-strip {
  flex-wrap: wrap;
}

.summary-strip > div,
.queue-panel {
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.summary-strip > div {
  min-width: 140px;
}

.summary-strip span {
  display: block;
  color: var(--dgm-text-faint);
  font-size: 12px;
}

.summary-strip strong {
  font-size: 18px;
}

.queue-grid {
  align-items: flex-start;
  flex-wrap: wrap;
}

.queue-panel {
  flex: 1 1 320px;
  display: grid;
  gap: 10px;
  min-width: 0;
}

.list {
  display: grid;
  gap: 8px;
}

.queue-row,
.warning-row {
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
}

@media (max-width: 760px) {
  .home-header,
  .queue-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
