import { DogeApiError, type DogeEvent } from './run.js'
import { Session, type AgentSession } from './session.js'
import { parseSse } from './streaming.js'

interface DogeClientOptions {
  baseUrl?: string
  apiToken?: string
  requestId?: string
}

export interface RunStreamOptions {
  lastEventId?: string
  reconnect?: boolean
  maxReconnects?: number
  backoffMs?: number
  sleep?: (milliseconds: number) => Promise<void>
}

export class DogeClient {
  readonly sessions: SessionsResource
  readonly runs: RunsResource
  readonly documents: DocumentsResource
  readonly platform: PlatformResource
  readonly capabilities: CapabilitiesResource
  private readonly baseUrl: string
  private readonly apiToken?: string
  private readonly requestId?: string

  constructor(options: DogeClientOptions = {}) {
    this.baseUrl = options.baseUrl?.replace(/\/$/, '') ?? ''
    this.apiToken = options.apiToken
    this.requestId = options.requestId
    this.sessions = new SessionsResource(this)
    this.runs = new RunsResource(this)
    this.documents = new DocumentsResource(this)
    this.platform = new PlatformResource(this)
    this.capabilities = new CapabilitiesResource(this)
  }

  async request<T>(method: string, path: string, body?: unknown, extraHeaders: Record<string, string> = {}): Promise<T> {
    const headers = this.headers(extraHeaders)
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!response.ok) {
      const message = await responseErrorMessage(response)
      throw new DogeApiError(response.status, redactMessage(message, this.apiToken))
    }
    return await response.json() as T
  }

  async requestForm<T>(
    method: string,
    path: string,
    form: FormData,
    extraHeaders: Record<string, string> = {},
  ): Promise<T> {
    const headers = this.headers(extraHeaders)
    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: form,
    })
    if (!response.ok) {
      const message = await responseErrorMessage(response)
      throw new DogeApiError(response.status, redactMessage(message, this.apiToken))
    }
    return await response.json() as T
  }

  async stream(path: string, lastEventId?: string): Promise<AsyncGenerator<DogeEvent>> {
    const headers = this.headers()
    if (lastEventId) headers['Last-Event-ID'] = lastEventId
    const response = await fetch(`${this.baseUrl}${path}`, { headers })
    if (!response.ok || !response.body) {
      const message = await responseErrorMessage(response)
      throw new DogeApiError(response.status, redactMessage(message, this.apiToken))
    }
    return parseSse(response.body)
  }

  private headers(extraHeaders: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = { ...extraHeaders }
    if (this.apiToken) headers.Authorization = `Bearer ${this.apiToken}`
    if (this.requestId) headers['X-Request-ID'] = this.requestId
    return headers
  }
}

export class SessionsResource {
  private readonly root: DogeClient

  constructor(root: DogeClient) {
    this.root = root
  }

  async create(title = 'Research session'): Promise<Session> {
    const data = await this.root.request<AgentSession>('POST', '/v1/sessions', { title })
    return new Session(this.root, data)
  }

  async list(limit = 20): Promise<AgentSession[]> {
    const payload = await this.root.request<{ sessions: AgentSession[] }>('GET', `/v1/sessions?limit=${limit}`)
    return payload.sessions
  }

  async get(sessionId: string): Promise<Session> {
    const data = await this.root.request<AgentSession>('GET', `/v1/sessions/${sessionId}`)
    return new Session(this.root, data)
  }

  async createTurn(sessionId: string, message: string, options: Record<string, unknown> = {}): Promise<string> {
    const payload = await this.root.request<{ run_id: string }>(
      'POST',
      `/v1/sessions/${sessionId}/turns`,
      { message, ...options },
      { 'Idempotency-Key': crypto.randomUUID() },
    )
    return payload.run_id
  }
}

export class RunsResource {
  private readonly root: DogeClient

  constructor(root: DogeClient) {
    this.root = root
  }

  get(runId: string): Promise<Record<string, unknown>> {
    return this.root.request('GET', `/v1/runs/${runId}`)
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

  approve(runId: string, approvalId: string, approved = true): Promise<Record<string, unknown>> {
    return this.root.request('POST', `/v1/runs/${runId}/approvals/${approvalId}`, { approved })
  }

  cancel(runId: string): Promise<Record<string, unknown>> {
    return this.root.request('POST', `/v1/runs/${runId}/cancel`)
  }
}

function defaultSleep(milliseconds: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, milliseconds))
}

async function responseErrorMessage(response: Response): Promise<string> {
  let message = response.statusText
  let body = ''
  if (typeof response.text === 'function') {
    try {
      body = await response.text()
    } catch {
      body = ''
    }
  }
  if (body) {
    try {
      const payload = JSON.parse(body) as { error?: { message?: string }, detail?: string }
      return payload.error?.message ?? payload.detail ?? body
    } catch {
      return body
    }
  }
  try {
    const payload = await response.json() as { error?: { message?: string }, detail?: string }
    message = payload.error?.message ?? payload.detail ?? message
  } catch {
    // Keep statusText when the body cannot be read.
  }
  return message
}

function redactMessage(message: string, apiToken?: string): string {
  let redacted = message.replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/g, 'Bearer [REDACTED]')
  redacted = redacted.replace(
    /\b(api[_-]?key|password|secret|token|access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|moonshot_api_key|deepseek_api_key|doge_api_token)\s*([=:])\s*(['"]?)[^&\s,'"}]+/gi,
    (_match, key, separator) => `${key}${separator}[REDACTED]`,
  )
  redacted = redacted.replace(/\bsk-[A-Za-z0-9._-]{6,}/g, 'sk-[REDACTED]')
  if (apiToken) redacted = redacted.split(apiToken).join('[REDACTED]')
  return redacted
}

export class DocumentsResource {
  private readonly root: DogeClient

  constructor(root: DogeClient) {
    this.root = root
  }

  create(filename: string, content = ''): Promise<Record<string, unknown>> {
    return this.root.request('POST', '/v1/documents', { filename, content })
  }

  upload(file: Blob, filename?: string): Promise<Record<string, unknown>> {
    const form = new FormData()
    form.append('file', file, filename ?? _blobFilename(file))
    return this.root.requestForm('POST', '/v1/documents', form)
  }

  async list(limit = 100): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ documents: Record<string, unknown>[] }>(
      'GET',
      `/v1/documents?limit=${limit}`,
    )
    return payload.documents
  }

  get(documentId: string): Promise<Record<string, unknown>> {
    return this.root.request('GET', `/v1/documents/${documentId}`)
  }
}

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

function _blobFilename(file: Blob): string {
  const maybeNamed = file as Blob & { name?: unknown }
  return typeof maybeNamed.name === 'string' && maybeNamed.name ? maybeNamed.name : 'document'
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
