import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NSelect } from 'naive-ui'
import { beforeEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import ScenarioPicker from './ScenarioPicker.vue'
import { useAgentStore } from '../../stores/agent'

/**
 * ScenarioPicker spec (Sprint UX-1 Slice G, WEB-10) — ADVISORY.
 *
 * Asserts the picker renders the four shipped scenario templates, defaults both
 * the picker and the store to `investment_committee_memo`, and that selecting a
 * scenario writes through to the store's `selectedScenarioSlug` (which Slice I's
 * threading then carries to the persisted run).
 */
describe('ScenarioPicker (UX-1 Slice G, WEB-10)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the four shipped scenario templates', () => {
    const wrapper = mount(ScenarioPicker)
    // n-select renders option labels lazily (only when open), so assert on the
    // options prop the picker passes in, not the closed-dropdown DOM.
    const options = wrapper.findComponent(NSelect).props('options') as Array<{
      label: string
      value: string
    }>
    expect(options.map(o => o.label)).toEqual([
      'Market Morning Brief',
      'Earnings Quality Review',
      'Portfolio Risk Review',
      'Investment Committee Memo',
    ])
    expect(options.map(o => o.value)).toEqual([
      'daily_market_brief',
      'earnings_review',
      'portfolio_risk_review',
      'investment_committee_memo',
    ])
    wrapper.unmount()
  })

  it('defaults the picker and the store to investment_committee_memo', () => {
    const store = useAgentStore()
    expect(store.selectedScenarioSlug).toBe('investment_committee_memo')
    const wrapper = mount(ScenarioPicker)
    expect(wrapper.findComponent(NSelect).props('value')).toBe('investment_committee_memo')
    wrapper.unmount()
  })

  it('writes the selected scenario through to the store', async () => {
    const store = useAgentStore()
    const wrapper = mount(ScenarioPicker)
    await wrapper.findComponent(NSelect).vm.$emit('update:value', 'earnings_review')
    await nextTick()
    expect(store.selectedScenarioSlug).toBe('earnings_review')
    wrapper.unmount()
  })
})
