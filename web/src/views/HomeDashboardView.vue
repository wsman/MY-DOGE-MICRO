<template>
  <div class="home-view" :class="{ 'developer-mode': isDeveloperMode }" aria-label="Analyst product home">
    <header class="home-header">
      <div>
        <div class="eyebrow">Analyst Home</div>
        <h1>Home</h1>
      </div>
      <div class="header-actions">
        <div class="mode-toggle" role="group" aria-label="Home mode">
          <n-button
            size="tiny"
            :type="agentStore.analystMode ? 'primary' : 'default'"
            :secondary="!agentStore.analystMode"
            :aria-pressed="agentStore.analystMode"
            @click="agentStore.setAnalystMode(true)"
          >
            Analyst
          </n-button>
          <n-button
            size="tiny"
            :type="isDeveloperMode ? 'primary' : 'default'"
            :secondary="!isDeveloperMode"
            :aria-pressed="isDeveloperMode"
            @click="agentStore.setAnalystMode(false)"
          >
            Developer
          </n-button>
        </div>
        <n-button size="small" :loading="platformStore.loading" @click="load">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          Refresh
        </n-button>
        <n-button size="small" type="primary" @click="router.push('/workspaces')">New Case</n-button>
      </div>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>
    <n-alert v-if="agentErrorMessage" type="error" :show-icon="false" role="alert">{{ agentErrorMessage }}</n-alert>

    <section class="start-band" aria-labelledby="start-research-title">
      <div>
        <div class="eyebrow">Start Research</div>
        <h2 id="start-research-title">Research Workspace</h2>
      </div>
      <n-space size="small">
        <n-button type="primary" @click="router.push('/research-agent')">
          <template #icon><n-icon><RocketOutline /></n-icon></template>
          Start research
        </n-button>
        <n-button :loading="agentStore.loading" @click="runDemo">
          <template #icon><n-icon><PlayCircleOutline /></n-icon></template>
          Run demo
        </n-button>
      </n-space>
    </section>

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
      <div>
        <span>Recent Memos</span>
        <strong>{{ queue?.recent_memos.length ?? 0 }}</strong>
      </div>
    </section>

    <section class="home-grid" aria-label="Analyst work queue">
      <article class="queue-panel wide" aria-labelledby="recent-runs-title">
        <div id="recent-runs-title" class="section-title">Recent Runs</div>
        <RunComparisonPanel />
      </article>

      <HomeRecentUploads />

      <article class="queue-panel" aria-labelledby="pending-approvals-title">
        <div id="pending-approvals-title" class="section-title">Pending Approvals</div>
        <div class="list">
          <div v-for="item in pendingApprovals" :key="item.id" class="queue-row">
            <div>
              <h2>{{ item.title }}</h2>
              <p>{{ item.meta }}</p>
            </div>
            <n-button v-if="item.runId" size="tiny" @click="router.push(`/runs/${item.runId}`)">Open</n-button>
          </div>
          <div v-if="!pendingApprovals.length" class="empty-state">No pending approvals</div>
        </div>
      </article>

      <article class="queue-panel" aria-labelledby="recent-cases-title">
        <div id="recent-cases-title" class="section-title">Recent Cases</div>
        <div class="list">
          <div v-for="item in recentCases" :key="item.case_id" class="queue-row">
            <div>
              <h2>{{ item.title }}</h2>
              <p>{{ item.status }} · {{ item.updated_at || item.created_at || 'no timestamp' }}</p>
            </div>
            <n-button size="tiny" @click="router.push(`/cases/${item.case_id}`)">Open</n-button>
          </div>
          <div v-if="!recentCases.length" class="empty-state">No recent cases</div>
        </div>
      </article>

      <article class="queue-panel" aria-labelledby="recent-memos-title">
        <div id="recent-memos-title" class="section-title">Recent Memos</div>
        <div class="list">
          <div v-for="item in recentMemos" :key="item.id" class="queue-row">
            <div>
              <h2>{{ item.title }}</h2>
              <p>{{ item.meta }}</p>
            </div>
            <n-button v-if="item.runId" size="tiny" @click="router.push(`/runs/${item.runId}`)">Open</n-button>
          </div>
          <div v-if="!recentMemos.length" class="empty-state">No recent memos</div>
        </div>
      </article>

      <HomeStaticCtas />

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

      <article class="queue-panel" aria-labelledby="recent-executions-title">
        <div id="recent-executions-title" class="section-title">Recent Executions</div>
        <div class="list">
          <div v-for="execution in queue?.recent_executions ?? []" :key="execution.execution_id" class="queue-row">
            <div>
              <h2>{{ execution.template_slug || execution.template_id }}</h2>
              <p>{{ execution.status }} · {{ execution.run_id || 'no run' }}</p>
            </div>
            <n-button size="tiny" @click="openExecution(execution)">Open</n-button>
          </div>
          <div v-if="!(queue?.recent_executions.length)" class="empty-state">No executions</div>
        </div>
      </article>

      <article class="queue-panel wide" aria-labelledby="readiness-title">
        <div id="readiness-title" class="section-title">System Readiness</div>
        <MaturityPanel />
      </article>
    </section>

    <section v-if="isDeveloperMode" class="home-grid operator-grid" aria-label="Operator diagnostics">
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

      <aside class="queue-panel" aria-labelledby="warnings-title">
        <div id="warnings-title" class="section-title">Data Freshness</div>
        <div class="list">
          <div v-if="dataFreshnessRows.length" class="data-freshness" aria-label="Data freshness details">
            <div v-for="row in dataFreshnessRows" :key="row.key" class="freshness-row">
              <span>{{ row.key }}</span>
              <strong>{{ row.value }}</strong>
            </div>
          </div>
          <div v-for="warning in queue?.warnings ?? []" :key="warning" class="warning-row">{{ warning }}</div>
          <div v-if="!queue?.warnings.length && !dataFreshnessRows.length" class="empty-state">No warnings</div>
        </div>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { PlayCircleOutline, RefreshOutline, RocketOutline } from '@vicons/ionicons5'
import { NAlert, NButton, NIcon, NSpace } from 'naive-ui'
import RunComparisonPanel from '../components/agent/RunComparisonPanel.vue'
import MaturityPanel from '../components/common/MaturityPanel.vue'
import HomeRecentUploads from '../components/home/HomeRecentUploads.vue'
import HomeStaticCtas from '../components/home/HomeStaticCtas.vue'
import { useAgentStore } from '../stores/agent'
import { usePlatformStore } from '../stores/platform'
import type { JsonObject, ResearchCase, WorkflowExecution } from 'doge-sdk'

const router = useRouter()
const platformStore = usePlatformStore()
const agentStore = useAgentStore()
const queue = computed(() => platformStore.homeQueue)
const errorMessage = computed(() => platformStore.error?.message ?? '')
const agentErrorMessage = computed(() => agentStore.error?.message ?? '')
const isDeveloperMode = computed(() => !agentStore.analystMode)

const pendingCases = computed(() => (
  queue.value?.pending_cases.map(item => ({
    case: item.case as unknown as ResearchCase,
    reason: String(item.reason ?? 'needs_action'),
  })) ?? []
))

const recentCases = computed(() => platformStore.researchCases.slice(0, 10))

const pendingApprovals = computed(() => (
  queue.value?.pending_approvals.map((item: JsonObject, index) => {
    const record = asRecord(item)
    const approvals = Array.isArray(record.approvals) ? record.approvals.map(asRecord) : []
    const firstApproval = approvals[0] ?? {}
    const runId = optionalString(record.run_id)
    const action = optionalString(firstApproval.action) ?? optionalString(record.action)
    return {
      id: runId ?? `approval-${index}`,
      runId,
      title: optionalString(record.question) ?? optionalString(record.workflow) ?? 'Awaiting approval',
      meta: [runId, action].filter(Boolean).join(' · ') || 'approval pending',
    }
  }) ?? []
))

const recentMemos = computed(() => (
  queue.value?.recent_memos.map((item: JsonObject, index) => {
    const record = asRecord(item)
    const run = asRecord(record.run)
    const artifact = asRecord(record.artifact)
    const runId = optionalString(run.run_id)
    const title = optionalString(artifact.title) ?? optionalString(run.question) ?? 'Investment memo'
    const status = optionalString(run.status) ?? 'completed'
    const timestamp = optionalString(artifact.created_at) ?? optionalString(run.updated_at)
    return {
      id: optionalString(artifact.artifact_id) ?? runId ?? `memo-${index}`,
      runId,
      title,
      meta: [status, timestamp].filter(Boolean).join(' · '),
    }
  }) ?? []
))

const failedRuns = computed(() => (
  queue.value?.failed_or_degraded_runs.map((item: JsonObject) => ({
    execution: item.execution as unknown as WorkflowExecution,
    reason: String(item.reason ?? 'failed'),
  })) ?? []
))

const dataFreshnessRows = computed(() => {
  const freshness = queue.value?.data_freshness
  if (!freshness || typeof freshness !== 'object' || Array.isArray(freshness)) return []
  return Object.entries(freshness).map(([key, value]) => ({
    key,
    value: String(value),
  }))
})

async function load() {
  await Promise.all([
    platformStore.loadHomeQueue(20),
    platformStore.loadResearchCases({ limit: 10 }),
  ].map(promise => promise.catch(() => undefined)))
}

async function runDemo() {
  agentStore.selectedScenarioSlug = 'earnings_review'
  agentStore.setDocumentIds([])
  agentStore.setPortfolioId(null)
  const run = await agentStore.startDemoRun()
  if (run) await router.push('/research-agent')
}

function openExecution(execution: WorkflowExecution) {
  if (execution.run_id) {
    router.push(`/runs/${execution.run_id}`)
    return
  }
  router.push(`/cases/${execution.case_id}`)
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function optionalString(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined
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
.header-actions,
.mode-toggle,
.start-band,
.summary-strip,
.home-grid,
.queue-row {
  display: flex;
  gap: 10px;
}

.home-header,
.start-band,
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
h3,
p {
  margin: 0;
}

h1 {
  font-size: 20px;
}

h2 {
  font-size: 14px;
}

h3 {
  font-size: 12px;
}

p,
.empty-state,
.warning-row,
.freshness-row {
  color: var(--dgm-text-muted);
  font-size: 12px;
}

.header-actions {
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.mode-toggle {
  align-items: center;
}

.start-band {
  flex-wrap: wrap;
  padding: 12px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
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

.home-grid {
  align-items: flex-start;
  flex-wrap: wrap;
}

.queue-panel {
  flex: 1 1 320px;
  display: grid;
  gap: 10px;
  min-width: 0;
}

.queue-panel.wide {
  flex-basis: 460px;
}

.operator-grid {
  padding-top: 2px;
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

.queue-row > div {
  min-width: 0;
}

.queue-row h2,
.queue-row p {
  overflow-wrap: anywhere;
}

.data-freshness {
  display: grid;
  gap: 4px;
}

.freshness-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
}

.freshness-row span,
.freshness-row strong {
  min-width: 0;
  overflow-wrap: anywhere;
}

@media (max-width: 760px) {
  .home-header,
  .start-band,
  .queue-row {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    justify-content: flex-start;
  }
}
</style>
