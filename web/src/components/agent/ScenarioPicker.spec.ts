import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NSelect } from 'naive-ui'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import ScenarioPicker from './ScenarioPicker.vue'
import { useAgentStore } from '../../stores/agent'
import { usePlatformStore } from '../../stores/platform'

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

  it('renders workflow templates from the platform store', () => {
    const platformStore = usePlatformStore()
    platformStore.workflowTemplates = [
      workflowTemplate('tpl-company', 'company_deep_dive', 'Company Deep Dive'),
      workflowTemplate('tpl-industry', 'industry_research', 'Industry Research'),
      workflowTemplate('tpl-quant', 'quant_experiment', 'Quant Experiment'),
      workflowTemplate('tpl-publication', 'publication_review', 'Publication Review'),
    ]
    const load = vi.spyOn(platformStore, 'loadWorkflowTemplates').mockResolvedValue(platformStore.workflowTemplates)

    const wrapper = mount(ScenarioPicker)
    const options = wrapper.findComponent(NSelect).props('options') as Array<{
      label: string
      value: string
    }>
    expect(options.map(o => o.label)).toEqual([
      'Company Deep Dive',
      'Industry Research',
      'Quant Experiment',
      'Publication Review',
    ])
    expect(options.map(o => o.value)).toEqual([
      'company_deep_dive',
      'industry_research',
      'quant_experiment',
      'publication_review',
    ])
    expect(load).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('falls back to the four shipped scenario templates when the store is empty', () => {
    const platformStore = usePlatformStore()
    vi.spyOn(platformStore, 'loadWorkflowTemplates').mockResolvedValue([])

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

  it('falls back when workflow template loading is unavailable', async () => {
    const platformStore = usePlatformStore()
    const load = vi.spyOn(platformStore, 'loadWorkflowTemplates').mockRejectedValue(new Error('disabled'))

    const wrapper = mount(ScenarioPicker)
    await Promise.resolve()
    await nextTick()

    const options = wrapper.findComponent(NSelect).props('options') as Array<{
      label: string
      value: string
    }>
    expect(load).toHaveBeenCalled()
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

function workflowTemplate(templateId: string, slug: string, name: string) {
  return {
    template_id: templateId,
    slug,
    name,
    description: '',
    status: 'active',
    current_version: '1',
    input_schema: {},
    run_instructions: '',
    tool_policy: {},
    evidence_policy: {},
    output_contract: {},
    tenant_id: null,
    metadata: {},
    created_at: '2026-07-05T00:00:00Z',
    updated_at: '2026-07-05T00:00:00Z',
  }
}
