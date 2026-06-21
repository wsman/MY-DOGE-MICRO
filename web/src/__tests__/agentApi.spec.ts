import { beforeEach, describe, expect, it, vi } from 'vitest'
import { approveAgentRun, createAgentRun } from '../api/agent'

const mocks = vi.hoisted(() => ({
  runs: {
    approve: vi.fn(),
    get: vi.fn(),
    stream: vi.fn(),
  },
  sessions: {
    create: vi.fn(),
  },
}))

vi.mock('../api/client', () => ({
  dogeClient: {
    runs: mocks.runs,
    sessions: mocks.sessions,
  },
}))

describe('agent api', () => {
  beforeEach(() => {
    mocks.runs.approve.mockReset()
    mocks.runs.get.mockReset()
    mocks.runs.stream.mockReset()
    mocks.sessions.create.mockReset()
  })

  it('streams newly created runs until display-ready', async () => {
    mocks.sessions.create.mockResolvedValue({
      createTurn: vi.fn(async () => 'run-1'),
    })
    mocks.runs.stream.mockImplementation(async function* () {
      yield { id: '1', type: 'run_created', data: { event_id: 'evt-1' } }
      yield { id: '2', type: 'approval_requested', data: { event_id: 'evt-2' } }
    })
    mocks.runs.get.mockResolvedValue({
      run_id: 'run-1',
      status: 'awaiting_approval',
      events: [],
      artifacts: [],
      approvals: [{ approval_id: 'appr-1' }],
    })

    const run = await createAgentRun({
      workflow: 'investment_research',
      question: 'Analyze',
      document_ids: [],
      portfolio_id: null,
      market: 'us',
      language: 'en',
      model_policy: {},
    })

    expect(run.status).toBe('awaiting_approval')
    expect(mocks.runs.stream).toHaveBeenCalledWith('run-1', { lastEventId: undefined, reconnect: true })
    expect(mocks.runs.get).toHaveBeenCalledWith('run-1')
  })

  it('streams after approval is accepted as queued', async () => {
    mocks.runs.approve.mockResolvedValue({
      run_id: 'run-1',
      status: 'queued',
      events: [{ sequence: 2 }],
      artifacts: [],
      approvals: [],
    })
    mocks.runs.stream.mockImplementation(async function* () {
      yield { id: '3', type: 'artifact_created', data: { event_id: 'evt-3' } }
    })
    mocks.runs.get.mockResolvedValue({
      run_id: 'run-1',
      status: 'completed',
      events: [],
      artifacts: [],
      approvals: [],
    })

    const run = await approveAgentRun('run-1', 'appr-1', true)

    expect(run.status).toBe('completed')
    expect(mocks.runs.approve).toHaveBeenCalledWith('run-1', 'appr-1', true)
    expect(mocks.runs.stream).toHaveBeenCalledWith('run-1', { lastEventId: '2', reconnect: true })
    expect(mocks.runs.get).toHaveBeenCalledWith('run-1')
  })
})
