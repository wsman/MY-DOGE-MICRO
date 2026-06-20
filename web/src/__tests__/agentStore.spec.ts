import { setActivePinia, createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAgentStore } from '../stores/agent'

vi.mock('../api/agent', () => ({
  createAgentRun: vi.fn(async () => ({
    run_id: 'run-1',
    workflow: 'investment_research',
    question: 'q',
    market: 'us',
    language: 'en',
    status: 'awaiting_approval',
    events: [{ event_id: 'evt-1', run_id: 'run-1', event_type: 'run_created', payload: {}, created_at: 'now' }],
    artifacts: [],
    approvals: [{ approval_id: 'appr-1', action: 'publish', risk_level: 'high', status: 'pending', created_at: 'now' }],
  })),
  approveAgentRun: vi.fn(async () => ({
    run_id: 'run-1',
    workflow: 'investment_research',
    question: 'q',
    market: 'us',
    language: 'en',
    status: 'completed',
    events: [],
    artifacts: [{ artifact_id: 'art-1', kind: 'investment_memo', title: 'Memo', content: '# Memo', data: {}, created_at: 'now' }],
    approvals: [],
  })),
}))

describe('agent store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts a demo run and exposes approvals', async () => {
    const store = useAgentStore()
    await store.startDemoRun()
    expect(store.run?.status).toBe('awaiting_approval')
    expect(store.approvals[0].approval_id).toBe('appr-1')
  })

  it('resolves approval and exposes memo artifact', async () => {
    const store = useAgentStore()
    await store.startDemoRun()
    await store.resolveApproval('appr-1', true)
    expect(store.run?.status).toBe('completed')
    expect(store.latestMemo).toBe('# Memo')
  })
})
