import { dogeClient } from './client'

export interface AgentEvent {
  event_id: string
  run_id: string
  event_type: string
  payload: Record<string, any>
  created_at: string
}

export interface AgentArtifact {
  artifact_id: string
  kind: string
  title: string
  content: string
  data: Record<string, any>
  created_at: string
}

export interface AgentApproval {
  approval_id: string
  action: string
  risk_level: string
  status: string
  created_at: string
  resolved_at?: string | null
}

export interface AgentRun {
  run_id: string
  workflow: string
  question: string
  market: string
  language: string
  status: string
  events: AgentEvent[]
  artifacts: AgentArtifact[]
  approvals: AgentApproval[]
}

export interface CreateAgentRunRequest {
  workflow: string
  question: string
  document_ids: string[]
  portfolio_id: string | null
  market: string
  language: string
  model_policy: Record<string, any>
}

export async function createAgentRun(payload: CreateAgentRunRequest): Promise<AgentRun> {
  const session = await dogeClient.sessions.create('Research Agent Workspace')
  const runId = await session.createTurn(payload.question, {
    market: payload.market,
    language: payload.language,
    document_ids: payload.document_ids,
    portfolio_id: payload.portfolio_id,
    model_policy: payload.model_policy,
  })
  return await pollAgentRun(runId)
}

export async function fetchAgentRun(runId: string): Promise<AgentRun> {
  return await dogeClient.runs.get(runId) as unknown as AgentRun
}

export async function approveAgentRun(runId: string, approvalId: string, approved: boolean): Promise<AgentRun> {
  const run = await dogeClient.runs.approve(runId, approvalId, approved) as unknown as AgentRun
  return isSettledForDisplay(run.status) ? run : await pollAgentRun(runId)
}

async function pollAgentRun(runId: string): Promise<AgentRun> {
  const terminal = new Set(['awaiting_approval', 'completed', 'failed', 'cancelled'])
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const run = await fetchAgentRun(runId)
    if (terminal.has(run.status)) return run
    await new Promise(resolve => setTimeout(resolve, 150))
  }
  return await fetchAgentRun(runId)
}

function isSettledForDisplay(status: string): boolean {
  return ['awaiting_approval', 'completed', 'failed', 'cancelled'].includes(status)
}
