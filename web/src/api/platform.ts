import { dogeClient } from './client'
import type {
  CapabilitySnapshot,
  CaseRunLink,
  CreateProjectPayload,
  CreateResearchCasePayload,
  CreateResearchCaseRunFromTemplatePayload,
  CreateWorkflowTemplatePayload,
  CreateWorkspacePayload,
  LinkResearchCaseRunPayload,
  ListProjectsOptions,
  ListResearchCasesOptions,
  Project,
  ResearchCase,
  RunCitation,
  RunClaim,
  RunEval,
  RunSummary,
  RunSummaryResources,
  WorkflowTemplate,
  Workspace,
} from '../types/platform'

export async function fetchCapabilities(): Promise<CapabilitySnapshot> {
  return await dogeClient.capabilities.get() as unknown as CapabilitySnapshot
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
  return await dogeClient.platform.createWorkflowTemplate(payload.slug, payload.name, {
    description: payload.description ?? '',
    currentVersion: payload.current_version ?? '1',
    inputSchema: payload.input_schema ?? {},
    runInstructions: payload.run_instructions ?? '',
    toolPolicy: payload.tool_policy ?? {},
    evidencePolicy: payload.evidence_policy ?? {},
    outputContract: payload.output_contract ?? {},
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
