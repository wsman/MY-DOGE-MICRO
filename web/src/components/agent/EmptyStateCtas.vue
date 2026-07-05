<template>
  <div class="empty-state-ctas" aria-label="Getting started">
    <p class="esc-hint">No memo generated yet. Try one of:</p>
    <n-space>
      <n-button size="small" type="primary" @click="$emit('run-demo')">Run Demo</n-button>
      <n-button size="small" @click="$emit('load-sample')">Load Sample Case</n-button>
      <n-button size="small" @click="$emit('upload')">Upload Documents</n-button>
      <n-button size="small" @click="$emit('import-portfolio')">Import Portfolio</n-button>
    </n-space>
  </div>
</template>

<script setup lang="ts">
/**
 * EmptyStateCtas — four getting-started CTAs shown in the memo pane when no run
 * has produced a memo yet (Sprint UX-1 Slice F, WEB-3). Each emits a distinct
 * event the parent wires to an existing flow (start the demo, pick a sample
 * scenario, scroll to the uploader / importer). Replaces the bare
 * "No memo generated" placeholder.
 */
import { NButton, NSpace } from 'naive-ui'

defineEmits<{
  'run-demo': []
  'load-sample': []
  upload: []
  'import-portfolio': []
}>()
</script>

<style scoped>
.empty-state-ctas {
  display: grid;
  gap: 8px;
}

.esc-hint {
  margin: 0;
  color: var(--dgm-text-faint);
  font-size: 13px;
}
</style>
