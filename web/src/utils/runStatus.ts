/**
 * Canonical RunStatus → human label / Naive-UI tone / speakable sentence.
 *
 * Single source of truth for how a run status is rendered across the Web
 * workspace (Sprint UX-1 Slice A, WEB-2). Mirrors the Python twin at
 * src/doge/interfaces/cli/run_status_labels.py; both are pinned to the 8
 * RunStatus members defined by the backend enum at
 * src/doge/core/domain/agent_models.py:19-27. The Python test
 * tests/unit/interfaces/test_run_status_labels.py asserts the Python twin
 * enumerates exactly those members; this spec asserts the TS twin labels them.
 *
 * Replaces the duplicated inline statusType() computeds that previously lived
 * in ResearchAgentView.vue and ExecutionMonitor.vue so a status reads as a
 * human sentence in every surface, never a raw enum.
 */

/**
 * Backend RunStatus enum values (agent_models.py:19-27). Kept as a literal
 * union so a backend enum rename or addition surfaces here as a typecheck
 * change rather than silently drifting.
 */
export type RunStatusValue =
  | 'created'
  | 'queued'
  | 'running'
  | 'awaiting_approval'
  | 'cancelling'
  | 'cancelled'
  | 'completed'
  | 'failed'

/** Naive-UI `n-tag` `type` values. */
export type RunStatusTone = 'default' | 'info' | 'success' | 'warning' | 'error'

interface RunStatusDescriptor {
  label: string
  tone: RunStatusTone
  nextActions?: string[]
}

const RUN_STATUS: Record<RunStatusValue, RunStatusDescriptor> = {
  created: { label: 'Preparing', tone: 'default', nextActions: ['Wait for worker'] },
  queued: { label: 'Queued', tone: 'warning', nextActions: ['Wait for worker'] },
  running: { label: 'Running', tone: 'info', nextActions: ['Watch live'] },
  awaiting_approval: { label: 'Waiting on your approval', tone: 'warning', nextActions: ['Approve or deny'] },
  cancelling: { label: 'Cancelling', tone: 'warning', nextActions: ['Wait for cancel'] },
  cancelled: { label: 'Cancelled', tone: 'default', nextActions: ['Re-queue or discard'] },
  completed: { label: 'Completed', tone: 'success', nextActions: ['Open artifacts'] },
  failed: { label: 'Failed', tone: 'error', nextActions: ['Inspect error', 'Re-run'] },
}

const IDLE_LABEL = 'Idle'

/**
 * Human label for a run status. `undefined`/`null`/`''` (no run yet) map to
 * "Idle". Unknown values fall through to "Status: <raw>" so future statuses
 * surface rather than hide behind a wrong label.
 */
export function labelFor(status: string | null | undefined): string {
  if (status === null || status === undefined || status === '') return IDLE_LABEL
  const descriptor = RUN_STATUS[status as RunStatusValue]
  return descriptor ? descriptor.label : `Status: ${status}`
}

/**
 * Naive-UI `n-tag` tone for a run status. Unknown / idle values get the
 * default tone.
 */
export function toneFor(status: string | null | undefined): RunStatusTone {
  if (status === null || status === undefined || status === '') return 'default'
  const descriptor = RUN_STATUS[status as RunStatusValue]
  return descriptor ? descriptor.tone : 'default'
}

/**
 * Speakable status text for aria-live regions. Today this is the label itself
 * (already screen-reader-friendly); it exists as a distinct export so callers
 * composing announcements depend on the speakable form rather than reaching
 * into the display label.
 */
export function sentenceFor(status: string | null | undefined): string {
  return labelFor(status)
}

/**
 * Operator-facing next actions for a run status. Unknown / idle values return
 * an empty list so callers can omit the hint without inventing guidance for
 * statuses this UI does not know yet.
 */
export function nextActionsFor(status: string | null | undefined): string[] {
  if (status === null || status === undefined || status === '') return []
  const descriptor = RUN_STATUS[status as RunStatusValue]
  return descriptor?.nextActions ? [...descriptor.nextActions] : []
}
