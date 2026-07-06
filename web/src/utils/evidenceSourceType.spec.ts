import { describe, expect, it } from 'vitest'

import { evidenceSourceLabel, evidenceSourceType } from './evidenceSourceType'

describe('evidenceSourceType', () => {
  it('honors explicit source type aliases', () => {
    expect(evidenceSourceType({ source_type: 'tool_result' })).toBe('tool')
    expect(evidenceSourceType({ sourceType: 'human_revision' })).toBe('note')
    expect(evidenceSourceType({ type: 'filing' })).toBe('document')
  })

  it('infers document, tool, note, and fallback sources from citation records', () => {
    expect(evidenceSourceType({ document_id: 'annual-report', page_number: 3 })).toBe('document')
    expect(evidenceSourceType({ source: 'annual report p.3' })).toBe('document')
    expect(evidenceSourceType({ source_tool: 'validate_financial_claims' })).toBe('tool')
    expect(evidenceSourceType({ note_id: 'note-1' })).toBe('note')
    expect(evidenceSourceType({ evidence_id: 'evd-1' })).toBe('tool')
    expect(evidenceSourceType({ source: 'local evidence' })).toBe('fallback')
  })

  it('provides stable display labels', () => {
    expect(evidenceSourceLabel('document')).toBe('Document')
    expect(evidenceSourceLabel('tool')).toBe('Tool')
    expect(evidenceSourceLabel('note')).toBe('Note')
    expect(evidenceSourceLabel('fallback')).toBe('Fallback')
  })
})
