import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import FirstRunGuide from './FirstRunGuide.vue'
import { useAgentStore } from '../../stores/agent'

describe('FirstRunGuide', () => {
  beforeEach(() => {
    window.localStorage.clear()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    document.body.innerHTML = ''
    window.localStorage.clear()
  })

  it('shows for a first empty research workspace and persists dismissal', async () => {
    const wrapper = mount(FirstRunGuide, {
      attachTo: document.body,
      global: { stubs: { teleport: true } },
    })

    expect(document.body.textContent).toContain('Start Research')
    await wrapper.find('button').trigger('click')
    await nextTick()

    expect(window.localStorage.getItem('doge.firstRunSeen')).toBe('1')
    expect(document.body.textContent).not.toContain('Start Research')
    wrapper.unmount()
  })

  it('stays hidden when a run already exists', () => {
    const store = useAgentStore()
    store.run = {
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

    mount(FirstRunGuide, {
      attachTo: document.body,
      global: { stubs: { teleport: true } },
    })

    expect(document.body.textContent).not.toContain('Start Research')
  })
})
