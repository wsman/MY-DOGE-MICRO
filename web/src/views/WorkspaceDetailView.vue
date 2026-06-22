<template>
  <div class="platform-view" aria-label="Workspace detail">
    <header class="platform-header">
      <div>
        <div class="eyebrow">Workspace</div>
        <h1>{{ workspace?.name || workspaceId || 'Workspace' }}</h1>
      </div>
      <n-space size="small">
        <n-button size="small" @click="router.push('/workspaces')">Back</n-button>
        <n-button size="small" :loading="store.loading" @click="load">Refresh</n-button>
      </n-space>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>

    <section class="summary-strip" aria-label="Workspace summary">
      <div>
        <span>Projects</span>
        <strong>{{ projects.length }}</strong>
      </div>
      <div>
        <span>Default market</span>
        <strong>{{ dominantMarket }}</strong>
      </div>
    </section>

    <section class="create-row" aria-label="Create project">
      <n-input v-model:value="projectName" size="small" placeholder="Project name" />
      <n-select v-model:value="defaultMarket" size="small" :options="marketOptions" />
      <n-button size="small" type="primary" :disabled="!projectName.trim()" @click="createProject">New</n-button>
    </section>

    <section aria-labelledby="project-list-title">
      <div id="project-list-title" class="section-title">Projects</div>
      <n-spin :show="store.loading">
        <div class="card-list">
          <article v-for="project in projects" :key="project.project_id" class="entity-card">
            <div>
              <h2>{{ project.name }}</h2>
              <p>{{ project.description || project.default_market || 'No description' }}</p>
            </div>
            <n-button size="tiny" @click="router.push(`/projects/${project.project_id}`)">Open</n-button>
          </article>
          <div v-if="!projects.length && !store.loading" class="empty-state">No projects</div>
        </div>
      </n-spin>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAlert, NButton, NInput, NSelect, NSpace, NSpin } from 'naive-ui'
import { usePlatformStore } from '../stores/platform'

const route = useRoute()
const router = useRouter()
const store = usePlatformStore()
const projectName = ref('')
const defaultMarket = ref<'us' | 'cn'>('us')

const workspaceId = computed(() => String(route.params.workspaceId || ''))
const workspace = computed(() => store.workspacesById[workspaceId.value])
const projects = computed(() => store.projectsByWorkspaceId[workspaceId.value] ?? [])
const errorMessage = computed(() => store.error?.message ?? '')
const dominantMarket = computed(() => projects.value[0]?.default_market || defaultMarket.value)
const marketOptions = [
  { label: 'US', value: 'us' },
  { label: 'CN', value: 'cn' },
]

async function load() {
  if (!workspaceId.value) return
  await Promise.all([
    store.loadWorkspace(workspaceId.value),
    store.loadProjects({ workspace_id: workspaceId.value, limit: 100 }),
  ]).catch(() => undefined)
}

async function createProject() {
  if (!workspaceId.value) return
  try {
    await store.createProject({
      workspace_id: workspaceId.value,
      name: projectName.value.trim(),
      description: '',
      default_market: defaultMarket.value,
    })
    projectName.value = ''
    await load()
  } catch {
    // Store owns surfaced error state.
  }
}

watch(workspaceId, load)
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
.summary-strip,
.entity-card {
  display: flex;
  gap: 10px;
}

.platform-header,
.entity-card {
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

.summary-strip > div {
  min-width: 150px;
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

.card-list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.entity-card {
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
  .create-row,
  .summary-strip {
    flex-direction: column;
  }
}
</style>
