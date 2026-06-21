import { describe, expect, it, vi } from 'vitest'
import { DogeClient } from '../client'

describe('DogeClient', () => {
  it('creates a session through v1 API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: 'ses-test', title: 'Test', turns: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()
    const session = await client.sessions.create('Test')
    expect(session.sessionId).toBe('ses-test')
    expect(fetchMock).toHaveBeenCalledWith('/v1/sessions', expect.objectContaining({ method: 'POST' }))
  })

  it('returns queued approval responses from v1 API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ run_id: 'run-test', status: 'queued' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()
    const run = await client.runs.approve('run-test', 'appr-1')
    expect(run.status).toBe('queued')
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/runs/run-test/approvals/appr-1',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('reconnects run streams with Last-Event-ID', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('id: 2\nevent: tool_call\ndata: {"ok": true}\n\n'))
        controller.close()
      },
    })
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError('network dropped'))
      .mockResolvedValueOnce({
        ok: true,
        body: stream,
      })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    const events = []
    for await (const event of client.runs.stream('run-test', {
      lastEventId: '1',
      maxReconnects: 1,
      backoffMs: 0,
      sleep: async () => undefined,
    })) {
      events.push(event)
    }

    expect(events[0].id).toBe('2')
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/v1/runs/run-test/stream',
      expect.objectContaining({ headers: { 'Last-Event-ID': '1' } }),
    )
  })
})
