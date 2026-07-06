import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const selectedDocumentIds = vi.hoisted(() => ['doc-1'] as string[])

// Stub the document store so step 1 (Add Evidence) status is deterministic
// without coupling to the real document-store API.
vi.mock('../../stores/documents', () => ({
  useDocumentStore: () => ({ selectedIds: selectedDocumentIds }),
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
    selectedDocumentIds.splice(0, selectedDocumentIds.length, 'doc-1')
    setActivePinia(createPinia())
  })

  it('renders the four numbered workflow steps', () => {
    const wrapper = mount(GuidedFlow)
    const text = wrapper.text()
    expect(text).toContain('Add Evidence')
    expect(text).toContain('Add Portfolio')
    expect(text).toContain('Ask Question')
    expect(text).toContain('Review Memo')
    expect(text).toContain('Optional')
    expect(text).toContain('Ready to run')
    expect(wrapper.findAll('.gf-step')).toHaveLength(4)
    wrapper.unmount()
  })

  it('marks done, pending, missing, and running states from existing store state', async () => {
    const agentStore = useAgentStore()
    agentStore.portfolioId = 'pf-1' // step 2 done; step 1 done via mocked documents
    const wrapper = mount(GuidedFlow)
    // Steps 1 (mocked docs) + 2 (portfolio) done; steps 3 (no run) + 4 (no memo) pending.
    expect(wrapper.findAll('.gf-done').length).toBe(2)
    expect(wrapper.findAll('.gf-pending').length).toBe(2)

    agentStore.run = {
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
      status: 'running',
      events: [],
      artifacts: [],
      approvals: [],
      cancel_requested_at: null,
      schema_version: '1.0',
      created_at: 'now',
      updated_at: 'now',
    }
    await nextTick()

    expect(wrapper.findAll('.gf-running').length).toBe(1)
    wrapper.unmount()
  })

  it('marks missing evidence only after a run exists without selected documents', async () => {
    selectedDocumentIds.splice(0)
    const agentStore = useAgentStore()
    agentStore.run = {
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
      status: 'running',
      events: [],
      artifacts: [],
      approvals: [],
      cancel_requested_at: null,
      schema_version: '1.0',
      created_at: 'now',
      updated_at: 'now',
    }

    const wrapper = mount(GuidedFlow)
    await nextTick()

    expect(wrapper.findAll('.gf-missing')).toHaveLength(1)
    expect(wrapper.text()).toContain('Missing input')
    wrapper.unmount()
  })

  it('emits select with the step id when a step is clicked', async () => {
    const wrapper = mount(GuidedFlow)
    await wrapper.findAll('.gf-step-button')[2].trigger('click') // Ask Question
    expect(wrapper.emitted('select')).toEqual([['question']])
    wrapper.unmount()
  })
})
