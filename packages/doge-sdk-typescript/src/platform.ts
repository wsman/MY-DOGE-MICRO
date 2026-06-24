import type { DogeClient } from './client.js'

interface ListProjectsOptions {
  workspaceId?: string
  limit?: number
}

interface ListResearchCasesOptions {
  projectId?: string
  limit?: number
}

interface CreateWorkflowTemplateOptions {
  description?: string
  currentVersion?: string
  inputSchema?: Record<string, unknown>
  runInstructions?: string
  toolPolicy?: Record<string, unknown>
  evidencePolicy?: Record<string, unknown>
  outputContract?: Record<string, unknown>
  metadata?: Record<string, unknown>
  requiredCapabilities?: string[]
  evalPolicy?: string[]
  approvalPolicy?: Record<string, unknown>
  uiSchema?: Record<string, unknown>
}

interface CreateResearchCaseRunFromTemplateOptions {
  question?: string
  modelPolicy?: Record<string, unknown>
  inputs?: Record<string, unknown>
  workflow?: string
  sessionId?: string
  market?: string
  language?: string
  documentIds?: string[]
  portfolioId?: string
  linkType?: string
}

interface CaseExecutionOptions {
  question?: string
  workflow?: string
  sessionId?: string
  market?: string
  language?: string
  documentIds?: string[]
  portfolioId?: string
  assetLinkIds?: string[]
  modelPolicy?: Record<string, unknown>
  inputs?: Record<string, unknown>
  skipPreflight?: boolean
}

export class PlatformResource {
  private readonly root: DogeClient

  constructor(root: DogeClient) {
    this.root = root
  }

  async listWorkspaces(limit = 100): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ workspaces: Record<string, unknown>[] }>(
      'GET',
      `/v1/workspaces?limit=${limit}`,
    )
    return payload.workspaces
  }

  createWorkspace(name: string, description = ''): Promise<Record<string, unknown>> {
    return this.root.request('POST', '/v1/workspaces', { name, description })
  }

  getWorkspace(workspaceId: string): Promise<Record<string, unknown>> {
    return this.root.request('GET', `/v1/workspaces/${workspaceId}`)
  }

  async listProjects(options: ListProjectsOptions = {}): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ projects: Record<string, unknown>[] }>(
      'GET',
      queryPath('/v1/projects', { workspace_id: options.workspaceId, limit: options.limit ?? 100 }),
    )
    return payload.projects
  }

  createProject(
    workspaceId: string,
    name: string,
    options: { description?: string, defaultMarket?: string } = {},
  ): Promise<Record<string, unknown>> {
    return this.root.request('POST', '/v1/projects', {
      workspace_id: workspaceId,
      name,
      description: options.description ?? '',
      default_market: options.defaultMarket,
    })
  }

  getProject(projectId: string): Promise<Record<string, unknown>> {
    return this.root.request('GET', `/v1/projects/${projectId}`)
  }

  async listResearchCases(options: ListResearchCasesOptions = {}): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ research_cases: Record<string, unknown>[] }>(
      'GET',
      queryPath('/v1/research-cases', { project_id: options.projectId, limit: options.limit ?? 100 }),
    )
    return payload.research_cases
  }

  createResearchCase(projectId: string, title: string, thesis = ''): Promise<Record<string, unknown>> {
    return this.root.request('POST', '/v1/research-cases', { project_id: projectId, title, thesis })
  }

  getResearchCase(caseId: string): Promise<Record<string, unknown>> {
    return this.root.request('GET', `/v1/research-cases/${caseId}`)
  }

  homeQueue(limit = 20): Promise<Record<string, unknown>> {
    return this.root.request('GET', `/v1/home-queue?limit=${limit}`)
  }

  linkResearchCaseRun(caseId: string, runId: string, linkType = 'primary'): Promise<Record<string, unknown>> {
    return this.root.request('POST', `/v1/research-cases/${caseId}/runs`, {
      run_id: runId,
      link_type: linkType,
    })
  }

  createResearchCaseRunFromTemplate(
    caseId: string,
    templateId: string,
    options: CreateResearchCaseRunFromTemplateOptions = {},
  ): Promise<Record<string, unknown>> {
    return this.root.request('POST', `/v1/research-cases/${caseId}/runs`, {
      template_id: templateId,
      question: options.question,
      model_policy: options.modelPolicy ?? {},
      inputs: options.inputs ?? {},
      workflow: options.workflow,
      session_id: options.sessionId,
      market: options.market ?? 'us',
      language: options.language ?? 'en',
      document_ids: options.documentIds ?? [],
      portfolio_id: options.portfolioId,
      link_type: options.linkType ?? 'primary',
    })
  }

  async listCaseAssets(caseId: string): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ assets: Record<string, unknown>[] }>(
      'GET',
      `/v1/research-cases/${caseId}/assets`,
    )
    return payload.assets
  }

  addCaseAsset(
    caseId: string,
    assetType: string,
    assetId: string,
    options: {
      assetName?: string
      role?: string
      version?: string
      metadata?: Record<string, unknown>
    } = {},
  ): Promise<Record<string, unknown>> {
    return this.root.request('POST', `/v1/research-cases/${caseId}/assets`, {
      asset_type: assetType,
      asset_id: assetId,
      asset_name: options.assetName ?? '',
      role: options.role ?? 'source',
      version: options.version,
      metadata: options.metadata ?? {},
    })
  }

  async listCaseDecisions(caseId: string): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ decisions: Record<string, unknown>[] }>(
      'GET',
      `/v1/research-cases/${caseId}/decisions`,
    )
    return payload.decisions
  }

  recordCaseDecision(
    caseId: string,
    decisionType: string,
    options: {
      rationale?: string
      sourceRunIds?: string[]
      sourceExecutionIds?: string[]
    } = {},
  ): Promise<Record<string, unknown>> {
    return this.root.request('POST', `/v1/research-cases/${caseId}/decisions`, {
      decision_type: decisionType,
      rationale: options.rationale ?? '',
      source_run_ids: options.sourceRunIds ?? [],
      source_execution_ids: options.sourceExecutionIds ?? [],
    })
  }

  preflightCaseExecution(
    caseId: string,
    templateId: string,
    options: CaseExecutionOptions = {},
  ): Promise<Record<string, unknown>> {
    return this.root.request(
      'POST',
      `/v1/research-cases/${caseId}/executions/preflight`,
      caseExecutionPayload(templateId, options),
    )
  }

  executeCaseTemplate(
    caseId: string,
    templateId: string,
    options: CaseExecutionOptions = {},
  ): Promise<Record<string, unknown>> {
    return this.root.request(
      'POST',
      `/v1/research-cases/${caseId}/executions`,
      caseExecutionPayload(templateId, options),
    )
  }

  async listCaseExecutions(caseId: string, limit = 100): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ executions: Record<string, unknown>[] }>(
      'GET',
      `/v1/research-cases/${caseId}/executions?limit=${limit}`,
    )
    return payload.executions
  }

  getCaseReview(caseId: string): Promise<Record<string, unknown>> {
    return this.root.request('GET', `/v1/research-cases/${caseId}/review`)
  }

  async listWorkflowTemplates(limit = 100): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ workflow_templates: Record<string, unknown>[] }>(
      'GET',
      `/v1/workflow-templates?limit=${limit}`,
    )
    return payload.workflow_templates
  }

  createWorkflowTemplate(
    slug: string,
    name: string,
    options: CreateWorkflowTemplateOptions = {},
  ): Promise<Record<string, unknown>> {
    return this.root.request('POST', '/v1/workflow-templates', {
      slug,
      name,
      description: options.description ?? '',
      current_version: options.currentVersion ?? '1',
      input_schema: options.inputSchema ?? {},
      run_instructions: options.runInstructions ?? '',
      tool_policy: options.toolPolicy ?? {},
      evidence_policy: options.evidencePolicy ?? {},
      output_contract: options.outputContract ?? {},
      metadata: options.metadata ?? {},
      required_capabilities: options.requiredCapabilities,
      eval_policy: options.evalPolicy,
      approval_policy: options.approvalPolicy,
      ui_schema: options.uiSchema,
    })
  }

  getWorkflowTemplate(templateId: string): Promise<Record<string, unknown>> {
    return this.root.request('GET', `/v1/workflow-templates/${templateId}`)
  }
}

export class CapabilitiesResource {
  private readonly root: DogeClient

  constructor(root: DogeClient) {
    this.root = root
  }

  get(): Promise<Record<string, unknown>> {
    return this.root.request('GET', '/v1/capabilities')
  }

  async list(): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ capabilities: Record<string, unknown>[] }>('GET', '/v1/capabilities')
    return payload.capabilities
  }
}

function queryPath(path: string, params: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) query.set(key, String(value))
  }
  const suffix = query.toString()
  return suffix ? `${path}?${suffix}` : path
}

function caseExecutionPayload(templateId: string, options: CaseExecutionOptions): Record<string, unknown> {
  return {
    template_id: templateId,
    question: options.question,
    workflow: options.workflow,
    session_id: options.sessionId,
    market: options.market ?? 'us',
    language: options.language ?? 'en',
    document_ids: options.documentIds ?? [],
    portfolio_id: options.portfolioId,
    asset_link_ids: options.assetLinkIds ?? [],
    model_policy: options.modelPolicy ?? {},
    inputs: options.inputs ?? {},
    skip_preflight: options.skipPreflight ?? false,
  }
}
