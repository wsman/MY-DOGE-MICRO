import { dogeClient } from './client'
import type {
  AgentApproval as SdkAgentApproval,
  AgentArtifact as SdkAgentArtifact,
  AgentEvent as SdkAgentEvent,
  AgentRun as SdkAgentRun,
} from 'doge-sdk'

type WebRecord = Record<string, unknown> & Record<string, any>

export type AgentEvent = Omit<SdkAgentEvent, 'payload'> & { payload: WebRecord }
export type AgentArtifact = Omit<SdkAgentArtifact, 'data'> & { data: WebRecord }
export type AgentApproval = SdkAgentApproval
export type AgentRun = Omit<SdkAgentRun, 'events' | 'artifacts'> & {
  events: AgentEvent[]
  artifacts: AgentArtifact[]
}

export interface CreateAgentRunRequest {
  workflow: string
  question: string
  execution_profile: string
  document_ids: string[]
  portfolio_id: string | null
  market: string
  language: string
  model_policy: Record<string, any>
}

export async function createAgentRun(payload: CreateAgentRunRequest): Promise<AgentRun> {
  const session = await dogeClient.sessions.create('Research Agent Workspace')
  const runId = await session.run(payload.question, {
    market: payload.market,
    language: payload.language,
    document_ids: payload.document_ids,
    portfolio_id: payload.portfolio_id,
    execution_profile: payload.execution_profile,
    model_policy: payload.model_policy,
  })
  return await streamAgentRun(runId)
}

export async function fetchAgentRun(runId: string): Promise<AgentRun> {
  return await dogeClient.runs.get(runId)
}

export async function approveAgentRun(runId: string, approvalId: string, approved: boolean): Promise<AgentRun> {
  const run = await dogeClient.runs.approve(runId, approvalId, approved)
  return isSettledForDisplay(run.status) ? run : await streamAgentRun(runId, latestEventId(run))
}

async function streamAgentRun(runId: string, lastEventId?: string): Promise<AgentRun> {
  for await (const event of dogeClient.runs.stream(runId, { lastEventId, reconnect: true })) {
    if (isSettledEvent(event.type)) break
  }
  return await fetchAgentRun(runId)
}

function isSettledForDisplay(status: string): boolean {
  return ['awaiting_approval', 'completed', 'failed', 'cancelled'].includes(status)
}

function isSettledEvent(eventType: string): boolean {
  return ['approval_requested', 'artifact_created', 'error', 'run_cancelled'].includes(eventType)
}

function latestEventId(run: AgentRun): string | undefined {
  const last = run.events[run.events.length - 1]
  return last ? String(last.sequence) : undefined
}
