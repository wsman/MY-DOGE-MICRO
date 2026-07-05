import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { approveAgentRun, createAgentRun } from '../api/agent'
import type { AgentRun } from '../api/agent'
import { toFetchError, type FetchError } from '../utils/fetchError'

export const useAgentStore = defineStore('agent', () => {
  const question = ref('Analyze the company earnings quality, industry momentum, and portfolio impact.')
  const market = ref<'cn' | 'us'>('us')
  const executionProfile = ref('financial_research')
  const selectedScenarioSlug = ref('investment_committee_memo')
  const documentIds = ref<string[]>([])
  const portfolioId = ref<string | null>(null)
  const run = ref<AgentRun | null>(null)
  const loading = ref(false)
  const error = ref<FetchError | null>(null)

  const events = computed(() => run.value?.events ?? [])
  const artifacts = computed(() => run.value?.artifacts ?? [])
  const approvals = computed(() => run.value?.approvals ?? [])
  const latestMemo = computed(() => artifacts.value.find(item => item.kind === 'investment_memo')?.content ?? '')

  async function startDemoRun() {
    loading.value = true
    error.value = null
    try {
      run.value = await createAgentRun({
        workflow: selectedScenarioSlug.value,
        question: question.value,
        execution_profile: executionProfile.value,
        document_ids: documentIds.value,
        portfolio_id: portfolioId.value,
        market: market.value,
        language: 'en',
        model_policy: {
          max_tool_rounds: 8,
          require_numeric_validation: true,
          require_citations: true,
        },
      })
    } catch (e) {
      error.value = toFetchError(e)
    } finally {
      loading.value = false
    }
  }

  async function resolveApproval(approvalId: string, approved: boolean) {
    if (!run.value) return
    loading.value = true
    error.value = null
    try {
      run.value = await approveAgentRun(run.value.run_id, approvalId, approved)
    } catch (e) {
      error.value = toFetchError(e)
    } finally {
      loading.value = false
    }
  }

  function setDocumentIds(ids: string[]) {
    documentIds.value = ids
  }

  function setPortfolioId(id: string | null) {
    portfolioId.value = id
  }

  return {
    question,
    market,
    executionProfile,
    selectedScenarioSlug,
    documentIds,
    portfolioId,
    run,
    loading,
    error,
    events,
    artifacts,
    approvals,
    latestMemo,
    startDemoRun,
    resolveApproval,
    setDocumentIds,
    setPortfolioId,
  }
})
