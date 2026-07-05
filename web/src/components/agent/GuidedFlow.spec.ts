import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// Stub the document store so step 1 (Add Evidence) status is deterministic
// without coupling to the real document-store API.
vi.mock('../../stores/documents', () => ({
  useDocumentStore: () => ({ selectedIds: ['doc-1'] }),
}))

import GuidedFlow from './GuidedFlow.vue'
import { useAgentStore } from '../../stores/agent'

/**
 * GuidedFlow spec (Sprint UX-1 Slice H, WEB-7) — ADVISORY.
 *
 * Asserts the four workflow steps render, that done/pending status tracks the
 * store state, and that clicking a step emits `select` with the step id.
 */
describe('GuidedFlow (UX-1 Slice H, WEB-7)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the four numbered workflow steps', () => {
    const wrapper = mount(GuidedFlow)
    const text = wrapper.text()
    expect(text).toContain('Add Evidence')
    expect(text).toContain('Add Portfolio')
    expect(text).toContain('Ask Question')
    expect(text).toContain('Review Memo')
    expect(wrapper.findAll('.gf-step')).toHaveLength(4)
    wrapper.unmount()
  })

  it('marks steps done as the relevant store state populates', () => {
    const agentStore = useAgentStore()
    agentStore.portfolioId = 'pf-1' // step 2 done; step 1 done via mocked documents
    const wrapper = mount(GuidedFlow)
    // Steps 1 (mocked docs) + 2 (portfolio) done; steps 3 (no run) + 4 (no memo) pending.
    expect(wrapper.findAll('.gf-done').length).toBe(2)
    expect(wrapper.findAll('.gf-pending').length).toBe(2)
    wrapper.unmount()
  })

  it('emits select with the step id when a step is clicked', async () => {
    const wrapper = mount(GuidedFlow)
    await wrapper.findAll('.gf-step-button')[2].trigger('click') // Ask Question
    expect(wrapper.emitted('select')).toEqual([['question']])
    wrapper.unmount()
  })
})
