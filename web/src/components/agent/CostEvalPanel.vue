<template>
  <div class="cost-eval-panel">
    <div class="section-title">Cost / Eval</div>
    <div class="metric-grid" aria-label="Cost and evaluation metrics">
      <div class="metric">
        <span>Total Tokens</span>
        <strong>{{ metricValue(usage.total_tokens) }}</strong>
      </div>
      <div class="metric">
        <span>Prompt Tokens</span>
        <strong>{{ metricValue(usage.prompt_tokens) }}</strong>
      </div>
      <div class="metric">
        <span>Cost USD</span>
        <strong>{{ moneyValue(costUsd) }}</strong>
      </div>
      <div class="metric">
        <span>Citation Precision</span>
        <strong>{{ percentValue(metrics.citation_precision) }}</strong>
      </div>
      <div class="metric">
        <span>Numerical Consistency</span>
        <strong>{{ percentValue(metrics.numerical_consistency) }}</strong>
      </div>
      <div class="metric">
        <span>Tool Success</span>
        <strong>{{ percentValue(metrics.tool_execution_success) }}</strong>
      </div>
    </div>
    <div class="routing" aria-label="Routing decision">
      <n-tag size="small">{{ routing.backend || 'backend n/a' }}</n-tag>
      <n-tag size="small">{{ routing.model || 'model n/a' }}</n-tag>
      <n-tag v-if="routing.run_budget_usd !== undefined" size="small">
        budget {{ moneyValue(routing.run_budget_usd) }}
      </n-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NTag } from 'naive-ui'
import type { AgentArtifact, AgentEvent } from '../../api/agent'

const props = defineProps<{
  artifacts: AgentArtifact[]
  events: AgentEvent[]
}>()

const latestArtifactData = computed(() => props.artifacts[0]?.data ?? {})
const latestModelPayload = computed(() => {
  for (const event of [...props.events].reverse()) {
    if (event.event_type === 'model_response') return event.payload
  }
  return {}
})

const usage = computed<Record<string, unknown>>(() => {
  const artifactUsage = latestArtifactData.value.usage
  if (isRecord(artifactUsage)) return artifactUsage
  const eventUsage = latestModelPayload.value.usage
  return isRecord(eventUsage) ? eventUsage : {}
})

const routing = computed<Record<string, unknown>>(() => {
  const eventRouting = latestModelPayload.value.routing
  return isRecord(eventRouting) ? eventRouting : {}
})

const metrics = computed<Record<string, unknown>>(() => ({
  citation_precision: latestArtifactData.value.citation_precision,
  numerical_consistency: latestArtifactData.value.numerical_consistency,
  tool_execution_success: latestArtifactData.value.tool_execution_success,
}))

const costUsd = computed(() => {
  if (usage.value.cost_usd !== undefined) return usage.value.cost_usd
  return latestArtifactData.value.cost_usd
})

function metricValue(value: unknown) {
  return value === undefined || value === null || value === '' ? 'n/a' : String(value)
}

function moneyValue(value: unknown) {
  const number = numberValue(value)
  return number === undefined ? 'n/a' : `$${number.toFixed(4)}`
}

function percentValue(value: unknown) {
  const number = numberValue(value)
  return number === undefined ? 'n/a' : `${Math.round(number * 100)}%`
}

function numberValue(value: unknown): number | undefined {
  if (typeof value === 'number') return value
  if (typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Number(value))) {
    return Number(value)
  }
  return undefined
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
</script>

<style scoped>
.cost-eval-panel {
  display: grid;
  gap: 8px;
}

.section-title {
  color: var(--dgm-text-muted);
  font-size: 12px;
  font-weight: 700;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.metric {
  min-width: 0;
  display: grid;
  gap: 2px;
  padding: 7px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.metric span {
  color: var(--dgm-text-faint);
  font-size: 11px;
}

.metric strong {
  color: var(--dgm-text);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.routing {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
