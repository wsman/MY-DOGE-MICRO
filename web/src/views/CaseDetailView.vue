<template>
  <div class="platform-view" aria-label="Research case workspace">
    <header class="platform-header">
      <div>
        <div class="eyebrow">Research Case</div>
        <h1>{{ researchCase?.title || caseId || 'Case' }}</h1>
      </div>
      <n-space size="small">
        <n-button size="small" @click="goProject">Project</n-button>
        <n-button size="small" :loading="store.loading" @click="load">Refresh</n-button>
      </n-space>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>
    <p class="thesis">{{ researchCase?.thesis || 'No thesis' }}</p>

    <n-spin :show="store.loading">
      <section class="workspace-grid">
        <CaseAssetPanel class="panel-frame" :assets="assets" @add="addAsset" />

        <main class="center-column">
          <TemplateConfigurator
            class="panel-frame"
            :templates="templates"
            @preflight="preflight"
            @execute="execute"
          />

          <section class="panel-frame" aria-labelledby="memo-title">
            <div id="memo-title" class="section-title">Memo</div>
            <p class="memo-text">{{ review?.summary?.summary_text || 'No memo yet' }}</p>
          </section>

          <ExecutionMonitor class="panel-frame" :executions="executions" @open-run="openRun" />
        </main>

        <aside class="right-column">
          <PreflightResult class="panel-frame" :result="preflightResult" />

          <section class="panel-frame" aria-labelledby="claims-title">
            <div id="claims-title" class="section-title">Claims</div>
            <div class="list">
              <div v-for="claim in reviewClaims" :key="claim.claim_id" class="row-item">
                <span>{{ claim.claim_text }}</span>
                <n-tag size="small">{{ claim.support_status }}</n-tag>
              </div>
              <div v-if="!reviewClaims.length" class="empty-state">No claims</div>
            </div>
          </section>

          <section class="panel-frame" aria-labelledby="citations-title">
            <div id="citations-title" class="section-title">Citations</div>
            <div class="list">
              <div v-for="citation in reviewCitations" :key="citation.citation_id" class="citation-item">
                <strong>{{ citation.source || citation.document_id || citation.citation_id }}</strong>
                <p>{{ citation.snippet || 'No snippet' }}</p>
              </div>
              <div v-if="!reviewCitations.length" class="empty-state">No citations</div>
            </div>
          </section>

          <section class="panel-frame" aria-labelledby="eval-title">
            <div id="eval-title" class="section-title">Eval</div>
            <div v-if="review?.eval" class="metric-row">
              <span>Coverage</span>
              <n-tag size="small">{{ Math.round(review.eval.coverage_ratio * 100) }}%</n-tag>
            </div>
            <div v-else class="empty-state">No eval</div>
          </section>

          <CaseApprovalPanel class="panel-frame" :approvals="reviewApprovals" @open-run="openRun" />

          <CaseDecisionPanel class="panel-frame" :decisions="decisions" @record="recordDecision" />
        </aside>
      </section>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAlert, NButton, NSpace, NSpin, NTag } from 'naive-ui'
import CaseApprovalPanel from '../components/case/CaseApprovalPanel.vue'
import CaseAssetPanel from '../components/case/CaseAssetPanel.vue'
import CaseDecisionPanel from '../components/case/CaseDecisionPanel.vue'
import ExecutionMonitor from '../components/case/ExecutionMonitor.vue'
import PreflightResult from '../components/case/PreflightResult.vue'
import TemplateConfigurator from '../components/case/TemplateConfigurator.vue'
import { usePlatformStore } from '../stores/platform'
import type { AddCaseAssetPayload, CaseExecutionPayload, RecordCaseDecisionPayload } from 'doge-sdk'

const route = useRoute()
const router = useRouter()
const store = usePlatformStore()

const caseId = computed(() => String(route.params.caseId || ''))
const researchCase = computed(() => store.researchCasesById[caseId.value])
const templates = computed(() => store.workflowTemplates)
const assets = computed(() => store.caseAssetsByCaseId[caseId.value] ?? [])
const executions = computed(() => store.workflowExecutionsByCaseId[caseId.value] ?? [])
const decisions = computed(() => store.caseDecisionsByCaseId[caseId.value] ?? [])
const review = computed(() => store.caseReviewByCaseId[caseId.value])
const preflightResult = computed(() => store.preflightByCaseId[caseId.value])
const reviewClaims = computed(() => review.value?.claims ?? [])
const reviewCitations = computed(() => review.value?.citations ?? [])
const reviewApprovals = computed(() => review.value?.approvals ?? [])
const errorMessage = computed(() => store.error?.message ?? '')

async function load() {
  if (!caseId.value) return
  await store.loadCaseWorkspace(caseId.value).catch(() => undefined)
}

async function addAsset(payload: AddCaseAssetPayload) {
  if (!caseId.value) return
  await store.addCaseAsset(caseId.value, payload).catch(() => undefined)
}

async function preflight(payload: { template_id: string; question: string; inputs: Record<string, unknown> }) {
  if (!caseId.value) return
  await store.preflightCaseExecution(caseId.value, executionPayload(payload)).catch(() => undefined)
}

async function execute(payload: { template_id: string; question: string; inputs: Record<string, unknown> }) {
  if (!caseId.value) return
  const execution = await store.executeCaseTemplate(caseId.value, executionPayload(payload)).catch(() => null)
  if (execution?.run_id) await store.loadCaseWorkspace(caseId.value).catch(() => undefined)
}

async function recordDecision(payload: RecordCaseDecisionPayload) {
  if (!caseId.value) return
  await store.recordCaseDecision(caseId.value, payload).catch(() => undefined)
}

function executionPayload(payload: {
  template_id: string
  question: string
  inputs: Record<string, unknown>
}): CaseExecutionPayload {
  const documentIds = assets.value.filter(asset => asset.asset_type === 'document').map(asset => asset.asset_id)
  const portfolio = assets.value.find(asset => asset.asset_type === 'portfolio')
  return {
    template_id: payload.template_id,
    question: payload.question || researchCase.value?.title || undefined,
    inputs: payload.inputs,
    document_ids: documentIds,
    portfolio_id: portfolio?.asset_id ?? undefined,
    asset_link_ids: assets.value.map(asset => asset.asset_link_id),
    trigger_channel: 'web',
  }
}

function goProject() {
  if (researchCase.value?.project_id) router.push(`/projects/${researchCase.value.project_id}`)
  else router.push('/workspaces')
}

function openRun(runId: string) {
  router.push(`/runs/${runId}`)
}

watch(caseId, load)
onMounted(load)
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
.workspace-grid,
.metric-row,
.row-item {
  display: flex;
  gap: 10px;
}

.platform-header,
.metric-row,
.row-item {
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

.thesis,
.memo-text,
.citation-item p {
  color: var(--dgm-text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.workspace-grid {
  align-items: flex-start;
}

.center-column,
.right-column,
.list {
  display: grid;
  gap: 10px;
}

.center-column {
  flex: 1 1 440px;
  min-width: 0;
}

.right-column {
  flex: 0 1 360px;
  min-width: 280px;
}

.panel-frame {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.row-item,
.citation-item {
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
}

.row-item span {
  min-width: 0;
}

.citation-item {
  display: grid;
  gap: 4px;
}

.empty-state {
  color: var(--dgm-text-faint);
  font-size: 13px;
}

@media (max-width: 900px) {
  .workspace-grid,
  .platform-header {
    flex-direction: column;
    align-items: stretch;
  }

  .right-column {
    width: 100%;
  }
}
</style>
