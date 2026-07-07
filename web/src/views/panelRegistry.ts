import type { UiPanel } from '../api/platform'

export type WorkspaceMode = 'analyst' | 'developer'
export type ResearchPanelZone =
  | 'research.input'
  | 'research.memo'
  | 'research.evidence'
  | 'research.quality'
  | 'research.timeline'

export type ResearchPanelId =
  | 'guided_flow'
  | 'scenario_picker'
  | 'market_selector'
  | 'execution_profile_selector'
  | 'research_question'
  | 'run_preflight_checklist'
  | 'run_action'
  | 'document_uploader'
  | 'document_selector'
  | 'portfolio_importer'
  | 'memo_body'
  | 'empty_state_ctas'
  | 'status_row'
  | 'conclusion_evidence_matrix'
  | 'citation_drilldown'
  | 'approval_list'
  | 'maturity_panel'
  | 'run_comparison_panel'
  | 'cost_eval_panel'
  | 'agent_timeline'

export interface ResearchPanelDefinition {
  panel_id: ResearchPanelId
  workspace: 'research_workspace'
  zone: ResearchPanelZone
  component_module: string
  order: number
  modes: WorkspaceMode[]
  required_artifact_fields: string[]
  label: string
}

export interface PanelFilter {
  mode: WorkspaceMode
  panels?: UiPanel[]
}

const allModes: WorkspaceMode[] = ['analyst', 'developer']
const developerOnly: WorkspaceMode[] = ['developer']

export const DEFAULT_RESEARCH_PANELS: ResearchPanelDefinition[] = [
  panel('guided_flow', 'research.input', 'components/agent/GuidedFlow.vue', 10, allModes, 'Guided Flow'),
  panel('scenario_picker', 'research.input', 'components/agent/ScenarioPicker.vue', 20, allModes, 'Scenario Picker'),
  panel('market_selector', 'research.input', 'builtin:market_selector', 30, allModes, 'Market Selector'),
  panel('execution_profile_selector', 'research.input', 'components/agent/ExecutionProfileSelector.vue', 40, allModes, 'Execution Profile'),
  panel('research_question', 'research.input', 'builtin:research_question', 50, allModes, 'Research Question'),
  panel('run_preflight_checklist', 'research.input', 'components/agent/RunPreflightChecklist.vue', 60, allModes, 'Run Preflight'),
  panel('run_action', 'research.input', 'builtin:run_action', 70, allModes, 'Run Action'),
  panel('document_uploader', 'research.input', 'components/agent/DocumentUploader.vue', 80, allModes, 'Document Uploader'),
  panel('document_selector', 'research.input', 'components/agent/DocumentSelector.vue', 90, allModes, 'Document Selector'),
  panel('portfolio_importer', 'research.input', 'components/agent/PortfolioImporter.vue', 100, allModes, 'Portfolio Importer'),
  panel('memo_body', 'research.memo', 'builtin:memo_body', 10, allModes, 'Memo Body'),
  panel('empty_state_ctas', 'research.memo', 'components/agent/EmptyStateCtas.vue', 20, allModes, 'Empty State CTAs'),
  panel('status_row', 'research.evidence', 'builtin:status_row', 10, allModes, 'Status Row'),
  panel('conclusion_evidence_matrix', 'research.evidence', 'components/agent/ConclusionEvidenceMatrix.vue', 20, allModes, 'Conclusion Evidence Matrix', ['structured_claims']),
  panel('citation_drilldown', 'research.evidence', 'components/agent/CitationDrilldown.vue', 30, allModes, 'Citation Drilldown', ['citations']),
  panel('approval_list', 'research.evidence', 'builtin:approval_list', 40, allModes, 'Approval List'),
  panel('maturity_panel', 'research.quality', 'components/common/MaturityPanel.vue', 10, allModes, 'Maturity Panel'),
  panel('run_comparison_panel', 'research.quality', 'components/agent/RunComparisonPanel.vue', 20, allModes, 'Run Comparison'),
  panel('cost_eval_panel', 'research.quality', 'components/agent/CostEvalPanel.vue', 30, developerOnly, 'Cost / Eval'),
  panel('agent_timeline', 'research.timeline', 'builtin:agent_timeline', 10, developerOnly, 'Agent Timeline'),
]

export function panelsFor(zone: ResearchPanelZone, filter: PanelFilter): ResearchPanelDefinition[] {
  return sourcePanels(filter.panels)
    .filter(panel => panel.zone === zone)
    .filter(panel => panel.modes.length === 0 || panel.modes.includes(filter.mode))
    .sort((a, b) => a.order - b.order || a.panel_id.localeCompare(b.panel_id))
}

export function visiblePanelIds(filter: PanelFilter): Set<ResearchPanelId> {
  return new Set(
    sourcePanels(filter.panels)
      .filter(panel => panel.modes.length === 0 || panel.modes.includes(filter.mode))
      .map(panel => panel.panel_id),
  )
}

function sourcePanels(panels?: UiPanel[]): ResearchPanelDefinition[] {
  if (!panels?.length) return DEFAULT_RESEARCH_PANELS
  const known = new Map(DEFAULT_RESEARCH_PANELS.map(panel => [panel.panel_id, panel]))
  const normalized = panels
    .filter(panel => panel.workspace === 'research_workspace')
    .map(panel => normalizePanel(panel, known))
    .filter((panel): panel is ResearchPanelDefinition => panel !== null)
  return normalized.length ? normalized : DEFAULT_RESEARCH_PANELS
}

function normalizePanel(
  remote: UiPanel,
  known: Map<ResearchPanelId, ResearchPanelDefinition>,
): ResearchPanelDefinition | null {
  if (!isResearchPanelId(remote.panel_id) || !isResearchPanelZone(remote.zone)) return null
  const fallback = known.get(remote.panel_id)
  return {
    panel_id: remote.panel_id,
    workspace: 'research_workspace',
    zone: remote.zone,
    component_module: remote.component_module || fallback?.component_module || '',
    order: Number.isFinite(remote.order) ? remote.order : fallback?.order ?? 0,
    modes: normalizeModes(remote.modes, fallback?.modes ?? allModes),
    required_artifact_fields: remote.required_artifact_fields ?? fallback?.required_artifact_fields ?? [],
    label: remote.label || fallback?.label || remote.panel_id,
  }
}

function normalizeModes(values: string[] | undefined, fallback: WorkspaceMode[]): WorkspaceMode[] {
  if (!values?.length) return fallback
  const modes = values.filter((value): value is WorkspaceMode => value === 'analyst' || value === 'developer')
  return modes.length ? modes : fallback
}

function panel(
  panel_id: ResearchPanelId,
  zone: ResearchPanelZone,
  component_module: string,
  order: number,
  modes: WorkspaceMode[],
  label: string,
  required_artifact_fields: string[] = [],
): ResearchPanelDefinition {
  return {
    panel_id,
    workspace: 'research_workspace',
    zone,
    component_module,
    order,
    modes,
    required_artifact_fields,
    label,
  }
}

function isResearchPanelId(value: string): value is ResearchPanelId {
  return DEFAULT_RESEARCH_PANELS.some(panel => panel.panel_id === value)
}

function isResearchPanelZone(value: string): value is ResearchPanelZone {
  return [
    'research.input',
    'research.memo',
    'research.evidence',
    'research.quality',
    'research.timeline',
  ].includes(value)
}
