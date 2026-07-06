<template>
  <div class="run-comparison" aria-label="Run comparison">
    <div class="comparison-header">
      <h3>Run Comparison</h3>
      <n-button size="tiny" :loading="loading" @click="loadRuns">Refresh</n-button>
    </div>
    <n-alert v-if="error" type="error" :show-icon="false">{{ error.message }}</n-alert>
    <div v-else-if="loading && runs.length === 0" class="muted">Loading runs</div>
    <div v-else-if="runs.length === 0" class="muted">No runs available</div>
    <div v-else class="comparison-table" role="table" aria-label="Recent run comparison">
      <div class="comparison-row header" role="row">
        <span>Run</span>
        <span>Status</span>
        <span>Workflow</span>
        <span>Evidence</span>
      </div>
      <div
        v-for="run in runs"
        :key="run.run_id"
        class="comparison-row"
        :class="{ current: run.run_id === currentRunId }"
        role="row"
      >
        <span class="run-id">{{ compactRunId(run.run_id) }}</span>
        <span><n-tag size="small" :type="toneFor(run.status)">{{ labelFor(run.status) }}</n-tag></span>
        <span>{{ run.workflow }}</span>
        <span>{{ run.artifact_count }} artifacts · {{ run.event_count }} events</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NAlert, NButton, NTag } from 'naive-ui'
import { listAgentRuns, type RunListItem } from '../../api/agent'
import { toFetchError, type FetchError } from '../../utils/fetchError'
import { labelFor, toneFor } from '../../utils/runStatus'

defineProps<{
  currentRunId?: string | null
}>()

const runs = ref<RunListItem[]>([])
const loading = ref(false)
const error = ref<FetchError | null>(null)

onMounted(() => {
  void loadRuns()
})

async function loadRuns() {
  loading.value = true
  error.value = null
  try {
    runs.value = await listAgentRuns(8)
  } catch (e) {
    error.value = toFetchError(e)
  } finally {
    loading.value = false
  }
}

function compactRunId(runId: string) {
  return runId.length > 12 ? `${runId.slice(0, 12)}...` : runId
}
</script>

<style scoped>
.run-comparison {
  display: grid;
  gap: 8px;
}

.comparison-header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.comparison-header h3 {
  margin: 0;
  font-size: 12px;
}

.comparison-table {
  display: grid;
  gap: 4px;
}

.comparison-row {
  display: grid;
  grid-template-columns: minmax(74px, 0.8fr) 92px minmax(90px, 1fr) minmax(118px, 1fr);
  gap: 6px;
  align-items: center;
  min-height: 28px;
  color: var(--dgm-text-muted);
  font-size: 11px;
}

.comparison-row.header {
  color: var(--dgm-text-faint);
  font-weight: 600;
  text-transform: uppercase;
}

.comparison-row.current {
  color: var(--dgm-text);
}

.run-id {
  font-family: var(--dgm-font-mono);
}

.comparison-row span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.muted {
  color: var(--dgm-text-faint);
  font-size: 11px;
}
</style>
