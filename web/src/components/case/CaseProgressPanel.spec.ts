import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CaseProgressPanel from './CaseProgressPanel.vue'

describe('CaseProgressPanel', () => {
  it('renders governance progress steps with blocking context', () => {
    const wrapper = mount(CaseProgressPanel, {
      props: {
        steps: [{
          progress_id: 'cps-1',
          case_id: 'case-1',
          step_key: 'workflow',
          label: 'Workflow',
          status: 'blocked',
          owner: 'research-agent',
          timestamp: '2026-07-05T00:00:00Z',
          blocking_issue: 'Execution failed preflight.',
          next_action: 'Fix missing assets.',
          source_type: 'execution',
          source_id: 'exec-1',
          tenant_id: null,
          metadata: {},
        }],
      },
    })

    expect(wrapper.text()).toContain('Progress')
    expect(wrapper.text()).toContain('Workflow')
    expect(wrapper.text()).toContain('research-agent')
    expect(wrapper.text()).toContain('Blocked')
    expect(wrapper.text()).toContain('Execution failed preflight.')
  })
})
