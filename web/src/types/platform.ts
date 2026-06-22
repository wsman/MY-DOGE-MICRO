export type JsonObject = Record<string, unknown>

export interface Workspace {
  workspace_id: string
  name: string
  description: string
  status: string
  tenant_id?: string | null
  metadata: JsonObject
  created_at: string
  updated_at: string
  deleted_at?: string | null
}

export interface Project {
  project_id: string
  workspace_id: string
  name: string
  description: string
  status: string
  default_market?: string | null
  tenant_id?: string | null
  metadata: JsonObject
  created_at: string
  updated_at: string
  deleted_at?: string | null
}

export interface ResearchCase {
  case_id: string
  project_id: string
  title: string
  thesis: string
  status: string
  decision?: string | null
  tenant_id?: string | null
  metadata: JsonObject
  created_at: string
  updated_at: string
  deleted_at?: string | null
}

export interface CaseRunLink {
  case_id: string
  run_id: string
  link_type: string
  tenant_id?: string | null
  linked_at: string
}

export interface WorkflowTemplate {
  template_id: string
  slug: string
  name: string
  description: string
  status: string
  current_version: string
  input_schema: JsonObject
  run_instructions: string
  tool_policy: JsonObject
  evidence_policy: JsonObject
  output_contract: JsonObject
  tenant_id?: string | null
  metadata: JsonObject
  created_at: string
  updated_at: string
}

export interface Capability {
  capability_id: string
  kind: string
  name: string
  status: string
  risk_level: string
  requires_approval: boolean
  metadata: JsonObject
}

export interface CapabilitySnapshot {
  snapshot_id: string
  generated_at: string
  redaction_version: string
  status_counts: Record<string, number>
  capabilities: Capability[]
}

export interface RunSummary {
  summary_id: string
  run_id: string
  status: string
  run_status: string
  summary_text: string
  source_artifact_id?: string | null
  source_event_high_watermark: number
  created_at: string
  updated_at: string
}

export interface RunClaim {
  claim_id: string
  summary_id: string
  run_id: string
  claim_text: string
  support_status: string
  evidence_count: number
  source: string
}

export interface RunCitation {
  citation_id: string
  run_id: string
  claim_id?: string | null
  evidence_id?: string | null
  document_id?: string | null
  page_id?: string | null
  chunk_id?: string | null
  page_number?: number | null
  source: string
  snippet: string
  snippet_hash: string
  provider_file_id?: string | null
  accessible: boolean
}

export interface RunEval {
  eval_id: string
  run_id: string
  summary_id: string
  coverage_ratio: number
  claim_count: number
  supported_claim_count: number
  citation_count: number
  accessible_citation_count: number
  failed_checks: string[]
  metrics: JsonObject
}

export interface RunSummaryResources {
  summary: RunSummary
  claims: RunClaim[]
  citations: RunCitation[]
  eval: RunEval
}

export interface CreateWorkspacePayload {
  name: string
  description?: string
}

export interface CreateProjectPayload {
  workspace_id: string
  name: string
  description?: string
  default_market?: string | null
}

export interface CreateResearchCasePayload {
  project_id: string
  title: string
  thesis?: string
}

export interface LinkResearchCaseRunPayload {
  run_id: string
  link_type?: string
}

export interface CreateResearchCaseRunFromTemplatePayload {
  template_id: string
  question?: string
  model_policy?: JsonObject
  inputs?: JsonObject
  workflow?: string
  session_id?: string
  market?: string
  language?: string
  document_ids?: string[]
  portfolio_id?: string | null
  link_type?: string
}

export interface CreateWorkflowTemplatePayload {
  slug: string
  name: string
  description?: string
  current_version?: string
  input_schema?: JsonObject
  run_instructions?: string
  tool_policy?: JsonObject
  evidence_policy?: JsonObject
  output_contract?: JsonObject
}

export interface ListProjectsOptions {
  workspace_id?: string
  limit?: number
}

export interface ListResearchCasesOptions {
  project_id?: string
  limit?: number
}
