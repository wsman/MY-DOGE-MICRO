<template>
  <section class="panel" aria-labelledby="execution-monitor-title">
    <div id="execution-monitor-title" class="section-title">Executions</div>
    <div class="list">
      <article v-for="execution in executions" :key="execution.execution_id" class="execution-row">
        <div>
          <h3>{{ execution.template_slug || execution.template_id }}</h3>
          <p>{{ execution.execution_id }} · {{ execution.run_id || 'no run' }}</p>
        </div>
        <n-space size="small" align="center">
          <n-tag size="small" :type="statusType(execution.status)">{{ execution.status }}</n-tag>
          <n-button v-if="execution.run_id" size="tiny" @click="$emit('open-run', execution.run_id)">Open</n-button>
        </n-space>
      </article>
      <div v-if="!executions.length" class="empty-state">No executions</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { NButton, NSpace, NTag } from 'naive-ui'
import type { WorkflowExecution } from 'doge-sdk'
import { toneFor } from '../../utils/runStatus'

defineProps<{ executions: WorkflowExecution[] }>()
defineEmits<{ 'open-run': [runId: string] }>()

// WorkflowExecution status overlaps RunStatus plus the execution-specific
// 'preflight_failed'. Delegate the shared tones to runStatus and keep only the
// execution-specific override here so no RunStatus literals are duplicated
// (Sprint UX-1 Slice A, WEB-2).
function statusType(status: string) {
  if (status === 'preflight_failed') return 'error'
  return toneFor(status)
}
</script>

<style scoped>
.panel,
.list {
  display: grid;
  gap: 8px;
}

.section-title {
  color: var(--dgm-text-faint);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.execution-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

h3,
p {
  margin: 0;
}

h3 {
  font-size: 13px;
}

p,
.empty-state {
  color: var(--dgm-text-muted);
  font-size: 12px;
}
</style>
