import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ResearchAgentView from './ResearchAgentView.vue'
import { useAgentStore } from '../stores/agent'

vi.mock('../api/agent', () => ({
  createAgentRun: vi.fn(),
  approveAgentRun: vi.fn(),
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
      ],
      artifacts: [
        {
          artifact_id: 'art-1',
          kind: 'investment_memo',
          title: 'Memo',
          content: '# Memo',
          data: { usage: { total_tokens: 42 } },
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
    expect(wrapper.findAll('[role="listitem"]').length).toBe(1)

    wrapper.unmount()
  })
})
