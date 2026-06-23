import { dogeClient } from './client'
import type {
  CapabilitySnapshot,
  AddCaseAssetPayload,
  CaseAssetLink,
  CaseDecision,
  CaseExecutionPayload,
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
} from '../types/platform'

export async function fetchCapabilities(): Promise<CapabilitySnapshot> {
  return await dogeClient.capabilities.get() as unknown as CapabilitySnapshot
}

export async function fetchHomeQueue(limit = 20): Promise<HomeQueue> {
  return await dogeClient.request('GET', `/v1/home-queue?limit=${limit}`) as unknown as HomeQueue
}

export async function listWorkspaces(limit = 100): Promise<Workspace[]> {
  return await dogeClient.platform.listWorkspaces(limit) as unknown as Workspace[]
}

export async function createWorkspace(payload: CreateWorkspacePayload): Promise<Workspace> {
  return await dogeClient.platform.createWorkspace(
    payload.name,
    payload.description ?? '',
  ) as unknown as Workspace
}

export async function getWorkspace(workspaceId: string): Promise<Workspace> {
  return await dogeClient.platform.getWorkspace(workspaceId) as unknown as Workspace
}

export async function listProjects(options: ListProjectsOptions = {}): Promise<Project[]> {
  const items = await dogeClient.platform.listProjects({
    workspaceId: options.workspace_id,
    limit: options.limit,
  })
  return items as unknown as Project[]
}

export async function createProject(payload: CreateProjectPayload): Promise<Project> {
  return await dogeClient.platform.createProject(payload.workspace_id, payload.name, {
    description: payload.description ?? '',
    defaultMarket: payload.default_market ?? undefined,
  }) as unknown as Project
}

export async function getProject(projectId: string): Promise<Project> {
  return await dogeClient.platform.getProject(projectId) as unknown as Project
}

export async function listResearchCases(options: ListResearchCasesOptions = {}): Promise<ResearchCase[]> {
  const items = await dogeClient.platform.listResearchCases({
    projectId: options.project_id,
    limit: options.limit,
  })
  return items as unknown as ResearchCase[]
}

export async function createResearchCase(payload: CreateResearchCasePayload): Promise<ResearchCase> {
  return await dogeClient.platform.createResearchCase(
    payload.project_id,
    payload.title,
    payload.thesis ?? '',
  ) as unknown as ResearchCase
}

export async function getResearchCase(caseId: string): Promise<ResearchCase> {
  return await dogeClient.platform.getResearchCase(caseId) as unknown as ResearchCase
}

export async function listCaseAssets(caseId: string): Promise<CaseAssetLink[]> {
  const payload = await dogeClient.request<{ assets: CaseAssetLink[] }>(
    'GET',
    `/v1/research-cases/${caseId}/assets`,
  )
  return payload.assets
}

export async function addCaseAsset(caseId: string, payload: AddCaseAssetPayload): Promise<CaseAssetLink> {
  return await dogeClient.request(
    'POST',
    `/v1/research-cases/${caseId}/assets`,
    payload,
  ) as unknown as CaseAssetLink
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
  return await dogeClient.request(
    'POST',
    `/v1/research-cases/${caseId}/decisions`,
    payload,
  ) as unknown as CaseDecision
}

export async function preflightCaseExecution(
  caseId: string,
  payload: CaseExecutionPayload,
): Promise<TemplatePreflightResult> {
  return await dogeClient.request(
    'POST',
    `/v1/research-cases/${caseId}/executions/preflight`,
    payload,
  ) as unknown as TemplatePreflightResult
}

export async function executeCaseTemplate(
  caseId: string,
  payload: CaseExecutionPayload,
): Promise<WorkflowExecution> {
  return await dogeClient.request(
    'POST',
    `/v1/research-cases/${caseId}/executions`,
    payload,
  ) as unknown as WorkflowExecution
}

export async function listCaseExecutions(caseId: string): Promise<WorkflowExecution[]> {
  const payload = await dogeClient.request<{ executions: WorkflowExecution[] }>(
    'GET',
    `/v1/research-cases/${caseId}/executions`,
  )
  return payload.executions
}

export async function getCaseReview(caseId: string): Promise<CaseReview> {
  return await dogeClient.request('GET', `/v1/research-cases/${caseId}/review`) as unknown as CaseReview
}

export async function linkResearchCaseRun(
  caseId: string,
  payload: LinkResearchCaseRunPayload,
): Promise<CaseRunLink> {
  return await dogeClient.platform.linkResearchCaseRun(
    caseId,
    payload.run_id,
    payload.link_type ?? 'primary',
  ) as unknown as CaseRunLink
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
  }) as unknown as CaseRunLink
}

export async function listWorkflowTemplates(limit = 100): Promise<WorkflowTemplate[]> {
  return await dogeClient.platform.listWorkflowTemplates(limit) as unknown as WorkflowTemplate[]
}

export async function createWorkflowTemplate(payload: CreateWorkflowTemplatePayload): Promise<WorkflowTemplate> {
  return await dogeClient.request('POST', '/v1/workflow-templates', {
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
  }) as unknown as WorkflowTemplate
}

export async function getWorkflowTemplate(templateId: string): Promise<WorkflowTemplate> {
  return await dogeClient.platform.getWorkflowTemplate(templateId) as unknown as WorkflowTemplate
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
