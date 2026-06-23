<template>
  <section class="panel" aria-labelledby="case-decision-title">
    <div id="case-decision-title" class="section-title">Decision</div>
    <div class="decision-form">
      <n-select
        v-model:value="decisionType"
        size="small"
        :options="decisionOptions"
        aria-label="Decision type"
        :input-props="{ 'aria-label': 'Decision type' }"
      />
      <n-input
        v-model:value="rationale"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 5 }"
        placeholder="Rationale"
        aria-label="Decision rationale"
        :input-props="{ 'aria-label': 'Decision rationale' }"
      />
      <n-button size="small" type="primary" @click="submit">Record</n-button>
    </div>
    <div class="list">
      <article v-for="decision in decisions" :key="decision.decision_id" class="decision-row">
        <div class="decision-top">
          <strong>{{ decision.decision_type }}</strong>
          <span>{{ decision.created_at }}</span>
        </div>
        <p>{{ decision.rationale || 'No rationale' }}</p>
      </article>
      <div v-if="!decisions.length" class="empty-state">No decisions</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NInput, NSelect } from 'naive-ui'
import type { CaseDecision } from '../../types/platform'

defineProps<{ decisions: CaseDecision[] }>()
const emit = defineEmits<{
  record: [payload: { decision_type: string; rationale: string }]
}>()

const decisionType = ref('hold')
const rationale = ref('')
const decisionOptions = [
  { label: 'Approve', value: 'approve' },
  { label: 'Reject', value: 'reject' },
  { label: 'Hold', value: 'hold' },
  { label: 'Escalate', value: 'escalate' },
]

function submit() {
  emit('record', {
    decision_type: decisionType.value,
    rationale: rationale.value.trim(),
  })
  rationale.value = ''
}
</script>

<style scoped>
.panel,
.decision-form,
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

.decision-row {
  display: grid;
  gap: 4px;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
}

.decision-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
}

p,
.empty-state {
  margin: 0;
  color: var(--dgm-text-muted);
  font-size: 12px;
}
</style>
