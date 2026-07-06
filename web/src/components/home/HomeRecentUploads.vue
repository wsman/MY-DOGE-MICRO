<template>
  <article class="home-panel" aria-labelledby="recent-uploads-title">
    <div id="recent-uploads-title" class="section-title">Recent Uploads</div>
    <n-alert v-if="documentStore.error" type="warning" :show-icon="false" role="alert">
      {{ documentStore.error.message }}
    </n-alert>
    <div class="list">
      <div v-if="documentStore.loading && visibleDocuments.length === 0" class="empty-state">Loading documents</div>
      <div v-for="document in visibleDocuments" :key="document.document_id" class="upload-row">
        <div>
          <h2>{{ document.filename }}</h2>
          <p>{{ document.mime_type || 'unknown type' }} · {{ document.parsing_status || document.status || 'uploaded' }}</p>
        </div>
        <time v-if="document.created_at">{{ document.created_at }}</time>
      </div>
      <div v-if="!documentStore.loading && visibleDocuments.length === 0" class="empty-state">No uploads</div>
    </div>
    <n-button size="tiny" @click="router.push('/research-agent')">
      <template #icon><n-icon><CloudUploadOutline /></n-icon></template>
      Upload
    </n-button>
  </article>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { CloudUploadOutline } from '@vicons/ionicons5'
import { NAlert, NButton, NIcon } from 'naive-ui'
import { useDocumentStore } from '../../stores/documents'

const props = withDefaults(defineProps<{
  limit?: number
}>(), {
  limit: 5,
})

const router = useRouter()
const documentStore = useDocumentStore()
const visibleDocuments = computed(() => documentStore.documents.slice(0, props.limit))

onMounted(() => {
  documentStore.loadDocuments().catch(() => undefined)
})
</script>

<style scoped>
.home-panel {
  flex: 1 1 320px;
  display: grid;
  gap: 10px;
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.section-title {
  color: var(--dgm-text-faint);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.list {
  display: grid;
  gap: 8px;
}

.upload-row {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
}

.upload-row > div {
  min-width: 0;
}

h2,
p {
  margin: 0;
  overflow-wrap: anywhere;
}

h2 {
  color: var(--dgm-text);
  font-size: 14px;
}

p,
time,
.empty-state {
  color: var(--dgm-text-muted);
  font-size: 12px;
}

time {
  flex: 0 0 auto;
}

@media (max-width: 760px) {
  .upload-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
