import { setActivePinia, createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createProject,
  createResearchCase,
  createResearchCaseRunFromTemplate,
  createWorkflowTemplate,
  createWorkspace,
  fetchCapabilities,
  fetchRunSummaryResources,
  getProject,
  getResearchCase,
  getWorkflowTemplate,
  getWorkspace,
  linkResearchCaseRun,
  listProjects,
  listResearchCases,
  listWorkflowTemplates,
  listWorkspaces,
} from '../api/platform'
import { usePlatformStore } from './platform'

vi.mock('../api/platform', () => ({
  fetchCapabilities: vi.fn(),
  fetchRunSummaryResources: vi.fn(),
  listWorkspaces: vi.fn(),
  listProjects: vi.fn(),
  listResearchCases: vi.fn(),
  listWorkflowTemplates: vi.fn(),
  getWorkspace: vi.fn(),
  getProject: vi.fn(),
  getResearchCase: vi.fn(),
  getWorkflowTemplate: vi.fn(),
  createWorkspace: vi.fn(),
  createProject: vi.fn(),
  createResearchCase: vi.fn(),
  createResearchCaseRunFromTemplate: vi.fn(),
  createWorkflowTemplate: vi.fn(),
  linkResearchCaseRun: vi.fn(),
}))

describe('platform store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(fetchCapabilities).mockResolvedValue({
      snapshot_id: 'cap-1',
      generated_at: '2026-06-22T00:00:00Z',
      redaction_version: 'doge.capability_redaction.v1',
      status_counts: { available: 1 },
      capabilities: [{
        capability_id: 'feature.platform_objects',
        kind: 'ui',
        name: 'Platform Objects',
        status: 'available',
        risk_level: 'low',
        requires_approval: false,
        metadata: {},
      }],
    })
    vi.mocked(listWorkspaces).mockResolvedValue([workspace('wsp-1', 'Desk')])
    vi.mocked(listProjects).mockResolvedValue([project('prj-1', 'wsp-1', 'Research')])
    vi.mocked(listResearchCases).mockResolvedValue([researchCase('case-1', 'prj-1')])
    vi.mocked(listWorkflowTemplates).mockResolvedValue([workflowTemplate('tpl-1')])
    vi.mocked(getWorkspace).mockResolvedValue(workspace('wsp-1', 'Desk'))
    vi.mocked(getProject).mockResolvedValue(project('prj-1', 'wsp-1', 'Research'))
    vi.mocked(getResearchCase).mockResolvedValue(researchCase('case-1', 'prj-1'))
    vi.mocked(getWorkflowTemplate).mockResolvedValue(workflowTemplate('tpl-1'))
    vi.mocked(createWorkspace).mockResolvedValue(workspace('wsp-2', 'Desk 2'))
    vi.mocked(createProject).mockResolvedValue(project('prj-2', 'wsp-2', 'Second Research'))
    vi.mocked(createResearchCase).mockResolvedValue(researchCase('case-2', 'prj-2'))
    vi.mocked(createWorkflowTemplate).mockResolvedValue(workflowTemplate('tpl-2'))
    vi.mocked(createResearchCaseRunFromTemplate).mockResolvedValue({
      case_id: 'case-2',
      run_id: 'run-template',
      link_type: 'primary',
      tenant_id: null,
      linked_at: '2026-06-22T00:00:00Z',
    })
    vi.mocked(linkResearchCaseRun).mockResolvedValue({
      case_id: 'case-2',
      run_id: 'run-1',
      link_type: 'primary',
      tenant_id: null,
      linked_at: '2026-06-22T00:00:00Z',
    })
    vi.mocked(fetchRunSummaryResources).mockResolvedValue({
      summary: {
        summary_id: 'sum-1',
        run_id: 'run-1',
        status: 'current',
        run_status: 'completed',
        summary_text: 'Summary',
        source_artifact_id: 'art-1',
        source_event_high_watermark: 4,
        created_at: '2026-06-22T00:00:00Z',
        updated_at: '2026-06-22T00:00:00Z',
      },
      claims: [{
        claim_id: 'clm-1',
        summary_id: 'sum-1',
        run_id: 'run-1',
        claim_text: 'Revenue improved',
        support_status: 'supported',
        evidence_count: 1,
        source: 'artifact',
      }],
      citations: [{
        citation_id: 'cit-1',
        run_id: 'run-1',
        claim_id: 'clm-1',
        evidence_id: 'ev-1',
        document_id: 'doc-1',
        page_id: null,
        chunk_id: null,
        page_number: 2,
        source: 'doc-1 p.2',
        snippet: 'Revenue improved',
        snippet_hash: 'hash',
        provider_file_id: null,
        accessible: true,
      }],
      eval: {
        eval_id: 'eval-1',
        run_id: 'run-1',
        summary_id: 'sum-1',
        coverage_ratio: 1,
        claim_count: 1,
        supported_claim_count: 1,
        citation_count: 1,
        accessible_citation_count: 1,
        failed_checks: [],
        metrics: {},
      },
    })
  })

  it('loads platform snapshots and indexes parent-child objects', async () => {
    const store = usePlatformStore()

    await store.loadCapabilities()
    await store.loadWorkspaces()
    await store.loadProjects({ workspace_id: 'wsp-1' })
    await store.loadProject('prj-1')
    await store.loadResearchCases({ project_id: 'prj-1' })
    await store.loadResearchCase('case-1')
    await store.loadWorkflowTemplates()

    expect(store.loading).toBe(false)
    expect(store.capabilitiesById['feature.platform_objects'].status).toBe('available')
    expect(store.workspaces[0].workspace_id).toBe('wsp-1')
    expect(store.projectsById['prj-1'].name).toBe('Research')
    expect(store.researchCasesById['case-1'].title).toBe('Case')
    expect(store.projectsByWorkspaceId['wsp-1'][0].project_id).toBe('prj-1')
    expect(store.casesByProjectId['prj-1'][0].case_id).toBe('case-1')
    expect(store.workflowTemplates[0].template_id).toBe('tpl-1')
  })

  it('creates objects, links runs, and caches run summary resources', async () => {
    const store = usePlatformStore()

    const createdWorkspace = await store.createWorkspace({ name: 'Desk 2' })
    const createdProject = await store.createProject({ workspace_id: createdWorkspace.workspace_id, name: 'Second Research' })
    const createdCase = await store.createResearchCase({ project_id: createdProject.project_id, title: 'Case 2' })
    const createdTemplate = await store.createWorkflowTemplate({ slug: 'stock', name: 'Stock Research' })
    const link = await store.linkResearchCaseRun(createdCase.case_id, { run_id: 'run-1' })
    const templateLink = await store.createResearchCaseRunFromTemplate(createdCase.case_id, {
      template_id: createdTemplate.template_id,
      question: 'Analyze NVDA',
      inputs: { ticker: 'NVDA' },
    })
    const resources = await store.loadRunSummaryResources('run-1')

    expect(store.workspaces[0].workspace_id).toBe('wsp-2')
    expect(store.projects[0].project_id).toBe('prj-2')
    expect(store.researchCases[0].case_id).toBe('case-2')
    expect(createdTemplate.template_id).toBe('tpl-2')
    expect(store.workflowTemplates[0].template_id).toBe('tpl-2')
    expect(link.run_id).toBe('run-1')
    expect(templateLink.run_id).toBe('run-template')
    expect(store.caseRunLinks[0].case_id).toBe('case-2')
    expect(resources.eval.coverage_ratio).toBe(1)
    expect(store.runResourcesById['run-1'].summary.summary_id).toBe('sum-1')
    expect(linkResearchCaseRun).toHaveBeenCalledWith('case-2', { run_id: 'run-1' })
    expect(createResearchCaseRunFromTemplate).toHaveBeenCalledWith('case-2', {
      template_id: 'tpl-2',
      question: 'Analyze NVDA',
      inputs: { ticker: 'NVDA' },
    })
    expect(fetchRunSummaryResources).toHaveBeenCalledWith('run-1')
  })

  it('surfaces request errors and clears loading state', async () => {
    vi.mocked(listWorkspaces).mockRejectedValueOnce(new Error('platform disabled'))
    const store = usePlatformStore()

    await expect(store.loadWorkspaces()).rejects.toThrow('platform disabled')

    expect(store.loading).toBe(false)
    expect(store.error).toEqual({
      code: 'fetch_failed',
      message: 'platform disabled',
    })
  })
})

function workspace(workspaceId: string, name: string) {
  return {
    workspace_id: workspaceId,
    name,
    description: '',
    status: 'active',
    tenant_id: null,
    metadata: {},
    created_at: '2026-06-22T00:00:00Z',
    updated_at: '2026-06-22T00:00:00Z',
    deleted_at: null,
  }
}

function project(projectId: string, workspaceId: string, name: string) {
  return {
    project_id: projectId,
    workspace_id: workspaceId,
    name,
    description: '',
    status: 'active',
    default_market: 'us',
    tenant_id: null,
    metadata: {},
    created_at: '2026-06-22T00:00:00Z',
    updated_at: '2026-06-22T00:00:00Z',
    deleted_at: null,
  }
}

function researchCase(caseId: string, projectId: string) {
  return {
    case_id: caseId,
    project_id: projectId,
    title: 'Case',
    thesis: '',
    status: 'open',
    decision: null,
    tenant_id: null,
    metadata: {},
    created_at: '2026-06-22T00:00:00Z',
    updated_at: '2026-06-22T00:00:00Z',
    deleted_at: null,
  }
}

function workflowTemplate(templateId: string) {
  return {
    template_id: templateId,
    slug: 'stock',
    name: 'Stock Research',
    description: '',
    status: 'active',
    current_version: '1',
    input_schema: {},
    run_instructions: '',
    tool_policy: {},
    evidence_policy: {},
    output_contract: {},
    tenant_id: null,
    metadata: {},
    created_at: '2026-06-22T00:00:00Z',
    updated_at: '2026-06-22T00:00:00Z',
  }
}
