/**
 * Platform entity and payload types — the SDK source of truth.
 *
 * These are the wire-shape (snake_case) types returned by the `/v1` platform and
 * capability endpoints and consumed by the TypeScript SDK's `PlatformResource` /
 * `CapabilitiesResource`. The Web app imports these from `doge-sdk` so the SDK is
 * the single type source and the Web client no longer maintains a second copy.
 *
 * Sprint 018 (Product Surface & SDK Contract Convergence).
 * Moved verbatim from `web/src/types/platform.ts`; do not re-introduce a Web-local copy.
 */
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

export interface CaseAssetLink {
  asset_link_id: string
  case_id: string
  asset_type: string
  asset_id: string
  asset_name: string
  role: string
  version?: string | null
  metadata: JsonObject
  tenant_id?: string | null
  linked_at: string
  deleted_at?: string | null
}

export interface WorkflowExecution {
  execution_id: string
  case_id: string
  template_id: string
  template_slug: string
  template_version: string
  run_id?: string | null
  status: string
  input_snapshot: JsonObject
  preflight_result: JsonObject
  trigger_channel: string
  tenant_id?: string | null
  created_at: string
  updated_at: string
  run_status?: string
  links?: Record<string, string>
}

export interface CaseDecision {
  decision_id: string
  case_id: string
  decision_type: string
  rationale: string
  actor_hash?: string | null
  source_run_ids: string[]
  source_execution_ids: string[]
  tenant_id?: string | null
  created_at: string
}

export interface TemplatePreflightResult {
  valid: boolean
  input_errors: JsonObject[]
  missing_capabilities: string[]
  missing_assets: JsonObject[]
  warnings: string[]
  estimated_cost: JsonObject
}

export interface CaseReview {
  case: ResearchCase
  assets: CaseAssetLink[]
  executions: WorkflowExecution[]
  latest_run?: JsonObject | null
  approvals: JsonObject[]
  summary?: RunSummary | null
  claims: RunClaim[]
  citations: RunCitation[]
  eval?: RunEval | null
  decisions: CaseDecision[]
  warnings: string[]
}

export interface HomeQueue {
  pending_cases: JsonObject[]
  pending_approvals: JsonObject[]
  failed_or_degraded_runs: JsonObject[]
  recent_memos: JsonObject[]
  recent_executions: WorkflowExecution[]
  data_freshness?: JsonObject | null
  warnings: string[]
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
  status: string
  evidence_refs: JsonObject[]
  numeric_check_status: string
  risk_level: string
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
  claim_evidence_relation_count: number
  supported_relation_count: number
  partial_relation_count: number
  unrelated_relation_count: number
  classification_confidence_avg: number
  failed_checks: string[]
  numeric_validation: JsonObject
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

export interface CaseExecutionPayload {
  template_id: string
  question?: string
  workflow?: string
  session_id?: string
  market?: string
  language?: string
  document_ids?: string[]
  portfolio_id?: string | null
  asset_link_ids?: string[]
  model_policy?: JsonObject
  inputs?: JsonObject
  skip_preflight?: boolean
  trigger_channel?: string
}

export interface AddCaseAssetPayload {
  asset_type: string
  asset_id: string
  asset_name?: string
  role?: string
  version?: string | null
  metadata?: JsonObject
}

export interface RecordCaseDecisionPayload {
  decision_type: string
  rationale?: string
  source_run_ids?: string[]
  source_execution_ids?: string[]
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
  metadata?: JsonObject
  required_capabilities?: string[] | null
  eval_policy?: string[] | null
  approval_policy?: JsonObject | null
  ui_schema?: JsonObject | null
}

export interface ListProjectsOptions {
  workspace_id?: string
  limit?: number
}

export interface ListResearchCasesOptions {
  project_id?: string
  limit?: number
}
