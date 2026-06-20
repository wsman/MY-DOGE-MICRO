import api from './client'

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
  portfolio_id: string
  market: string
  language: string
  model_policy: Record<string, any>
}

export async function createAgentRun(payload: CreateAgentRunRequest): Promise<AgentRun> {
  const { data } = await api.post('/agent/runs', payload)
  return data
}

export async function fetchAgentRun(runId: string): Promise<AgentRun> {
  const { data } = await api.get(`/agent/runs/${runId}`)
  return data
}

export async function approveAgentRun(runId: string, approvalId: string, approved: boolean): Promise<AgentRun> {
  const { data } = await api.post(`/agent/runs/${runId}/approvals/${approvalId}`, { approved })
  return data
}
