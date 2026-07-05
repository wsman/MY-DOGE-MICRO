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
 * ScenarioPicker — pick one of the four shipped scenario templates so the run's
 * workflow matches it (Sprint UX-1 Slice G, WEB-10 frontend half).
 *
 * The selection flows to the agent store's `selectedScenarioSlug`, which
 * `startDemoRun` passes as the `workflow` on the create-run payload — and, via
 * the ADR-0028 threading landed in Slice I, that slug reaches the persisted
 * `AgentRun.workflow`.
 *
 * The four slugs/labels are hardcoded here (matching
 * `src/doge/platform/workspace/template_seed.py`) rather than fetched, so the
 * picker has no network dependency and renders immediately.
 */
import { computed } from 'vue'
import { NSelect } from 'naive-ui'

import { useAgentStore } from '../../stores/agent'

const agentStore = useAgentStore()

// The four shipped named templates (template_seed.py).
const SCENARIOS = [
  { slug: 'daily_market_brief', label: 'Market Morning Brief' },
  { slug: 'earnings_review', label: 'Earnings Quality Review' },
  { slug: 'portfolio_risk_review', label: 'Portfolio Risk Review' },
  { slug: 'investment_committee_memo', label: 'Investment Committee Memo' },
] as const

const options = SCENARIOS.map(scenario => ({ label: scenario.label, value: scenario.slug }))

const model = computed<string>({
  get: () => agentStore.selectedScenarioSlug,
  set: (value: string) => {
    agentStore.selectedScenarioSlug = value
  },
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
