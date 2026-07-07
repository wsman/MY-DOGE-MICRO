import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  addCaseAsset as addCaseAssetApi,
  createProject as createProjectApi,
  createResearchCase as createResearchCaseApi,
  createResearchCaseRunFromTemplate as createResearchCaseRunFromTemplateApi,
  createWorkflowTemplate as createWorkflowTemplateApi,
  createWorkspace as createWorkspaceApi,
  executeCaseTemplate as executeCaseTemplateApi,
  fetchCapabilities,
  fetchHomeQueue,
  fetchRunSummaryResources,
  getCaseProgress,
  getCaseReview,
  getProject,
  getResearchCase,
  getWorkflowTemplate,
  getWorkspace,
  linkResearchCaseRun as linkResearchCaseRunApi,
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
  preflightCaseExecution as preflightCaseExecutionApi,
  recordCaseDecision as recordCaseDecisionApi,
  type SlotBundleRow,
  type SlotStatusRow,
  type UiPanel,
} from '../api/platform'
import type {
  AddCaseAssetPayload,
  CapabilitySnapshot,
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
  RunSummaryResources,
  TemplatePreflightResult,
  WorkflowExecution,
  WorkflowTemplate,
  Workspace,
} from 'doge-sdk'
import { toFetchError, type FetchError } from '../utils/fetchError'

export const usePlatformStore = defineStore('platform', () => {
  const capabilities = ref<CapabilitySnapshot | null>(null)
  const workspaces = ref<Workspace[]>([])
  const projects = ref<Project[]>([])
  const researchCases = ref<ResearchCase[]>([])
  const workflowTemplates = ref<WorkflowTemplate[]>([])
  const caseRunLinks = ref<CaseRunLink[]>([])
  const caseAssetsByCaseId = ref<Record<string, CaseAssetLink[]>>({})
  const workflowExecutionsByCaseId = ref<Record<string, WorkflowExecution[]>>({})
  const caseProgressByCaseId = ref<Record<string, CaseProgressStep[]>>({})
  const caseDecisionsByCaseId = ref<Record<string, CaseDecision[]>>({})
  const caseReviewByCaseId = ref<Record<string, CaseReview>>({})
  const preflightByCaseId = ref<Record<string, TemplatePreflightResult>>({})
  const homeQueue = ref<HomeQueue | null>(null)
  const runResourcesById = ref<Record<string, RunSummaryResources>>({})
  const uiPanels = ref<UiPanel[]>([])
  const slotRows = ref<SlotStatusRow[]>([])
  const slotBundles = ref<SlotBundleRow[]>([])
  const pendingCount = ref(0)
  const error = ref<FetchError | null>(null)

  const loading = computed(() => pendingCount.value > 0)
  const capabilitiesById = computed(() => {
    const items = capabilities.value?.capabilities ?? []
    return Object.fromEntries(items.map(item => [item.capability_id, item]))
  })
  const workspacesById = computed(() => Object.fromEntries(workspaces.value.map(item => [item.workspace_id, item])))
  const projectsById = computed(() => Object.fromEntries(projects.value.map(item => [item.project_id, item])))
  const researchCasesById = computed(() => Object.fromEntries(researchCases.value.map(item => [item.case_id, item])))
  const workflowTemplatesById = computed(() => (
    Object.fromEntries(workflowTemplates.value.map(item => [item.template_id, item]))
  ))
  const workflowTemplatesBySlug = computed(() => (
    Object.fromEntries(workflowTemplates.value.map(item => [item.slug, item]))
  ))
  const slotRowsById = computed(() => Object.fromEntries(slotRows.value.map(item => [item.id, item])))
  const slotBundlesById = computed(() => Object.fromEntries(slotBundles.value.map(item => [item.id, item])))
  const projectsByWorkspaceId = computed(() => groupBy(projects.value, 'workspace_id'))
  const casesByProjectId = computed(() => groupBy(researchCases.value, 'project_id'))

  async function loadCapabilities() {
    return await runTracked(async () => {
      capabilities.value = await fetchCapabilities()
      return capabilities.value
    })
  }

  async function loadHomeQueue(limit = 20) {
    return await runTracked(async () => {
      homeQueue.value = await fetchHomeQueue(limit)
      return homeQueue.value
    })
  }

  async function loadUiPanels(workspace = 'research_workspace') {
    return await runTracked(async () => {
      uiPanels.value = await listUiPanels(workspace)
      return uiPanels.value
    })
  }

  async function loadSlots() {
    return await runTracked(async () => {
      slotRows.value = await listSlots()
      return slotRows.value
    })
  }

  async function loadSlotBundles() {
    return await runTracked(async () => {
      slotBundles.value = await listSlotBundles()
      return slotBundles.value
    })
  }

  async function loadWorkspaces(limit = 100) {
    return await runTracked(async () => {
      workspaces.value = await listWorkspaces(limit)
      return workspaces.value
    })
  }

  async function loadWorkspace(workspaceId: string) {
    return await runTracked(async () => {
      const workspace = await getWorkspace(workspaceId)
      workspaces.value = upsertById(workspaces.value, workspace, 'workspace_id')
      return workspace
    })
  }

  async function loadProjects(options: ListProjectsOptions = {}) {
    return await runTracked(async () => {
      const items = await listProjects(options)
      projects.value = mergeScopedList(projects.value, items, 'project_id', options.workspace_id, 'workspace_id')
      return items
    })
  }

  async function loadProject(projectId: string) {
    return await runTracked(async () => {
      const project = await getProject(projectId)
      projects.value = upsertById(projects.value, project, 'project_id')
      return project
    })
  }

  async function loadResearchCases(options: ListResearchCasesOptions = {}) {
    return await runTracked(async () => {
      const items = await listResearchCases(options)
      researchCases.value = mergeScopedList(researchCases.value, items, 'case_id', options.project_id, 'project_id')
      return items
    })
  }

  async function loadResearchCase(caseId: string) {
    return await runTracked(async () => {
      const researchCase = await getResearchCase(caseId)
      researchCases.value = upsertById(researchCases.value, researchCase, 'case_id')
      return researchCase
    })
  }

  async function loadCaseWorkspace(caseId: string) {
    return await runTracked(async () => {
      const [researchCase, templates, assets, executions, progress, decisions, review] = await Promise.all([
        getResearchCase(caseId),
        listWorkflowTemplates(100),
        listCaseAssets(caseId),
        listCaseExecutions(caseId),
        getCaseProgress(caseId),
        listCaseDecisions(caseId),
        getCaseReview(caseId),
      ])
      researchCases.value = upsertById(researchCases.value, researchCase, 'case_id')
      workflowTemplates.value = templates
      caseAssetsByCaseId.value = { ...caseAssetsByCaseId.value, [caseId]: assets }
      workflowExecutionsByCaseId.value = { ...workflowExecutionsByCaseId.value, [caseId]: executions }
      caseProgressByCaseId.value = { ...caseProgressByCaseId.value, [caseId]: progress }
      caseDecisionsByCaseId.value = { ...caseDecisionsByCaseId.value, [caseId]: decisions }
      caseReviewByCaseId.value = { ...caseReviewByCaseId.value, [caseId]: review }
      return review
    })
  }

  async function loadWorkflowTemplates(limit = 100) {
    return await runTracked(async () => {
      workflowTemplates.value = await listWorkflowTemplates(limit)
      return workflowTemplates.value
    })
  }

  async function loadWorkflowTemplate(templateId: string) {
    return await runTracked(async () => {
      const template = await getWorkflowTemplate(templateId)
      workflowTemplates.value = upsertById(workflowTemplates.value, template, 'template_id')
      return template
    })
  }

  async function createWorkspace(payload: CreateWorkspacePayload) {
    return await runTracked(async () => {
      const workspace = await createWorkspaceApi(payload)
      workspaces.value = upsertById(workspaces.value, workspace, 'workspace_id')
      return workspace
    })
  }

  async function createProject(payload: CreateProjectPayload) {
    return await runTracked(async () => {
      const project = await createProjectApi(payload)
      projects.value = upsertById(projects.value, project, 'project_id')
      return project
    })
  }

  async function createResearchCase(payload: CreateResearchCasePayload) {
    return await runTracked(async () => {
      const researchCase = await createResearchCaseApi(payload)
      researchCases.value = upsertById(researchCases.value, researchCase, 'case_id')
      return researchCase
    })
  }

  async function createWorkflowTemplate(payload: CreateWorkflowTemplatePayload) {
    return await runTracked(async () => {
      const template = await createWorkflowTemplateApi(payload)
      workflowTemplates.value = upsertById(workflowTemplates.value, template, 'template_id')
      return template
    })
  }

  async function linkResearchCaseRun(caseId: string, payload: LinkResearchCaseRunPayload) {
    return await runTracked(async () => {
      const link = await linkResearchCaseRunApi(caseId, payload)
      caseRunLinks.value = upsertCaseRunLink(caseRunLinks.value, link)
      return link
    })
  }

  async function createResearchCaseRunFromTemplate(caseId: string, payload: CreateResearchCaseRunFromTemplatePayload) {
    return await runTracked(async () => {
      const link = await createResearchCaseRunFromTemplateApi(caseId, payload)
      caseRunLinks.value = upsertCaseRunLink(caseRunLinks.value, link)
      return link
    })
  }

  async function preflightCaseExecution(caseId: string, payload: CaseExecutionPayload) {
    return await runTracked(async () => {
      const preflight = await preflightCaseExecutionApi(caseId, payload)
      preflightByCaseId.value = { ...preflightByCaseId.value, [caseId]: preflight }
      return preflight
    })
  }

  async function executeCaseTemplate(caseId: string, payload: CaseExecutionPayload) {
    return await runTracked(async () => {
      const execution = await executeCaseTemplateApi(caseId, payload)
      workflowExecutionsByCaseId.value = {
        ...workflowExecutionsByCaseId.value,
        [caseId]: upsertById(workflowExecutionsByCaseId.value[caseId] ?? [], execution, 'execution_id'),
      }
      if (execution.run_id) {
        caseRunLinks.value = upsertCaseRunLink(caseRunLinks.value, {
          case_id: caseId,
          run_id: execution.run_id,
          link_type: 'primary',
          tenant_id: execution.tenant_id,
          linked_at: execution.created_at,
        })
      }
      return execution
    })
  }

  async function addCaseAsset(caseId: string, payload: AddCaseAssetPayload) {
    return await runTracked(async () => {
      const asset = await addCaseAssetApi(caseId, payload)
      caseAssetsByCaseId.value = {
        ...caseAssetsByCaseId.value,
        [caseId]: upsertById(caseAssetsByCaseId.value[caseId] ?? [], asset, 'asset_link_id'),
      }
      return asset
    })
  }

  async function recordCaseDecision(caseId: string, payload: RecordCaseDecisionPayload) {
    return await runTracked(async () => {
      const decision = await recordCaseDecisionApi(caseId, payload)
      caseDecisionsByCaseId.value = {
        ...caseDecisionsByCaseId.value,
        [caseId]: upsertById(caseDecisionsByCaseId.value[caseId] ?? [], decision, 'decision_id'),
      }
      return decision
    })
  }

  async function loadRunSummaryResources(runId: string) {
    return await runTracked(async () => {
      const resources = await fetchRunSummaryResources(runId)
      runResourcesById.value = {
        ...runResourcesById.value,
        [runId]: resources,
      }
      return resources
    })
  }

  async function runTracked<T>(operation: () => Promise<T>): Promise<T> {
    pendingCount.value += 1
    error.value = null
    try {
      return await operation()
    } catch (e) {
      error.value = toFetchError(e)
      throw e
    } finally {
      pendingCount.value -= 1
    }
  }

  return {
    capabilities,
    workspaces,
    projects,
    researchCases,
    workflowTemplates,
    caseRunLinks,
    caseAssetsByCaseId,
    workflowExecutionsByCaseId,
    caseProgressByCaseId,
    caseDecisionsByCaseId,
    caseReviewByCaseId,
    preflightByCaseId,
    homeQueue,
    runResourcesById,
    uiPanels,
    slotRows,
    slotBundles,
    loading,
    error,
    capabilitiesById,
    workspacesById,
    projectsById,
    researchCasesById,
    workflowTemplatesById,
    workflowTemplatesBySlug,
    slotRowsById,
    slotBundlesById,
    projectsByWorkspaceId,
    casesByProjectId,
    loadCapabilities,
    loadHomeQueue,
    loadUiPanels,
    loadSlots,
    loadSlotBundles,
    loadWorkspaces,
    loadWorkspace,
    loadProjects,
    loadProject,
    loadResearchCases,
    loadResearchCase,
    loadCaseWorkspace,
    loadWorkflowTemplates,
    loadWorkflowTemplate,
    createWorkspace,
    createProject,
    createResearchCase,
    createWorkflowTemplate,
    linkResearchCaseRun,
    createResearchCaseRunFromTemplate,
    preflightCaseExecution,
    executeCaseTemplate,
    addCaseAsset,
    recordCaseDecision,
    loadRunSummaryResources,
  }
})

function upsertById<T, K extends keyof T>(items: T[], item: T, key: K): T[] {
  const index = items.findIndex(existing => existing[key] === item[key])
  if (index < 0) return [item, ...items]
  return items.map((existing, itemIndex) => itemIndex === index ? item : existing)
}

function upsertCaseRunLink(items: CaseRunLink[], item: CaseRunLink): CaseRunLink[] {
  const index = items.findIndex(existing => (
    existing.case_id === item.case_id &&
    existing.run_id === item.run_id &&
    existing.link_type === item.link_type
  ))
  if (index < 0) return [item, ...items]
  return items.map((existing, itemIndex) => itemIndex === index ? item : existing)
}

function mergeScopedList<T, IdKey extends keyof T, ScopeKey extends keyof T>(
  current: T[],
  incoming: T[],
  idKey: IdKey,
  scopeId: string | undefined,
  scopeKey: ScopeKey,
): T[] {
  if (!scopeId) return incoming
  const outsideScope = current.filter(item => item[scopeKey] !== scopeId)
  return [...incoming, ...outsideScope].reduce<T[]>((items, item) => upsertById(items, item, idKey), [])
}

function groupBy<T, K extends keyof T>(items: T[], key: K): Record<string, T[]> {
  return items.reduce<Record<string, T[]>>((groups, item) => {
    const raw = item[key]
    if (typeof raw !== 'string' || raw.length === 0) return groups
    groups[raw] = [...(groups[raw] ?? []), item]
    return groups
  }, {})
}
