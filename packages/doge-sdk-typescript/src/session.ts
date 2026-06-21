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
