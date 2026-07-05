<template>
  <section class="preflight" aria-label="Run preflight checklist">
    <div class="preflight-title">Run checks</div>
    <div class="preflight-list">
      <div
        v-for="item in checks"
        :key="item.id"
        class="preflight-item"
        :class="`is-${item.status}`"
      >
        <n-tag size="small" :type="item.status === 'ok' ? 'success' : 'warning'">
          {{ item.status === 'ok' ? 'OK' : 'Warn' }}
        </n-tag>
        <div class="preflight-copy">
          <div class="preflight-label">{{ item.label }}</div>
          <div class="preflight-detail">{{ item.detail }}</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { NTag } from 'naive-ui'

import { useAgentStore } from '../../stores/agent'
import { useDocumentStore } from '../../stores/documents'
import { usePlatformStore } from '../../stores/platform'

const agentStore = useAgentStore()
const documentStore = useDocumentStore()
const platformStore = usePlatformStore()

const kimiConfigured = computed(() => (
  platformStore.capabilitiesById['provider.kimi']?.metadata?.configured === true
))

const providerKnown = computed(() => Boolean(platformStore.capabilities))

const checks = computed(() => [
  {
    id: 'market',
    label: 'Market',
    status: agentStore.market ? 'ok' : 'warn',
    detail: agentStore.market ? `${agentStore.market.toUpperCase()} selected` : 'Select a market before running.',
  },
  {
    id: 'documents',
    label: 'Evidence',
    status: documentStore.selectedIds.length > 0 ? 'ok' : 'warn',
    detail: documentStore.selectedIds.length > 0
      ? `${documentStore.selectedIds.length} document${documentStore.selectedIds.length === 1 ? '' : 's'} selected`
      : 'No document selected; evidence-backed sections may degrade.',
  },
  {
    id: 'portfolio',
    label: 'Portfolio',
    status: agentStore.portfolioId ? 'ok' : 'warn',
    detail: agentStore.portfolioId
      ? `Portfolio ${agentStore.portfolioId} imported`
      : 'No portfolio imported; portfolio risk sections will be skipped.',
  },
  {
    id: 'provider',
    label: 'Kimi provider',
    status: kimiConfigured.value ? 'ok' : 'warn',
    detail: kimiConfigured.value
      ? 'Kimi key configured'
      : providerKnown.value
        ? 'Kimi key not configured; scripted fallback may be used.'
        : 'Provider status unknown; run can still use local fallback.',
  },
] as const)

onMounted(() => {
  if (!platformStore.capabilities) {
    platformStore.loadCapabilities().catch(() => undefined)
  }
})
</script>

<style scoped>
.preflight {
  display: grid;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.preflight-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--dgm-text-faint);
  text-transform: uppercase;
}

.preflight-list {
  display: grid;
  gap: 6px;
}

.preflight-item {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}

.preflight-copy {
  min-width: 0;
}

.preflight-label {
  color: var(--dgm-text);
  font-size: 12px;
  font-weight: 600;
}

.preflight-detail {
  color: var(--dgm-text-muted);
  font-size: 12px;
  line-height: 1.35;
}
</style>
