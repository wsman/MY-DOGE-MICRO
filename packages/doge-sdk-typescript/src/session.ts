import type { DogeClient } from './client.js'

export interface AgentSession {
  session_id: string
  title: string
  turns: Array<Record<string, unknown>>
}

export class Session {
  private readonly client: DogeClient
  readonly data: AgentSession

  constructor(client: DogeClient, data: AgentSession) {
    this.client = client
    this.data = data
  }

  get sessionId(): string {
    return this.data.session_id
  }

  async createTurn(message: string, options: Record<string, unknown> = {}): Promise<string> {
    return this.client.sessions.createTurn(this.sessionId, message, options)
  }

  async run(
    question: string,
    options: Record<string, unknown> & { execution_profile?: string, model_policy?: Record<string, unknown> } = {},
  ): Promise<string> {
    const { execution_profile = 'financial_research', model_policy = {}, ...rest } = options
    return this.createTurn(question, {
      ...rest,
      model_policy: {
        ...model_policy,
        execution_profile,
      },
    })
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
