import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import MaturityPanel from './MaturityPanel.vue'
import { usePlatformStore } from '../../stores/platform'

/**
 * MaturityPanel spec (Sprint UX-1 Slice E, WEB-8) — ADVISORY.
 *
 * Asserts the honest Local-Alpha disclosure: Runtime Level label, the
 * live-or-scripted provider line derived from the capability snapshot, the four
 * open production-readiness gate IDs, and — critically — that no
 * "production-ready" / "stable" / "GA" promotion language appears in the DOM.
 *
 * The platform store is seeded directly and its `loadCapabilities` is spied to
 * a no-op so the panel renders the seeded snapshot without a real fetch.
 */
describe('MaturityPanel (UX-1 Slice E, WEB-8)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function seed(caps: unknown) {
    const store = usePlatformStore()
    store.capabilities = caps as never
    vi.spyOn(store, 'loadCapabilities').mockResolvedValue(store.capabilities)
  }

  it('renders Local Alpha, a live provider line, and the 4 open gates', () => {
    seed({
      snapshot_id: 'cap-test',
      generated_at: 'now',
      redaction_version: 'doge.capability_redaction.v1',
      status_counts: {},
      capabilities: [
        {
          capability_id: 'provider.kimi',
          kind: 'model_provider',
          name: 'Kimi / Moonshot',
          status: 'available',
          risk_level: 'medium',
          requires_approval: false,
          metadata: { configured: true },
        },
      ],
    })
    const wrapper = mount(MaturityPanel)
    const text = wrapper.text()
    expect(text).toContain('Local Alpha')
    expect(text).toContain('Kimi / Moonshot (live)')
    expect(text).toContain('4 open')
    for (const id of ['S017-003', 'W3-live', 'AUTH-prod', 'S017-007']) {
      expect(text).toContain(id)
    }
    wrapper.unmount()
  })

  it('uses the scripted-fallback provider line when no provider is available', () => {
    seed({
      snapshot_id: 'cap-test',
      generated_at: 'now',
      redaction_version: 'doge.capability_redaction.v1',
      status_counts: {},
      capabilities: [],
    })
    const wrapper = mount(MaturityPanel)
    expect(wrapper.text()).toContain('scripted fallback (local_demo)')
    wrapper.unmount()
  })

  it('shows "unknown" provider and still labels Local Alpha when the snapshot is absent', () => {
    seed(null)
    const wrapper = mount(MaturityPanel)
    const text = wrapper.text()
    expect(text).toContain('unknown')
    expect(text).toContain('Local Alpha')
    wrapper.unmount()
  })

  it('never emits production-ready / stable / GA promotion language', () => {
    seed({
      snapshot_id: 'cap-test',
      generated_at: 'now',
      redaction_version: 'doge.capability_redaction.v1',
      status_counts: {},
      capabilities: [],
    })
    const wrapper = mount(MaturityPanel)
    const text = wrapper.text()
    // "not production ready" (space, with \bnot\b) is allowed; the hyphenated
    // promotion form "production-ready" is what must not appear.
    expect(text).not.toContain('production-ready')
    expect(text).not.toContain('stable')
    expect(text).not.toContain('GA')
    wrapper.unmount()
  })
})
