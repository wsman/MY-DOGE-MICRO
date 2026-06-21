import { DogeApiError, type DogeEvent } from './run'
import { Session, type AgentSession } from './session'
import { parseSse } from './streaming'

interface DogeClientOptions {
  baseUrl?: string
  apiToken?: string
}

export interface RunStreamOptions {
  lastEventId?: string
  reconnect?: boolean
  maxReconnects?: number
  backoffMs?: number
  sleep?: (milliseconds: number) => Promise<void>
}

export class DogeClient {
  readonly sessions: SessionsResource
  readonly runs: RunsResource
  readonly documents: DocumentsResource
  private readonly baseUrl: string
  private readonly apiToken?: string

  constructor(options: DogeClientOptions = {}) {
    this.baseUrl = options.baseUrl?.replace(/\/$/, '') ?? ''
    this.apiToken = options.apiToken
    this.sessions = new SessionsResource(this)
    this.runs = new RunsResource(this)
    this.documents = new DocumentsResource(this)
  }

  async request<T>(method: string, path: string, body?: unknown, extraHeaders: Record<string, string> = {}): Promise<T> {
    const headers: Record<string, string> = { ...extraHeaders }
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    if (this.apiToken) headers.Authorization = `Bearer ${this.apiToken}`
    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!response.ok) {
      let message = response.statusText
      try {
        const payload = await response.json() as { error?: { message?: string }, detail?: string }
        message = payload.error?.message ?? payload.detail ?? message
      } catch {
        message = await response.text()
      }
      throw new DogeApiError(response.status, message)
    }
    return await response.json() as T
  }

  async stream(path: string, lastEventId?: string): Promise<AsyncGenerator<DogeEvent>> {
    const headers: Record<string, string> = {}
    if (lastEventId) headers['Last-Event-ID'] = lastEventId
    if (this.apiToken) headers.Authorization = `Bearer ${this.apiToken}`
    const response = await fetch(`${this.baseUrl}${path}`, { headers })
    if (!response.ok || !response.body) {
      throw new DogeApiError(response.status, response.statusText)
    }
    return parseSse(response.body)
  }
}

export class SessionsResource {
  private readonly root: DogeClient

  constructor(root: DogeClient) {
    this.root = root
  }

  async create(title = 'Research session'): Promise<Session> {
    const data = await this.root.request<AgentSession>('POST', '/v1/sessions', { title })
    return new Session(this.root, data)
  }

  async list(limit = 20): Promise<AgentSession[]> {
    const payload = await this.root.request<{ sessions: AgentSession[] }>('GET', `/v1/sessions?limit=${limit}`)
    return payload.sessions
  }

  async get(sessionId: string): Promise<Session> {
    const data = await this.root.request<AgentSession>('GET', `/v1/sessions/${sessionId}`)
    return new Session(this.root, data)
  }

  async createTurn(sessionId: string, message: string, options: Record<string, unknown> = {}): Promise<string> {
    const payload = await this.root.request<{ run_id: string }>(
      'POST',
      `/v1/sessions/${sessionId}/turns`,
      { message, ...options },
      { 'Idempotency-Key': crypto.randomUUID() },
    )
    return payload.run_id
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

export class DocumentsResource {
  private readonly root: DogeClient

  constructor(root: DogeClient) {
    this.root = root
  }

  create(filename: string, content = ''): Promise<Record<string, unknown>> {
    return this.root.request('POST', '/v1/documents', { filename, content })
  }
}
