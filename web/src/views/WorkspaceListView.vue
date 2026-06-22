<template>
  <div class="platform-view" aria-label="Workspace list">
    <header class="platform-header">
      <div>
        <div class="eyebrow">Platform</div>
        <h1>Workspaces</h1>
      </div>
      <n-space size="small">
        <n-button size="small" :loading="store.loading" @click="load">Refresh</n-button>
        <n-button size="small" type="primary" :disabled="!workspaceName.trim()" @click="createWorkspace">
          New
        </n-button>
      </n-space>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>

    <section class="create-row" aria-label="Create workspace">
      <n-input v-model:value="workspaceName" size="small" placeholder="Workspace name" />
      <n-input v-model:value="workspaceDescription" size="small" placeholder="Description" />
    </section>

    <div class="platform-grid">
      <section class="main-section" aria-labelledby="workspace-list-title">
        <div id="workspace-list-title" class="section-title">Workspace Queue</div>
        <n-spin :show="store.loading">
          <div class="card-list">
          <article v-for="workspace in store.workspaces" :key="workspace.workspace_id" class="entity-card">
              <div>
                <h2>{{ workspace.name }}</h2>
                <p>{{ workspace.description || 'No description' }}</p>
              </div>
              <n-button size="tiny" @click="router.push(`/workspaces/${workspace.workspace_id}`)">Open</n-button>
            </article>
            <div v-if="!store.workspaces.length && !store.loading" class="empty-state">No workspaces</div>
          </div>
        </n-spin>
      </section>

      <aside class="side-section" aria-labelledby="workspace-side-title">
        <div id="workspace-side-title" class="section-title">Readiness</div>
        <div class="metric-row">
          <span>Templates</span>
          <n-tag size="small">{{ store.workflowTemplates.length }}</n-tag>
        </div>
        <div class="metric-row">
          <span>Capabilities</span>
          <n-tag size="small">{{ capabilities.length }}</n-tag>
        </div>
        <div class="status-list">
          <div v-for="capability in visibleCapabilities" :key="capability.capability_id" class="status-item">
            <span>{{ capability.capability_id }}</span>
            <n-tag size="small" :type="capability.status === 'available' ? 'success' : 'warning'">
              {{ capability.status }}
            </n-tag>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NAlert, NButton, NInput, NSpace, NSpin, NTag } from 'naive-ui'
import { usePlatformStore } from '../stores/platform'

const router = useRouter()
const store = usePlatformStore()
const workspaceName = ref('')
const workspaceDescription = ref('')

const errorMessage = computed(() => store.error?.message ?? '')
const capabilities = computed(() => store.capabilities?.capabilities ?? [])
const visibleCapabilities = computed(() => capabilities.value.slice(0, 6))

async function load() {
  await Promise.all([
    store.loadWorkspaces(50),
    store.loadWorkflowTemplates(50),
    store.loadCapabilities(),
  ]).catch(() => undefined)
}

async function createWorkspace() {
  try {
    await store.createWorkspace({
      name: workspaceName.value.trim(),
      description: workspaceDescription.value.trim(),
    })
    workspaceName.value = ''
    workspaceDescription.value = ''
    await load()
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
.platform-grid,
.metric-row,
.status-item,
.entity-card {
  display: flex;
  gap: 10px;
}

.platform-header {
  align-items: center;
  justify-content: space-between;
}

.eyebrow,
.section-title {
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

.create-row {
  align-items: center;
}

.platform-grid {
  align-items: start;
}

.main-section {
  flex: 1;
  min-width: 0;
}

.side-section {
  width: min(340px, 38%);
  min-width: 260px;
}

.main-section,
.side-section {
  display: grid;
  gap: 10px;
}

.card-list,
.status-list {
  display: grid;
  gap: 8px;
}

.entity-card {
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.metric-row,
.status-item {
  align-items: center;
  justify-content: space-between;
}

.empty-state {
  color: var(--dgm-text-faint);
  font-size: 13px;
}

@media (max-width: 760px) {
  .platform-grid,
  .create-row {
    flex-direction: column;
  }

  .side-section {
    width: 100%;
  }
}
</style>
