import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ResearchAgentView from './ResearchAgentView.vue'
import { useAgentStore } from '../stores/agent'

vi.mock('../api/agent', () => ({
  createAgentRun: vi.fn(),
  approveAgentRun: vi.fn(),
}))

vi.mock('../api/documents', () => ({
  listDocuments: vi.fn(async () => []),
  uploadDocument: vi.fn(),
}))

// MaturityPanel (UX-1 Slice E) reads the platform capability store and
// self-loads it on mount. Stub the store so mounting ResearchAgentView does
// not trigger a real /v1/capabilities fetch under jsdom.
vi.mock('../stores/platform', () => ({
  usePlatformStore: () => ({
    capabilities: null,
    capabilitiesById: {},
    workflowTemplates: [],
    loadCapabilities: vi.fn(async () => null),
    loadWorkflowTemplates: vi.fn(async () => []),
  }),
}))

describe('ResearchAgentView accessibility', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('announces run status, approval groups, and timeline semantics', async () => {
    const store = useAgentStore()
    store.run = {
      run_id: 'run-1',
      workflow: 'investment_research',
      question: 'Analyze',
      session_id: null,
      market: 'us',
      language: 'en',
      document_ids: [],
      portfolio_id: null,
      model_policy: {},
      workflow_context: null,
      identity_snapshot: null,
      status: 'awaiting_approval',
      events: [
        {
          event_id: 'evt-1',
          run_id: 'run-1',
          event_type: 'approval_requested',
          payload: { action: 'publish memo' },
          sequence: 1,
          schema_version: '1.0',
          created_at: 'now',
        },
        {
          event_id: 'evt-2',
          run_id: 'run-1',
          event_type: 'model_response',
          payload: {
            usage: { total_tokens: 42, prompt_tokens: 30, cost_usd: 0.0012 },
            routing: { backend: 'direct_kimi_api', model: 'kimi-k2.6' },
          },
          sequence: 2,
          schema_version: '1.0',
          created_at: 'now',
        },
        {
          event_id: 'evt-3',
          run_id: 'run-1',
          event_type: 'tool_result',
          payload: {
            result: {
              data: {
                results: [
                  {
                    evidence_id: 'evd-abc',
                    document_id: 'doc-1',
                    page_number: 3,
                    text: 'Revenue growth was supported by accelerator demand.',
                    score: 0.91,
                  },
                ],
              },
            },
          },
          sequence: 3,
          schema_version: '1.0',
          created_at: 'now',
        },
      ],
      artifacts: [
        {
          artifact_id: 'art-1',
          kind: 'investment_memo',
          title: 'Memo',
          content: '# Memo\n\nSource evd-abc',
          run_id: 'run-1',
          data: {
            usage: { total_tokens: 42 },
            citation_precision: 1,
            numerical_consistency: 0.5,
            tool_execution_success: 1,
            structured_claims: [
              {
                claim_id: 'claim-1',
                claim_text: 'Revenue growth was supported by accelerator demand.',
                status: 'supported',
                evidence_refs: [{ evidence_id: 'evd-abc' }],
                numeric_check_status: 'not_applicable',
                risk_level: 'low',
              },
            ],
          },
          created_at: 'now',
        },
      ],
      approvals: [
        {
          approval_id: 'appr-1',
          action: 'publish memo',
          risk_level: 'high',
          why_needed: 'External publishing requires review.',
          impact: 'Memo becomes visible to the client.',
          deny_consequence: 'Memo remains internal.',
          publish_target: 'client portal',
          run_id: 'run-1',
          status: 'pending',
          created_at: 'now',
          resolved_at: null,
        },
        {
          approval_id: 'appr-2',
          action: 'archive memo',
          risk_level: 'low',
          why_needed: '  ',
          impact: undefined,
          deny_consequence: '',
          publish_target: undefined,
          run_id: 'run-1',
          status: 'pending',
          created_at: 'now',
          resolved_at: null,
        },
      ],
      cancel_requested_at: null,
      schema_version: '1.0',
      created_at: 'now',
      updated_at: 'now',
    }

    const wrapper = mount(ResearchAgentView)

    const status = wrapper.find('[role="status"]')
    expect(status.exists()).toBe(true)
    expect(status.attributes('aria-live')).toBe('polite')
    expect(status.attributes('aria-label')).toBe('Agent status Waiting on your approval; tokens 42')

    const approvals = wrapper.findAll('[role="group"]')
    const approval = approvals[0]
    expect(approval.attributes('aria-label')).toBe(
      'high risk approval pending: publish memo; why needed: External publishing requires review.',
    )
    expect(approval.findAll('.detail-row').map(row => row.text())).toEqual([
      'Why neededExternal publishing requires review.',
      'ImpactMemo becomes visible to the client.',
      'Deny consequenceMemo remains internal.',
      'Publish targetclient portal',
    ])
    expect(approvals[1].attributes('aria-label')).toBe('low risk approval pending: archive memo')
    expect(approvals[1].findAll('.detail-row')).toHaveLength(0)

    const timeline = wrapper.find('[role="list"][aria-label="Agent event timeline"]')
    expect(timeline.exists()).toBe(true)
    expect(wrapper.findAll('.timeline-item[role="listitem"]').length).toBe(3)
    expect(wrapper.find('#research-agent-quality-title').text()).toBe('Quality')
    expect(wrapper.text()).toContain('Citation Precision')
    expect(wrapper.text()).toContain('100%')
    expect(wrapper.text()).toContain('doc-1 p.3')
    const claims = wrapper.find('[aria-label="Structured claims"]')
    expect(claims.exists()).toBe(true)
    expect(claims.text()).toContain('Revenue growth was supported by accelerator demand.')
    expect(claims.text()).toContain('supported')
    expect(claims.text()).toContain('not_applicable')
    expect(claims.text()).toContain('low')
    expect(claims.text()).toContain('1 evidence')
    expect(wrapper.text()).not.toContain('annual report')

    wrapper.unmount()
  })

  it('opens citation drill-down details for populated evidence', async () => {
    const store = useAgentStore()
    store.run = {
      run_id: 'run-2',
      workflow: 'investment_research',
      question: 'Analyze',
      session_id: null,
      market: 'us',
      language: 'en',
      document_ids: [],
      portfolio_id: null,
      model_policy: {},
      workflow_context: null,
      identity_snapshot: null,
      status: 'completed',
      events: [],
      artifacts: [
        {
          artifact_id: 'art-2',
          kind: 'investment_memo',
          title: 'Memo',
          content: '# Memo\n\nSource evd-click',
          run_id: 'run-2',
          data: {
            citations: [
              {
                evidence_id: 'evd-click',
                document_id: 'doc-click',
                page_number: 7,
                snippet: 'Operating cash flow covered net income.',
                score: 0.88,
              },
            ],
          },
          created_at: 'now',
        },
      ],
      approvals: [],
      cancel_requested_at: null,
      schema_version: '1.0',
      created_at: 'now',
      updated_at: 'now',
    }

    const wrapper = mount(ResearchAgentView, { attachTo: document.body })

    await wrapper.find('.citation-row').trigger('click')
    await nextTick()

    expect(document.body.textContent).toContain('Source')
    expect(document.body.textContent).toContain('doc-click')
    expect(document.body.textContent).toContain('Page')
    expect(document.body.textContent).toContain('7')
    expect(document.body.textContent).toContain('Operating cash flow covered net income.')

    wrapper.unmount()
  })
})
