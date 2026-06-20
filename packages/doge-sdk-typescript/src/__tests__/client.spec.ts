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
})
