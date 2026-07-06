export type EvidenceSourceType = 'document' | 'tool' | 'note' | 'fallback'

const SOURCE_TYPES: EvidenceSourceType[] = ['document', 'tool', 'note', 'fallback']

export function evidenceSourceType(record: Record<string, unknown>): EvidenceSourceType {
  const explicit = normalizedSourceType(textField(record, 'source_type', 'sourceType', 'type'))
  if (explicit) return explicit

  if (textField(record, 'document_id', 'documentId') || textField(record, 'chunk_id', 'chunkId')) {
    return 'document'
  }
  if (record.page_number !== undefined) return 'document'
  if (textField(record, 'source_tool', 'tool_name', 'toolName')) return 'tool'
  if (textField(record, 'note_id', 'noteId', 'analyst_note_id')) return 'note'
  if (textField(record, 'evidence_id', 'evidenceId', 'citation_id', 'citationId')) return 'tool'

  const source = textField(record, 'source', 'label')
  const sourceLower = source.toLowerCase()
  if (sourceLower.startsWith('tool:') || sourceLower.includes(' tool ')) return 'tool'
  if (sourceLower.includes('note')) return 'note'
  if (/\bp(?:age)?\.?\s*\d+\b/.test(sourceLower)) return 'document'

  return 'fallback'
}

export const deriveSourceType = evidenceSourceType

export function evidenceSourceLabel(sourceType: EvidenceSourceType): string {
  if (sourceType === 'document') return 'Document'
  if (sourceType === 'tool') return 'Tool'
  if (sourceType === 'note') return 'Note'
  return 'Fallback'
}

function normalizedSourceType(value: string): EvidenceSourceType | null {
  const normalized = value.toLowerCase().replace(/[_\s-]+/g, '')
  for (const sourceType of SOURCE_TYPES) {
    if (normalized === sourceType) return sourceType
  }
  if (['file', 'filing', 'citation', 'chunk'].includes(normalized)) return 'document'
  if (['toolresult', 'function', 'api'].includes(normalized)) return 'tool'
  if (['analystnote', 'humanrevision'].includes(normalized)) return 'note'
  return null
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
