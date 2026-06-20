<template>
  <div class="research-agent-view">
    <section class="input-pane">
      <div class="pane-header">Input</div>
      <n-space vertical size="small">
        <n-select v-model:value="store.market" :options="marketOptions" size="small" />
        <n-input
          v-model:value="store.question"
          type="textarea"
          :autosize="{ minRows: 5, maxRows: 8 }"
        />
        <n-button type="primary" size="small" :loading="store.loading" @click="store.startDemoRun">
          Run
        </n-button>
        <div class="file-list">
          <n-tag size="small">annual report</n-tag>
          <n-tag size="small">presentation</n-tag>
          <n-tag size="small">chart</n-tag>
          <n-tag size="small">portfolio.csv</n-tag>
        </div>
      </n-space>
    </section>

    <section class="memo-pane">
      <div class="pane-header">Research Memo</div>
      <n-alert v-if="store.error" type="error" :show-icon="false">
        {{ store.error.message }}
      </n-alert>
      <div v-if="store.latestMemo" class="memo-body" v-html="renderedMemo" />
      <div v-else class="empty-state">No memo generated</div>
    </section>

    <section class="evidence-pane">
      <div class="pane-header">Evidence</div>
      <div class="status-row">
        <n-tag :type="statusType" size="small">{{ store.run?.status || 'idle' }}</n-tag>
        <n-tag size="small">tokens {{ usage.total_tokens ?? 0 }}</n-tag>
      </div>
      <div class="approval-list">
        <div v-for="approval in store.approvals" :key="approval.approval_id" class="approval-item">
          <div class="approval-title">{{ approval.risk_level }} · {{ approval.status }}</div>
          <div class="approval-action">{{ approval.action }}</div>
          <n-space v-if="approval.status === 'pending'" size="small">
            <n-button size="tiny" type="primary" @click="store.resolveApproval(approval.approval_id, true)">Approve</n-button>
            <n-button size="tiny" @click="store.resolveApproval(approval.approval_id, false)">Deny</n-button>
          </n-space>
        </div>
      </div>
    </section>

    <section class="timeline-pane">
      <div class="pane-header">Agent Timeline</div>
      <div class="timeline">
        <div v-for="event in store.events" :key="event.event_id" class="timeline-item">
          <n-tag size="small">{{ event.event_type }}</n-tag>
          <code>{{ compactPayload(event.payload) }}</code>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import { NAlert, NButton, NInput, NSelect, NSpace, NTag } from 'naive-ui'
import { useAgentStore } from '../stores/agent'

const store = useAgentStore()
const md = new MarkdownIt()

const marketOptions = [
  { label: 'US Market', value: 'us' },
  { label: 'A-Share (CN)', value: 'cn' },
]

const renderedMemo = computed(() => md.render(store.latestMemo))
const statusType = computed(() => {
  if (store.run?.status === 'completed') return 'success'
  if (store.run?.status === 'awaiting_approval') return 'warning'
  if (store.run?.status === 'failed') return 'error'
  return 'default'
})
const usage = computed(() => store.artifacts[0]?.data?.usage ?? {})

function compactPayload(payload: Record<string, any>) {
  const text = JSON.stringify(payload)
  return text.length > 180 ? `${text.slice(0, 180)}...` : text
}
</script>

<style scoped>
.research-agent-view {
  height: 100%;
  padding: 12px;
  display: grid;
  grid-template-columns: minmax(220px, 0.9fr) minmax(320px, 1.4fr) minmax(240px, 0.9fr);
  grid-template-rows: minmax(0, 1fr) 180px;
  gap: 12px;
  color: var(--dgm-text);
}

section {
  min-width: 0;
  min-height: 0;
  border: 1px solid var(--dgm-border);
  background: var(--dgm-surface);
  border-radius: 6px;
  padding: 12px;
  overflow: auto;
}

.timeline-pane {
  grid-column: 1 / 4;
}

.pane-header {
  font-size: 12px;
  font-weight: 700;
  color: var(--dgm-text-muted);
  margin-bottom: 10px;
  text-transform: uppercase;
}

.file-list,
.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.memo-body {
  line-height: 1.6;
  color: var(--dgm-text-muted);
}

.memo-body :deep(h1),
.memo-body :deep(h2) {
  font-size: 16px;
  margin: 12px 0 8px;
  color: var(--dgm-text);
}

.empty-state {
  color: var(--dgm-text-faint);
  font-size: 13px;
}

.approval-list {
  margin-top: 12px;
  display: grid;
  gap: 10px;
}

.approval-item {
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  padding: 8px;
}

.approval-title {
  font-size: 12px;
  color: var(--dgm-text);
}

.approval-action {
  font-size: 12px;
  color: var(--dgm-text-muted);
  margin: 4px 0 8px;
}

.timeline {
  display: grid;
  gap: 8px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}

code {
  font-family: var(--dgm-font-mono);
  font-size: 12px;
  color: var(--dgm-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 900px) {
  .research-agent-view {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto minmax(160px, 1fr);
  }

  .timeline-pane {
    grid-column: 1;
  }

  .timeline-item {
    grid-template-columns: 1fr;
  }
}
</style>
