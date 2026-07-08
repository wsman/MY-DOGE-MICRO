<template>
  <div class="platform-view" aria-label="Admin center">
    <header class="platform-header">
      <div>
        <div class="eyebrow">Admin</div>
        <h1>Capability / Slot Center</h1>
      </div>
      <n-button size="small" :loading="store.loading" @click="load">
        <template #icon>
          <n-icon><RefreshOutline /></n-icon>
        </template>
        Refresh
      </n-button>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>

    <section class="ops-section" aria-label="Slot Center">
      <div class="section-heading">
        <div>
          <div class="eyebrow">Slots</div>
          <h2>Slot Center</h2>
        </div>
        <p>{{ slotStatusLine }}</p>
      </div>

      <section class="summary-strip" aria-label="Slot summary">
        <div v-for="metric in slotMetrics" :key="metric.label">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
        </div>
      </section>

      <n-spin :show="store.loading">
        <div class="slot-layout">
          <div class="row-list" role="list" aria-label="Installed slots">
            <article v-for="slot in slots" :key="slot.id" class="slot-row" role="listitem">
              <div class="row-main">
                <div class="row-copy">
                  <h3>{{ slot.name }}</h3>
                  <p>{{ slot.id }}</p>
                </div>
                <n-space size="small" class="row-tags">
                  <n-tag size="small">{{ slot.type }}</n-tag>
                  <n-tag size="small" :type="slotTagType(slot.status)">{{ slot.status }}</n-tag>
                  <n-tag size="small" :type="healthTagType(slot.health.status)">{{ slot.health.status }}</n-tag>
                  <n-tag size="small" :type="riskTagType(slot.permissions.risk_level)">{{ slot.permissions.risk_level }}</n-tag>
                </n-space>
              </div>
              <div class="row-meta">
                <span>{{ slot.owner }}</span>
                <span>{{ slot.maturity }}</span>
                <span>{{ slot.counts.tools }} tools</span>
                <span>{{ slot.counts.capabilities }} caps</span>
                <span>{{ flagsLabel(slot.feature_flags) }}</span>
              </div>
            </article>
            <div v-if="!slots.length && !store.loading" class="empty-state">No slots</div>
          </div>

          <div class="bundle-panel" aria-label="Slot bundles">
            <div class="bundle-header">
              <h3>Bundles</h3>
              <n-tag size="small">{{ bundles.length }}</n-tag>
            </div>
            <div class="row-list compact" role="list" aria-label="Slot bundle status">
              <article v-for="bundle in bundles" :key="bundle.id" class="bundle-row" role="listitem">
                <div class="row-main">
                  <div class="row-copy">
                    <h4>{{ bundle.name }}</h4>
                    <p>{{ bundle.id }}</p>
                  </div>
                  <n-space size="small" class="row-tags">
                    <n-tag v-if="bundle.active" size="small" type="success">active</n-tag>
                    <n-tag size="small" :type="bundleTagType(bundle.status)">{{ bundle.status }}</n-tag>
                  </n-space>
                </div>
                <div class="row-meta">
                  <span>{{ bundle.counts.enabled }} enabled</span>
                  <span>{{ bundle.counts.disabled }} disabled</span>
                  <span>{{ bundle.counts.missing }} missing</span>
                </div>
                <div class="bundle-actions">
                  <n-button
                    size="tiny"
                    secondary
                    type="primary"
                    :disabled="activateDisabled(bundle)"
                    :loading="pendingBundleId === bundle.id && pendingAction === 'activate'"
                    @click="activateBundle(bundle.id)"
                  >
                    <template #icon>
                      <n-icon><PlayCircleOutline /></n-icon>
                    </template>
                    Activate
                  </n-button>
                  <n-button
                    v-if="bundle.active"
                    size="tiny"
                    secondary
                    type="warning"
                    :disabled="deactivateDisabled(bundle)"
                    :loading="pendingBundleId === bundle.id && pendingAction === 'deactivate'"
                    @click="deactivateBundle(bundle.id)"
                  >
                    <template #icon>
                      <n-icon><StopCircleOutline /></n-icon>
                    </template>
                    Deactivate
                  </n-button>
                </div>
              </article>
              <div v-if="!bundles.length && !store.loading" class="empty-state">No bundles</div>
            </div>
          </div>
        </div>
      </n-spin>
    </section>

    <section class="ops-section" aria-label="Capability registry">
      <div class="section-heading">
        <div>
          <div class="eyebrow">Capabilities</div>
          <h2>Capability Registry</h2>
        </div>
      </div>

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
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { PlayCircleOutline, RefreshOutline, StopCircleOutline } from '@vicons/ionicons5'
import { NAlert, NButton, NIcon, NSpace, NSpin, NTag } from 'naive-ui'
import { usePlatformStore } from '../stores/platform'
import type { SlotBundleRow } from '../api/platform'

const store = usePlatformStore()
const pendingBundleId = ref<string | null>(null)
const pendingAction = ref<'activate' | 'deactivate' | null>(null)
const errorMessage = computed(() => store.error?.message ?? '')
const capabilities = computed(() => store.capabilities?.capabilities ?? [])
const statusCounts = computed(() => store.capabilities?.status_counts ?? {})
const slots = computed(() => [...store.slotRows].sort((left, right) => (
  left.type.localeCompare(right.type) || left.id.localeCompare(right.id)
)))
const bundles = computed(() => [...store.slotBundles].sort((left, right) => left.id.localeCompare(right.id)))
const slotMetrics = computed(() => {
  const rows = slots.value
  return [
    { label: 'Installed', value: rows.length },
    { label: 'Enabled', value: rows.filter(slot => slot.status === 'resolved').length },
    { label: 'Disabled', value: rows.filter(slot => slot.status === 'disabled').length },
    { label: 'Degraded', value: rows.filter(slot => slot.health.status === 'degraded').length },
    { label: 'High risk', value: rows.filter(slot => ['high', 'forbidden'].includes(slot.permissions.risk_level)).length },
  ]
})
const slotStatusLine = computed(() => {
  const resolved = slotMetrics.value.find(metric => metric.label === 'Enabled')?.value ?? 0
  return `${resolved}/${slots.value.length} enabled`
})

function tagType(status: string) {
  if (status === 'available') return 'success'
  if (status === 'blocked' || status === 'unconfigured') return 'warning'
  return 'default'
}

function slotTagType(status: string) {
  if (status === 'resolved') return 'success'
  if (status === 'disabled' || status === 'partial') return 'warning'
  if (status === 'invalid') return 'error'
  return 'default'
}

function healthTagType(status: string) {
  if (status === 'healthy') return 'success'
  if (status === 'degraded') return 'warning'
  if (status === 'disabled') return 'default'
  return 'info'
}

function riskTagType(risk: string) {
  if (risk === 'high' || risk === 'forbidden') return 'error'
  if (risk === 'medium') return 'warning'
  return 'success'
}

function bundleTagType(status: string) {
  if (status === 'resolved') return 'success'
  if (status === 'partial' || status === 'disabled') return 'warning'
  if (status === 'invalid') return 'error'
  return 'default'
}

function activateDisabled(bundle: SlotBundleRow) {
  return (
    store.loading ||
    pendingBundleId.value !== null ||
    bundle.active ||
    bundle.status === 'invalid' ||
    bundle.counts.missing > 0
  )
}

function deactivateDisabled(bundle: SlotBundleRow) {
  return store.loading || pendingBundleId.value !== null || !bundle.active
}

function flagsLabel(flags: string[]) {
  return flags.length ? flags.join(', ') : 'always on'
}

async function load() {
  await Promise.allSettled([
    store.loadCapabilities(),
    store.loadSlots(),
    store.loadSlotBundles(),
  ])
}

async function activateBundle(bundleId: string) {
  pendingBundleId.value = bundleId
  pendingAction.value = 'activate'
  try {
    await store.activateSlotBundle(bundleId)
  } finally {
    pendingBundleId.value = null
    pendingAction.value = null
  }
}

async function deactivateBundle(bundleId: string) {
  pendingBundleId.value = bundleId
  pendingAction.value = 'deactivate'
  try {
    await store.deactivateSlotBundle()
  } finally {
    pendingBundleId.value = null
    pendingAction.value = null
  }
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
.capability-row,
.row-main,
.bundle-header {
  display: flex;
  gap: 10px;
}

.platform-header,
.capability-row,
.row-main,
.bundle-header {
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
h3,
h4,
p {
  margin: 0;
}

h1 {
  font-size: 20px;
}

h2 {
  font-size: 14px;
}

h3,
h4 {
  font-size: 13px;
}

p {
  color: var(--dgm-text-muted);
  font-size: 12px;
}

.ops-section {
  display: grid;
  gap: 10px;
}

.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
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

.slot-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 0.42fr);
  gap: 10px;
  align-items: start;
}

.row-list {
  display: grid;
  gap: 8px;
}

.row-list.compact {
  gap: 6px;
}

.slot-row,
.bundle-row,
.capability-row {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.bundle-panel {
  display: grid;
  gap: 8px;
}

.bundle-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.row-copy,
.row-tags {
  min-width: 0;
}

.row-copy p,
.row-meta {
  overflow-wrap: anywhere;
}

.row-tags {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.row-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  margin-top: 8px;
  color: var(--dgm-text-faint);
  font-size: 12px;
}

.empty-state {
  color: var(--dgm-text-faint);
  font-size: 13px;
}

@media (max-width: 760px) {
  .capability-row,
  .row-main,
  .section-heading,
  .platform-header {
    flex-direction: column;
    align-items: stretch;
  }

  .slot-layout {
    grid-template-columns: 1fr;
  }

  .row-tags {
    justify-content: flex-start;
  }
}
</style>
