<template>
  <nav class="guided-flow" aria-label="Research workflow steps">
    <ol>
      <li
        v-for="step in steps"
        :key="step.id"
        :class="['gf-step', statusFor(step.status)]"
      >
        <button type="button" class="gf-step-button" @click="select(step.id)">
          <span class="gf-index">{{ step.index }}</span>
          <span class="gf-copy">
            <span class="gf-label">{{ step.label }}</span>
            <span class="gf-status">{{ step.statusLabel }}</span>
          </span>
        </button>
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
/**
 * GuidedFlow — a 4-step status rail over the research workflow (Sprint UX-1
 * Slice H, WEB-7). Each step's done/pending status is derived from existing
 * store state; clicking a step emits `select(stepId)` so the parent can scroll
 * to the relevant pane. Pure UX orchestration — adds no new inputs.
 *
 * Steps: Add Evidence (documents selected) -> Add Portfolio (portfolio set) ->
 * Ask Question (question + a run started) -> Review Memo (memo produced).
 */
import { computed } from 'vue'

import { useAgentStore } from '../../stores/agent'
import { useDocumentStore } from '../../stores/documents'

const emit = defineEmits<{ select: [stepId: string] }>()

const agentStore = useAgentStore()
const documentStore = useDocumentStore()

type StepStatus = 'done' | 'running' | 'pending' | 'missing'

interface GuidedStep {
  id: string
  index: number
  label: string
  status: StepStatus
  statusLabel: string
}

const steps = computed<GuidedStep[]>(() => [
  {
    id: 'evidence',
    index: 1,
    label: 'Add Evidence',
    ...evidenceStatus(),
  },
  {
    id: 'portfolio',
    index: 2,
    label: 'Add Portfolio',
    status: agentStore.portfolioId ? 'done' : 'pending',
    statusLabel: agentStore.portfolioId ? 'Ready' : 'Optional',
  },
  {
    id: 'question',
    index: 3,
    label: 'Ask Question',
    ...questionStatus(),
  },
  {
    id: 'memo',
    index: 4,
    label: 'Review Memo',
    ...memoStatus(),
  },
])

function evidenceStatus(): { status: StepStatus, statusLabel: string } {
  if (documentStore.selectedIds.length > 0) return { status: 'done', statusLabel: 'Ready' }
  if (agentStore.run !== null) return { status: 'missing', statusLabel: 'Missing input' }
  return { status: 'pending', statusLabel: 'Pending' }
}

function questionStatus(): { status: StepStatus, statusLabel: string } {
  if (agentStore.run !== null && !agentStore.latestMemo && ['running', 'awaiting_approval'].includes(String(agentStore.run.status))) {
    return { status: 'running', statusLabel: 'Running' }
  }
  if (agentStore.question.trim() && agentStore.run !== null) return { status: 'done', statusLabel: 'Submitted' }
  if (!agentStore.question.trim()) return { status: 'pending', statusLabel: 'Pending' }
  if (agentStore.run === null) return { status: 'pending', statusLabel: 'Ready to run' }
  return { status: 'pending', statusLabel: 'Pending' }
}

function memoStatus(): { status: StepStatus, statusLabel: string } {
  if (agentStore.latestMemo) return { status: 'done', statusLabel: 'Ready' }
  if (agentStore.run !== null && ['completed', 'failed', 'cancelled'].includes(String(agentStore.run.status))) {
    return { status: 'running', statusLabel: 'Loading' }
  }
  return { status: 'pending', statusLabel: 'Pending' }
}

function statusFor(status: StepStatus) {
  return `gf-${status}`
}

function select(stepId: string) {
  emit('select', stepId)
}
</script>

<style scoped>
.guided-flow ol {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  list-style: none;
  padding: 0;
  margin: 0;
}

.gf-step-button {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--dgm-border);
  background: var(--dgm-surface);
  border-radius: 6px;
  padding: 4px 8px;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  color: var(--dgm-text-muted);
}

.gf-copy {
  display: grid;
  gap: 1px;
}

.gf-index {
  font-weight: 700;
  color: var(--dgm-text-faint);
}

.gf-done .gf-step-button {
  color: var(--dgm-text);
  border-color: var(--dgm-text-muted);
}

.gf-running .gf-step-button {
  color: var(--dgm-text);
  border-color: var(--dgm-accent);
}

.gf-missing .gf-step-button {
  border-color: var(--dgm-warning, var(--dgm-border));
}

.gf-status {
  color: var(--dgm-text-faint);
  font-size: 10px;
  line-height: 1.2;
}
</style>
