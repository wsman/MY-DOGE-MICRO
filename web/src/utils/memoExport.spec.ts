import { describe, expect, it } from 'vitest'

import {
  buildMemoExportPayload,
  collectCitationRecords,
  extractIcQuestions,
  formatCitationsForClipboard,
  memoFilename,
  normalizeCitationRecord,
} from './memoExport'
import type { AgentArtifact, AgentEvent, AgentRun } from '../api/agent'

describe('memoExport', () => {
  it('extracts IC questions from a markdown section and stops at the next heading', () => {
    const questions = extractIcQuestions(`# Memo

## Findings
- Supported claim.

## IC Questions
1. Which reported figures require source-page confirmation?
2) What downside scenario should be approved?
- What unresolved data gaps remain?

## Sources
- evd-1`)

    expect(questions).toEqual([
      '1. Which reported figures require source-page confirmation?',
      '2. What downside scenario should be approved?',
      '- What unresolved data gaps remain?',
    ])
  })

  it('returns an empty list when no IC question section exists', () => {
    expect(extractIcQuestions('# Memo\n\n## Findings\n- No questions.')).toEqual([])
  })

  it('normalizes and collects claim, artifact, event, and memo citations with dedupe', () => {
    const artifact = memoArtifact({
      citations: [
        {
          evidence_id: 'evd-claim',
          document_id: 'doc-1',
          page_number: 3,
          snippet: 'Duplicate citation should be removed.',
        },
        {
          citation_id: 'cit-art',
          source: 'annual report p.9',
          snippet: 'Artifact citation.',
        },
      ],
    })
    const events: AgentEvent[] = [
      {
        event_id: 'evt-1',
        run_id: 'run-1',
        event_type: 'tool_result',
        payload: {
          result: {
            data: {
              results: [{
                evidence_id: 'evd-event',
                document_id: 'doc-2',
                page_number: 5,
                text: 'Tool result citation.',
              }],
            },
          },
        },
        sequence: 1,
        schema_version: '1.0',
        created_at: 'now',
      },
    ]

    const records = collectCitationRecords({
      artifact,
      events,
      memo: 'Memo cites evd-memo.',
      claims: [
        {
          claim_id: 'claim-1',
          claim_text: 'Revenue grew.',
          status: 'supported',
          numeric_check_status: 'checked',
          risk_level: 'low',
          evidence_refs: [{
            key: 'evd-claim',
            label: 'evd-claim',
            source: 'doc-1 p.3',
            snippet: 'Claim citation.',
            evidence_id: 'evd-claim',
            document_id: 'doc-1',
            page_number: 3,
          }],
        },
      ],
    })

    expect(records.map(record => record.key)).toEqual(['evd-claim', 'cit-art', 'evd-event', 'memo-evd-memo'])
    expect(formatCitationsForClipboard(records)).toContain('annual report p.9 | cit-art | Artifact citation.')
    expect(formatCitationsForClipboard(records)).toContain('doc-2 p.5 | evd-event | Tool result citation.')
  })

  it('builds a web-local JSON payload without raw event leakage', () => {
    const run = agentRun()
    const artifact = memoArtifact({
      usage: { total_tokens: 42 },
      citation_precision: 1,
      numerical_consistency: 0.5,
      tool_execution_success: 1,
      structured_claims: [{ claim_id: 'claim-1' }],
    })
    const citation = normalizeCitationRecord({
      evidence_id: 'evd-1',
      source: 'doc p.1',
      snippet: 'Source text.',
    }, 0)
    expect(citation).not.toBeNull()

    const payload = buildMemoExportPayload({
      run,
      artifact,
      memo: '# Memo',
      claims: [],
      citations: citation ? [citation] : [],
      icQuestions: ['1. What data gap remains?'],
      generatedAt: '2026-07-05T00:00:00.000Z',
    })

    expect(payload).toMatchObject({
      schema_version: 'doge.web.memo_export.v1',
      export_kind: 'investment_memo',
      generated_at: '2026-07-05T00:00:00.000Z',
      run: {
        run_id: 'run-1',
        workflow: 'investment_research',
        status: 'completed',
        language: 'en',
      },
      artifact: {
        artifact_id: 'art-1',
        content_markdown: '# Memo',
      },
      ic_questions: ['1. What data gap remains?'],
      metrics: {
        usage: { total_tokens: 42 },
        citation_precision: 1,
      },
    })
    expect(JSON.stringify(payload)).not.toContain('tool_result')
    expect(payload).not.toHaveProperty('events')
  })

  it('generates stable local memo filenames', () => {
    expect(memoFilename(agentRun(), 'md')).toBe('investment-memo-run-1.md')
    expect(memoFilename(null, 'json')).toBe('investment-memo-draft.json')
  })
})

function memoArtifact(data: Record<string, unknown>): AgentArtifact {
  return {
    artifact_id: 'art-1',
    kind: 'investment_memo',
    title: 'Memo',
    content: '# Memo',
    run_id: 'run-1',
    data,
    created_at: 'now',
  }
}

function agentRun(): AgentRun {
  return {
    run_id: 'run-1',
    workflow: 'investment_research',
    question: 'Analyze',
    session_id: null,
    market: 'us',
    language: 'en',
    document_ids: ['doc-1'],
    portfolio_id: null,
    model_policy: {},
    workflow_context: null,
    identity_snapshot: null,
    status: 'completed',
    events: [],
    artifacts: [],
    approvals: [],
    cancel_requested_at: null,
    schema_version: '1.0',
    created_at: 'now',
    updated_at: 'now',
  }
}
