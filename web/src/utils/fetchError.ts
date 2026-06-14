/**
 * Shared fetch-error vocabulary for REST views (S003-009).
 *
 * The scanner/SSE path already has its own structured error shape —
 * `SSEError` in composables/useSSE.ts ({ code: string; message: string }).
 * REST-backed views (InsightsView, AnalysisView, …) catch raw axios/fetch
 * rejections and today swallow them with bare `catch {}` blocks, silently
 * blanking the panel. `toFetchError` normalizes any thrown value into the same
 * { code, message } shape the SSE path uses, so views can route both into a
 * single StatusView (components/common/StatusView.vue) without a second error
 * dialect.
 *
 * Error classification (in order):
 *   - axios response present (server answered with a non-2xx):
 *       code = `http_<status>`, message prefers the server's own message,
 *       then axios's own message, then a bare "HTTP <status>".
 *   - axios request present but no response (network/CORS/DNS/timeout):
 *       code = `network_error` (matches useSSE.ts so a network drop carries
 *       the same code under REST and SSE — one error dialect), message
 *       prefers e.message, else a generic.
 *   - anything else (programming error, non-Error throw, unknown):
 *       code = `fetch_failed`, message prefers e.message else String(e),
 *       else "Request failed".
 *
 * The accessor shape (`e.response?.status`, `e.request`) intentionally matches
 * the axios error contract by duck-typing rather than importing AxiosError's
 * types, so this helper stays free of an axios type dependency and works for
 * any Error that happens to carry those fields.
 */

/**
 * Structured fetch error. Shape mirrors SSEError
 * (composables/useSSE.ts) so stores and views share one error dialect.
 */
export interface FetchError {
  code: string
  message: string
}

/**
 * Coerce any thrown value into a FetchError. Detects axios-style errors by
 * duck-typing their `response` / `request` fields; everything else degrades
 * to a generic `fetch_failed`. Never throws — always returns a populated
 * FetchError so callers can assign directly to a `ref<FetchError | null>`.
 */
export function toFetchError(e: unknown): FetchError {
  // Axios "server responded with non-2xx" branch: a `response` object carrying
  // a numeric status is attached. Prefer the server's own message, then
  // axios's own message, then a bare "HTTP <status>" fallback.
  const response = (e as { response?: { status?: number; data?: unknown } } | null | undefined)?.response
  if (response && typeof response.status === 'number') {
    const status = response.status
    const serverMessage = extractResponseMessage(response.data)
    const ownMessage = e instanceof Error ? e.message : undefined
    return {
      code: `http_${status}`,
      message: serverMessage || ownMessage || `HTTP ${status}`,
    }
  }

  // Axios "request made but no response received" branch (network drop, CORS,
  // DNS, timeout). A `request` field is present with no `response`. This also
  // covers raw fetch() rejections that carry no request/response (TypeError).
  const hasRequest = (e as { request?: unknown } | null | undefined)?.request !== undefined
  if (hasRequest) {
    const message = (e instanceof Error ? e.message : undefined) || 'Network request failed'
    return {
      // Matches useSSE.ts `network_error` so a network drop is the same code
      // regardless of REST vs SSE transport (one error dialect).
      code: 'network_error',
      message,
    }
  }

  // Generic fallback for any other thrown value (programming error, a bare
  // string thrown, a raw fetch() TypeError, or an unknown Error subclass).
  const message = (e instanceof Error ? e.message : String(e)) || 'Request failed'
  return {
    code: 'fetch_failed',
    message,
  }
}

/**
 * Pull a human-readable message out of an axios response body, preferring the
 * same S002-009 envelope (`{ error: { message } }`) useSSE.ts parses, then a
 * top-level `message`/`detail`, then the raw body string. Returns undefined
 * when nothing useful is present so the caller can fall back further.
 */
function extractResponseMessage(data: unknown): string | undefined {
  if (typeof data === 'string') {
    return data.length > 0 ? data : undefined
  }
  if (typeof data !== 'object' || data === null) {
    return undefined
  }
  const d = data as Record<string, unknown>
  const envelope = d.error
  if (
    typeof envelope === 'object' &&
    envelope !== null &&
    typeof (envelope as { message?: unknown }).message === 'string'
  ) {
    return (envelope as { message: string }).message
  }
  if (typeof d.message === 'string') return d.message
  if (typeof d.detail === 'string') return d.detail
  return undefined
}
