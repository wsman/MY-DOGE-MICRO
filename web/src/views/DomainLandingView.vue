<template>
  <div class="domain-view" :aria-label="config.ariaLabel">
    <header class="domain-header">
      <div>
        <div class="eyebrow">{{ config.eyebrow }}</div>
        <h1>{{ config.title }}</h1>
      </div>
      <n-space size="small">
        <n-button size="small" :loading="store.loading" @click="load">Refresh</n-button>
        <n-button
          v-if="config.primaryAction"
          size="small"
          type="primary"
          @click="openRoute(config.primaryAction.path)"
        >
          {{ config.primaryAction.label }}
        </n-button>
      </n-space>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>

    <section class="summary-strip" aria-label="Domain summary">
      <div v-for="metric in metrics" :key="metric.label">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
      </div>
    </section>

    <div class="domain-grid">
      <section class="main-section" :aria-labelledby="`${domain}-actions-title`">
        <div :id="`${domain}-actions-title`" class="section-title">{{ config.actionTitle }}</div>
        <div class="action-list">
          <article v-for="action in config.actions" :key="action.path + action.label" class="action-row">
            <div>
              <h2>{{ action.label }}</h2>
              <p>{{ action.caption }}</p>
            </div>
            <n-space size="small" align="center">
              <n-tag v-if="action.status" size="small">{{ action.status }}</n-tag>
              <n-button size="tiny" @click="openRoute(action.path)">Open</n-button>
            </n-space>
          </article>
        </div>
      </section>

      <aside class="side-section" :aria-labelledby="`${domain}-readiness-title`">
        <div :id="`${domain}-readiness-title`" class="section-title">{{ config.sideTitle }}</div>
        <slot name="side">
          <div class="status-list">
            <div v-for="capability in visibleCapabilities" :key="capability.capability_id" class="status-item">
              <span>{{ capability.capability_id }}</span>
              <n-tag size="small" :type="capability.status === 'available' ? 'success' : 'warning'">
                {{ capability.status }}
              </n-tag>
            </div>
            <div v-if="!visibleCapabilities.length && !store.loading" class="empty-state">No capabilities</div>
          </div>
        </slot>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NAlert, NButton, NSpace, NTag } from 'naive-ui'
import { usePlatformStore } from '../stores/platform'

export type DomainKey = 'home' | 'research' | 'market' | 'portfolio' | 'quant'

interface DomainAction {
  label: string
  caption: string
  path: string
  status?: string
}

interface DomainConfig {
  ariaLabel: string
  eyebrow: string
  title: string
  actionTitle: string
  sideTitle: string
  primaryAction?: { label: string; path: string }
  actions: DomainAction[]
}

const props = defineProps<{ domain: DomainKey }>()
const router = useRouter()
const store = usePlatformStore()

const configs: Record<DomainKey, DomainConfig> = {
  home: {
    ariaLabel: 'Product home',
    eyebrow: 'Operations',
    title: 'Home',
    actionTitle: 'Queues',
    sideTitle: 'Data Sources',
    primaryAction: { label: 'New Case', path: '/research-agent' },
    actions: [
      { label: 'Today Market', caption: 'Scanner and market archive', path: '/market', status: 'Market' },
      { label: 'Recent Research', caption: 'Projects, cases, templates', path: '/research', status: 'Research' },
      { label: 'Pending Approvals', caption: 'Case execution approvals', path: '/research-agent', status: 'Runtime' },
      { label: 'Capability Status', caption: 'Connectors and model readiness', path: '/admin', status: 'Admin' },
    ],
  },
  research: {
    ariaLabel: 'Research domain',
    eyebrow: 'Product Domain',
    title: 'Research',
    actionTitle: 'Work Areas',
    sideTitle: 'Evidence Capabilities',
    primaryAction: { label: 'Ad-hoc Case', path: '/research-agent' },
    actions: [
      { label: 'Projects', caption: 'Workspace-backed research projects', path: '/workspaces', status: 'Cases' },
      { label: 'Templates', caption: 'Workflow templates for repeatable work', path: '/templates', status: 'Workflow' },
      { label: 'Research Agent', caption: 'Compatibility entry for case execution', path: '/research-agent', status: 'Legacy URL' },
      { label: 'Insights', caption: 'Macro and research report archive', path: '/insights', status: 'Evidence' },
    ],
  },
  market: {
    ariaLabel: 'Market domain',
    eyebrow: 'Product Domain',
    title: 'Market',
    actionTitle: 'Market Workbench',
    sideTitle: 'Market Capabilities',
    primaryAction: { label: 'Open Scanner', path: '/scanner' },
    actions: [
      { label: 'Scanner', caption: 'Momentum, breadth, anomaly lists', path: '/scanner', status: 'Live' },
      { label: 'A-Share Archive', caption: 'CN market history and reports', path: '/cn-archive', status: 'Archive' },
      { label: 'US Market Archive', caption: 'US market history and reports', path: '/us-archive', status: 'Archive' },
      { label: 'Market Insights', caption: 'Macro and stock notes', path: '/insights', status: 'Reports' },
    ],
  },
  portfolio: {
    ariaLabel: 'Portfolio domain',
    eyebrow: 'Product Domain',
    title: 'Portfolio',
    actionTitle: 'Portfolio Workbench',
    sideTitle: 'Import',
    primaryAction: { label: 'Analyze', path: '/research-agent' },
    actions: [
      { label: 'Exposure Review', caption: 'Portfolio-aware research run', path: '/research-agent', status: 'Runtime' },
      { label: 'Risk Scenario', caption: 'Scenario notes through case execution', path: '/research-agent', status: 'Draft' },
      { label: 'Investment Memo', caption: 'Memo with portfolio context', path: '/research-agent', status: 'Case' },
    ],
  },
  quant: {
    ariaLabel: 'Quant domain',
    eyebrow: 'Product Domain',
    title: 'Quant',
    actionTitle: 'Lab Workbench',
    sideTitle: 'Quant Capabilities',
    primaryAction: { label: 'Open Lab', path: '/analysis' },
    actions: [
      { label: 'Python Analysis', caption: 'Agent run with python profile', path: '/research-agent', status: 'Runtime' },
      { label: 'SQL Analysis', caption: 'Agent run with SQL profile', path: '/research-agent', status: 'Runtime' },
      { label: 'Backtests', caption: 'Backtest profile and result review', path: '/research-agent', status: 'Experimental' },
      { label: 'Analysis Reports', caption: 'Generated industry reports', path: '/analysis', status: 'Reports' },
    ],
  },
}

const config = computed(() => configs[props.domain])
const errorMessage = computed(() => store.error?.message ?? '')
const capabilities = computed(() => store.capabilities?.capabilities ?? [])
const visibleCapabilities = computed(() => {
  const terms = capabilityTerms(props.domain)
  const matches = capabilities.value.filter(capability => {
    const text = `${capability.capability_id} ${capability.name} ${capability.kind}`.toLowerCase()
    return terms.some(term => text.includes(term))
  })
  return (matches.length ? matches : capabilities.value).slice(0, 6)
})
const availableCapabilityCount = computed(() => (
  capabilities.value.filter(item => item.status === 'available').length
))
const blockedCapabilityCount = computed(() => (
  capabilities.value.filter(item => item.status !== 'available').length
))
const metrics = computed(() => {
  switch (props.domain) {
    case 'home':
      return [
        { label: 'Workspaces', value: store.workspaces.length },
        { label: 'Templates', value: store.workflowTemplates.length },
        { label: 'Available', value: availableCapabilityCount.value },
        { label: 'Blocked', value: blockedCapabilityCount.value },
      ]
    case 'research':
      return [
        { label: 'Projects', value: store.projects.length },
        { label: 'Cases', value: store.researchCases.length },
        { label: 'Templates', value: store.workflowTemplates.length },
        { label: 'Capabilities', value: visibleCapabilities.value.length },
      ]
    case 'market':
    case 'portfolio':
    case 'quant':
      return [
        { label: 'Capabilities', value: visibleCapabilities.value.length },
        { label: 'Available', value: availableCapabilityCount.value },
        { label: 'Blocked', value: blockedCapabilityCount.value },
        { label: 'Templates', value: store.workflowTemplates.length },
      ]
  }
})

function capabilityTerms(domain: DomainKey): string[] {
  if (domain === 'market') return ['market', 'scanner', 'rsrs', 'breadth', 'anomaly', 'ticker']
  if (domain === 'portfolio') return ['portfolio', 'risk', 'scenario', 'exposure']
  if (domain === 'quant') return ['quant', 'python', 'sql', 'backtest', 'data']
  if (domain === 'research') return ['research', 'evidence', 'document', 'citation', 'fundamental']
  return []
}

async function load() {
  await Promise.all([
    store.loadWorkspaces(50),
    store.loadProjects({}),
    store.loadResearchCases({}),
    store.loadWorkflowTemplates(50),
    store.loadCapabilities(),
  ]).catch(() => undefined)
}

async function openRoute(path: string) {
  await router.push(path)
}

onMounted(load)
</script>

<style scoped>
.domain-view {
  min-height: 100%;
  display: grid;
  align-content: start;
  gap: 12px;
  padding: 12px;
  color: var(--dgm-text);
}

.domain-header,
.summary-strip,
.domain-grid,
.action-row,
.status-item {
  display: flex;
  gap: 10px;
}

.domain-header,
.action-row,
.status-item {
  align-items: center;
  justify-content: space-between;
}

.eyebrow,
.section-title {
  color: var(--dgm-text-faint);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: 20px;
}

h2 {
  font-size: 14px;
}

p {
  color: var(--dgm-text-muted);
  font-size: 12px;
}

.summary-strip {
  flex-wrap: wrap;
}

.summary-strip > div {
  min-width: 132px;
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.summary-strip span {
  display: block;
  color: var(--dgm-text-faint);
  font-size: 12px;
}

.summary-strip strong {
  font-size: 18px;
}

.domain-grid {
  align-items: start;
}

.main-section,
.side-section,
.action-list,
.status-list {
  display: grid;
  gap: 10px;
}

.main-section {
  flex: 1;
  min-width: 0;
}

.side-section {
  width: min(340px, 38%);
  min-width: 260px;
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.action-row {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.status-item {
  min-width: 0;
}

.status-item span {
  min-width: 0;
  overflow: hidden;
  color: var(--dgm-text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-state {
  color: var(--dgm-text-faint);
  font-size: 13px;
}

@media (max-width: 760px) {
  .domain-header,
  .domain-grid,
  .action-row {
    flex-direction: column;
    align-items: stretch;
  }

  .side-section {
    width: 100%;
  }
}
</style>
