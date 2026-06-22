/**
 * View registry: maps ViewId to lazy-loaded components and metadata.
 *
 * Each view is loaded on demand via dynamic import, so only the views
 * actually mounted in panels consume bundle space.
 */
import type { ViewId } from '../types/splitTree'

export interface ViewRegistryEntry {
  id: ViewId
  label: string
  icon: string
  loader: () => Promise<any>
  /** Minimum content width in pixels for this view */
  minWidth: number
}

export const VIEW_REGISTRY: Record<ViewId, ViewRegistryEntry> = {
  'scanner': {
    id: 'scanner',
    label: 'Scanner',
    icon: 'scan',
    loader: () => import('./ScannerView.vue'),
    minWidth: 420,
  },
  'cn-archive': {
    id: 'cn-archive',
    label: 'A-Share',
    icon: 'chart',
    loader: () => import('./CnArchiveView.vue'),
    minWidth: 350,
  },
  'us-archive': {
    id: 'us-archive',
    label: 'US Market',
    icon: 'globe',
    loader: () => import('./UsArchiveView.vue'),
    minWidth: 350,
  },
  'ticker': {
    id: 'ticker',
    label: 'Ticker',
    icon: 'line-chart',
    loader: () => import('./TickerView.vue'),
    minWidth: 380,
  },
  'insights': {
    id: 'insights',
    label: 'Insights',
    icon: 'book',
    loader: () => import('./InsightsView.vue'),
    minWidth: 300,
  },
  'analysis': {
    id: 'analysis',
    label: 'Analysis',
    icon: 'doc',
    loader: () => import('./AnalysisView.vue'),
    minWidth: 300,
  },
  'research-agent': {
    id: 'research-agent',
    label: 'Research Agent',
    icon: 'spark',
    loader: () => import('./ResearchAgentView.vue'),
    minWidth: 520,
  },
  'workspace-list': {
    id: 'workspace-list',
    label: 'Workspaces',
    icon: 'grid',
    loader: () => import('./WorkspaceListView.vue'),
    minWidth: 520,
  },
  'workspace-detail': {
    id: 'workspace-detail',
    label: 'Workspace',
    icon: 'folder',
    loader: () => import('./WorkspaceDetailView.vue'),
    minWidth: 520,
  },
  'project-detail': {
    id: 'project-detail',
    label: 'Project',
    icon: 'briefcase',
    loader: () => import('./ProjectDetailView.vue'),
    minWidth: 520,
  },
  'case-detail': {
    id: 'case-detail',
    label: 'Case',
    icon: 'doc',
    loader: () => import('./CaseDetailView.vue'),
    minWidth: 520,
  },
  'template-center': {
    id: 'template-center',
    label: 'Templates',
    icon: 'layers',
    loader: () => import('./TemplateCenterView.vue'),
    minWidth: 480,
  },
  'run-detail': {
    id: 'run-detail',
    label: 'Run Detail',
    icon: 'line-chart',
    loader: () => import('./RunDetailView.vue'),
    minWidth: 560,
  },
  'admin-center': {
    id: 'admin-center',
    label: 'Admin',
    icon: 'settings',
    loader: () => import('./AdminCenterView.vue'),
    minWidth: 480,
  },
}

export const ALL_VIEW_IDS: ViewId[] = Object.keys(VIEW_REGISTRY) as ViewId[]

/** View options formatted for Naive UI's n-select component. */
export const VIEW_SELECT_OPTIONS = ALL_VIEW_IDS.map(id => ({
  label: VIEW_REGISTRY[id].label,
  value: id,
}))
