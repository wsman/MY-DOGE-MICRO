<template>
  <div class="research-agent-view" :class="{ 'developer-mode': isDeveloperMode }" aria-label="Research Agent workspace">
    <div class="workspace-toolbar" aria-label="Research workspace toolbar">
      <div class="mode-toggle" role="group" aria-label="Workspace mode">
        <n-button
          size="tiny"
          :type="store.analystMode ? 'primary' : 'default'"
          :secondary="!store.analystMode"
          :aria-pressed="store.analystMode"
          @click="store.setAnalystMode(true)"
        >
          Analyst
        </n-button>
        <n-button
          size="tiny"
          :type="isDeveloperMode ? 'primary' : 'default'"
          :secondary="!isDeveloperMode"
          :aria-pressed="isDeveloperMode"
          @click="store.setAnalystMode(false)"
        >
          Developer
        </n-button>
      </div>
      <div class="export-actions" role="group" aria-label="Memo export actions">
        <n-button
          size="tiny"
          :disabled="!store.latestMemo"
          aria-label="Export memo as Markdown"
          @click="downloadMemoMarkdown"
        >
          <template #icon><n-icon><DownloadOutline /></n-icon></template>
          Markdown
        </n-button>
        <n-button
          size="tiny"
          :disabled="!store.latestMemo"
          aria-label="Export memo as JSON"
          @click="downloadMemoJson"
        >
          <template #icon><n-icon><CodeDownloadOutline /></n-icon></template>
          JSON
        </n-button>
        <n-button
          size="tiny"
          :disabled="!copyableIcQuestions"
          aria-label="Copy IC questions"
          @click="copyIcQuestions"
        >
          <template #icon><n-icon><CopyOutline /></n-icon></template>
          IC Questions
        </n-button>
        <n-button
          size="tiny"
          :disabled="!copyableCitations"
          aria-label="Copy citations"
          @click="copyCitations"
        >
          <template #icon><n-icon><CopyOutline /></n-icon></template>
          Citations
        </n-button>
        <n-button
          size="tiny"
          :disabled="!store.latestMemo"
          aria-label="Print memo"
          @click="printMemo"
        >
          <template #icon><n-icon><PrintOutline /></n-icon></template>
          Print
        </n-button>
      </div>
    </div>

    <section ref="inputPaneRef" class="input-pane" aria-labelledby="research-agent-input-title">
      <div id="research-agent-input-title" class="pane-header">Input</div>
      <n-space vertical size="small">
        <GuidedFlow @select="onStepSelect" />
        <ScenarioPicker />
        <n-select v-model:value="store.market" :options="marketOptions" size="small" aria-label="Market" />
        <ExecutionProfileSelector v-model="store.executionProfile" />
        <n-input
          v-model:value="store.question"
          type="textarea"
          :autosize="{ minRows: 5, maxRows: 8 }"
          aria-label="Research question"
        />
        <RunPreflightChecklist />
        <n-button type="primary" size="small" :loading="store.loading" @click="startRun">
          Run
        </n-button>
        <DocumentUploader />
        <DocumentSelector />
        <PortfolioImporter @imported="onPortfolioImported" />
      </n-space>
    </section>

    <section ref="memoPaneRef" class="memo-pane" aria-labelledby="research-agent-memo-title">
      <div id="research-agent-memo-title" class="pane-header">Research Memo</div>
      <n-alert v-if="store.error" type="error" :show-icon="false" role="alert" aria-live="assertive">
        {{ store.error.message }}
      </n-alert>
      <div v-if="store.latestMemo" class="memo-body" aria-live="polite" v-html="renderedMemo" />
      <EmptyStateCtas
        v-else
        @run-demo="store.startDemoRun"
        @load-sample="loadSampleCase"
        @upload="scrollToInput"
        @import-portfolio="scrollToInput"
      />
    </section>

    <section class="evidence-pane" aria-labelledby="research-agent-evidence-title">
      <div id="research-agent-evidence-title" class="pane-header">Evidence</div>
      <div class="status-row" role="status" aria-live="polite" :aria-label="statusAnnouncement">
        <n-tag :type="toneFor(store.run?.status)" size="small">{{ labelFor(store.run?.status) }}</n-tag>
        <n-tag v-if="isDeveloperMode" size="small">tokens {{ usage.total_tokens ?? 0 }}</n-tag>
        <n-tag v-for="action in statusNextActions" :key="action" size="small" class="next-action-tag">
          Next: {{ action }}
        </n-tag>
      </div>
      <ConclusionEvidenceMatrix
        v-if="structuredClaims.length"
        :claims="structuredClaims"
        @select-evidence="selectEvidence"
      />
      <CitationDrilldown
        v-model="selectedEvidence"
        :memo="store.latestMemo"
        :artifacts="store.artifacts"
        :events="store.events"
        :records="activeClaimEvidenceRefs"
      />
      <div class="approval-list" aria-label="Approval requests">
        <div
          v-for="approval in store.approvals"
          :key="approval.approval_id"
          class="approval-item"
          role="group"
          :aria-label="approvalLabel(approval)"
        >
          <div class="approval-title">{{ approval.risk_level }} · {{ approval.status }}</div>
          <div class="approval-action">{{ approval.action }}</div>
          <div v-if="approvalDetailRows(approval).length" class="approval-details">
            <div v-for="row in approvalDetailRows(approval)" :key="row.key" class="detail-row">
              <span>{{ row.label }}</span>
              <strong>{{ row.value }}</strong>
            </div>
          </div>
          <n-space v-if="approval.status === 'pending'" size="small">
            <n-button size="tiny" type="primary" @click="store.resolveApproval(approval.approval_id, true)">Approve</n-button>
            <n-button size="tiny" @click="store.resolveApproval(approval.approval_id, false)">Deny</n-button>
          </n-space>
        </div>
        <div v-if="!store.approvals.length" class="empty-state">No approvals pending</div>
      </div>
    </section>

    <section class="quality-pane" aria-labelledby="research-agent-quality-title">
      <div id="research-agent-quality-title" class="pane-header">Quality</div>
      <MaturityPanel />
      <RunComparisonPanel :current-run-id="store.run?.run_id" />
      <CostEvalPanel v-if="isDeveloperMode" :artifacts="store.artifacts" :events="store.events" />
    </section>

    <section v-if="isDeveloperMode" class="timeline-pane" aria-labelledby="research-agent-timeline-title">
      <div id="research-agent-timeline-title" class="pane-header">Agent Timeline</div>
      <div class="timeline" role="list" aria-label="Agent event timeline">
        <div v-for="event in store.events" :key="event.event_id" class="timeline-item" role="listitem">
          <n-tag size="small">{{ event.event_type }}</n-tag>
          <code>{{ compactPayload(event.payload) }}</code>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import { CodeDownloadOutline, CopyOutline, DownloadOutline, PrintOutline } from '@vicons/ionicons5'
import { NAlert, NButton, NIcon, NInput, NSelect, NSpace, NTag } from 'naive-ui'
import CitationDrilldown from '../components/agent/CitationDrilldown.vue'
import type { CitationRecord } from '../components/agent/CitationDrilldown.vue'
import ConclusionEvidenceMatrix from '../components/agent/ConclusionEvidenceMatrix.vue'
import type { ConclusionClaimDisplay, EvidenceSelection } from '../components/agent/ConclusionEvidenceMatrix.vue'
import CostEvalPanel from '../components/agent/CostEvalPanel.vue'
import MaturityPanel from '../components/common/MaturityPanel.vue'
import DocumentSelector from '../components/agent/DocumentSelector.vue'
import DocumentUploader from '../components/agent/DocumentUploader.vue'
import EmptyStateCtas from '../components/agent/EmptyStateCtas.vue'
import GuidedFlow from '../components/agent/GuidedFlow.vue'
import ExecutionProfileSelector from '../components/agent/ExecutionProfileSelector.vue'
import PortfolioImporter from '../components/agent/PortfolioImporter.vue'
import RunPreflightChecklist from '../components/agent/RunPreflightChecklist.vue'
import RunComparisonPanel from '../components/agent/RunComparisonPanel.vue'
import ScenarioPicker from '../components/agent/ScenarioPicker.vue'
import type { ImportedPortfolio } from '../api/portfolio'
import { useAgentStore } from '../stores/agent'
import { useDocumentStore } from '../stores/documents'
import {
  buildMemoExportPayload,
  collectCitationRecords,
  copyText,
  downloadTextFile,
  extractIcQuestions,
  formatCitationsForClipboard,
  latestMemoArtifact,
  memoFilename,
  questionsFromClaims,
} from '../utils/memoExport'
import { labelFor, nextActionsFor, toneFor } from '../utils/runStatus'

const store = useAgentStore()
const documentStore = useDocumentStore()
const md = new MarkdownIt()
const inputPaneRef = ref<HTMLElement | null>(null)
const isDeveloperMode = computed(() => !store.analystMode)

function scrollToInput() {
  inputPaneRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function loadSampleCase() {
  store.selectedScenarioSlug = 'earnings_review'
  scrollToInput()
}

const memoPaneRef = ref<HTMLElement | null>(null)

function scrollToMemo() {
  memoPaneRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function onStepSelect(stepId: string) {
  if (stepId === 'memo') {
    scrollToMemo()
  } else {
    scrollToInput()
  }
}

const marketOptions = [
  { label: 'US Market', value: 'us' },
  { label: 'A-Share (CN)', value: 'cn' },
]

const memoArtifact = computed(() => latestMemoArtifact(store.artifacts))
const renderedMemo = computed(() => md.render(store.latestMemo))
const usage = computed(() => store.artifacts[0]?.data?.usage ?? {})
const structuredClaims = computed(() => {
  const claims = memoArtifact.value?.data?.structured_claims
  if (!Array.isArray(claims)) return []
  return claims.map(claimRow).filter(row => row.claim_id && row.claim_text)
})
const selectedClaimId = ref<string | null>(null)
const selectedEvidence = ref<CitationRecord | null>(null)
const activeClaimEvidenceRefs = computed(() => {
  if (!selectedClaimId.value) return undefined
  return structuredClaims.value.find(claim => claim.claim_id === selectedClaimId.value)?.evidence_refs ?? []
})
const statusNextActions = computed(() => nextActionsFor(store.run?.status))
const statusAnnouncement = computed(() => {
  const tokens = isDeveloperMode.value ? `; tokens ${usage.value.total_tokens ?? 0}` : ''
  const next = statusNextActions.value.length ? `; next ${statusNextActions.value.join(', ')}` : ''
  return `Agent status ${labelFor(store.run?.status)}${tokens}${next}`
})
const exportCitationRecords = computed(() => collectCitationRecords({
  artifact: memoArtifact.value,
  claims: structuredClaims.value,
  memo: store.latestMemo,
  events: store.events,
}))
const icQuestions = computed(() => {
  const fromMemo = extractIcQuestions(store.latestMemo)
  return fromMemo.length ? fromMemo : questionsFromClaims(structuredClaims.value)
})
const icQuestionsText = computed(() => icQuestions.value.join('\n'))
const citationClipboardText = computed(() => formatCitationsForClipboard(exportCitationRecords.value))
const copyableIcQuestions = computed(() => Boolean(icQuestionsText.value.trim()))
const copyableCitations = computed(() => Boolean(citationClipboardText.value.trim()))

function selectEvidence(selection: EvidenceSelection) {
  selectedClaimId.value = selection.claimId
  selectedEvidence.value = selection.ref
}

function downloadMemoMarkdown() {
  if (!store.latestMemo) return
  downloadTextFile(memoFilename(store.run, 'md'), 'text/markdown;charset=utf-8', store.latestMemo)
}

function downloadMemoJson() {
  if (!store.latestMemo) return
  const payload = buildMemoExportPayload({
    run: store.run,
    artifact: memoArtifact.value,
    memo: store.latestMemo,
    claims: structuredClaims.value,
    citations: exportCitationRecords.value,
    icQuestions: icQuestions.value,
  })
  downloadTextFile(
    memoFilename(store.run, 'json'),
    'application/json;charset=utf-8',
    JSON.stringify(payload, null, 2),
  )
}

async function copyIcQuestions() {
  if (!icQuestionsText.value.trim()) return
  await copyText(icQuestionsText.value)
}

async function copyCitations() {
  if (!citationClipboardText.value.trim()) return
  await copyText(citationClipboardText.value)
}

function printMemo() {
  if (!store.latestMemo) return
  window.print()
}

interface ApprovalDisplay {
  risk_level: string
  status: string
  action: string
  why_needed?: unknown
  impact?: unknown
  deny_consequence?: unknown
  publish_target?: unknown
}

const approvalDetailFields = [
  { key: 'why_needed', label: 'Why needed' },
  { key: 'impact', label: 'Impact' },
  { key: 'deny_consequence', label: 'Deny consequence' },
  { key: 'publish_target', label: 'Publish target' },
] as const

function approvalDetailRows(approval: ApprovalDisplay) {
  return approvalDetailFields
    .map(field => ({
      key: field.key,
      label: field.label,
      value: textValue(approval[field.key]),
    }))
    .filter(row => row.value)
}

function approvalLabel(approval: ApprovalDisplay) {
  const whyNeeded = textValue(approval.why_needed)
  const suffix = whyNeeded ? `; why needed: ${whyNeeded}` : ''
  return `${approval.risk_level} risk approval ${approval.status}: ${approval.action}${suffix}`
}

function textValue(value: unknown) {
  if (value === undefined || value === null) return ''
  return String(value).trim()
}

function claimRow(value: unknown): ConclusionClaimDisplay {
  const item = isRecord(value) ? value : {}
  const refs = Array.isArray(item.evidence_refs) ? item.evidence_refs : []
  const claimId = textValue(item.claim_id)
  return {
    claim_id: claimId,
    claim_text: textValue(item.claim_text),
    status: textValue(item.status) || 'unverified',
    numeric_check_status: textValue(item.numeric_check_status) || 'not_checked',
    risk_level: textValue(item.risk_level) || 'medium',
    evidence_refs: refs.map((ref, index) => citationRecordFromRef(ref, index, claimId)),
  }
}

function citationRecordFromRef(value: unknown, index: number, claimId: string): CitationRecord {
  const item = isRecord(value) ? value : {}
  const fallback = textValue(value) || `${claimId || 'claim'}-evidence-${index + 1}`
  const pageNumber = numberValue(item.page_number)
  const evidenceId = textField(item, 'evidence_id')
  const citationId = textField(item, 'citation_id')
  const chunkId = textField(item, 'chunk_id')
  const key = textField(item, 'key') || evidenceId || citationId || chunkId || fallback
  return {
    key,
    label: textField(item, 'label') || evidenceId || citationId || chunkId || `Evidence ${index + 1}`,
    source: textField(item, 'source') || sourceLabel(item, pageNumber) || key,
    snippet: textField(item, 'snippet', 'text', 'support_snippet', 'content') || key,
    document_id: textField(item, 'document_id') || undefined,
    page_number: pageNumber,
    chunk_id: chunkId || undefined,
    evidence_id: evidenceId || undefined,
    citation_id: citationId || undefined,
    score: numberValue(item.score ?? item.retrieval_score),
  }
}

function textField(record: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) {
    const value = textValue(record[key])
    if (value) return value
  }
  return ''
}

function numberValue(value: unknown): number | undefined {
  if (typeof value === 'number') return value
  if (typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Number(value))) {
    return Number(value)
  }
  return undefined
}

function sourceLabel(record: Record<string, unknown>, pageNumber: number | undefined) {
  const documentId = textField(record, 'document_id')
  if (documentId && pageNumber !== undefined) return `${documentId} p.${pageNumber}`
  if (documentId) return documentId
  return textField(record, 'chunk_id', 'evidence_id', 'citation_id')
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

async function startRun() {
  store.setDocumentIds([...documentStore.selectedIds])
  await store.startDemoRun()
}

function onPortfolioImported(portfolio: ImportedPortfolio) {
  store.setPortfolioId(portfolio.portfolio_id)
}

function compactPayload(payload: Record<string, unknown>) {
  const text = JSON.stringify(payload)
  return text.length > 180 ? `${text.slice(0, 180)}...` : text
}
</script>

<style scoped>
.research-agent-view {
  height: 100%;
  padding: 12px;
  display: grid;
  grid-template-columns: minmax(220px, 0.85fr) minmax(320px, 1.25fr) minmax(240px, 0.95fr) minmax(220px, 0.85fr);
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  color: var(--dgm-text);
}

.research-agent-view.developer-mode {
  grid-template-rows: auto minmax(0, 1fr) 180px;
}

section {
  min-width: 0;
  min-height: 0;
  border: 1px solid var(--dgm-border);
  background: var(--dgm-surface);
  border-radius: 6px;
  padding: 12px;
  overflow: auto;
}

.workspace-toolbar {
  grid-column: 1 / -1;
  min-width: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.mode-toggle,
.export-actions {
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.timeline-pane {
  grid-column: 1 / 5;
}

.evidence-pane,
.quality-pane {
  display: grid;
  align-content: start;
  gap: 12px;
}

.pane-header {
  font-size: 12px;
  font-weight: 700;
  color: var(--dgm-text-muted);
  margin-bottom: 10px;
  text-transform: uppercase;
}

.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.memo-body {
  line-height: 1.6;
  color: var(--dgm-text-muted);
}

.memo-body :deep(h1),
.memo-body :deep(h2) {
  font-size: 16px;
  margin: 12px 0 8px;
  color: var(--dgm-text);
}

.empty-state {
  color: var(--dgm-text-faint);
  font-size: 13px;
}

.approval-list {
  display: grid;
  gap: 10px;
}

.approval-item {
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  padding: 8px;
}

.approval-title {
  font-size: 12px;
  color: var(--dgm-text);
}

.approval-action {
  font-size: 12px;
  color: var(--dgm-text-muted);
  margin: 4px 0 8px;
}

.approval-details {
  display: grid;
  gap: 8px;
  margin-bottom: 8px;
}

.detail-row {
  display: grid;
  grid-template-columns: 104px minmax(0, 1fr);
  gap: 8px;
  font-size: 12px;
}

.detail-row span {
  color: var(--dgm-text-faint);
}

.detail-row strong {
  min-width: 0;
  overflow-wrap: anywhere;
}

.timeline {
  display: grid;
  gap: 8px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}

code {
  font-family: var(--dgm-font-mono);
  font-size: 12px;
  color: var(--dgm-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 900px) {
  .research-agent-view {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }

  .research-agent-view.developer-mode {
    grid-template-rows: auto;
  }

  .workspace-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .timeline-pane {
    grid-column: 1;
  }

  .timeline-item {
    grid-template-columns: 1fr;
  }
}
</style>
