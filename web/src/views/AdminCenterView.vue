<template>
  <div class="platform-view" aria-label="Admin center">
    <header class="platform-header">
      <div>
        <div class="eyebrow">Admin</div>
        <h1>Capability Registry</h1>
      </div>
      <n-button size="small" :loading="store.loading" @click="load">Refresh</n-button>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>

    <section class="summary-strip" aria-label="Capability summary">
      <div v-for="(count, status) in statusCounts" :key="status">
        <span>{{ status }}</span>
        <strong>{{ count }}</strong>
      </div>
    </section>

    <n-spin :show="store.loading">
      <div class="capability-list" role="list" aria-label="Capabilities">
        <article v-for="capability in capabilities" :key="capability.capability_id" class="capability-row" role="listitem">
          <div>
            <h2>{{ capability.name }}</h2>
            <p>{{ capability.capability_id }}</p>
          </div>
          <n-space size="small">
            <n-tag size="small">{{ capability.kind }}</n-tag>
            <n-tag size="small" :type="tagType(capability.status)">{{ capability.status }}</n-tag>
          </n-space>
        </article>
        <div v-if="!capabilities.length && !store.loading" class="empty-state">No capabilities</div>
      </div>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { NAlert, NButton, NSpace, NSpin, NTag } from 'naive-ui'
import { usePlatformStore } from '../stores/platform'

const store = usePlatformStore()
const errorMessage = computed(() => store.error?.message ?? '')
const capabilities = computed(() => store.capabilities?.capabilities ?? [])
const statusCounts = computed(() => store.capabilities?.status_counts ?? {})

function tagType(status: string) {
  if (status === 'available') return 'success'
  if (status === 'blocked' || status === 'unconfigured') return 'warning'
  return 'default'
}

async function load() {
  await store.loadCapabilities().catch(() => undefined)
}

onMounted(load)
</script>

<style scoped>
.platform-view {
  min-height: 100%;
  display: grid;
  align-content: start;
  gap: 12px;
  padding: 12px;
  color: var(--dgm-text);
}

.platform-header,
.summary-strip,
.capability-row {
  display: flex;
  gap: 10px;
}

.platform-header,
.capability-row {
  align-items: center;
  justify-content: space-between;
}

.eyebrow {
  color: var(--dgm-text-faint);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: 20px;
}

h2 {
  font-size: 14px;
}

p {
  color: var(--dgm-text-muted);
  font-size: 12px;
}

.summary-strip {
  flex-wrap: wrap;
}

.summary-strip > div {
  min-width: 140px;
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.summary-strip span {
  display: block;
  color: var(--dgm-text-faint);
  font-size: 12px;
}

.summary-strip strong {
  font-size: 18px;
}

.capability-list {
  display: grid;
  gap: 8px;
}

.capability-row {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.empty-state {
  color: var(--dgm-text-faint);
  font-size: 13px;
}

@media (max-width: 760px) {
  .capability-row,
  .platform-header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
