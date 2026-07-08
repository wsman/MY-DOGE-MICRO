import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AdminCenterView from './AdminCenterView.vue'

const storeMock = vi.hoisted(() => ({
  loading: false,
  error: null as { message: string } | null,
  capabilities: {
    snapshot_id: 'cap-1',
    generated_at: '2026-07-07T00:00:00Z',
    redaction_version: 'doge.capability_redaction.v1',
    status_counts: { available: 1 },
    capabilities: [{
      capability_id: 'feature.slot_platform',
      kind: 'feature',
      name: 'Slot Platform',
      status: 'available',
      risk_level: 'medium',
      requires_approval: false,
      metadata: {},
    }],
  },
  slotRows: [] as ReturnType<typeof slotRow>[],
  slotBundles: [] as ReturnType<typeof slotBundle>[],
  loadCapabilities: vi.fn(async () => undefined),
  loadSlots: vi.fn(async () => undefined),
  loadSlotBundles: vi.fn(async () => undefined),
  activateSlotBundle: vi.fn(async (_bundleId: string) => undefined),
  deactivateSlotBundle: vi.fn(async () => undefined),
}))

vi.mock('../stores/platform', () => ({
  usePlatformStore: () => storeMock,
}))

describe('AdminCenterView', () => {
  beforeEach(() => {
    storeMock.loading = false
    storeMock.error = null
    storeMock.slotRows = [
      slotRow('market.core', { name: 'Market Core', type: 'tool', status: 'resolved' }),
      slotRow('ui.research_workspace', {
        name: 'Research Workspace UI',
        type: 'ui',
        status: 'disabled',
        health: 'degraded',
        risk: 'high',
      }),
    ]
    storeMock.slotBundles = [
      slotBundle('bundle.research_workspace', { status: 'partial', enabled: 1, disabled: 1 }),
      slotBundle('bundle.local_analyst', { active: true, enabled: 2 }),
    ]
    storeMock.loadCapabilities.mockClear()
    storeMock.loadSlots.mockClear()
    storeMock.loadSlotBundles.mockClear()
    storeMock.activateSlotBundle.mockClear()
    storeMock.deactivateSlotBundle.mockClear()
  })

  it('renders slot center summaries, slots, bundles, and capabilities', async () => {
    const wrapper = mount(AdminCenterView)
    await flushPromises()

    expect(storeMock.loadCapabilities).toHaveBeenCalledTimes(1)
    expect(storeMock.loadSlots).toHaveBeenCalledTimes(1)
    expect(storeMock.loadSlotBundles).toHaveBeenCalledTimes(1)

    const text = wrapper.text()
    expect(text).toContain('Capability / Slot Center')
    expect(text).toContain('Slot Center')
    expect(text).toContain('1/2 enabled')
    expect(text).toContain('Installed2')
    expect(text).toContain('Enabled1')
    expect(text).toContain('Disabled1')
    expect(text).toContain('Degraded1')
    expect(text).toContain('High risk1')
    expect(text).toContain('Market Core')
    expect(text).toContain('market.core')
    expect(text).toContain('Research Workspace UI')
    expect(text).toContain('ui.research_workspace')
    expect(text).toContain('Research Workspace')
    expect(text).toContain('bundle.research_workspace')
    expect(text).toContain('bundle.local_analyst')
    expect(text).toContain('active')
    expect(text).toContain('Activate')
    expect(text).toContain('Deactivate')
    expect(text).toContain('Capability Registry')
    expect(text).toContain('Slot Platform')
  })

  it('activates and deactivates slot bundles from row controls', async () => {
    const wrapper = mount(AdminCenterView)
    await flushPromises()

    await buttonByText(wrapper, 'Activate').trigger('click')
    await flushPromises()
    await buttonByText(wrapper, 'Deactivate').trigger('click')
    await flushPromises()

    expect(storeMock.activateSlotBundle).toHaveBeenCalledWith('bundle.research_workspace')
    expect(storeMock.deactivateSlotBundle).toHaveBeenCalledWith()
  })

  it('surfaces slot bundle permission errors through the generic alert', async () => {
    storeMock.error = { message: 'slot_bundle access denied' }

    const wrapper = mount(AdminCenterView)
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toContain('slot_bundle access denied')
  })
})

function slotRow(
  id: string,
  overrides: Partial<{
    name: string
    type: string
    status: string
    health: string
    risk: string
  }> = {},
) {
  return {
    id,
    name: overrides.name ?? 'Market Core',
    version: '0.1.0',
    type: overrides.type ?? 'tool',
    owner: 'platform',
    maturity: 'alpha',
    description: 'Slot row',
    entrypoint: 'doge.platform.slot.ExampleSlot',
    status: overrides.status ?? 'resolved',
    feature_flags: ['slot_platform'],
    provides: {
      tools: ['query_stock'],
      capabilities: ['market.read'],
      metadata: {},
    },
    requires: [],
    permissions: {
      filesystem: 'none',
      network: 'none',
      shell: 'none',
      database: 'none',
      secrets: [],
      risk_level: overrides.risk ?? 'low',
    },
    health: {
      status: overrides.health ?? 'experimental',
      notes: '',
    },
    compatibility: {
      runtime_min: '1',
      replaces: [],
      breaking: false,
    },
    counts: {
      tools: 1,
      capabilities: 1,
    },
  }
}

function slotBundle(
  id: string,
  overrides: Partial<{
    active: boolean
    status: string
    enabled: number
    disabled: number
    missing: number
  }> = {},
) {
  const enabled = overrides.enabled ?? 1
  const disabled = overrides.disabled ?? 0
  const missing = overrides.missing ?? 0
  return {
    id,
    name: 'Research Workspace',
    description: 'Research workspace bundle',
    active: overrides.active ?? false,
    status: overrides.status ?? 'resolved',
    slot_ids: ['market.core', 'ui.research_workspace'],
    enabled_slot_ids: Array.from({ length: enabled }, (_, index) => `enabled.${index}`),
    disabled_slot_ids: Array.from({ length: disabled }, (_, index) => `disabled.${index}`),
    missing_slot_ids: Array.from({ length: missing }, (_, index) => `missing.${index}`),
    maturity: 'experimental',
    counts: {
      slots: enabled + disabled + missing,
      enabled,
      disabled,
      missing,
    },
  }
}

function buttonByText(wrapper: ReturnType<typeof mount>, label: string) {
  const button = wrapper.findAll('button').find(item => (
    item.text().includes(label) && item.attributes('disabled') === undefined
  ))
  if (!button) {
    throw new Error(`button not found: ${label}`)
  }
  return button
}
