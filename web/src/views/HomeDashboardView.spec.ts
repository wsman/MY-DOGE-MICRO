import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import HomeDashboardView from './HomeDashboardView.vue'
import { createAgentRun, listAgentRuns } from '../api/agent'
import { listDocuments } from '../api/documents'
import {
  addCaseAsset,
  createProject,
  createResearchCase,
  createResearchCaseRunFromTemplate,
  createWorkflowTemplate,
  createWorkspace,
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
  listWorkflowTemplates,
  listWorkspaces,
  preflightCaseExecution,
  recordCaseDecision,
} from '../api/platform'
import { useAgentStore } from '../stores/agent'

const pushMock = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}))

vi.mock('../api/agent', () => ({
  approveAgentRun: vi.fn(),
  createAgentRun: vi.fn(),
  listAgentRuns: vi.fn(),
}))

vi.mock('../api/documents', () => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
}))

vi.mock('../api/platform', () => ({
  addCaseAsset: vi.fn(),
  createProject: vi.fn(),
  createResearchCase: vi.fn(),
  createResearchCaseRunFromTemplate: vi.fn(),
  createWorkflowTemplate: vi.fn(),
  createWorkspace: vi.fn(),
  executeCaseTemplate: vi.fn(),
  fetchCapabilities: vi.fn(),
  fetchHomeQueue: vi.fn(),
  fetchRunSummaryResources: vi.fn(),
  getCaseProgress: vi.fn(),
  getCaseReview: vi.fn(),
  getProject: vi.fn(),
  getResearchCase: vi.fn(),
  getWorkflowTemplate: vi.fn(),
  getWorkspace: vi.fn(),
  linkResearchCaseRun: vi.fn(),
  listCaseAssets: vi.fn(),
  listCaseDecisions: vi.fn(),
  listCaseExecutions: vi.fn(),
  listProjects: vi.fn(),
  listResearchCases: vi.fn(),
  listWorkflowTemplates: vi.fn(),
  listWorkspaces: vi.fn(),
  preflightCaseExecution: vi.fn(),
  recordCaseDecision: vi.fn(),
}))

describe('HomeDashboardView', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    window.localStorage.clear()
    setActivePinia(createPinia())
    pushMock.mockReset()
    resetApiMocks()
  })

  it('renders the analyst product home from existing local-alpha data sources', async () => {
    const wrapper = mount(HomeDashboardView)
    await flushPromises()

    expect(fetchHomeQueue).toHaveBeenCalledWith(20)
    expect(listResearchCases).toHaveBeenCalledWith({ limit: 10 })
    expect(listDocuments).toHaveBeenCalledTimes(1)
    expect(listAgentRuns).toHaveBeenCalledWith(8)
    expect(fetchCapabilities).toHaveBeenCalledTimes(1)

    const text = wrapper.text()
    expect(text).toContain('Start research')
    expect(text).toContain('Run demo')
    expect(text).toContain('Recent Runs')
    expect(text).toContain('Run Comparison')
    expect(text).toContain('Recent Uploads')
    expect(text).toContain('annual-report.pdf')
    expect(text).toContain('Pending Approvals')
    expect(text).toContain('Approve publication')
    expect(text).toContain('Recent Cases')
    expect(text).toContain('NVDA Earnings Review')
    expect(text).toContain('Recent Memos')
    expect(text).toContain('IC Memo')
    expect(text).toContain('Workflow Shortcuts')
    expect(text).toContain('doge demo-pack')
    expect(text).toContain('System Readiness')
    expect(text).toContain('Local Alpha')
    expect(wrapper.find('#failed-runs-title').exists()).toBe(false)
    expect(wrapper.find('#warnings-title').exists()).toBe(false)
  })

  it('shows operator diagnostics only in Developer mode', async () => {
    const agentStore = useAgentStore()
    agentStore.setAnalystMode(false)

    const wrapper = mount(HomeDashboardView)
    await flushPromises()

    expect(wrapper.find('#failed-runs-title').exists()).toBe(true)
    expect(wrapper.find('#warnings-title').exists()).toBe(true)
    expect(wrapper.text()).toContain('preflight_failed')
    expect(wrapper.text()).toContain('data_freshness_unavailable')
  })

  it('routes start research and runs a zero-key demo from Home', async () => {
    const wrapper = mount(HomeDashboardView)
    await flushPromises()

    await buttonByText(wrapper, 'Start research').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/research-agent')

    pushMock.mockClear()
    await buttonByText(wrapper, 'Run demo').trigger('click')
    await flushPromises()

    expect(createAgentRun).toHaveBeenCalledWith(expect.objectContaining({
      workflow: 'earnings_review',
      document_ids: [],
      portfolio_id: null,
    }))
    expect(pushMock).toHaveBeenCalledWith('/research-agent')
  })

  it('does not route to a stale run when the Home demo request fails', async () => {
    const agentStore = useAgentStore()
    agentStore.run = {
      run_id: 'run-stale',
      workflow: 'earnings_review',
      question: 'Previous run',
      session_id: null,
      market: 'us',
      language: 'en',
      document_ids: [],
      portfolio_id: null,
      model_policy: {},
      workflow_context: null,
      identity_snapshot: null,
      status: 'completed',
      events: [],
      artifacts: [],
      approvals: [],
      cancel_requested_at: null,
      schema_version: '1.0',
      created_at: '2026-07-06T00:00:00Z',
      updated_at: '2026-07-06T00:00:00Z',
    }
    vi.mocked(createAgentRun).mockRejectedValueOnce(new Error('daemon offline'))

    const wrapper = mount(HomeDashboardView)
    await flushPromises()

    await buttonByText(wrapper, 'Run demo').trigger('click')
    await flushPromises()

    expect(pushMock).not.toHaveBeenCalled()
    expect(agentStore.run).toBeNull()
    expect(agentStore.error?.message).toContain('daemon offline')
  })
})

function resetApiMocks() {
  for (const fn of [
    addCaseAsset,
    createProject,
    createResearchCase,
    createResearchCaseRunFromTemplate,
    createWorkflowTemplate,
    createWorkspace,
    executeCaseTemplate,
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
    listWorkflowTemplates,
    listWorkspaces,
    preflightCaseExecution,
    recordCaseDecision,
  ]) {
    vi.mocked(fn).mockReset()
  }

  vi.mocked(fetchCapabilities).mockReset()
  vi.mocked(fetchCapabilities).mockResolvedValue({
    snapshot_id: 'cap-home',
    generated_at: '2026-07-06T00:00:00Z',
    redaction_version: 'doge.capability_redaction.v1',
    status_counts: { available: 1 },
    capabilities: [{
      capability_id: 'provider.kimi',
      kind: 'model_provider',
      name: 'Kimi / Moonshot',
      status: 'available',
      risk_level: 'medium',
      requires_approval: false,
      metadata: {},
    }],
  })

  vi.mocked(fetchHomeQueue).mockReset()
  vi.mocked(fetchHomeQueue).mockResolvedValue({
    pending_cases: [{ case: researchCase('case-1', 'NVDA Earnings Review'), reason: 'no_recent_execution' }],
    pending_approvals: [{
      run_id: 'run-approval',
      workflow: 'investment_committee_memo',
      question: 'Approve publication',
      approvals: [{ approval_id: 'appr-1', action: 'publish memo', status: 'pending' }],
    }],
    failed_or_degraded_runs: [{ execution: workflowExecution('exec-failed', 'case-1', 'preflight_failed'), reason: 'preflight_failed' }],
    recent_memos: [{
      run: { run_id: 'run-memo', status: 'completed', question: 'Memo question', updated_at: '2026-07-06T00:00:00Z' },
      artifact: { artifact_id: 'art-1', title: 'IC Memo', created_at: '2026-07-06T00:00:00Z' },
    }],
    recent_executions: [workflowExecution('exec-1', 'case-1', 'completed')],
    data_freshness: { provider: 'local_demo' },
    warnings: ['data_freshness_unavailable'],
  })

  vi.mocked(listResearchCases).mockReset()
  vi.mocked(listResearchCases).mockResolvedValue([researchCase('case-1', 'NVDA Earnings Review')])
  vi.mocked(listDocuments).mockReset()
  vi.mocked(listDocuments).mockResolvedValue([{
    document_id: 'doc-1',
    filename: 'annual-report.pdf',
    mime_type: 'application/pdf',
    parsing_status: 'parsed',
    created_at: '2026-07-06T00:00:00Z',
  }])
  vi.mocked(listAgentRuns).mockReset()
  vi.mocked(listAgentRuns).mockResolvedValue([{
    run_id: 'run-1',
    workflow: 'earnings_review',
    question: 'Analyze',
    session_id: 'ses-1',
    market: 'us',
    language: 'en',
    portfolio_id: null,
    status: 'completed',
    event_count: 3,
    artifact_count: 1,
    approval_count: 0,
    created_at: '2026-07-06T00:00:00Z',
    updated_at: '2026-07-06T00:00:00Z',
  }])
  vi.mocked(createAgentRun).mockReset()
  vi.mocked(createAgentRun).mockResolvedValue({
    run_id: 'run-demo',
    workflow: 'earnings_review',
    question: 'Analyze',
    session_id: null,
    market: 'us',
    language: 'en',
    document_ids: [],
    portfolio_id: null,
    model_policy: {},
    workflow_context: null,
    identity_snapshot: null,
    status: 'completed',
    events: [],
    artifacts: [],
    approvals: [],
    cancel_requested_at: null,
    schema_version: '1.0',
    created_at: '2026-07-06T00:00:00Z',
    updated_at: '2026-07-06T00:00:00Z',
  })
}

function researchCase(caseId: string, title: string) {
  return {
    case_id: caseId,
    project_id: 'project-1',
    title,
    thesis: '',
    status: 'open',
    owner: 'analyst',
    metadata: {},
    created_at: '2026-07-06T00:00:00Z',
    updated_at: '2026-07-06T00:00:00Z',
  } as never
}

function workflowExecution(executionId: string, caseId: string, status: string) {
  return {
    execution_id: executionId,
    case_id: caseId,
    template_id: 'tpl-1',
    template_slug: 'earnings_review',
    run_id: status === 'completed' ? 'run-1' : null,
    status,
    inputs: {},
    metadata: {},
    created_at: '2026-07-06T00:00:00Z',
    updated_at: '2026-07-06T00:00:00Z',
  } as never
}

function buttonByText(wrapper: VueWrapper, text: string) {
  const button = wrapper.findAll('button').find(candidate => candidate.text().includes(text))
  if (!button) throw new Error(`Missing button: ${text}`)
  return button
}
