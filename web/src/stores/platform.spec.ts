import { setActivePinia, createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  activateSlotBundle,
  addCaseAsset,
  createProject,
  createResearchCase,
  createResearchCaseRunFromTemplate,
  createWorkflowTemplate,
  createWorkspace,
  deactivateSlotBundle,
  executeCaseTemplate,
  fetchCapabilities,
  fetchHomeQueue,
  fetchRunSummaryResources,
  getCaseProgress,
  getCaseReview,
  getProject,
  getResearchCase,
  getWorkflowTemplate,
  getWorkspace,
  linkResearchCaseRun,
  listCaseAssets,
  listCaseDecisions,
  listCaseExecutions,
  listProjects,
  listResearchCases,
  listSlotBundles,
  listSlots,
  listUiPanels,
  listWorkflowTemplates,
  listWorkspaces,
  preflightCaseExecution,
  recordCaseDecision,
} from '../api/platform'
import { usePlatformStore } from './platform'

vi.mock('../api/platform', () => ({
  activateSlotBundle: vi.fn(),
  fetchCapabilities: vi.fn(),
  fetchHomeQueue: vi.fn(),
  fetchRunSummaryResources: vi.fn(),
  getCaseProgress: vi.fn(),
  getCaseReview: vi.fn(),
  listWorkspaces: vi.fn(),
  listProjects: vi.fn(),
  listResearchCases: vi.fn(),
  listSlots: vi.fn(),
  listSlotBundles: vi.fn(),
  listUiPanels: vi.fn(),
  listWorkflowTemplates: vi.fn(),
  listCaseAssets: vi.fn(),
  listCaseExecutions: vi.fn(),
  listCaseDecisions: vi.fn(),
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
  preflightCaseExecution: vi.fn(),
  executeCaseTemplate: vi.fn(),
  deactivateSlotBundle: vi.fn(),
  addCaseAsset: vi.fn(),
  recordCaseDecision: vi.fn(),
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
    vi.mocked(listSlots).mockResolvedValue([slotRow('market.core')])
    vi.mocked(listSlotBundles).mockResolvedValue([slotBundle('bundle.research_workspace')])
    vi.mocked(activateSlotBundle).mockResolvedValue({
      status: 'activated',
      active_bundle_id: 'bundle.research_workspace',
    })
    vi.mocked(deactivateSlotBundle).mockResolvedValue({
      status: 'deactivated',
      active_bundle_id: null,
    })
    vi.mocked(listUiPanels).mockResolvedValue([uiPanel('guided_flow')])
    vi.mocked(listWorkflowTemplates).mockResolvedValue([workflowTemplate('tpl-1')])
    vi.mocked(listCaseAssets).mockResolvedValue([caseAsset('asset-1', 'case-1')])
    vi.mocked(listCaseExecutions).mockResolvedValue([workflowExecution('exec-1', 'case-1')])
    vi.mocked(getCaseProgress).mockResolvedValue([caseProgressStep('cps-1', 'case-1')])
    vi.mocked(listCaseDecisions).mockResolvedValue([caseDecision('dec-1', 'case-1')])
    vi.mocked(getWorkspace).mockResolvedValue(workspace('wsp-1', 'Desk'))
    vi.mocked(getProject).mockResolvedValue(project('prj-1', 'wsp-1', 'Research'))
    vi.mocked(getResearchCase).mockResolvedValue(researchCase('case-1', 'prj-1'))
    vi.mocked(getWorkflowTemplate).mockResolvedValue(workflowTemplate('tpl-1'))
    vi.mocked(getCaseReview).mockResolvedValue(caseReview('case-1'))
    vi.mocked(fetchHomeQueue).mockResolvedValue({
      pending_cases: [{ case: researchCase('case-1', 'prj-1'), reason: 'no_recent_execution' }],
      pending_approvals: [],
      failed_or_degraded_runs: [],
      recent_memos: [],
      recent_executions: [workflowExecution('exec-1', 'case-1')],
      data_freshness: null,
      warnings: ['data_freshness_unavailable'],
    })
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
    vi.mocked(preflightCaseExecution).mockResolvedValue({
      valid: true,
      input_errors: [],
      missing_capabilities: [],
      missing_assets: [],
      warnings: [],
      estimated_cost: {},
    })
    vi.mocked(executeCaseTemplate).mockResolvedValue(workflowExecution('exec-2', 'case-2'))
    vi.mocked(addCaseAsset).mockResolvedValue(caseAsset('asset-2', 'case-2'))
    vi.mocked(recordCaseDecision).mockResolvedValue(caseDecision('dec-2', 'case-2'))
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
        status: 'supported',
        evidence_refs: [{ evidence_id: 'ev-1', source: 'doc-1 p.2' }],
        numeric_check_status: 'not_applicable',
        risk_level: 'low',
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
        claim_evidence_relation_count: 1,
        supported_relation_count: 1,
        partial_relation_count: 0,
        unrelated_relation_count: 0,
        classification_confidence_avg: 1,
        failed_checks: [],
        numeric_validation: {},
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
    await store.loadSlots()
    await store.loadSlotBundles()
    await store.loadUiPanels()
    await store.loadWorkflowTemplates()
    await store.loadHomeQueue()

    expect(store.loading).toBe(false)
    expect(store.capabilitiesById['feature.platform_objects'].status).toBe('available')
    expect(store.workspaces[0].workspace_id).toBe('wsp-1')
    expect(store.projectsById['prj-1'].name).toBe('Research')
    expect(store.researchCasesById['case-1'].title).toBe('Case')
    expect(store.slotRowsById['market.core'].status).toBe('resolved')
    expect(store.slotBundlesById['bundle.research_workspace'].status).toBe('partial')
    expect(store.uiPanels[0].panel_id).toBe('guided_flow')
    expect(store.projectsByWorkspaceId['wsp-1'][0].project_id).toBe('prj-1')
    expect(store.casesByProjectId['prj-1'][0].case_id).toBe('case-1')
    expect(store.workflowTemplates[0].template_id).toBe('tpl-1')
    expect(store.workflowTemplatesBySlug.stock.template_id).toBe('tpl-1')
    expect(store.homeQueue?.pending_cases[0].reason).toBe('no_recent_execution')
  })

  it('creates objects, executes case templates, and caches run summary resources', async () => {
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
    const preflight = await store.preflightCaseExecution(createdCase.case_id, {
      template_id: createdTemplate.template_id,
      inputs: { ticker: 'NVDA' },
    })
    const execution = await store.executeCaseTemplate(createdCase.case_id, {
      template_id: createdTemplate.template_id,
      inputs: { ticker: 'NVDA' },
    })
    const asset = await store.addCaseAsset(createdCase.case_id, {
      asset_type: 'document',
      asset_id: 'doc-1',
    })
    const decision = await store.recordCaseDecision(createdCase.case_id, {
      decision_type: 'hold',
      rationale: 'Needs review',
    })
    const resources = await store.loadRunSummaryResources('run-1')

    expect(store.workspaces[0].workspace_id).toBe('wsp-2')
    expect(store.projects[0].project_id).toBe('prj-2')
    expect(store.researchCases[0].case_id).toBe('case-2')
    expect(createdTemplate.template_id).toBe('tpl-2')
    expect(store.workflowTemplates[0].template_id).toBe('tpl-2')
    expect(link.run_id).toBe('run-1')
    expect(templateLink.run_id).toBe('run-template')
    expect(preflight.valid).toBe(true)
    expect(execution.execution_id).toBe('exec-2')
    expect(asset.asset_link_id).toBe('asset-2')
    expect(decision.decision_id).toBe('dec-2')
    expect(store.caseRunLinks[0].case_id).toBe('case-2')
    expect(store.workflowExecutionsByCaseId['case-2'][0].execution_id).toBe('exec-2')
    expect(store.caseAssetsByCaseId['case-2'][0].asset_link_id).toBe('asset-2')
    expect(store.caseDecisionsByCaseId['case-2'][0].decision_id).toBe('dec-2')
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

  it('loads a complete case workspace snapshot', async () => {
    const store = usePlatformStore()

    await store.loadCaseWorkspace('case-1')

    expect(store.researchCasesById['case-1'].title).toBe('Case')
    expect(store.caseAssetsByCaseId['case-1'][0].asset_link_id).toBe('asset-1')
    expect(store.workflowExecutionsByCaseId['case-1'][0].execution_id).toBe('exec-1')
    expect(store.caseProgressByCaseId['case-1'][0].step_key).toBe('workflow')
    expect(store.caseDecisionsByCaseId['case-1'][0].decision_id).toBe('dec-1')
    expect(store.caseReviewByCaseId['case-1'].case.case_id).toBe('case-1')
    expect(store.caseReviewByCaseId['case-1'].approvals[0].approval_id).toBe('appr-1')
  })

  it('activates a slot bundle and refreshes slot center snapshots', async () => {
    vi.mocked(listSlots).mockResolvedValueOnce([slotRow('market.core', 'resolved')])
    vi.mocked(listSlotBundles).mockResolvedValueOnce([slotBundle('bundle.research_workspace', true)])
    const store = usePlatformStore()

    const payload = await store.activateSlotBundle('bundle.research_workspace')

    expect(activateSlotBundle).toHaveBeenCalledWith('bundle.research_workspace')
    expect(payload.active_bundle_id).toBe('bundle.research_workspace')
    expect(store.slotRowsById['market.core'].status).toBe('resolved')
    expect(store.slotBundlesById['bundle.research_workspace'].active).toBe(true)
  })

  it('deactivates the active slot bundle and refreshes slot center snapshots', async () => {
    vi.mocked(listSlots).mockResolvedValueOnce([slotRow('market.core', 'resolved')])
    vi.mocked(listSlotBundles).mockResolvedValueOnce([slotBundle('bundle.research_workspace', false)])
    const store = usePlatformStore()

    const payload = await store.deactivateSlotBundle()

    expect(deactivateSlotBundle).toHaveBeenCalledWith()
    expect(payload.active_bundle_id).toBeNull()
    expect(store.slotRowsById['market.core'].status).toBe('resolved')
    expect(store.slotBundlesById['bundle.research_workspace'].active).toBe(false)
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

function uiPanel(panelId: string) {
  return {
    panel_id: panelId,
    workspace: 'research_workspace',
    zone: 'research.input',
    component_module: 'components/agent/GuidedFlow.vue',
    order: 10,
    modes: ['analyst', 'developer'],
    required_artifact_fields: [],
    label: 'Guided Flow',
  }
}

function slotRow(slotId: string, status = 'resolved') {
  return {
    id: slotId,
    name: 'Market Core',
    version: '0.1.0',
    type: 'tool',
    owner: 'market',
    maturity: 'alpha',
    description: 'Market tools',
    entrypoint: 'doge.products.market.slot.MarketCoreSlot',
    status,
    feature_flags: ['slot_platform'],
    provides: {
      tools: ['query_stock'],
      capabilities: ['market.read'],
      metadata: {},
    },
    requires: [],
    permissions: {
      filesystem: 'none',
      network: 'none',
      shell: 'none',
      database: 'none',
      secrets: [],
      risk_level: 'low',
    },
    health: {
      status: 'experimental',
      notes: '',
    },
    compatibility: {
      runtime_min: '1',
      replaces: [],
      breaking: false,
    },
    counts: {
      tools: 1,
      capabilities: 1,
    },
  }
}

function slotBundle(bundleId: string, active = false) {
  return {
    id: bundleId,
    name: 'Research Workspace',
    description: 'Research workspace bundle',
    active,
    status: 'partial',
    slot_ids: ['market.core', 'ui.research_workspace'],
    enabled_slot_ids: ['market.core'],
    disabled_slot_ids: ['ui.research_workspace'],
    missing_slot_ids: [],
    maturity: 'experimental',
    counts: {
      slots: 2,
      enabled: 1,
      disabled: 1,
      missing: 0,
    },
  }
}

function caseAsset(assetLinkId: string, caseId: string) {
  return {
    asset_link_id: assetLinkId,
    case_id: caseId,
    asset_type: 'document',
    asset_id: 'doc-1',
    asset_name: '10-Q',
    role: 'source',
    version: null,
    metadata: {},
    tenant_id: null,
    linked_at: '2026-06-22T00:00:00Z',
    deleted_at: null,
  }
}

function workflowExecution(executionId: string, caseId: string) {
  return {
    execution_id: executionId,
    case_id: caseId,
    template_id: 'tpl-1',
    template_slug: 'stock',
    template_version: '1',
    run_id: 'run-template',
    status: 'queued',
    input_snapshot: {},
    preflight_result: {},
    trigger_channel: 'web',
    tenant_id: null,
    created_at: '2026-06-22T00:00:00Z',
    updated_at: '2026-06-22T00:00:00Z',
  }
}

function caseProgressStep(progressId: string, caseId: string) {
  return {
    progress_id: progressId,
    case_id: caseId,
    step_key: 'workflow',
    label: 'Workflow',
    status: 'in_progress',
    owner: 'research-agent',
    timestamp: '2026-07-05T00:00:00Z',
    blocking_issue: '',
    next_action: 'Monitor execution.',
    source_type: 'execution',
    source_id: 'exec-1',
    tenant_id: null,
    metadata: {},
  }
}

function caseDecision(decisionId: string, caseId: string) {
  return {
    decision_id: decisionId,
    case_id: caseId,
    decision_type: 'hold',
    rationale: 'Needs review',
    actor_hash: null,
    source_run_ids: [],
    source_execution_ids: [],
    tenant_id: null,
    created_at: '2026-06-22T00:00:00Z',
  }
}

function caseReview(caseId: string) {
  return {
    case: researchCase(caseId, 'prj-1'),
    assets: [caseAsset('asset-1', caseId)],
    executions: [workflowExecution('exec-1', caseId)],
    latest_run: null,
    approvals: [{
      approval_id: 'appr-1',
      run_id: 'run-template',
      action: 'publish memo',
      risk_level: 'high',
      status: 'pending',
      created_at: '2026-06-22T00:00:00Z',
      resolved_at: null,
    }],
    summary: null,
    claims: [],
    citations: [],
    eval: null,
    decisions: [caseDecision('dec-1', caseId)],
    warnings: [],
  }
}
