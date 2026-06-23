<template>
  <DomainLandingView domain="portfolio">
    <template #side>
      <div class="portfolio-side">
        <PortfolioImporter @imported="onPortfolioImported" />
        <n-tag v-if="portfolioId" size="small" type="success">{{ portfolioId }}</n-tag>
      </div>
    </template>
  </DomainLandingView>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NTag } from 'naive-ui'
import DomainLandingView from './DomainLandingView.vue'
import PortfolioImporter from '../components/agent/PortfolioImporter.vue'
import { useAgentStore } from '../stores/agent'
import type { ImportedPortfolio } from '../api/portfolio'

const store = useAgentStore()
const portfolioId = computed(() => store.portfolioId)

function onPortfolioImported(portfolio: ImportedPortfolio) {
  store.setPortfolioId(portfolio.portfolio_id)
}
</script>

<style scoped>
.portfolio-side {
  display: grid;
  gap: 8px;
}
</style>
