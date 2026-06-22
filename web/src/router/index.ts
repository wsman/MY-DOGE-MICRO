import { createRouter, createWebHashHistory } from 'vue-router'
import { platformShellEnabled } from '../config/features'

const platformRouteNames = new Set([
  'workspace-list',
  'workspace-detail',
  'project-detail',
  'case-detail',
  'template-center',
  'run-detail',
  'admin-center',
])

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: platformShellEnabled ? '/workspaces' : '/research-agent' },
    { path: '/scanner', name: 'scanner', component: () => import('../views/ScannerView.vue') },
    { path: '/cn-archive', name: 'cn-archive', component: () => import('../views/CnArchiveView.vue') },
    { path: '/us-archive', name: 'us-archive', component: () => import('../views/UsArchiveView.vue') },
    { path: '/insights', name: 'insights', component: () => import('../views/InsightsView.vue') },
    { path: '/analysis', name: 'analysis', component: () => import('../views/AnalysisView.vue') },
    { path: '/research-agent', name: 'research-agent', component: () => import('../views/ResearchAgentView.vue') },
    { path: '/workspaces', name: 'workspace-list', component: () => import('../views/WorkspaceListView.vue') },
    { path: '/workspaces/:workspaceId', name: 'workspace-detail', component: () => import('../views/WorkspaceDetailView.vue') },
    { path: '/projects/:projectId', name: 'project-detail', component: () => import('../views/ProjectDetailView.vue') },
    { path: '/cases/:caseId', name: 'case-detail', component: () => import('../views/CaseDetailView.vue') },
    { path: '/templates', name: 'template-center', component: () => import('../views/TemplateCenterView.vue') },
    { path: '/runs/:runId?', name: 'run-detail', component: () => import('../views/RunDetailView.vue') },
    { path: '/admin', name: 'admin-center', component: () => import('../views/AdminCenterView.vue') },
  ],
})

router.beforeEach(to => {
  if (!platformShellEnabled && typeof to.name === 'string' && platformRouteNames.has(to.name)) {
    return '/research-agent'
  }
  return true
})

export default router
