<template>
  <section class="panel" aria-labelledby="case-approval-title">
    <div id="case-approval-title" class="section-title">Approval</div>
    <div class="list">
      <article
        v-for="approval in approvals"
        :key="String(approval.approval_id)"
        class="approval-row"
        role="group"
        :aria-label="approvalLabel(approval)"
      >
        <div class="approval-top">
          <strong>{{ approval.risk_level || 'review' }}</strong>
          <n-tag size="small" :type="approval.status === 'pending' ? 'warning' : 'default'">
            {{ approval.status || 'unknown' }}
          </n-tag>
        </div>
        <p>{{ approval.action || 'Approval action pending' }}</p>
        <n-button
          v-if="approval.run_id"
          size="tiny"
          secondary
          @click="$emit('openRun', String(approval.run_id))"
        >
          Open Run
        </n-button>
      </article>
      <div v-if="!approvals.length" class="empty-state">No approvals pending</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { NButton, NTag } from 'naive-ui'
import type { JsonObject } from 'doge-sdk'

defineProps<{ approvals: JsonObject[] }>()
defineEmits<{
  openRun: [runId: string]
}>()

function approvalLabel(approval: JsonObject): string {
  const risk = String(approval.risk_level || 'review')
  const status = String(approval.status || 'unknown')
  const action = String(approval.action || 'approval action')
  return `${risk} risk approval ${status}: ${action}`
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

.approval-row {
  display: grid;
  gap: 6px;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
}

.approval-top {
  display: flex;
  align-items: center;
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
