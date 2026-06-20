import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/scanner' },
    { path: '/scanner', name: 'scanner', component: () => import('../views/ScannerView.vue') },
    { path: '/cn-archive', name: 'cn-archive', component: () => import('../views/CnArchiveView.vue') },
    { path: '/us-archive', name: 'us-archive', component: () => import('../views/UsArchiveView.vue') },
    { path: '/insights', name: 'insights', component: () => import('../views/InsightsView.vue') },
    { path: '/analysis', name: 'analysis', component: () => import('../views/AnalysisView.vue') },
    { path: '/research-agent', name: 'research-agent', component: () => import('../views/ResearchAgentView.vue') },
  ],
})

export default router
