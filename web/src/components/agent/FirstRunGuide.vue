<template>
  <n-modal :show="visible" preset="card" class="first-run-guide" @update:show="onUpdateShow">
    <div class="guide-body" aria-label="First run guide">
      <div>
        <h2>Start Research</h2>
        <p>Load a sample, add evidence, run the agent, review citations, then export the memo.</p>
      </div>
      <div class="guide-actions" role="group" aria-label="First run actions">
        <n-button type="primary" size="small" @click="dismiss">Begin</n-button>
        <n-button size="small" secondary @click="dismiss">Skip</n-button>
      </div>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NModal } from 'naive-ui'

import { useAgentStore } from '../../stores/agent'

const STORAGE_KEY = 'doge.firstRunSeen'

const store = useAgentStore()
const dismissed = ref(readDismissed())
const visible = computed(() => !dismissed.value && store.run === null)

function onUpdateShow(show: boolean) {
  if (!show) dismiss()
}

function dismiss() {
  dismissed.value = true
  writeDismissed()
}

function readDismissed() {
  if (typeof window === 'undefined') return false
  return window.localStorage.getItem(STORAGE_KEY) === '1'
}

function writeDismissed() {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(STORAGE_KEY, '1')
}
</script>

<style scoped>
.guide-body {
  display: grid;
  gap: 14px;
  color: var(--dgm-text);
}

h2 {
  margin: 0 0 6px;
  font-size: 18px;
}

p {
  margin: 0;
  color: var(--dgm-text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.guide-actions {
  display: flex;
  gap: 8px;
}
</style>
