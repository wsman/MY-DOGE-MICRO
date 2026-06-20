import { beforeEach, describe, expect, it, vi } from 'vitest'
import { approveAgentRun } from '../api/agent'

const mocks = vi.hoisted(() => ({
  runs: {
    approve: vi.fn(),
    get: vi.fn(),
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
  })

  it('polls after approval is accepted as queued', async () => {
    mocks.runs.approve.mockResolvedValue({
      run_id: 'run-1',
      status: 'queued',
      events: [],
      artifacts: [],
      approvals: [],
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
    expect(mocks.runs.get).toHaveBeenCalledWith('run-1')
  })
})
