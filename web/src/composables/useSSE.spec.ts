import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useSSE } from './useSSE'

/**
 * useSSE composable spec (TR-036 / S002-010).
 *
 * The composable reads SSE over raw `fetch` (NOT EventSource — see
 * docs/architecture/adr-0008-web-architecture.md Decision 5). We mock global
 * `fetch` to return a controllable ReadableStream and feed it `data: {...}\n\n`
 * chunks. Watchdog behavior is exercised with `vi.useFakeTimers` and a short
 * `stallTimeoutMs` so tests don't block for 30s.
 *
 * Does NOT import @pretext — safe under jsdom (vitest.config.ts alias).
 */

/** Encode a string to Uint8Array (TextEncoder is available in jsdom). */
function enc(s: string): Uint8Array {
  return new TextEncoder().encode(s)
}

/**
 * A handle the test uses to drive a mocked SSE stream. `enqueue` feeds a
 * chunk, `close` ends the stream, `error` fails it.
 */
interface StreamHandle {
  enqueue: (chunk: Uint8Array) => void
  close: () => void
  error: (e: unknown) => void
}

/**
 * Build a mock fetch Response whose `body` is a ReadableStream fed from a
 * controller. Returns the Response (to pass to mockResolvedValue) and a handle
 * whose enqueue/close/error the test drives to simulate server-sent chunks.
 */
function makeStreamResponse(): { response: Response; handle: StreamHandle } {
  let controller: ReadableStreamDefaultController<Uint8Array> | null = null
  const body = new ReadableStream<Uint8Array>({
    start(c) {
      controller = c
    },
  })
  const handle: StreamHandle = {
    enqueue: (chunk) => controller?.enqueue(chunk),
    close: () => controller?.close(),
    error: (e) => controller?.error(e),
  }
  const response = new Response(body, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  })
  return { response, handle }
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('useSSE', () => {
  it('consumes data lines and updates progress + messages', async () => {
    const { response, handle } = makeStreamResponse()
    vi.mocked(fetch).mockResolvedValue(response)

    const { progress, messages, start } = useSSE()
    const onProgress = vi.fn()

    const promise = start('/api/scan/cn', {}, { onProgress })
    // Feed a progress event then close the stream.
    handle.enqueue(enc('data: {"progress":50,"message":"scanning"}\n\n'))
    await Promise.resolve()
    handle.close()
    await promise

    expect(progress.value).toBe(50)
    expect(messages.value).toEqual(['scanning'])
    expect(onProgress).toHaveBeenCalledWith(50, 'scanning')
  })

  it('calls onComplete and sets isRunning false on progress >= 100', async () => {
    const { response, handle } = makeStreamResponse()
    vi.mocked(fetch).mockResolvedValue(response)

    const { isRunning, status, start } = useSSE()
    const onComplete = vi.fn()

    const promise = start('/api/scan/cn', {}, { onComplete })
    handle.enqueue(enc('data: {"progress":100,"message":"done"}\n\n'))
    await Promise.resolve()
    await promise

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(isRunning.value).toBe(false)
    expect(status.value).toBe('complete')
  })

  it('progress === -1 sets error and calls onError with structured object', async () => {
    const { response, handle } = makeStreamResponse()
    vi.mocked(fetch).mockResolvedValue(response)

    const { error, status, isRunning, start } = useSSE()
    const onError = vi.fn()

    const promise = start('/api/scan/cn', {}, { onError })
    handle.enqueue(enc('data: {"progress":-1,"message":"duckdb refresh failed"}\n\n'))
    await Promise.resolve()
    await promise

    expect(error.value).not.toBeNull()
    expect(error.value).toMatchObject({ message: 'duckdb refresh failed' })
    expect(typeof error.value?.code).toBe('string')
    expect(status.value).toBe('error')
    expect(isRunning.value).toBe(false)
    expect(onError).toHaveBeenCalledTimes(1)
    // onError receives the structured {code,message} object, not a bare string.
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'duckdb refresh failed' }),
    )
  })

  it('watchdog trips after stallTimeoutMs of no data -> terminal error (not stuck running)', async () => {
    vi.useFakeTimers()
    const { response } = makeStreamResponse()
    vi.mocked(fetch).mockResolvedValue(response)

    const { isRunning, status, error, start } = useSSE()
    const onError = vi.fn()

    // Start a scan that NEVER emits data, with a 5s watchdog.
    const promise = start('/api/scan/cn', {}, { onError, stallTimeoutMs: 5000 })

    // Let microtasks flush so fetch resolves and the reader loop begins.
    await vi.advanceTimersByTimeAsync(0)
    expect(isRunning.value).toBe(true)

    // Advance past the threshold — watchdog should trip.
    await vi.advanceTimersByTimeAsync(5001)

    // The reader.cancel() inside surfaceTerminalError rejects the pending
    // read(); settle the promise.
    await promise

    expect(status.value).toBe('error')
    expect(isRunning.value).toBe(false)
    expect(error.value).toMatchObject({
      code: 'stream_stalled',
      message: 'live data stream stalled',
    })
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ code: 'stream_stalled' }),
    )
  })

  it('watchdog is cleared on normal completion (no spurious onError)', async () => {
    vi.useFakeTimers()
    const { response, handle } = makeStreamResponse()
    vi.mocked(fetch).mockResolvedValue(response)

    const { status, start } = useSSE()
    const onError = vi.fn()
    const onComplete = vi.fn()

    const promise = start('/api/scan/cn', {}, {
      onError,
      onComplete,
      stallTimeoutMs: 5000,
    })

    handle.enqueue(enc('data: {"progress":100,"message":"done"}\n\n'))
    await vi.advanceTimersByTimeAsync(0)
    await promise

    expect(status.value).toBe('complete')

    // Advance well past the watchdog threshold after completion — onError must
    // NOT fire (watchdog interval was cleared).
    await vi.advanceTimersByTimeAsync(20000)
    expect(onError).not.toHaveBeenCalled()
  })

  it('watchdog is cleared on fetch rejection (no double-error)', async () => {
    vi.useFakeTimers()
    vi.mocked(fetch).mockRejectedValue(new Error('network drop'))

    const { status, start } = useSSE()
    const onError = vi.fn()

    const promise = start('/api/scan/cn', {}, {
      onError,
      stallTimeoutMs: 5000,
    })
    await vi.advanceTimersByTimeAsync(0)
    await promise

    expect(status.value).toBe('error')
    expect(onError).toHaveBeenCalledTimes(1)
    // First call surfaced the network_error.
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ code: 'network_error' }),
    )

    // Advance past the threshold — the watchdog must have been cleared, so
    // onError must NOT fire a second time.
    await vi.advanceTimersByTimeAsync(20000)
    expect(onError).toHaveBeenCalledTimes(1)
  })

  it('HTTP non-ok response surfaces a terminal error (parses S002-009 envelope code when present)', async () => {
    const envelope = JSON.stringify({
      error: { code: 'internal_error', message: 'db down' },
    })
    vi.mocked(fetch).mockResolvedValue(
      new Response(envelope, { status: 500, headers: { 'Content-Type': 'application/json' } }),
    )

    const { error, status, isRunning, start } = useSSE()
    const onError = vi.fn()

    await start('/api/scan/cn', {}, { onError })

    expect(status.value).toBe('error')
    expect(isRunning.value).toBe(false)
    expect(error.value).toMatchObject({
      code: 'internal_error',
      message: 'db down',
    })
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ code: 'internal_error' }),
    )
  })

  it('HTTP non-ok with non-JSON body falls back to a numeric status code', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response('plain text oops', { status: 502 }),
    )

    const { error, start } = useSSE()
    await start('/api/scan/cn', {}, {})

    expect(error.value).toMatchObject({
      code: 'http_502',
      message: 'plain text oops',
    })
  })
})
