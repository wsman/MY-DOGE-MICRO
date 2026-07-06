<template>
  <article class="home-panel" aria-labelledby="workflow-shortcuts-title">
    <div id="workflow-shortcuts-title" class="section-title">Workflow Shortcuts</div>
    <div class="cta-list">
      <div class="cta-row">
        <div>
          <h2>Import portfolio</h2>
          <p>{{ portfolioLabel }}</p>
        </div>
        <n-button size="tiny" @click="router.push('/research-agent')">
          <template #icon><n-icon><BriefcaseOutline /></n-icon></template>
          Import
        </n-button>
      </div>
      <div class="cta-row">
        <div>
          <h2>Generate demo pack</h2>
          <p><code>doge demo-pack</code> · local CLI command</p>
        </div>
        <span class="docs-note">Local CLI</span>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { BriefcaseOutline } from '@vicons/ionicons5'
import { NButton, NIcon } from 'naive-ui'
import { useAgentStore } from '../../stores/agent'

const router = useRouter()
const agentStore = useAgentStore()
const portfolioLabel = computed(() => agentStore.portfolioId ? agentStore.portfolioId : 'No portfolio imported')
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

.cta-list {
  display: grid;
  gap: 8px;
}

.cta-row {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
}

.cta-row > div {
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
.docs-note {
  color: var(--dgm-text-muted);
  font-size: 12px;
}

.docs-note {
  flex: 0 0 auto;
}

code {
  font-family: var(--dgm-font-mono);
}

@media (max-width: 760px) {
  .cta-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
