import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

/**
 * StatusView spec (S003-009).
 *
 * StatusView is a pure presentational component — no Pinia, no network, no
 * composables — so we mount it directly with @vue/test-utils and assert which
 * Naive UI primitive each status renders, that the default slot is gated on
 * `idle` only, and that the a11y attributes (role="alert", aria-live,
 * aria-busy) are present on the right wrappers. Mount/style mirrors
 * composables/useSSE.spec.ts and stores/scanner.spec.ts: jsdom + globals,
 * vi.fn for the retry callback.
 *
 * Does NOT import @pretext — safe under jsdom (vitest.config.ts alias).
 *
 * Naive UI components render real DOM under jsdom, so we assert on the
 * rendered class names n-skeleton / n-spin / n-empty / n-result rather than
 * stubbing them. This catches regressions if the template's primitive choice
 * drifts (e.g. someone swaps n-skeleton for n-spin by default).
 */

import StatusView from './StatusView.vue'

/**
 * Props the test drives. `status` is required by StatusView; the rest are
 * optional and defaulted by the SFC. Typed loosely enough that each test
 * passes only the props it cares about, but narrowly enough that vue-tsc sees
 * `status` is always satisfied.
 */
type StatusViewProps = {
  status: 'idle' | 'loading' | 'empty' | 'error'
  emptyDescription?: string
  error?: { code: string; message: string } | null
  onRetry?: () => void
  skeletonRows?: number
}

/**
 * Convenience mount. StatusView has no required globals (no config-provided
 * components), so a bare mount suffices — Naive UI primitives are imported
 * directly by the SFC.
 */
function mountStatus(props: StatusViewProps, slotContent = '') {
  return mount(StatusView, {
    props,
    slots: { default: slotContent },
  })
}

describe('StatusView', () => {
  it('loading + skeletonRows=3 renders n-skeleton rows', () => {
    const wrapper = mountStatus({ status: 'loading', skeletonRows: 3 })
    // n-skeleton leaves an .n-skeleton element per row.
    const skeletons = wrapper.findAll('.n-skeleton')
    expect(skeletons.length).toBe(3)
    // No spinner and no slot content in the loading state.
    expect(wrapper.find('.n-spin').exists()).toBe(false)
    expect(wrapper.text()).toBe('')
    wrapper.unmount()
  })

  it('loading + skeletonRows=0 renders n-spin instead of n-skeleton', () => {
    const wrapper = mountStatus({ status: 'loading', skeletonRows: 0 })
    expect(wrapper.find('.n-spin').exists()).toBe(true)
    // Zero skeleton rows when the caller asked for a spinner.
    expect(wrapper.findAll('.n-skeleton').length).toBe(0)
    wrapper.unmount()
  })

  it('empty renders n-empty with the provided description', () => {
    const wrapper = mountStatus({ status: 'empty', emptyDescription: 'No reports' })
    const empty = wrapper.find('.n-empty')
    expect(empty.exists()).toBe(true)
    // n-empty surfaces the description as text inside its description node.
    expect(wrapper.text()).toContain('No reports')
    wrapper.unmount()
  })

  it('error + onRetry renders n-result with the error message and a Retry button that calls onRetry', async () => {
    const onRetry = vi.fn()
    const wrapper = mountStatus({
      status: 'error',
      error: { code: 'http_500', message: 'db down' },
      onRetry,
    })

    const result = wrapper.find('.n-result')
    expect(result.exists()).toBe(true)
    // The error.message surfaces as the n-result title.
    expect(wrapper.text()).toContain('db down')

    // Retry button is rendered only because onRetry was provided.
    const retryButton = wrapper.find('button')
    expect(retryButton.exists()).toBe(true)
    expect(retryButton.text()).toContain('Retry')

    await retryButton.trigger('click')
    expect(onRetry).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('idle renders the default slot, and non-idle states do NOT render the slot', () => {
    // idle -> slot is yielded.
    const idleWrapper = mountStatus({ status: 'idle' }, 'REAL CONTENT')
    expect(idleWrapper.text()).toContain('REAL CONTENT')
    idleWrapper.unmount()

    // loading -> slot is suppressed (skeleton replaces it).
    const loadingWrapper = mountStatus({ status: 'loading' }, 'REAL CONTENT')
    expect(loadingWrapper.text()).not.toContain('REAL CONTENT')
    loadingWrapper.unmount()

    // empty -> slot is suppressed.
    const emptyWrapper = mountStatus({ status: 'empty' }, 'REAL CONTENT')
    expect(emptyWrapper.text()).not.toContain('REAL CONTENT')
    emptyWrapper.unmount()

    // error -> slot is suppressed.
    const errorWrapper = mountStatus(
      { status: 'error', error: { code: 'http_500', message: 'boom' } },
      'REAL CONTENT',
    )
    expect(errorWrapper.text()).not.toContain('REAL CONTENT')
    errorWrapper.unmount()
  })

  it('exposes role="alert" + aria-live="assertive" on the error wrapper and aria-busy="true" on the loading wrapper', () => {
    // Error wrapper: assertive alert so screen readers announce failures.
    const errorWrapper = mountStatus({
      status: 'error',
      error: { code: 'http_500', message: 'db down' },
    })
    const errorRoot = errorWrapper.find('.sv-error')
    expect(errorRoot.exists()).toBe(true)
    expect(errorRoot.attributes('role')).toBe('alert')
    expect(errorRoot.attributes('aria-live')).toBe('assertive')
    errorWrapper.unmount()

    // Loading wrapper: politely announced busy region.
    const loadingWrapper = mountStatus({ status: 'loading', skeletonRows: 2 })
    const loadingRoot = loadingWrapper.find('.sv-loading')
    expect(loadingRoot.exists()).toBe(true)
    expect(loadingRoot.attributes('aria-busy')).toBe('true')
    expect(loadingRoot.attributes('aria-live')).toBe('polite')
    loadingWrapper.unmount()
  })
})
