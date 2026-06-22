<template>
  <div class="document-selector">
    <n-space size="small" align="center">
      <n-button size="tiny" :loading="store.loading" @click="store.loadDocuments">Refresh</n-button>
      <n-button size="tiny" secondary @click="store.selectAll">All</n-button>
      <n-button size="tiny" secondary @click="store.clearSelection">Clear</n-button>
    </n-space>

    <div v-if="store.documents.length" class="document-list" role="list" aria-label="Uploaded documents">
      <label
        v-for="document in store.documents"
        :key="document.document_id"
        class="document-row"
        role="listitem"
      >
        <n-checkbox
          :checked="store.selectedIds.includes(document.document_id)"
          @update:checked="checked => store.toggleSelection(document.document_id, Boolean(checked))"
        />
        <span class="document-main">
          <span class="document-name">{{ document.filename || document.original_filename || document.document_id }}</span>
          <span class="document-meta">
            {{ document.mime_type || 'unknown' }} · {{ formatBytes(document.size_bytes) }}
          </span>
        </span>
        <n-tag size="small" :type="statusType(document.parsing_status || document.status)">
          {{ document.parsing_status || document.status || 'unknown' }}
        </n-tag>
      </label>
    </div>
    <div v-else class="empty-documents">No documents uploaded</div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { NButton, NCheckbox, NSpace, NTag } from 'naive-ui'
import { useDocumentStore } from '../../stores/documents'

const store = useDocumentStore()

onMounted(() => {
  void store.loadDocuments()
})

function formatBytes(value?: number | null) {
  if (!value) return '0 B'
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

function statusType(status?: string): 'default' | 'success' | 'error' | 'warning' {
  if (status === 'parsed') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'parsing') return 'warning'
  return 'default'
}
</script>

<style scoped>
.document-selector {
  display: grid;
  gap: 8px;
}

.document-list {
  display: grid;
  gap: 6px;
  max-height: 190px;
  overflow: auto;
}

.document-row {
  min-width: 0;
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 7px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.document-main {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.document-name,
.document-meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-name {
  color: var(--dgm-text);
  font-size: 12px;
}

.document-meta,
.empty-documents {
  color: var(--dgm-text-faint);
  font-size: 12px;
}
</style>
