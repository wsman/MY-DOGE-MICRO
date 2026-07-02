<template>
  <section class="panel" aria-labelledby="case-assets-title">
    <div class="panel-header">
      <div id="case-assets-title" class="section-title">Case Assets</div>
      <n-tag size="small">{{ assets.length }}</n-tag>
    </div>

    <div class="asset-form">
      <n-select
        v-model:value="assetType"
        size="small"
        :options="assetTypeOptions"
        aria-label="Asset type"
        :input-props="{ 'aria-label': 'Asset type' }"
      />
      <n-input
        v-model:value="assetId"
        size="small"
        placeholder="Asset ID or URL"
        aria-label="Asset ID or URL"
        :input-props="{ 'aria-label': 'Asset ID or URL' }"
      />
      <n-input
        v-model:value="assetName"
        size="small"
        placeholder="Name"
        aria-label="Asset display name"
        :input-props="{ 'aria-label': 'Asset display name' }"
      />
      <n-button size="small" type="primary" :disabled="!assetId.trim()" @click="submit">Add</n-button>
    </div>

    <div class="list">
      <article v-for="asset in assets" :key="asset.asset_link_id" class="asset-row">
        <div>
          <h3>{{ asset.asset_name || asset.asset_id }}</h3>
          <p>{{ asset.asset_type }} · {{ asset.role }}</p>
        </div>
        <n-tag size="small">{{ asset.version || 'current' }}</n-tag>
      </article>
      <div v-if="!assets.length" class="empty-state">No assets</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NInput, NSelect, NTag } from 'naive-ui'
import type { CaseAssetLink } from 'doge-sdk'

defineProps<{ assets: CaseAssetLink[] }>()
const emit = defineEmits<{
  add: [payload: { asset_type: string; asset_id: string; asset_name: string; role: string }]
}>()

const assetType = ref('document')
const assetId = ref('')
const assetName = ref('')
const assetTypeOptions = [
  { label: 'Document', value: 'document' },
  { label: 'Portfolio', value: 'portfolio' },
  { label: 'URL', value: 'url' },
]

function submit() {
  if (!assetId.value.trim()) return
  emit('add', {
    asset_type: assetType.value,
    asset_id: assetId.value.trim(),
    asset_name: assetName.value.trim(),
    role: assetType.value === 'portfolio' ? 'portfolio' : 'source',
  })
  assetId.value = ''
  assetName.value = ''
}
</script>

<style scoped>
.panel,
.asset-form,
.list {
  display: grid;
  gap: 8px;
}

.panel {
  min-width: 0;
}

.panel-header,
.asset-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.section-title {
  color: var(--dgm-text-faint);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.asset-row {
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

h3,
p {
  margin: 0;
}

h3 {
  font-size: 13px;
}

p,
.empty-state {
  color: var(--dgm-text-muted);
  font-size: 12px;
}
</style>
