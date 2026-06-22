<template>
  <div class="platform-view" aria-label="Template center">
    <header class="platform-header">
      <div>
        <div class="eyebrow">Workflow</div>
        <h1>Templates</h1>
      </div>
      <n-space size="small">
        <n-button size="small" :loading="store.loading" @click="load">Refresh</n-button>
        <n-button size="small" type="primary" :disabled="!slug.trim() || !name.trim()" @click="createTemplate">
          New
        </n-button>
      </n-space>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>

    <section class="create-row" aria-label="Create workflow template">
      <n-input v-model:value="slug" size="small" placeholder="slug" />
      <n-input v-model:value="name" size="small" placeholder="Name" />
      <n-input v-model:value="description" size="small" placeholder="Description" />
    </section>

    <n-spin :show="store.loading">
      <div class="template-grid">
        <article v-for="template in store.workflowTemplates" :key="template.template_id" class="template-card">
          <div class="template-head">
            <h2>{{ template.name }}</h2>
            <n-tag size="small">v{{ template.current_version }}</n-tag>
          </div>
          <p>{{ template.description || template.slug }}</p>
          <div class="template-meta">
            <span>{{ template.status }}</span>
            <code>{{ template.template_id }}</code>
          </div>
        </article>
        <div v-if="!store.workflowTemplates.length && !store.loading" class="empty-state">No templates</div>
      </div>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NAlert, NButton, NInput, NSpace, NSpin, NTag } from 'naive-ui'
import { usePlatformStore } from '../stores/platform'

const store = usePlatformStore()
const slug = ref('')
const name = ref('')
const description = ref('')
const errorMessage = computed(() => store.error?.message ?? '')

async function load() {
  await store.loadWorkflowTemplates(100).catch(() => undefined)
}

async function createTemplate() {
  try {
    await store.createWorkflowTemplate({
      slug: slug.value.trim(),
      name: name.value.trim(),
      description: description.value.trim(),
    })
    slug.value = ''
    name.value = ''
    description.value = ''
  } catch {
    // Store owns surfaced error state.
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
.create-row,
.template-head,
.template-meta {
  display: flex;
  gap: 10px;
}

.platform-header,
.template-head,
.template-meta {
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

p,
.template-meta {
  color: var(--dgm-text-muted);
  font-size: 12px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 10px;
}

.template-card {
  display: grid;
  gap: 8px;
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

code {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--dgm-font-mono);
}

.empty-state {
  color: var(--dgm-text-faint);
  font-size: 13px;
}

@media (max-width: 760px) {
  .create-row {
    flex-direction: column;
  }
}
</style>
