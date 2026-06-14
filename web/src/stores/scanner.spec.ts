import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

/**
 * scanner store spec (TR-036-mandated location — tr-registry.yaml:483).
 *
 * The store wraps `useSSE`. Rather than mock global fetch, we mock the
 * `useSSE` composable so each `start(url, body, opts)` call exposes its opts
 * callbacks to the test via a captured handle. This lets us deterministically
 * drive the onComplete / onError transitions (including the watchdog's
 * terminal-error path) and assert the store reacts correctly.
 *
 * Does NOT import @pretext — safe under jsdom (vitest.config.ts alias).
 */

/**
 * Hoisted test handles shared between the vi.mock factory and the test body.
 * `vi.hoisted` runs before the (hoisted) vi.mock factory, so the factory can
 * safely reference these. `lastOpts` captures the most-recent SSEOptions
 * passed to `start(...)`; `startMock` is the vi.fn backing the mocked `start`
 * so tests can assert call counts.
 */
const { lastOptsBox, startMock } = vi.hoisted(() => ({
  lastOptsBox: { current: null as any },
  startMock: vi.fn(),
}))

// Mock useSSE. The refs returned are shared so the store reads the same
// reactive state the test can mutate.
vi.mock('../composables/useSSE', () => {
  const shared = {
    progress: ref(0),
    messages: ref<string[]>([]),
    isRunning: ref(false),
    error: ref<{ code: string; message: string } | null>(null),
    status: ref<'idle' | 'running' | 'error' | 'complete'>('idle'),
  }
  // The hoisted startMock captures opts into lastOptsBox and flips isRunning.
  startMock.mockImplementation(async (_url: string, _body: object, opts: any) => {
    lastOptsBox.current = opts
    shared.isRunning.value = true
    shared.status.value = 'running'
  })
  return {
    useSSE: () => ({ ...shared, start: startMock }),
  }
})

// Stub api/config so fetchServers/testServers never hit the network.
vi.mock('../api/config', () => ({
  getServers: vi.fn().mockResolvedValue({ cn: [], us: [] }),
  testServers: vi.fn().mockResolvedValue({ results: [] }),
}))

import { useScannerStore } from './scanner'

beforeEach(() => {
  setActivePinia(createPinia())
  lastOptsBox.current = null
  startMock.mockClear()
})

describe('useScannerStore', () => {
  describe('scanCn lifecycle', () => {
    it('transitions cnStatus idle -> running -> idle on completion', async () => {
      const store = useScannerStore()
      expect(store.cnStatus).toBe('idle')

      const p = store.scanCn()
      // While the (mocked) start is in flight, status is running.
      expect(store.cnStatus).toBe('running')

      lastOptsBox.current.onComplete()
      await p

      expect(store.cnStatus).toBe('idle')
    })

    it('sets cnStatus to "error" (NOT "idle") on terminal stream error', async () => {
      // Regression for the bug where a dropped stream silently reset to 'idle'.
      const store = useScannerStore()
      const p = store.scanCn()
      expect(store.cnStatus).toBe('running')

      lastOptsBox.current.onError({ code: 'stream_stalled', message: 'live data stream stalled' })
      await p

      expect(store.cnStatus).toBe('error')
    })

    it('Retry after error transitions error -> running -> idle on success', async () => {
      const store = useScannerStore()
      // First scan fails terminally.
      const p1 = store.scanCn()
      lastOptsBox.current.onError({ code: 'stream_stalled', message: 'stalled' })
      await p1
      expect(store.cnStatus).toBe('error')

      // Explicit Retry (operator clicks Retry).
      const p2 = store.scanCn()
      expect(store.cnStatus).toBe('running')
      lastOptsBox.current.onComplete()
      await p2
      expect(store.cnStatus).toBe('idle')
    })
  })

  describe('auto-scan timer teardown on terminal error', () => {
    it('clears the CN auto-scan interval when a terminal error occurs', async () => {
      vi.useFakeTimers()
      const store = useScannerStore()

      // Enable CN auto-scan on a 1-minute interval and start a manual scan.
      store.toggleAutoScan('cn', true)
      store.setInterval_('cn', 1)
      // startAutoScan scheduled a setInterval; verify the store reports auto on.
      expect(store.cnAutoEnabled).toBe(true)

      const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval')

      const p = store.scanCn()
      lastOptsBox.current.onError({ code: 'stream_stalled', message: 'stalled' })
      await p

      expect(store.cnStatus).toBe('error')
      // A terminal error MUST have cleared the auto-scan timer so the next
      // tick doesn't silently restart into another stuck stream.
      expect(clearIntervalSpy).toHaveBeenCalled()

      // Advance past the full interval — no auto-restart should occur. If the
      // timer had survived, scanCn would have been called again (re-mocking
      // isRunning on); assert cnStatus stays 'error'.
      vi.advanceTimersByTime(60 * 1000 + 1)
      expect(store.cnStatus).toBe('error')

      clearIntervalSpy.mockRestore()
      vi.useRealTimers()
    })
  })

  describe('scanUs lifecycle (mirrors CN)', () => {
    it('transitions usStatus idle -> running -> idle on completion', async () => {
      const store = useScannerStore()
      const p = store.scanUs()
      expect(store.usStatus).toBe('running')
      lastOptsBox.current.onComplete()
      await p
      expect(store.usStatus).toBe('idle')
    })

    it('sets usStatus to "error" on terminal stream error', async () => {
      const store = useScannerStore()
      const p = store.scanUs()
      lastOptsBox.current.onError({ code: 'stream_stalled', message: 'stalled' })
      await p
      expect(store.usStatus).toBe('error')
    })
  })
})
