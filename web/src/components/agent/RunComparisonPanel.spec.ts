import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import RunComparisonPanel from './RunComparisonPanel.vue'
import { listAgentRuns } from '../../api/agent'

vi.mock('../../api/agent', () => ({
  listAgentRuns: vi.fn(),
}))

describe('RunComparisonPanel', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders compact recent run comparison rows', async () => {
    vi.mocked(listAgentRuns).mockResolvedValue([
      {
        run_id: 'run-current-123456',
        workflow: 'investment_research',
        question: 'Analyze',
        session_id: 'ses-1',
        market: 'us',
        language: 'en',
        portfolio_id: null,
        status: 'completed',
        event_count: 4,
        artifact_count: 1,
        approval_count: 0,
        created_at: 'now',
        updated_at: 'now',
      },
    ])

    const wrapper = mount(RunComparisonPanel, {
      props: { currentRunId: 'run-current-123456' },
    })
    await flushPromises()

    expect(listAgentRuns).toHaveBeenCalledWith(8)
    expect(wrapper.text()).toContain('Run Comparison')
    expect(wrapper.text()).toContain('Completed')
    expect(wrapper.text()).toContain('investment_research')
    expect(wrapper.text()).toContain('1 artifacts')
    expect(wrapper.find('.comparison-row.current').exists()).toBe(true)
  })
})
