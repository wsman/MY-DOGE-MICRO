import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import CaseApprovalPanel from './CaseApprovalPanel.vue'

describe('CaseApprovalPanel', () => {
  it('renders approval explanation rows and emits run navigation', async () => {
    const wrapper = mount(CaseApprovalPanel, {
      props: {
        approvals: [
          {
            approval_id: 'appr-1',
            risk_level: 'high',
            status: 'pending',
            action: 'publish memo',
            run_id: 'run-1',
            why_needed: 'External publishing requires review.',
            impact: 'Memo becomes visible to the client.',
          },
        ],
      },
    })

    expect(wrapper.text()).toContain('Approval')
    expect(wrapper.text()).toContain('publish memo')
    expect(wrapper.findAll('.detail-row').map(row => row.text())).toEqual([
      'Why neededExternal publishing requires review.',
      'ImpactMemo becomes visible to the client.',
    ])

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('openRun')).toEqual([['run-1']])
  })

  it('renders an empty state when there are no approvals', () => {
    const wrapper = mount(CaseApprovalPanel, {
      props: { approvals: [] },
    })

    expect(wrapper.text()).toContain('No approvals pending')
  })

  it('renders approval policy rows for matching run ids', () => {
    const wrapper = mount(CaseApprovalPanel, {
      props: {
        approvals: [
          {
            approval_id: 'appr-1',
            risk_level: 'high',
            status: 'pending',
            action: 'publish memo',
            run_id: 'run-1',
            why_needed: 'External publishing requires review.',
          },
        ],
        policyByRunId: {
          'run-1': {
            publish: 'required',
          },
        },
      },
    })

    expect(wrapper.findAll('.detail-row').map(row => row.text())).toEqual([
      'Why neededExternal publishing requires review.',
      'Policy · publishrequired',
    ])
  })
})
