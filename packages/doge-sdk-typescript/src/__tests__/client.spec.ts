import { describe, expect, it, vi } from 'vitest'
import { DogeClient } from '../client'
import { DogeApiError } from '../run'

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

  it('creates runs with execution profiles through session helper', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session_id: 'ses-test', title: 'Test', turns: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'accepted', run_id: 'run-test' }),
      })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()
    const session = await client.sessions.create('Test')
    const runId = await session.run('Analyze', { execution_profile: 'quant_code', document_ids: ['doc-1'] })

    expect(runId).toBe('run-test')
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/v1/sessions/ses-test/turns',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          message: 'Analyze',
          document_ids: ['doc-1'],
          model_policy: { execution_profile: 'quant_code' },
        }),
      }),
    )
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

  it('reconnects after a mid-stream drop with the latest event id', async () => {
    let reads = 0
    const initialStream = new ReadableStream<Uint8Array>({
      pull(controller) {
        reads += 1
        if (reads > 1) {
          controller.error(new Error('socket closed'))
          return
        }
        controller.enqueue(new TextEncoder().encode('id: 2\nevent: tool_call\ndata: {"step": "started"}\n\n'))
      },
    })
    const replayStream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('id: 3\nevent: artifact_created\ndata: {"terminal": true}\n\n'))
        controller.close()
      },
    })
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, body: initialStream })
      .mockResolvedValueOnce({ ok: true, body: replayStream })
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

    expect(events.map(event => event.id)).toEqual(['2', '3'])
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/v1/runs/run-test/stream',
      expect.objectContaining({ headers: { 'Last-Event-ID': '1' } }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/v1/runs/run-test/stream',
      expect.objectContaining({ headers: { 'Last-Event-ID': '2' } }),
    )
  })

  it('gets and lists documents', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ documents: [{ document_id: 'doc-1' }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ document_id: 'doc-1' }),
      })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    const documents = await client.documents.list()
    const document = await client.documents.get('doc-1')

    expect(documents[0].document_id).toBe('doc-1')
    expect(document.document_id).toBe('doc-1')
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/v1/documents?limit=100', expect.objectContaining({ method: 'GET' }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/v1/documents/doc-1', expect.objectContaining({ method: 'GET' }))
  })

  it('uploads documents as multipart form data without forcing json headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ document_id: 'doc-upload' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient({ apiToken: 'secret' })

    const document = await client.documents.upload(new Blob(['alpha beta'], { type: 'text/plain' }), 'report.txt')

    expect(document.document_id).toBe('doc-upload')
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/documents',
      expect.objectContaining({
        method: 'POST',
        headers: { Authorization: 'Bearer secret' },
        body: expect.any(FormData),
      }),
    )
  })

  it('sends bearer and request id headers and redacts token from errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      json: async () => ({ error: { message: 'rejected Authorization: Bearer secret-token' } }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient({ apiToken: 'secret-token', requestId: 'req-123' })

    await expect(client.sessions.list()).rejects.toMatchObject({
      name: 'DogeApiError',
      statusCode: 403,
      message: 'rejected Authorization: Bearer [REDACTED]',
    } satisfies Partial<DogeApiError>)
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/sessions?limit=20',
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer secret-token',
          'X-Request-ID': 'req-123',
        },
      }),
    )
  })

  it('redacts key-value secrets from API errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => ({
        detail: 'provider failed MOONSHOT_API_KEY=moonshot-secret client_secret=client-secret sk-live-secret',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    await expect(client.sessions.list()).rejects.toMatchObject({
      name: 'DogeApiError',
      statusCode: 500,
      message: 'provider failed MOONSHOT_API_KEY=[REDACTED] client_secret=[REDACTED] sk-[REDACTED]',
    } satisfies Partial<DogeApiError>)
  })

  it('sends bearer and request id headers on SSE streams', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('id: 2\nevent: tool_call\ndata: {"ok": true}\n\n'))
        controller.close()
      },
    })
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, body: stream })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient({ apiToken: 'secret-token', requestId: 'req-123' })

    const events = []
    for await (const event of client.runs.stream('run-test', { lastEventId: '1' })) {
      events.push(event)
    }

    expect(events[0].id).toBe('2')
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/runs/run-test/stream',
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer secret-token',
          'X-Request-ID': 'req-123',
          'Last-Event-ID': '1',
        },
      }),
    )
  })

  it('redacts bearer tokens from SSE stream errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ detail: 'stream rejected Authorization: Bearer secret-token' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient({ apiToken: 'secret-token' })

    const events = client.runs.stream('run-test')
    await expect(events.next()).rejects.toMatchObject({
      name: 'DogeApiError',
      statusCode: 401,
      message: 'stream rejected Authorization: Bearer [REDACTED]',
    } satisfies Partial<DogeApiError>)
  })
})
