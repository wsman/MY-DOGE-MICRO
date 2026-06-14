import { describe, it, expect } from 'vitest'
import { toFetchError } from './fetchError'

/**
 * fetchError spec (S003-009).
 *
 * `toFetchError` is the load-bearing correctness surface of the S003-009
 * "surface fetch errors instead of silently blanking" story: REST-backed views
 * (InsightsView, AnalysisView, …) route every caught value through it before
 * handing the result to StatusView, so a wrong classification or a dropped
 * message-precedence rule turns a surfaced error back into a silent blank.
 *
 * The contract (see fetchError.ts header) is three branches with precise
 * message-precedence rules, detected by duck-typing axios's `response` /
 * `request` fields rather than importing AxiosError's types. These tests pin
 * each branch and each precedence step so a refactor that swaps the order,
 * drops the "HTTP <status>" fallback, or breaks the duck-typing fails loudly.
 *
 * Mount/style mirrors composables/useSSE.spec.ts and
 * components/common/StatusView.spec.ts: vitest globals, relative import, a
 * leading intent comment per case. No network, no Pinia, no jsdom dependency —
 * `toFetchError` is a pure coercion, so each case just builds a thrown value
 * and asserts the resulting { code, message } shape.
 *
 * Does NOT import @pretext — safe under jsdom (vitest.config.ts alias).
 */

/**
 * Build a minimal axios-shaped error carrying a `response`. Only the fields
 * `toFetchError` reads (`response.status`, `response.data`, own `message`) are
 * populated, so the duck-typing stays honest — if the helper ever starts
 * importing AxiosError it will still classify these, but if it starts requiring
 * a field this builder omits, that contract change shows up as a failing case.
 */
function axiosResponseError(
  status: number,
  data: unknown,
  ownMessage = 'axios message',
): Error & { response: { status: number; data: unknown } } {
  const e = new Error(ownMessage) as Error & {
    response: { status: number; data: unknown }
  }
  e.response = { status, data }
  return e
}

/**
 * Build a minimal axios-shaped error with a `request` but no `response` — the
 * "network drop / CORS / DNS / timeout" branch. `request` can be any non-null
 * sentinel; the helper only checks for its presence.
 */
function axiosNoResponseError(
  ownMessage?: string,
): Error & { request: unknown } {
  const e = (ownMessage !== undefined ? new Error(ownMessage) : new Error()) as
    Error & { request: unknown }
  e.request = {}
  return e
}

describe('toFetchError', () => {
  describe('axios response branch (server answered non-2xx)', () => {
    it('http_<status>, message prefers response.data.message', () => {
      // (a) status 500 with a top-level data.message -> that message wins.
      const e = axiosResponseError(500, { message: 'db down' })

      expect(toFetchError(e)).toEqual({
        code: 'http_500',
        message: 'db down',
      })
    })

    it('http_<status>, message prefers the { error: { message } } envelope', () => {
      // (b) status 500 with the S002-009 envelope -> the envelope message wins
      // (same shape useSSE.ts parses for the SSE path — one error dialect).
      const e = axiosResponseError(500, {
        error: { message: 'envelope failure detail' },
      })

      expect(toFetchError(e)).toEqual({
        code: 'http_500',
        message: 'envelope failure detail',
      })
    })

    it('http_<status>, no message body -> bare "HTTP <status>" fallback', () => {
      // (c) status 404 with an empty body -> precedence exhausts
      // server-message -> own-message would win here, so use an empty own
      // message to assert the final "HTTP <status>" fallback in isolation.
      const e = axiosResponseError(404, null, '')

      expect(toFetchError(e)).toEqual({
        code: 'http_404',
        message: 'HTTP 404',
      })
    })

    it('falls back to the axios own message when the body has no message', () => {
      // Precedence middle step: body present but message-less, own message
      // populated -> own message wins over the bare "HTTP <status>".
      const e = axiosResponseError(502, { unrelated: 'field' }, 'bad gateway')

      expect(toFetchError(e)).toEqual({
        code: 'http_502',
        message: 'bad gateway',
      })
    })
  })

  describe('axios request branch (no response — network/CORS/timeout)', () => {
    it('network_error (parity with useSSE), message prefers e.message', () => {
      // (d) request present, no response, own message -> that message wins.
      // code is `network_error` to match useSSE.ts so REST + SSE share one dialect.
      const e = axiosNoResponseError('network drop')

      expect(toFetchError(e)).toEqual({
        code: 'network_error',
        message: 'network drop',
      })
    })

    it('network_error, empty message -> "Network request failed" generic', () => {
      // (e) request present, no response, empty own message -> generic.
      const e = axiosNoResponseError('')

      expect(toFetchError(e)).toEqual({
        code: 'network_error',
        message: 'Network request failed',
      })
    })
  })

  describe('generic fallback branch (programming error / non-Error throw)', () => {
    it('fetch_failed, bare Error -> e.message', () => {
      // (f) plain Error with a message -> that message.
      expect(toFetchError(new Error('boom'))).toEqual({
        code: 'fetch_failed',
        message: 'boom',
      })
    })

    it('fetch_failed, non-Error string throw -> String(e)', () => {
      // (g) a bare string thrown (no .message) -> String(e) renders it back.
      expect(toFetchError('something went wrong')).toEqual({
        code: 'fetch_failed',
        message: 'something went wrong',
      })
    })

    it('fetch_failed, non-Error falsy throw -> "Request failed" generic', () => {
      // (h) a falsy non-Error throw whose String() coercion is empty (e.g.
      // `throw ''` / `throw 0` only when String(0) is '0'; the empty string is
      // the canonical falsy that reaches the final fallback) -> String(e) is
      // '' (falsy), so the "Request failed" generic wins.
      //
      // Note: `throw null`/`throw undefined` do NOT reach this fallback in the
      // current implementation because String(null) === 'null' (truthy). That
      // asymmetry is pinned in the next case so a future change is detected.
      expect(toFetchError('')).toEqual({
        code: 'fetch_failed',
        message: 'Request failed',
      })
    })

    it('fetch_failed, throw null/undefined -> String(e) (pins current coercion asymmetry)', () => {
      // The generic branch is `(e instanceof Error ? e.message : String(e)) || 'Request failed'`.
      // String(null) === 'null' and String(undefined) === 'undefined' are both
      // truthy, so they do NOT fall through to 'Request failed'. This case pins
      // that current behavior so a refactor that either (a) starts using the
      // 'Request failed' fallback for null/undefined, or (b) stops stringifying
      // them, is caught here rather than silently changing surfaced messages.
      expect(toFetchError(null)).toEqual({
        code: 'fetch_failed',
        message: 'null',
      })
      expect(toFetchError(undefined)).toEqual({
        code: 'fetch_failed',
        message: 'undefined',
      })
    })
  })

  describe('never throws', () => {
    it('returns a populated FetchError for every input, including falsy throws', () => {
      // The helper must be safe to call as `toFetchError(caughtValue)` inside a
      // catch block without a nested try/catch — it always returns a populated
      // object so callers can assign directly to a ref<FetchError | null>.
      // Drives every branch input once to confirm the shape holds.
      for (const input of [
        axiosResponseError(500, { message: 'x' }),
        axiosNoResponseError('y'),
        new Error('z'),
        'str',
        '',
        null,
        undefined,
      ] as const) {
        const result = toFetchError(input)
        expect(typeof result.code).toBe('string')
        expect(typeof result.message).toBe('string')
        expect(result.message.length).toBeGreaterThan(0)
      }
    })
  })
})
