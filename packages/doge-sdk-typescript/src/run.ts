import type { DogeClient } from './client.js'

export interface DogeEvent {
  id?: string
  type: string
  data: Record<string, unknown>
}

export type RunStatus =
  | 'created'
  | 'queued'
  | 'running'
  | 'awaiting_approval'
  | 'cancelling'
  | 'cancelled'
  | 'completed'
  | 'failed'

export type RunEventType =
  | 'run_created'
  | 'run_queued'
  | 'model_response'
  | 'tool_call'
  | 'tool_result'
  | 'approval_requested'
  | 'approval_resolved'
  | 'artifact_created'
  | 'run_cancelled'
  | 'error'

export interface AgentEvent {
  event_id: string
  run_id: string
  event_type: RunEventType | string
  payload: Record<string, unknown>
  sequence: number
  schema_version: string
  created_at: string
}

export interface AgentArtifact {
  artifact_id: string
  kind: string
  title: string
  content: string
  run_id: string
  data: Record<string, unknown>
  created_at: string
}

export interface AgentApproval {
  approval_id: string
  action: string
  risk_level: string
  run_id: string
  status: string
  created_at: string
  resolved_at: string | null
  why_needed?: string
  impact?: string
  deny_consequence?: string
  publish_target?: string
}

export interface AgentRun {
  run_id: string
  workflow: string
  question: string
  session_id: string | null
  market: string
  language: string
  document_ids: string[]
  portfolio_id: string | null
  model_policy: Record<string, unknown>
  workflow_context: unknown | null
  identity_snapshot: unknown | null
  status: RunStatus | string
  events: AgentEvent[]
  artifacts: AgentArtifact[]
  approvals: AgentApproval[]
  cancel_requested_at: string | null
  schema_version: string
  created_at: string
  updated_at: string
}

export interface RunListItem {
  run_id: string
  workflow: string
  question: string
  session_id: string | null
  market: string
  language: string
  portfolio_id: string | null
  status: RunStatus | string
  event_count: number
  artifact_count: number
  approval_count: number
  created_at: string
  updated_at: string
}

export interface RunStreamOptions {
  lastEventId?: string
  reconnect?: boolean
  maxReconnects?: number
  backoffMs?: number
  sleep?: (milliseconds: number) => Promise<void>
}

export interface RunResumeOptions {
  approvalId?: string
  approved?: boolean
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

  async list(options: { limit?: number; sessionId?: string } = {}): Promise<RunListItem[]> {
    const params = new URLSearchParams()
    params.set('limit', String(options.limit ?? 20))
    if (options.sessionId) params.set('session_id', options.sessionId)
    const payload = await this.root.request<{ runs: RunListItem[] }>('GET', `/v1/runs?${params.toString()}`)
    return payload.runs
  }

  get(runId: string): Promise<AgentRun> {
    return this.root.request<AgentRun>('GET', `/v1/runs/${runId}`)
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

  approve(runId: string, approvalId: string, approved = true): Promise<AgentRun> {
    return this.root.request<AgentRun>('POST', `/v1/runs/${runId}/approvals/${approvalId}`, { approved })
  }

  resume(runId: string, options: RunResumeOptions = {}): Promise<AgentRun> {
    const body: Record<string, unknown> = { approved: options.approved ?? true }
    if (options.approvalId !== undefined) body.approval_id = options.approvalId
    return this.root.request<AgentRun>('POST', `/v1/runs/${runId}/resume`, body)
  }

  cancel(runId: string): Promise<AgentRun> {
    return this.root.request<AgentRun>('POST', `/v1/runs/${runId}/cancel`)
  }
}

function defaultSleep(milliseconds: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, milliseconds))
}
