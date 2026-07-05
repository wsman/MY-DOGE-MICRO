import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import RunPreflightChecklist from './RunPreflightChecklist.vue'
import { useAgentStore } from '../../stores/agent'
import { useDocumentStore } from '../../stores/documents'
import { usePlatformStore } from '../../stores/platform'

describe('RunPreflightChecklist', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders warnings for optional missing inputs and unknown provider state', () => {
    const platformStore = usePlatformStore()
    vi.spyOn(platformStore, 'loadCapabilities').mockResolvedValue({
      snapshot_id: 'cap-empty',
      generated_at: '2026-07-05T00:00:00Z',
      redaction_version: 'doge.capability_redaction.v1',
      status_counts: {},
      capabilities: [],
    })

    const wrapper = mount(RunPreflightChecklist)

    expect(wrapper.text()).toContain('US selected')
    expect(wrapper.text()).toContain('No document selected')
    expect(wrapper.text()).toContain('No portfolio imported')
    expect(wrapper.text()).toContain('Provider status unknown')
    expect(wrapper.findAll('.is-warn')).toHaveLength(3)
    expect(wrapper.findAll('.is-ok')).toHaveLength(1)
    wrapper.unmount()
  })

  it('renders OK states from selected documents, portfolio, and Kimi capability metadata', () => {
    const agentStore = useAgentStore()
    const documentStore = useDocumentStore()
    const platformStore = usePlatformStore()

    agentStore.market = 'cn'
    agentStore.setPortfolioId('portfolio-1')
    documentStore.selectedIds = ['doc-1', 'doc-2']
    platformStore.capabilities = {
      snapshot_id: 'cap-1',
      generated_at: '2026-07-05T00:00:00Z',
      redaction_version: 'doge.capability_redaction.v1',
      status_counts: { available: 1 },
      capabilities: [{
        capability_id: 'provider.kimi',
        kind: 'provider',
        name: 'Kimi / Moonshot',
        status: 'available',
        risk_level: 'medium',
        requires_approval: false,
        metadata: { configured: true },
      }],
    }
    const load = vi.spyOn(platformStore, 'loadCapabilities').mockResolvedValue(platformStore.capabilities)

    const wrapper = mount(RunPreflightChecklist)

    expect(wrapper.text()).toContain('CN selected')
    expect(wrapper.text()).toContain('2 documents selected')
    expect(wrapper.text()).toContain('Portfolio portfolio-1 imported')
    expect(wrapper.text()).toContain('Kimi key configured')
    expect(wrapper.findAll('.is-ok')).toHaveLength(4)
    expect(load).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
