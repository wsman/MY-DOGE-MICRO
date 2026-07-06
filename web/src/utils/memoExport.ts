import type { AgentArtifact, AgentEvent, AgentRun } from '../api/agent'

export interface MemoCitationRecord {
  key: string
  label: string
  source: string
  snippet: string
  document_id?: string
  page_number?: number
  chunk_id?: string
  evidence_id?: string
  citation_id?: string
  score?: number
}

export interface MemoClaimExport {
  claim_id: string
  claim_text: string
  status: string
  numeric_check_status: string
  risk_level: string
  evidence_refs: MemoCitationRecord[]
}

export interface MemoExportPayloadInput {
  run: AgentRun | null
  artifact: AgentArtifact | undefined
  memo: string
  claims: MemoClaimExport[]
  citations: MemoCitationRecord[]
  icQuestions: string[]
  generatedAt?: string
}

export function latestMemoArtifact(artifacts: AgentArtifact[]) {
  return artifacts.find(item => item.kind === 'investment_memo')
}

export function extractIcQuestions(markdown: string, headings = ['IC Questions', 'Suggested Research Questions']) {
  const section = extractMarkdownSection(markdown, headings)
  if (!section) return []
  return section
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => line.replace(/^(\d+)[.)]\s+/, '$1. ').replace(/^[-*]\s+/, '- '))
}

export function questionsFromClaims(claims: MemoClaimExport[]) {
  return claims.map(
    (claim, index) => `${index + 1}. What evidence would change the conclusion that "${claim.claim_text}"?`,
  )
}

export function collectCitationRecords(input: {
  artifact?: AgentArtifact
  claims: MemoClaimExport[]
  memo: string
  events: AgentEvent[]
}): MemoCitationRecord[] {
  const claimRefs = input.claims.flatMap(claim => claim.evidence_refs)
  const artifactRefs = citationRecordsFromContainer(input.artifact?.data, 'artifact')
  const eventRefs = input.events.flatMap((event, index) => {
    if (event.event_type !== 'tool_result') return []
    return citationRecordsFromContainer(event.payload?.result?.data, `event-${index + 1}`)
  })
  const memoRefs = recordsFromMemo(input.memo)
  return dedupeCitationRecords([...claimRefs, ...artifactRefs, ...eventRefs, ...memoRefs])
}

export function normalizeCitationRecord(value: unknown, index: number, namespace = 'citation'): MemoCitationRecord | null {
  if (!isRecord(value)) return null
  const snippet = textField(value, 'snippet', 'text', 'support_snippet', 'content')
  const evidenceId = textField(value, 'evidence_id')
  const citationId = textField(value, 'citation_id')
  const chunkId = textField(value, 'chunk_id')
  const pageNumber = numberValue(value.page_number)
  const source = textField(value, 'source') || sourceLabel(value, pageNumber)
  if (!snippet && !evidenceId && !citationId && !chunkId) return null
  const key = textField(value, 'key') || evidenceId || citationId || chunkId || `${namespace}-${index + 1}`
  return {
    key,
    label: textField(value, 'label') || evidenceId || citationId || chunkId || `Citation ${index + 1}`,
    source: source || key,
    snippet: snippet || key,
    document_id: textField(value, 'document_id') || undefined,
    page_number: pageNumber,
    chunk_id: chunkId || undefined,
    evidence_id: evidenceId || undefined,
    citation_id: citationId || undefined,
    score: numberValue(value.score ?? value.retrieval_score),
  } satisfies MemoCitationRecord
}

export function formatCitationsForClipboard(records: MemoCitationRecord[]) {
  return records.map((record, index) => citationClipboardLine(record, index)).join('\n')
}

export function buildMemoExportPayload(input: MemoExportPayloadInput) {
  const data = input.artifact?.data ?? {}
  return {
    schema_version: 'doge.web.memo_export.v1',
    export_kind: 'investment_memo',
    generated_at: input.generatedAt ?? new Date().toISOString(),
    run: input.run ? {
      run_id: input.run.run_id,
      workflow: input.run.workflow,
      question: input.run.question,
      status: input.run.status,
      market: input.run.market,
      language: input.run.language,
      document_ids: input.run.document_ids,
      portfolio_id: input.run.portfolio_id,
      created_at: input.run.created_at,
      updated_at: input.run.updated_at,
    } : null,
    artifact: input.artifact ? {
      artifact_id: input.artifact.artifact_id,
      kind: input.artifact.kind,
      title: input.artifact.title,
      created_at: input.artifact.created_at,
      content_markdown: input.memo,
    } : null,
    ic_questions: input.icQuestions,
    claims: input.claims,
    citations: input.citations,
    metrics: {
      usage: isRecord(data.usage) ? data.usage : {},
      citation_precision: data.citation_precision,
      numerical_consistency: data.numerical_consistency,
      tool_execution_success: data.tool_execution_success,
      support_status: data.support_status,
      coverage_ratio: data.coverage_ratio,
      numeric_validation: data.numeric_validation,
    },
  }
}

export function memoFilename(run: AgentRun | null, ext: 'md' | 'json') {
  const runId = run?.run_id || 'draft'
  return `investment-memo-${safeFilename(runId)}.${ext}`
}

export function downloadTextFile(filename: string, mimeType: string, content: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export async function copyText(content: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(content)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = content
  textarea.setAttribute('readonly', 'true')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  textarea.remove()
}

function extractMarkdownSection(markdown: string, headings: string[]) {
  if (!markdown.trim()) return ''
  const lines = markdown.split(/\r?\n/)
  const normalizedHeadings = new Set(headings.map(heading => heading.toLowerCase()))
  const collected: string[] = []
  let collecting = false
  let headingLevel = 0

  for (const line of lines) {
    const match = /^(#{1,6})\s+(.+?)\s*$/.exec(line)
    if (match) {
      const currentLevel = match[1].length
      const title = match[2].replace(/#+$/, '').trim().toLowerCase()
      if (collecting && currentLevel <= headingLevel) break
      if (normalizedHeadings.has(title)) {
        collecting = true
        headingLevel = currentLevel
        continue
      }
    }
    if (collecting) collected.push(line)
  }

  return collected.join('\n').trim()
}

function citationRecordsFromContainer(container: unknown, namespace: string): MemoCitationRecord[] {
  if (!isRecord(container)) return []
  const rows = [
    ...arrayField(container, 'citations'),
    ...arrayField(container, 'evidence'),
    ...arrayField(container, 'results'),
  ]
  return rows
    .map((row, index) => normalizeCitationRecord(row, index, namespace))
    .filter((row): row is MemoCitationRecord => row !== null)
}

function recordsFromMemo(memo: string): MemoCitationRecord[] {
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

function dedupeCitationRecords(rows: MemoCitationRecord[]) {
  const seen = new Set<string>()
  return rows.filter(row => {
    const key = row.evidence_id || row.citation_id || row.chunk_id || row.key
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function citationClipboardLine(record: MemoCitationRecord, index: number) {
  const parts = [`${index + 1}. ${record.label}`, record.source]
  if (record.page_number !== undefined && !record.source.includes(`p.${record.page_number}`)) {
    parts.push(`p.${record.page_number}`)
  }
  const evidenceId = record.evidence_id || record.citation_id || record.chunk_id
  if (evidenceId) parts.push(evidenceId)
  parts.push(record.snippet)
  return parts.filter(Boolean).join(' | ')
}

function sourceLabel(record: Record<string, unknown>, pageNumber: number | undefined) {
  const documentId = textField(record, 'document_id')
  if (documentId && pageNumber !== undefined) return `${documentId} p.${pageNumber}`
  if (documentId) return documentId
  return textField(record, 'chunk_id', 'evidence_id', 'citation_id')
}

function textField(record: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) {
    const value = textValue(record[key])
    if (value) return value
  }
  return ''
}

function textValue(value: unknown) {
  if (value === undefined || value === null) return ''
  return String(value).trim()
}

function numberValue(value: unknown): number | undefined {
  if (typeof value === 'number') return value
  if (typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Number(value))) {
    return Number(value)
  }
  return undefined
}

function arrayField(record: Record<string, unknown>, key: string): unknown[] {
  const value = record[key]
  return Array.isArray(value) ? value : []
}

function safeFilename(value: string) {
  return value.replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '') || 'memo'
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
