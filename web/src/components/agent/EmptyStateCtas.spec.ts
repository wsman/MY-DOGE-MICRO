import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import EmptyStateCtas from './EmptyStateCtas.vue'

/**
 * EmptyStateCtas spec (Sprint UX-1 Slice F, WEB-3) — ADVISORY.
 *
 * Asserts the four getting-started CTAs render and that each emits its distinct
 * event on click (the parent wires these to startDemoRun / sample scenario /
 * scroll handlers).
 */
describe('EmptyStateCtas (UX-1 Slice F, WEB-3)', () => {
  it('renders the four getting-started CTAs', () => {
    const wrapper = mount(EmptyStateCtas)
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(4)
    const text = wrapper.text()
    expect(text).toContain('Run Demo')
    expect(text).toContain('Load Sample Case')
    expect(text).toContain('Upload Documents')
    expect(text).toContain('Import Portfolio')
    wrapper.unmount()
  })

  it('emits a distinct event when each CTA is clicked', async () => {
    const wrapper = mount(EmptyStateCtas)
    const [runDemo, loadSample, upload, importPortfolio] = wrapper.findAll('button')
    await runDemo.trigger('click')
    await loadSample.trigger('click')
    await upload.trigger('click')
    await importPortfolio.trigger('click')
    expect(wrapper.emitted('run-demo')).toHaveLength(1)
    expect(wrapper.emitted('load-sample')).toHaveLength(1)
    expect(wrapper.emitted('upload')).toHaveLength(1)
    expect(wrapper.emitted('import-portfolio')).toHaveLength(1)
    wrapper.unmount()
  })
})
