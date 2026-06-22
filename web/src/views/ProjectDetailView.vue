<template>
  <div class="platform-view" aria-label="Project detail">
    <header class="platform-header">
      <div>
        <div class="eyebrow">Project</div>
        <h1>{{ project?.name || projectId || 'Project' }}</h1>
      </div>
      <n-space size="small">
        <n-button size="small" @click="goWorkspace">Workspace</n-button>
        <n-button size="small" :loading="store.loading" @click="load">Refresh</n-button>
      </n-space>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>

    <section class="create-row" aria-label="Create research case">
      <n-input v-model:value="caseTitle" size="small" placeholder="Case title" />
      <n-input v-model:value="thesis" size="small" placeholder="Thesis" />
      <n-button size="small" type="primary" :disabled="!caseTitle.trim()" @click="createCase">New</n-button>
    </section>

    <section aria-labelledby="case-list-title">
      <div id="case-list-title" class="section-title">Research Cases</div>
      <n-spin :show="store.loading">
        <div class="card-list">
          <article v-for="item in cases" :key="item.case_id" class="entity-card">
            <div>
              <h2>{{ item.title }}</h2>
              <p>{{ item.thesis || 'No thesis' }}</p>
            </div>
            <n-button size="tiny" @click="router.push(`/cases/${item.case_id}`)">Open</n-button>
          </article>
          <div v-if="!cases.length && !store.loading" class="empty-state">No cases</div>
        </div>
      </n-spin>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAlert, NButton, NInput, NSpace, NSpin } from 'naive-ui'
import { usePlatformStore } from '../stores/platform'

const route = useRoute()
const router = useRouter()
const store = usePlatformStore()
const caseTitle = ref('')
const thesis = ref('')

const projectId = computed(() => String(route.params.projectId || ''))
const project = computed(() => store.projectsById[projectId.value])
const cases = computed(() => store.casesByProjectId[projectId.value] ?? [])
const errorMessage = computed(() => store.error?.message ?? '')

async function load() {
  if (!projectId.value) return
  await Promise.all([
    store.loadProject(projectId.value),
    store.loadResearchCases({ project_id: projectId.value, limit: 100 }),
  ]).catch(() => undefined)
}

async function createCase() {
  if (!projectId.value) return
  try {
    await store.createResearchCase({
      project_id: projectId.value,
      title: caseTitle.value.trim(),
      thesis: thesis.value.trim(),
    })
    caseTitle.value = ''
    thesis.value = ''
    await load()
  } catch {
    // Store owns surfaced error state.
  }
}

function goWorkspace() {
  if (project.value?.workspace_id) router.push(`/workspaces/${project.value.workspace_id}`)
  else router.push('/workspaces')
}

watch(projectId, load)
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
  .create-row {
    flex-direction: column;
  }
}
</style>
