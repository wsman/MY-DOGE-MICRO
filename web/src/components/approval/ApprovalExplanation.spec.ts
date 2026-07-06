import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ApprovalExplanation from './ApprovalExplanation.vue'

describe('ApprovalExplanation', () => {
  it('renders business explanation rows in stable order', () => {
    const wrapper = mount(ApprovalExplanation, {
      props: {
        approval: {
          why_needed: 'External publishing requires review.',
          impact: 'Memo becomes visible to the client.',
          deny_consequence: 'Memo remains internal.',
          publish_target: 'client portal',
        },
      },
    })

    expect(wrapper.findAll('.detail-row').map(row => row.text())).toEqual([
      'Why neededExternal publishing requires review.',
      'ImpactMemo becomes visible to the client.',
      'Deny consequenceMemo remains internal.',
      'Publish targetclient portal',
    ])
  })

  it('omits blank explanation rows', () => {
    const wrapper = mount(ApprovalExplanation, {
      props: {
        approval: {
          why_needed: '  ',
          impact: null,
          deny_consequence: '',
        },
      },
    })

    expect(wrapper.find('.approval-details').exists()).toBe(false)
    expect(wrapper.findAll('.detail-row')).toHaveLength(0)
  })

  it('appends policy rows when approval policy is provided', () => {
    const wrapper = mount(ApprovalExplanation, {
      props: {
        approval: {
          why_needed: 'External publishing requires review.',
        },
        policy: {
          publish: 'required',
          trade_action: 'optional',
        },
      },
    })

    expect(wrapper.findAll('.detail-row').map(row => row.text())).toEqual([
      'Why neededExternal publishing requires review.',
      'Policy · publishrequired',
      'Policy · trade_actionoptional',
    ])
  })
})
