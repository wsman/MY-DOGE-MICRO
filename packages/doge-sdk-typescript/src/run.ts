import type { DogeClient } from './client.js'

export interface DogeEvent {
  id?: string
  type: string
  data: Record<string, unknown>
}

export interface RunStreamOptions {
  lastEventId?: string
  reconnect?: boolean
  maxReconnects?: number
  backoffMs?: number
  sleep?: (milliseconds: number) => Promise<void>
}

export class DogeApiError extends Error {
  readonly statusCode: number

  constructor(statusCode: number, message: string) {
    super(message)
    this.name = 'DogeApiError'
    this.statusCode = statusCode
  }
}

export class RunsResource {
  private readonly root: DogeClient

  constructor(root: DogeClient) {
    this.root = root
  }

  get(runId: string): Promise<Record<string, unknown>> {
    return this.root.request('GET', `/v1/runs/${runId}`)
  }

  async summary(runId: string): Promise<Record<string, unknown>> {
    const payload = await this.root.request<{ summary: Record<string, unknown> }>(
      'GET',
      `/v1/runs/${runId}/summary`,
    )
    return payload.summary
  }

  async claims(runId: string): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ claims: Record<string, unknown>[] }>(
      'GET',
      `/v1/runs/${runId}/claims`,
    )
    return payload.claims
  }

  async citations(runId: string): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ citations: Record<string, unknown>[] }>(
      'GET',
      `/v1/runs/${runId}/citations`,
    )
    return payload.citations
  }

  async evaluation(runId: string): Promise<Record<string, unknown>> {
    const payload = await this.root.request<{ eval: Record<string, unknown> }>('GET', `/v1/runs/${runId}/eval`)
    return payload.eval
  }

  async *stream(runId: string, options?: string | RunStreamOptions): AsyncGenerator<DogeEvent> {
    const config = typeof options === 'string' ? { lastEventId: options } : { ...(options ?? {}) }
    const reconnect = config.reconnect ?? true
    const maxReconnects = config.maxReconnects ?? 3
    const backoffMs = config.backoffMs ?? 250
    const sleep = config.sleep ?? defaultSleep
    let lastEventId = config.lastEventId
    let attempts = 0
    while (true) {
      try {
        const generator = await this.root.stream(`/v1/runs/${runId}/stream`, lastEventId)
        for await (const event of generator) {
          if (event.id) lastEventId = event.id
          attempts = 0
          yield event
        }
        return
      } catch (error) {
        if (error instanceof DogeApiError) throw error
        if (!reconnect || attempts >= maxReconnects) throw error
        attempts += 1
        await sleep(backoffMs * attempts)
      }
    }
  }

  approve(runId: string, approvalId: string, approved = true): Promise<Record<string, unknown>> {
    return this.root.request('POST', `/v1/runs/${runId}/approvals/${approvalId}`, { approved })
  }

  cancel(runId: string): Promise<Record<string, unknown>> {
    return this.root.request('POST', `/v1/runs/${runId}/cancel`)
  }
}

function defaultSleep(milliseconds: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, milliseconds))
}
