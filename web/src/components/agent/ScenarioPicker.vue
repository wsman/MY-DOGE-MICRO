<template>
  <div class="scenario-picker" aria-label="Scenario template">
    <span class="sp-label">Scenario</span>
    <n-select
      v-model:value="model"
      :options="options"
      size="small"
      aria-label="Scenario template"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * ScenarioPicker — pick a workflow template so the run's workflow matches it.
 *
 * The selection flows to the agent store's `selectedScenarioSlug`, which
 * `startDemoRun` passes as the `workflow` on the create-run payload — and, via
 * the ADR-0028 threading landed in Slice I, that slug reaches the persisted
 * `AgentRun.workflow`.
 *
 * Template browsing is best-effort in Local Alpha: `/v1/workflow-templates` is
 * feature-flagged and may be disabled, so the four UX-1 defaults remain the
 * first-paint fallback.
 */
import { computed, onMounted } from 'vue'
import { NSelect } from 'naive-ui'

import { useAgentStore } from '../../stores/agent'
import { usePlatformStore } from '../../stores/platform'

const agentStore = useAgentStore()
const platformStore = usePlatformStore()

const FALLBACK_SCENARIOS = [
  { slug: 'daily_market_brief', label: 'Market Morning Brief' },
  { slug: 'earnings_review', label: 'Earnings Quality Review' },
  { slug: 'portfolio_risk_review', label: 'Portfolio Risk Review' },
  { slug: 'investment_committee_memo', label: 'Investment Committee Memo' },
] as const

const options = computed(() => {
  if (platformStore.workflowTemplates.length > 0) {
    return platformStore.workflowTemplates.map(template => ({
      label: template.name,
      value: template.slug,
    }))
  }
  return FALLBACK_SCENARIOS.map(scenario => ({ label: scenario.label, value: scenario.slug }))
})

const model = computed<string>({
  get: () => agentStore.selectedScenarioSlug,
  set: (value: string) => {
    agentStore.selectedScenarioSlug = value
  },
})

onMounted(() => {
  if (platformStore.workflowTemplates.length > 0) return
  platformStore.loadWorkflowTemplates().catch(() => undefined)
})
</script>

<style scoped>
.scenario-picker {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sp-label {
  color: var(--dgm-text-faint);
  font-size: 11px;
  text-transform: uppercase;
}
</style>
