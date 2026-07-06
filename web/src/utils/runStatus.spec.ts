import { describe, expect, it } from 'vitest'

import { labelFor, nextActionsFor, sentenceFor, toneFor, type RunStatusValue } from './runStatus'

/**
 * runStatus spec (Sprint UX-1 Slice A, WEB-2).
 *
 * Pins the Web run-status label/tone map to the 8 backend RunStatus members
 * (src/doge/core/domain/agent_models.py:19-27) plus the idle pseudo-status and
 * the unknown-value fallback. The Python twin's enum parity is pinned separately
 * by tests/unit/interfaces/test_run_status_labels.py.
 */
describe('runStatus', () => {
  // The exact 8 RunStatus members. If the backend adds a member, update this
  // list and the util together.
  const ALL_STATUSES: RunStatusValue[] = [
    'created',
    'queued',
    'running',
    'awaiting_approval',
    'cancelling',
    'cancelled',
    'completed',
    'failed',
  ]

  it('labels every RunStatus member', () => {
    expect(labelFor('created')).toBe('Preparing')
    expect(labelFor('queued')).toBe('Queued')
    expect(labelFor('running')).toBe('Running')
    expect(labelFor('awaiting_approval')).toBe('Waiting on your approval')
    expect(labelFor('cancelling')).toBe('Cancelling')
    expect(labelFor('cancelled')).toBe('Cancelled')
    expect(labelFor('completed')).toBe('Completed')
    expect(labelFor('failed')).toBe('Failed')
  })

  it('treats undefined/null/empty as idle', () => {
    expect(labelFor(undefined)).toBe('Idle')
    expect(labelFor(null)).toBe('Idle')
    expect(labelFor('')).toBe('Idle')
    expect(toneFor(undefined)).toBe('default')
    expect(toneFor(null)).toBe('default')
  })

  it('falls unknown values through to "Status: <raw>" so they surface', () => {
    expect(labelFor('something_new')).toBe('Status: something_new')
    expect(toneFor('something_new')).toBe('default')
    expect(sentenceFor('something_new')).toBe('Status: something_new')
  })

  it('returns a Naive-UI tone per status (success/error/warning/info/default)', () => {
    expect(toneFor('completed')).toBe('success')
    expect(toneFor('failed')).toBe('error')
    expect(toneFor('awaiting_approval')).toBe('warning')
    expect(toneFor('queued')).toBe('warning')
    expect(toneFor('cancelling')).toBe('warning')
    expect(toneFor('running')).toBe('info')
    expect(toneFor('created')).toBe('default')
    expect(toneFor('cancelled')).toBe('default')
  })

  it('sentenceFor returns the speakable label for aria-live regions', () => {
    expect(sentenceFor('awaiting_approval')).toBe('Waiting on your approval')
    expect(sentenceFor('completed')).toBe('Completed')
    expect(sentenceFor(undefined)).toBe('Idle')
  })

  it('returns next-action hints for all 8 backend RunStatus members', () => {
    expect(nextActionsFor('created')).toEqual(['Wait for worker'])
    expect(nextActionsFor('queued')).toEqual(['Wait for worker'])
    expect(nextActionsFor('running')).toEqual(['Watch live'])
    expect(nextActionsFor('awaiting_approval')).toEqual(['Approve or deny'])
    expect(nextActionsFor('cancelling')).toEqual(['Wait for cancel'])
    expect(nextActionsFor('cancelled')).toEqual(['Re-queue or discard'])
    expect(nextActionsFor('completed')).toEqual(['Open artifacts'])
    expect(nextActionsFor('failed')).toEqual(['Inspect error', 'Re-run'])
  })

  it('returns no next-action hint for idle or unknown statuses', () => {
    expect(nextActionsFor(undefined)).toEqual([])
    expect(nextActionsFor(null)).toEqual([])
    expect(nextActionsFor('')).toEqual([])
    expect(nextActionsFor('data_unavailable')).toEqual([])
  })

  it('labels all 8 backend RunStatus members without hitting the fallback', () => {
    // Parity guard: every known member resolves to a real label, never the
    // "Status: <raw>" fallback. Catches a util that forgot a member.
    for (const status of ALL_STATUSES) {
      expect(labelFor(status)).not.toBe(`Status: ${status}`)
      expect(nextActionsFor(status)).not.toHaveLength(0)
    }
  })
})
