import type { DogeClient } from './client'

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
}
