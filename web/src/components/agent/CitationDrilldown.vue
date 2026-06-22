<template>
  <div class="citation-drilldown">
    <div class="section-title">Sources</div>
    <div v-if="candidates.length" class="citation-list" role="list" aria-label="Citation evidence">
      <button
        v-for="candidate in candidates"
        :key="candidate.key"
        class="citation-row"
        type="button"
        role="listitem"
        @click="active = candidate"
      >
        <span class="citation-label">{{ candidate.label }}</span>
        <span class="citation-source">{{ candidate.source }}</span>
        <n-tag v-if="candidate.score !== undefined" size="small">{{ formatScore(candidate.score) }}</n-tag>
      </button>
    </div>
    <div v-else class="empty-state">No source citations available</div>

    <n-drawer :show="Boolean(active)" width="420" @update:show="show => { if (!show) active = null }">
      <n-drawer-content :title="active?.label || 'Citation'" closable>
        <div v-if="active" class="citation-detail">
          <div class="detail-row">
            <span>Source</span>
            <strong>{{ active.source }}</strong>
          </div>
          <div v-if="active.document_id" class="detail-row">
            <span>Document</span>
            <strong>{{ active.document_id }}</strong>
          </div>
          <div v-if="active.page_number !== undefined" class="detail-row">
            <span>Page</span>
            <strong>{{ active.page_number }}</strong>
          </div>
          <div v-if="active.chunk_id || active.evidence_id" class="detail-row">
            <span>Evidence</span>
            <strong>{{ active.evidence_id || active.chunk_id }}</strong>
          </div>
          <p class="snippet">{{ active.snippet }}</p>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NDrawer, NDrawerContent, NTag } from 'naive-ui'
import type { AgentArtifact, AgentEvent } from '../../api/agent'

interface CitationCandidate {
  key: string
  label: string
  source: string
  snippet: string
  document_id?: string
  page_number?: number
  chunk_id?: string
  evidence_id?: string
  score?: number
}

const props = defineProps<{
  memo: string
  artifacts: AgentArtifact[]
  events: AgentEvent[]
}>()

const active = ref<CitationCandidate | null>(null)

const candidates = computed(() => {
  const rows: CitationCandidate[] = []
  for (const artifact of props.artifacts) {
    rows.push(...recordsFromContainer(artifact.data))
  }
  for (const event of props.events) {
    if (event.event_type !== 'tool_result') continue
    rows.push(...recordsFromContainer(event.payload?.result?.data))
  }
  rows.push(...recordsFromMemo(props.memo))
  return dedupe(rows).slice(0, 12)
})

function recordsFromContainer(container: unknown): CitationCandidate[] {
  if (!isRecord(container)) return []
  const records = [
    ...arrayField(container, 'citations'),
    ...arrayField(container, 'evidence'),
    ...arrayField(container, 'results'),
  ]
  return records.map(candidateFromRecord).filter(Boolean) as CitationCandidate[]
}

function candidateFromRecord(record: unknown, index: number): CitationCandidate | null {
  if (!isRecord(record)) return null
  const snippet = textField(record, 'snippet', 'text', 'support_snippet', 'content')
  const evidenceId = textField(record, 'evidence_id')
  const chunkId = textField(record, 'chunk_id')
  const source = textField(record, 'source') || sourceLabel(record)
  if (!snippet && !evidenceId && !chunkId) return null
  const key = evidenceId || chunkId || textField(record, 'citation_id') || `${source}-${index}`
  return {
    key,
    label: evidenceId || chunkId || `Citation ${index + 1}`,
    source,
    snippet: snippet || key,
    document_id: textField(record, 'document_id') || undefined,
    page_number: numberField(record, 'page_number'),
    chunk_id: chunkId || undefined,
    evidence_id: evidenceId || undefined,
    score: numberField(record, 'score', 'retrieval_score'),
  }
}

function recordsFromMemo(memo: string): CitationCandidate[] {
  const ids = new Set(memo.match(/\b(?:evd|chk|page)-[A-Za-z0-9_-]+\b/g) ?? [])
  return Array.from(ids).map(id => ({
    key: `memo-${id}`,
    label: id,
    source: 'memo marker',
    snippet: id,
    evidence_id: id.startsWith('evd-') ? id : undefined,
    chunk_id: id.startsWith('chk-') ? id : undefined,
  }))
}

function dedupe(rows: CitationCandidate[]) {
  const seen = new Set<string>()
  return rows.filter(row => {
    if (seen.has(row.key)) return false
    seen.add(row.key)
    return true
  })
}

function arrayField(record: Record<string, unknown>, key: string): unknown[] {
  const value = record[key]
  return Array.isArray(value) ? value : []
}

function textField(record: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) {
    const value = record[key]
    if (value !== undefined && value !== null && String(value).trim()) {
      return String(value).trim()
    }
  }
  return ''
}

function numberField(record: Record<string, unknown>, ...keys: string[]): number | undefined {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'number') return value
    if (typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Number(value))) {
      return Number(value)
    }
  }
  return undefined
}

function sourceLabel(record: Record<string, unknown>) {
  const documentId = textField(record, 'document_id')
  const page = numberField(record, 'page_number')
  if (documentId && page !== undefined) return `${documentId} p.${page}`
  if (documentId) return documentId
  return textField(record, 'chunk_id', 'evidence_id') || 'local evidence'
}

function formatScore(score: number) {
  return score <= 1 ? score.toFixed(2) : String(score)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
</script>

<style scoped>
.citation-drilldown {
  display: grid;
  gap: 8px;
}

.section-title {
  color: var(--dgm-text-muted);
  font-size: 12px;
  font-weight: 700;
}

.citation-list {
  display: grid;
  gap: 6px;
}

.citation-row {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(80px, 0.7fr) minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 7px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  color: var(--dgm-text);
  background: var(--dgm-surface);
  text-align: left;
  cursor: pointer;
}

.citation-row:hover {
  background: var(--dgm-surface-hover);
}

.citation-label,
.citation-source {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.citation-source,
.empty-state {
  color: var(--dgm-text-faint);
}

.citation-detail {
  display: grid;
  gap: 10px;
}

.detail-row {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
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

.snippet {
  margin: 0;
  line-height: 1.55;
  color: var(--dgm-text-muted);
  overflow-wrap: anywhere;
}
</style>
