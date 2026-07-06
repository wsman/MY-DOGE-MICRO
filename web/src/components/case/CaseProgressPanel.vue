<template>
  <section class="panel" aria-labelledby="case-progress-title">
    <div id="case-progress-title" class="section-title">Progress</div>
    <div class="list">
      <article
        v-for="step in steps"
        :key="step.progress_id"
        class="progress-row"
        role="group"
        :aria-label="progressLabel(step)"
      >
        <div class="progress-top">
          <div class="step-main">
            <strong>{{ step.label }}</strong>
            <span>{{ step.owner }}</span>
          </div>
          <n-tag size="small" :type="toneFor(step.status)">
            {{ labelFor(step.status) }}
          </n-tag>
        </div>
        <p v-if="step.blocking_issue">{{ step.blocking_issue }}</p>
        <p v-else>{{ step.next_action || step.timestamp }}</p>
      </article>
      <div v-if="!steps.length" class="empty-state">No progress</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { NTag } from 'naive-ui'
import type { CaseProgressStep } from 'doge-sdk'

defineProps<{ steps: CaseProgressStep[] }>()

function labelFor(status: string): string {
  const labels: Record<string, string> = {
    blocked: 'Blocked',
    done: 'Done',
    in_progress: 'In progress',
    todo: 'Todo',
  }
  return labels[status] ?? status
}

function toneFor(status: string): 'default' | 'error' | 'info' | 'success' | 'warning' {
  if (status === 'done') return 'success'
  if (status === 'blocked') return 'warning'
  if (status === 'in_progress') return 'info'
  return 'default'
}

function progressLabel(step: CaseProgressStep): string {
  return `${step.label} ${labelFor(step.status)} owned by ${step.owner}`
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

.progress-row {
  display: grid;
  gap: 6px;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
}

.progress-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.step-main {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.step-main span,
p,
.empty-state {
  margin: 0;
  color: var(--dgm-text-muted);
  font-size: 12px;
  line-height: 1.4;
}
</style>
