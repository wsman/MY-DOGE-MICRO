<template>
  <div class="platform-view" aria-label="Research case detail">
    <header class="platform-header">
      <div>
        <div class="eyebrow">Research Case</div>
        <h1>{{ researchCase?.title || caseId || 'Case' }}</h1>
      </div>
      <n-space size="small">
        <n-button size="small" @click="goProject">Project</n-button>
        <n-button size="small" :loading="store.loading" @click="load">Refresh</n-button>
      </n-space>
    </header>

    <n-alert v-if="errorMessage" type="warning" :show-icon="false" role="alert">{{ errorMessage }}</n-alert>
    <p class="thesis">{{ researchCase?.thesis || 'No thesis' }}</p>

    <section class="case-grid">
      <div class="main-section" aria-labelledby="case-template-title">
        <div id="case-template-title" class="section-title">Templates</div>
        <div class="card-list">
          <article v-for="template in templates" :key="template.template_id" class="entity-card">
            <div>
              <h2>{{ template.name }}</h2>
              <p>{{ template.slug }} · v{{ template.current_version || '1' }}</p>
            </div>
            <n-button size="tiny" @click="router.push('/templates')">Open</n-button>
          </article>
          <div v-if="!templates.length && !store.loading" class="empty-state">No templates</div>
        </div>
      </div>

      <aside class="side-section" aria-labelledby="case-run-title">
        <div id="case-run-title" class="section-title">Run Link</div>
        <n-input v-model:value="runId" size="small" placeholder="Run ID" />
        <n-button size="small" type="primary" :disabled="!runId.trim()" :loading="store.loading" @click="linkRun">
          Link
        </n-button>
        <n-button size="small" :disabled="!runId.trim()" @click="router.push(`/runs/${runId.trim()}`)">Open Run</n-button>
        <div v-if="linkedRunId" class="linked-run">Linked {{ linkedRunId }}</div>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAlert, NButton, NInput, NSpace } from 'naive-ui'
import { usePlatformStore } from '../stores/platform'

const route = useRoute()
const router = useRouter()
const store = usePlatformStore()
const runId = ref('')
const linkedRunId = ref('')

const caseId = computed(() => String(route.params.caseId || ''))
const researchCase = computed(() => store.researchCasesById[caseId.value])
const templates = computed(() => store.workflowTemplates)
const errorMessage = computed(() => store.error?.message ?? '')

async function load() {
  if (!caseId.value) return
  await Promise.all([
    store.loadResearchCase(caseId.value),
    store.loadWorkflowTemplates(100),
  ]).catch(() => undefined)
}

async function linkRun() {
  if (!caseId.value || !runId.value.trim()) return
  try {
    const link = await store.linkResearchCaseRun(caseId.value, {
      run_id: runId.value.trim(),
      link_type: 'primary',
    })
    linkedRunId.value = link.run_id
  } catch {
    // Store owns surfaced error state.
  }
}

function goProject() {
  if (researchCase.value?.project_id) router.push(`/projects/${researchCase.value.project_id}`)
  else router.push('/workspaces')
}

watch(caseId, load)
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
.case-grid,
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

p,
.thesis {
  color: var(--dgm-text-muted);
  font-size: 12px;
}

.main-section {
  flex: 1;
  min-width: 0;
}

.side-section {
  width: min(320px, 36%);
  min-width: 240px;
  display: grid;
  align-content: start;
  gap: 8px;
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

.linked-run,
.empty-state {
  color: var(--dgm-text-faint);
  font-size: 13px;
}

@media (max-width: 760px) {
  .case-grid {
    flex-direction: column;
  }

  .side-section {
    width: 100%;
  }
}
</style>
