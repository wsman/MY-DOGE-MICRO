import { dogeClient } from './client'
import type {
  CapabilitySnapshot,
  AddCaseAssetPayload,
  CaseAssetLink,
  CaseDecision,
  CaseExecutionPayload,
  CaseProgressStep,
  CaseReview,
  CaseRunLink,
  CreateProjectPayload,
  CreateResearchCasePayload,
  CreateResearchCaseRunFromTemplatePayload,
  CreateWorkflowTemplatePayload,
  CreateWorkspacePayload,
  LinkResearchCaseRunPayload,
  ListProjectsOptions,
  ListResearchCasesOptions,
  HomeQueue,
  Project,
  RecordCaseDecisionPayload,
  ResearchCase,
  RunCitation,
  RunClaim,
  RunEval,
  RunSummary,
  RunSummaryResources,
  TemplatePreflightResult,
  WorkflowExecution,
  WorkflowTemplate,
  Workspace,
} from 'doge-sdk'

export interface UiPanel {
  panel_id: string
  workspace: string
  zone: string
  component_module: string
  order: number
  modes: string[]
  required_artifact_fields: string[]
  label: string | null
}

export interface UiPanelListResponse {
  panels: UiPanel[]
}

export interface SlotStatusRow {
  id: string
  name: string
  version: string
  type: string
  owner: string
  maturity: string
  description: string
  entrypoint: string
  status: string
  feature_flags: string[]
  provides: {
    tools: string[]
    capabilities: string[]
    metadata: Record<string, unknown>
  }
  requires: Array<{
    kind: string
    id: string
    optional: boolean
  }>
  permissions: {
    filesystem: string
    network: string
    shell: string
    database: string
    secrets: string[]
    risk_level: string
  }
  health: {
    status: string
    notes: string
  }
  compatibility: {
    runtime_min: string
    replaces: string[]
    breaking: boolean
  }
  counts: {
    tools: number
    capabilities: number
  }
}

export interface SlotListResponse {
  slots: SlotStatusRow[]
}

export interface SlotBundleRow {
  id: string
  name: string
  description: string
  active: boolean
  status: string
  slot_ids: string[]
  enabled_slot_ids: string[]
  disabled_slot_ids: string[]
  missing_slot_ids: string[]
  maturity: string
  counts: {
    slots: number
    enabled: number
    disabled: number
    missing: number
  }
}

export interface SlotBundleListResponse {
  bundles: SlotBundleRow[]
}

export interface SlotBundleActivationResponse {
  status: string
  active_bundle_id: string | null
  bundle?: SlotBundleRow
}

export async function fetchCapabilities(): Promise<CapabilitySnapshot> {
  return await dogeClient.capabilities.get()
}

export async function fetchHomeQueue(limit = 20): Promise<HomeQueue> {
  return await dogeClient.request<HomeQueue>('GET', `/v1/home-queue?limit=${limit}`)
}

export async function listUiPanels(workspace = 'research_workspace'): Promise<UiPanel[]> {
  const params = new URLSearchParams({ workspace })
  const payload = await dogeClient.request<UiPanelListResponse>('GET', `/v1/ui-panels?${params.toString()}`)
  return payload.panels
}

export async function listSlots(): Promise<SlotStatusRow[]> {
  const payload = await dogeClient.request<SlotListResponse>('GET', '/v1/slots')
  return payload.slots
}

export async function listSlotBundles(): Promise<SlotBundleRow[]> {
  const payload = await dogeClient.request<SlotBundleListResponse>('GET', '/v1/slot-bundles')
  return payload.bundles
}

export async function activateSlotBundle(bundleId: string): Promise<SlotBundleActivationResponse> {
  return await dogeClient.request<SlotBundleActivationResponse>('POST', `/v1/slot-bundles/${bundleId}/activate`)
}

export async function deactivateSlotBundle(): Promise<SlotBundleActivationResponse> {
  return await dogeClient.request<SlotBundleActivationResponse>('POST', '/v1/slot-bundles/active/deactivate')
}

export async function listWorkspaces(limit = 100): Promise<Workspace[]> {
  return await dogeClient.platform.listWorkspaces(limit)
}

export async function createWorkspace(payload: CreateWorkspacePayload): Promise<Workspace> {
  return await dogeClient.platform.createWorkspace(
    payload.name,
    payload.description ?? '',
  )
}

export async function getWorkspace(workspaceId: string): Promise<Workspace> {
  return await dogeClient.platform.getWorkspace(workspaceId)
}

export async function listProjects(options: ListProjectsOptions = {}): Promise<Project[]> {
  return await dogeClient.platform.listProjects({
    workspaceId: options.workspace_id,
    limit: options.limit,
  })
}

export async function createProject(payload: CreateProjectPayload): Promise<Project> {
  return await dogeClient.platform.createProject(payload.workspace_id, payload.name, {
    description: payload.description ?? '',
    defaultMarket: payload.default_market ?? undefined,
  })
}

export async function getProject(projectId: string): Promise<Project> {
  return await dogeClient.platform.getProject(projectId)
}

export async function listResearchCases(options: ListResearchCasesOptions = {}): Promise<ResearchCase[]> {
  return await dogeClient.platform.listResearchCases({
    projectId: options.project_id,
    limit: options.limit,
  })
}

export async function createResearchCase(payload: CreateResearchCasePayload): Promise<ResearchCase> {
  return await dogeClient.platform.createResearchCase(
    payload.project_id,
    payload.title,
    payload.thesis ?? '',
  )
}

export async function getResearchCase(caseId: string): Promise<ResearchCase> {
  return await dogeClient.platform.getResearchCase(caseId)
}

export async function getCaseProgress(caseId: string): Promise<CaseProgressStep[]> {
  return await dogeClient.platform.getCaseProgress(caseId)
}

export async function listCaseAssets(caseId: string): Promise<CaseAssetLink[]> {
  const payload = await dogeClient.request<{ assets: CaseAssetLink[] }>(
    'GET',
    `/v1/research-cases/${caseId}/assets`,
  )
  return payload.assets
}

export async function addCaseAsset(caseId: string, payload: AddCaseAssetPayload): Promise<CaseAssetLink> {
  return await dogeClient.request<CaseAssetLink>(
    'POST',
    `/v1/research-cases/${caseId}/assets`,
    payload,
  )
}

export async function listCaseDecisions(caseId: string): Promise<CaseDecision[]> {
  const payload = await dogeClient.request<{ decisions: CaseDecision[] }>(
    'GET',
    `/v1/research-cases/${caseId}/decisions`,
  )
  return payload.decisions
}

export async function recordCaseDecision(
  caseId: string,
  payload: RecordCaseDecisionPayload,
): Promise<CaseDecision> {
  return await dogeClient.request<CaseDecision>(
    'POST',
    `/v1/research-cases/${caseId}/decisions`,
    payload,
  )
}

export async function preflightCaseExecution(
  caseId: string,
  payload: CaseExecutionPayload,
): Promise<TemplatePreflightResult> {
  return await dogeClient.request<TemplatePreflightResult>(
    'POST',
    `/v1/research-cases/${caseId}/executions/preflight`,
    payload,
  )
}

export async function executeCaseTemplate(
  caseId: string,
  payload: CaseExecutionPayload,
): Promise<WorkflowExecution> {
  return await dogeClient.request<WorkflowExecution>(
    'POST',
    `/v1/research-cases/${caseId}/executions`,
    payload,
  )
}

export async function listCaseExecutions(caseId: string): Promise<WorkflowExecution[]> {
  const payload = await dogeClient.request<{ executions: WorkflowExecution[] }>(
    'GET',
    `/v1/research-cases/${caseId}/executions`,
  )
  return payload.executions
}

export async function getCaseReview(caseId: string): Promise<CaseReview> {
  return await dogeClient.request<CaseReview>('GET', `/v1/research-cases/${caseId}/review`)
}

export async function linkResearchCaseRun(
  caseId: string,
  payload: LinkResearchCaseRunPayload,
): Promise<CaseRunLink> {
  return await dogeClient.platform.linkResearchCaseRun(
    caseId,
    payload.run_id,
    payload.link_type ?? 'primary',
  )
}

export async function createResearchCaseRunFromTemplate(
  caseId: string,
  payload: CreateResearchCaseRunFromTemplatePayload,
): Promise<CaseRunLink> {
  return await dogeClient.platform.createResearchCaseRunFromTemplate(caseId, payload.template_id, {
    question: payload.question,
    modelPolicy: payload.model_policy ?? {},
    inputs: payload.inputs ?? {},
    workflow: payload.workflow,
    sessionId: payload.session_id,
    market: payload.market ?? 'us',
    language: payload.language ?? 'en',
    documentIds: payload.document_ids ?? [],
    portfolioId: payload.portfolio_id ?? undefined,
    linkType: payload.link_type ?? 'primary',
  })
}

export async function listWorkflowTemplates(limit = 100): Promise<WorkflowTemplate[]> {
  return await dogeClient.platform.listWorkflowTemplates(limit)
}

export async function createWorkflowTemplate(payload: CreateWorkflowTemplatePayload): Promise<WorkflowTemplate> {
  return await dogeClient.request<WorkflowTemplate>('POST', '/v1/workflow-templates', {
    slug: payload.slug,
    name: payload.name,
    description: payload.description ?? '',
    current_version: payload.current_version ?? '1',
    input_schema: payload.input_schema ?? {},
    run_instructions: payload.run_instructions ?? '',
    tool_policy: payload.tool_policy ?? {},
    evidence_policy: payload.evidence_policy ?? {},
    output_contract: payload.output_contract ?? {},
    metadata: payload.metadata ?? {},
    required_capabilities: payload.required_capabilities ?? undefined,
    eval_policy: payload.eval_policy ?? undefined,
    approval_policy: payload.approval_policy ?? undefined,
    ui_schema: payload.ui_schema ?? undefined,
  })
}

export async function getWorkflowTemplate(templateId: string): Promise<WorkflowTemplate> {
  return await dogeClient.platform.getWorkflowTemplate(templateId)
}

export async function fetchRunSummary(runId: string): Promise<RunSummary> {
  return await dogeClient.runs.summary(runId) as unknown as RunSummary
}

export async function fetchRunClaims(runId: string): Promise<RunClaim[]> {
  return await dogeClient.runs.claims(runId) as unknown as RunClaim[]
}

export async function fetchRunCitations(runId: string): Promise<RunCitation[]> {
  return await dogeClient.runs.citations(runId) as unknown as RunCitation[]
}

export async function fetchRunEval(runId: string): Promise<RunEval> {
  return await dogeClient.runs.evaluation(runId) as unknown as RunEval
}

export async function fetchRunSummaryResources(runId: string): Promise<RunSummaryResources> {
  const [summary, claims, citations, evaluation] = await Promise.all([
    fetchRunSummary(runId),
    fetchRunClaims(runId),
    fetchRunCitations(runId),
    fetchRunEval(runId),
  ])
  return {
    summary,
    claims,
    citations,
    eval: evaluation,
  }
}
