<template>
  <section class="panel" aria-labelledby="preflight-title">
    <div class="panel-header">
      <div id="preflight-title" class="section-title">Preflight</div>
      <n-tag v-if="result" size="small" :type="result.valid ? 'success' : 'warning'">
        {{ result.valid ? 'valid' : 'needs input' }}
      </n-tag>
    </div>
    <div v-if="result" class="list">
      <div v-for="error in result.input_errors" :key="String(error.field) + String(error.code)" class="row">
        {{ error.message || error.code }}
      </div>
      <div v-for="asset in result.missing_assets" :key="String(asset.asset_type) + String(asset.asset_id)" class="row">
        Missing {{ asset.asset_type }} {{ asset.asset_id }}
      </div>
      <div v-for="capability in result.missing_capabilities" :key="capability" class="row">
        Missing capability {{ capability }}
      </div>
      <div v-for="warning in result.warnings" :key="warning" class="row muted">{{ warning }}</div>
      <div v-if="isEmpty" class="empty-state">Ready</div>
    </div>
    <div v-else class="empty-state">Not checked</div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NTag } from 'naive-ui'
import type { TemplatePreflightResult } from 'doge-sdk'

const props = defineProps<{ result?: TemplatePreflightResult | null }>()

const isEmpty = computed(() => {
  const result = props.result
  return Boolean(result) &&
    !result?.input_errors.length &&
    !result?.missing_assets.length &&
    !result?.missing_capabilities.length &&
    !result?.warnings.length
})
</script>

<style scoped>
.panel,
.list {
  display: grid;
  gap: 8px;
}

.panel-header {
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

.row {
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  color: var(--dgm-text);
  font-size: 12px;
}

.muted,
.empty-state {
  color: var(--dgm-text-muted);
  font-size: 12px;
}
</style>
