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
      market: 'us',
      language: 'en',
      status: 'awaiting_approval',
      events: [
        {
          event_id: 'evt-1',
          run_id: 'run-1',
          event_type: 'approval_requested',
          payload: { action: 'publish memo' },
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
          created_at: 'now',
        },
      ],
      artifacts: [
        {
          artifact_id: 'art-1',
          kind: 'investment_memo',
          title: 'Memo',
          content: '# Memo\n\nSource evd-abc',
          data: {
            usage: { total_tokens: 42 },
            citation_precision: 1,
            numerical_consistency: 0.5,
            tool_execution_success: 1,
          },
          created_at: 'now',
        },
      ],
      approvals: [
        {
          approval_id: 'appr-1',
          action: 'publish memo',
          risk_level: 'high',
          status: 'pending',
          created_at: 'now',
        },
      ],
    }

    const wrapper = mount(ResearchAgentView)

    const status = wrapper.find('[role="status"]')
    expect(status.exists()).toBe(true)
    expect(status.attributes('aria-live')).toBe('polite')
    expect(status.attributes('aria-label')).toBe('Agent status awaiting_approval; tokens 42')

    const approval = wrapper.find('[role="group"]')
    expect(approval.attributes('aria-label')).toBe('high risk approval pending: publish memo')

    const timeline = wrapper.find('[role="list"][aria-label="Agent event timeline"]')
    expect(timeline.exists()).toBe(true)
    expect(wrapper.findAll('.timeline-item[role="listitem"]').length).toBe(3)
    expect(wrapper.find('#research-agent-quality-title').text()).toBe('Quality')
    expect(wrapper.text()).toContain('Citation Precision')
    expect(wrapper.text()).toContain('100%')
    expect(wrapper.text()).toContain('doc-1 p.3')
    expect(wrapper.text()).not.toContain('annual report')

    wrapper.unmount()
  })

  it('opens citation drill-down details for populated evidence', async () => {
    const store = useAgentStore()
    store.run = {
      run_id: 'run-2',
      workflow: 'investment_research',
      question: 'Analyze',
      market: 'us',
      language: 'en',
      status: 'completed',
      events: [],
      artifacts: [
        {
          artifact_id: 'art-2',
          kind: 'investment_memo',
          title: 'Memo',
          content: '# Memo\n\nSource evd-click',
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
