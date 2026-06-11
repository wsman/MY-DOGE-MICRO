import { ref } from 'vue'

/**
 * Structured SSE error. The `code` is a stable string enum the UI can branch on
 * (see docs/architecture/adr-0008-web-architecture.md watchdog amendment).
 *
 * Today the only client-originated code is `stream_stalled` (watchdog trip).
 * Server-emitted codes (e.g. the S002-009 envelope `code`) will be threaded
 * through `progress === -1` once S002-009 lands its string-enum convention;
 * until then the in-band error path falls back to `internal_error`.
 */
export interface SSEError {
  code: string
  message: string
}

/**
 * Reactive lifecycle of an SSE stream consumed by the scanner UI.
 * - `idle`     — no stream has started (or it was reset).
 * - `running`  — fetch/reader loop is active and the watchdog has not tripped.
 * - `error`    — a terminal failure occurred (watchdog trip, HTTP non-ok,
 *                fetch rejection, or an in-band `progress === -1` sentinel).
 * - `complete` — the stream emitted `progress >= 100` and ended cleanly.
 */
export type SSEStatus = 'idle' | 'running' | 'error' | 'complete'

export interface SSEOptions {
  onProgress?: (pct: number, msg: string) => void
  onComplete?: () => void
  onError?: (err: SSEError) => void
  /**
   * Watchdog threshold: if no `data:` line arrives within this many
   * milliseconds while `isRunning` is true, the stream is treated as dropped
   * and a terminal `stream_stalled` error is surfaced. Default 30000 (30s) —
   * conservative enough to avoid false-trips on legitimately slow scan steps
   * (a full CN-universe scan can have multi-second gaps between progress
   * callbacks). See ADR-0008 watchdog amendment.
   */
  stallTimeoutMs?: number
}

/** Default watchdog threshold in milliseconds. */
export const DEFAULT_STALL_TIMEOUT_MS = 30000

export function useSSE() {
  const progress = ref(0)
  const messages = ref<string[]>([])
  const isRunning = ref(false)
  const error = ref<SSEError | null>(null)
  const status = ref<SSEStatus>('idle')

  async function start(url: string, body: object, opts: SSEOptions = {}) {
    const stallTimeoutMs = opts.stallTimeoutMs ?? DEFAULT_STALL_TIMEOUT_MS

    // Reset reactive state for a fresh run.
    progress.value = 0
    messages.value = []
    isRunning.value = true
    error.value = null
    status.value = 'running'

    // Watchdog bookkeeping.
    let lastEventAt = Date.now()
    let watchdog: ReturnType<typeof setInterval> | null = null
    let watchdogTripped = false
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null

    /** Idempotently clear the watchdog interval. */
    const clearWatchdog = () => {
      if (watchdog !== null) {
        clearInterval(watchdog)
        watchdog = null
      }
    }

    /**
     * Record that we just received a data event, resetting the watchdog clock.
     * Called on connect (fetch resolved) and on every parsed `data:` line.
     */
    const markEvent = () => {
      lastEventAt = Date.now()
    }

    /**
     * Surface a terminal error and tear the stream down. Idempotent — once a
     * terminal state is reached, subsequent calls are no-ops.
     */
    const surfaceTerminalError = (err: SSEError) => {
      if (watchdogTripped) return
      watchdogTripped = true
      clearWatchdog()
      error.value = err
      status.value = 'error'
      isRunning.value = false
      // Cancel the reader so the blocked `await reader.read()` rejects/returns
      // and the while-loop unwinds; guard against already-released readers.
      if (reader) {
        try {
          reader.cancel()
        } catch {
          // Reader may already be closed/locked — ignore.
        }
      }
      opts.onError?.(err)
    }

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      // The HTTP response itself counts as the first event for watchdog purposes.
      markEvent()

      if (!resp.ok) {
        // HTTP-level terminal error. Try to parse the S002-009 envelope
        // ({error: {code, message}}) for a stable code; degrade gracefully
        // to a numeric status code string if the envelope is absent.
        let code = `http_${resp.status}`
        let message = `HTTP ${resp.status}`
        try {
          const text = await resp.text()
          message = text || message
          const parsed = JSON.parse(text)
          if (parsed?.error?.code) code = parsed.error.code
          if (parsed?.error?.message) message = parsed.error.message
        } catch {
          // Non-JSON body — keep the numeric status code + raw text.
        }
        surfaceTerminalError({ code, message })
        return
      }

      reader = resp.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      // Start the watchdog now that the reader loop is about to block.
      // Comparing Date.now() (real time) keeps the watchdog faithful to wall
      // clock gaps even though the read loop is async.
      watchdog = setInterval(() => {
        if (!isRunning.value || watchdogTripped) return
        if (Date.now() - lastEventAt >= stallTimeoutMs) {
          surfaceTerminalError({
            code: 'stream_stalled',
            message: 'live data stream stalled',
          })
        }
      }, stallTimeoutMs)

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // Every decoded chunk resets the watchdog clock — even chunks that
        // don't contain a complete `data:` line prove the stream is alive.
        markEvent()

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data:')) {
            try {
              const payload = JSON.parse(line.slice(5).trim())
              const pct = payload.progress ?? 0
              const msg = payload.message ?? ''

              if (pct === -1) {
                // In-band error sentinel from the server (e.g. scan.py
                // `f'error: {e}'`). S002-009 will add a stable `code` field;
                // until then this is a terminal internal_error.
                surfaceTerminalError({
                  code: payload.code ?? 'internal_error',
                  message: msg || 'scan failed',
                })
                return
              } else {
                progress.value = pct
                messages.value.push(msg)
                opts.onProgress?.(pct, msg)

                if (pct >= 100) {
                  // Terminal completion — clear the watchdog BEFORE invoking
                  // onComplete so a slow callback can't trip a stale timer.
                  clearWatchdog()
                  status.value = 'complete'
                  isRunning.value = false
                  opts.onComplete?.()
                  return
                }
              }
            } catch {
              // skip malformed data lines
            }
          }
        }
      }

      // Stream ended (done) without an explicit completion sentinel. Treat as
      // complete so the UI leaves the 'running' state.
      if (!watchdogTripped) {
        clearWatchdog()
        status.value = 'complete'
        isRunning.value = false
      }
    } catch (e: unknown) {
      // Network drop / fetch rejection / reader.cancel() rejection.
      // Avoid double-erroring if the watchdog already surfaced a terminal state.
      if (!watchdogTripped) {
        const message = e instanceof Error ? e.message : String(e)
        surfaceTerminalError({ code: 'network_error', message })
      }
    } finally {
      clearWatchdog()
      isRunning.value = false
    }
  }

  return { progress, messages, isRunning, error, status, start }
}
