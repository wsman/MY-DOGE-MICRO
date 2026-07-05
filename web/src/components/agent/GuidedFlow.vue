<template>
  <nav class="guided-flow" aria-label="Research workflow steps">
    <ol>
      <li
        v-for="step in steps"
        :key="step.id"
        :class="['gf-step', statusFor(step.done)]"
      >
        <button type="button" class="gf-step-button" @click="select(step.id)">
          <span class="gf-index">{{ step.index }}</span>
          <span class="gf-label">{{ step.label }}</span>
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

const steps = computed(() => [
  { id: 'evidence', index: 1, label: 'Add Evidence', done: documentStore.selectedIds.length > 0 },
  { id: 'portfolio', index: 2, label: 'Add Portfolio', done: Boolean(agentStore.portfolioId) },
  {
    id: 'question',
    index: 3,
    label: 'Ask Question',
    done: Boolean(agentStore.question) && agentStore.run !== null,
  },
  { id: 'memo', index: 4, label: 'Review Memo', done: Boolean(agentStore.latestMemo) },
])

function statusFor(done: boolean) {
  return done ? 'gf-done' : 'gf-pending'
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

.gf-index {
  font-weight: 700;
  color: var(--dgm-text-faint);
}

.gf-done .gf-step-button {
  color: var(--dgm-text);
  border-color: var(--dgm-text-muted);
}
</style>
