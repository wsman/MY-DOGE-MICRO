import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import ResearchAgentView from './ResearchAgentView.vue'
import { useAgentStore } from '../stores/agent'

const platformStoreMock = vi.hoisted(() => ({
  capabilities: null as unknown,
  capabilitiesById: {} as Record<string, unknown>,
  workflowTemplates: [] as unknown[],
  workflowTemplatesBySlug: {} as Record<string, unknown>,
  loadCapabilities: vi.fn(async () => null),
  loadWorkflowTemplates: vi.fn(async () => []),
}))

vi.mock('../api/agent', () => ({
  createAgentRun: vi.fn(),
  approveAgentRun: vi.fn(),
  listAgentRuns: vi.fn(async () => []),
}))

vi.mock('../api/documents', () => ({
  listDocuments: vi.fn(async () => []),
  uploadDocument: vi.fn(),
}))

// MaturityPanel (UX-1 Slice E) reads the platform capability store and
// self-loads it on mount. Stub the store so mounting ResearchAgentView does
// not trigger a real /v1/capabilities fetch under jsdom.
vi.mock('../stores/platform', () => ({
  usePlatformStore: () => platformStoreMock,
}))

describe('ResearchAgentView accessibility', () => {
  beforeEach(() => {
    window.localStorage.setItem('doge.firstRunSeen', '1')
    setActivePinia(createPinia())
    platformStoreMock.capabilities = null
    platformStoreMock.capabilitiesById = {}
    platformStoreMock.workflowTemplates = []
    platformStoreMock.workflowTemplatesBySlug = {}
    platformStoreMock.loadCapabilities = vi.fn(async () => null)
    platformStoreMock.loadWorkflowTemplates = vi.fn(async () => [])
  })

  afterEach(() => {
    document.body.innerHTML = ''
    window.localStorage.clear()
    vi.restoreAllMocks()
  })

  it('keeps diagnostics hidden in Analyst mode and reveals them in Developer mode', async () => {
    const store = useAgentStore()
    store.run = {
      run_id: 'run-1',
      workflow: 'investment_research',
      question: 'Analyze',
      session_id: null,
      market: 'us',
      language: 'en',
      document_ids: [],
      portfolio_id: null,
      model_policy: {},
      workflow_context: null,
      identity_snapshot: null,
      status: 'awaiting_approval',
      events: [
        {
          event_id: 'evt-1',
          run_id: 'run-1',
          event_type: 'approval_requested',
          payload: { action: 'publish memo' },
          sequence: 1,
          schema_version: '1.0',
          created_at: 'now',
        },
        {
          event_id: 'evt-2',
          run_id: 'run-1',
          event_type: 'model_response',
          payload: {
            usage: { total_tokens: 42, prompt_tokens: 30, cost_usd: 0.0012 },
            routing: { backend: 'direct_kimi_api', model: 'kimi-k2.6' },
          },
          sequence: 2,
          schema_version: '1.0',
          created_at: 'now',
        },
        {
          event_id: 'evt-3',
          run_id: 'run-1',
          event_type: 'tool_result',
          payload: {
            result: {
              data: {
                results: [
                  {
                    evidence_id: 'evd-abc',
                    document_id: 'doc-1',
                    page_number: 3,
                    text: 'Revenue growth was supported by accelerator demand.',
                    score: 0.91,
                  },
                ],
              },
            },
          },
          sequence: 3,
          schema_version: '1.0',
          created_at: 'now',
        },
      ],
      artifacts: [
        {
          artifact_id: 'art-1',
          kind: 'investment_memo',
          title: 'Memo',
          content: '# Memo\n\nSource evd-abc',
          run_id: 'run-1',
          data: {
            usage: { total_tokens: 42 },
            citation_precision: 1,
            numerical_consistency: 0.5,
            tool_execution_success: 1,
            structured_claims: [
              {
                claim_id: 'claim-1',
                claim_text: 'Revenue growth was supported by accelerator demand.',
                status: 'supported',
                evidence_refs: [{ evidence_id: 'evd-abc' }],
                numeric_check_status: 'not_applicable',
                risk_level: 'low',
              },
            ],
          },
          created_at: 'now',
        },
      ],
      approvals: [
        {
          approval_id: 'appr-1',
          action: 'publish memo',
          risk_level: 'high',
          why_needed: 'External publishing requires review.',
          impact: 'Memo becomes visible to the client.',
          deny_consequence: 'Memo remains internal.',
          publish_target: 'client portal',
          run_id: 'run-1',
          status: 'pending',
          created_at: 'now',
          resolved_at: null,
        },
        {
          approval_id: 'appr-2',
          action: 'archive memo',
          risk_level: 'low',
          why_needed: '  ',
          impact: undefined,
          deny_consequence: '',
          publish_target: undefined,
          run_id: 'run-1',
          status: 'pending',
          created_at: 'now',
          resolved_at: null,
        },
      ],
      cancel_requested_at: null,
      schema_version: '1.0',
      created_at: 'now',
      updated_at: 'now',
    }

    const wrapper = mount(ResearchAgentView)

    const status = wrapper.find('[role="status"]')
    expect(status.exists()).toBe(true)
    expect(status.attributes('aria-live')).toBe('polite')
    expect(status.attributes('aria-label')).toBe(
      'Agent status Waiting on your approval; next Approve or deny',
    )
    expect(status.text()).toContain('Next: Approve or deny')
    expect(status.text()).not.toContain('tokens 42')

    const approvals = wrapper.findAll('.approval-item[role="group"]')
    const approval = approvals[0]
    expect(approval.attributes('aria-label')).toBe(
      'high risk approval pending: publish memo; why needed: External publishing requires review.',
    )
    expect(approval.findAll('.detail-row').map(row => row.text())).toEqual([
      'Why neededExternal publishing requires review.',
      'ImpactMemo becomes visible to the client.',
      'Deny consequenceMemo remains internal.',
      'Publish targetclient portal',
    ])
    expect(approvals[1].attributes('aria-label')).toBe('low risk approval pending: archive memo')
    expect(approvals[1].findAll('.detail-row')).toHaveLength(0)

    expect(wrapper.find('[role="list"][aria-label="Agent event timeline"]').exists()).toBe(false)
    expect(wrapper.findAll('.timeline-item[role="listitem"]').length).toBe(0)
    expect(wrapper.text()).not.toContain('Agent Timeline')
    expect(wrapper.text()).not.toContain('Cost / Eval')
    expect(wrapper.text()).not.toContain('Total Tokens')
    expect(wrapper.text()).not.toContain('Cost USD')
    expect(wrapper.text()).not.toContain('direct_kimi_api')
    expect(wrapper.text()).not.toContain('kimi-k2.6')
    expect(wrapper.find('#research-agent-quality-title').text()).toBe('Quality')
    expect(wrapper.text()).toContain('doc-1 p.3')
    const matrix = wrapper.find('[aria-label="Conclusion evidence matrix"]')
    expect(matrix.exists()).toBe(true)
    expect(matrix.text()).toContain('Revenue growth was supported by accelerator demand.')
    expect(matrix.text()).toContain('supported')
    expect(matrix.text()).toContain('not_applicable')
    expect(matrix.text()).toContain('low')
    expect(matrix.find('.evidence-chip').text()).toContain('evd-abc')
    expect(matrix.find('.evidence-cell').text()).toContain('Tool')
    expect(wrapper.text()).not.toContain('annual report')

    const developerButton = wrapper.findAll('button').find(button => button.text().includes('Developer'))
    expect(developerButton).toBeTruthy()
    await developerButton?.trigger('click')
    await nextTick()

    const developerStatus = wrapper.find('[role="status"]')
    expect(developerStatus.attributes('aria-label')).toBe(
      'Agent status Waiting on your approval; tokens 42; next Approve or deny',
    )
    expect(developerStatus.text()).toContain('tokens 42')
    expect(wrapper.find('[role="list"][aria-label="Agent event timeline"]').exists()).toBe(true)
    expect(wrapper.findAll('.timeline-item[role="listitem"]').length).toBe(3)
    expect(wrapper.text()).toContain('Cost / Eval')
    expect(wrapper.text()).toContain('Total Tokens')
    expect(wrapper.text()).toContain('Cost USD')
    expect(wrapper.text()).toContain('Citation Precision')
    expect(wrapper.text()).toContain('100%')
    expect(wrapper.text()).toContain('direct_kimi_api')
    expect(wrapper.text()).toContain('kimi-k2.6')

    wrapper.unmount()
  })

  it('renders approval policy rows from the matching workflow template', () => {
    platformStoreMock.workflowTemplatesBySlug = {
      investment_research: {
        metadata: {
          contract: {
            approval_policy: {
              publish: 'required',
            },
          },
        },
      },
    }
    const store = useAgentStore()
    store.run = {
      run_id: 'run-policy',
      workflow: 'investment_research',
      question: 'Analyze',
      session_id: null,
      market: 'us',
      language: 'en',
      document_ids: [],
      portfolio_id: null,
      model_policy: {},
      workflow_context: null,
      identity_snapshot: null,
      status: 'awaiting_approval',
      events: [],
      artifacts: [],
      approvals: [
        {
          approval_id: 'appr-policy',
          action: 'publish memo',
          risk_level: 'high',
          why_needed: 'External publishing requires review.',
          impact: undefined,
          deny_consequence: undefined,
          publish_target: undefined,
          run_id: 'run-policy',
          status: 'pending',
          created_at: 'now',
          resolved_at: null,
        },
      ],
      cancel_requested_at: null,
      schema_version: '1.0',
      created_at: 'now',
      updated_at: 'now',
    }

    const wrapper = mount(ResearchAgentView)

    expect(wrapper.find('.approval-item').findAll('.detail-row').map(row => row.text())).toEqual([
      'Why neededExternal publishing requires review.',
      'Policy · publishrequired',
    ])

    wrapper.unmount()
  })

  it('opens citation drill-down details for populated evidence', async () => {
    const store = useAgentStore()
    store.run = {
      run_id: 'run-2',
      workflow: 'investment_research',
      question: 'Analyze',
      session_id: null,
      market: 'us',
      language: 'en',
      document_ids: [],
      portfolio_id: null,
      model_policy: {},
      workflow_context: null,
      identity_snapshot: null,
      status: 'completed',
      events: [],
      artifacts: [
        {
          artifact_id: 'art-2',
          kind: 'investment_memo',
          title: 'Memo',
          content: '# Memo\n\nSource evd-click',
          run_id: 'run-2',
          data: {
            citations: [
              {
                evidence_id: 'evd-click',
                document_id: 'doc-click',
                page_number: 7,
                snippet: 'Operating cash flow covered net income.',
                score: 0.88,
              },
            ],
          },
          created_at: 'now',
        },
      ],
      approvals: [],
      cancel_requested_at: null,
      schema_version: '1.0',
      created_at: 'now',
      updated_at: 'now',
    }

    const wrapper = mount(ResearchAgentView, { attachTo: document.body })

    await wrapper.find('.citation-row').trigger('click')
    await nextTick()

    expect(document.body.textContent).toContain('Source')
    expect(document.body.textContent).toContain('doc-click')
    expect(document.body.textContent).toContain('Page')
    expect(document.body.textContent).toContain('7')
    expect(document.body.textContent).toContain('Operating cash flow covered net income.')

    wrapper.unmount()
  })

  it('opens claim-scoped citation details from the conclusion matrix', async () => {
    const store = useAgentStore()
    store.run = {
      run_id: 'run-3',
      workflow: 'investment_research',
      question: 'Analyze',
      session_id: null,
      market: 'us',
      language: 'en',
      document_ids: [],
      portfolio_id: null,
      model_policy: {},
      workflow_context: null,
      identity_snapshot: null,
      status: 'completed',
      events: [],
      artifacts: [
        {
          artifact_id: 'art-3',
          kind: 'investment_memo',
          title: 'Memo',
          content: '# Memo',
          run_id: 'run-3',
          data: {
            usage: { total_tokens: 15 },
            structured_claims: [
              {
                claim_id: 'claim-cash',
                claim_text: 'Operating cash flow covered net income.',
                status: 'supported',
                evidence_refs: [
                  {
                    evidence_id: 'evd-cash',
                    source: 'cash-flow-report p.8',
                    document_id: 'cash-flow-report',
                    page_number: 8,
                    snippet: 'Operating cash flow covered net income by 1.4x.',
                    score: 0.93,
                  },
                ],
                numeric_check_status: 'checked',
                risk_level: 'low',
              },
            ],
          },
          created_at: 'now',
        },
      ],
      approvals: [],
      cancel_requested_at: null,
      schema_version: '1.0',
      created_at: 'now',
      updated_at: 'now',
    }

    const wrapper = mount(ResearchAgentView, { attachTo: document.body })

    expect(wrapper.find('[aria-label="Conclusion evidence matrix"]').text()).toContain('cash-flow-report p.8')
    await wrapper.find('.evidence-chip').trigger('click')
    await nextTick()

    expect(document.body.textContent).toContain('Source')
    expect(document.body.textContent).toContain('cash-flow-report p.8')
    expect(document.body.textContent).toContain('Page')
    expect(document.body.textContent).toContain('8')
    expect(document.body.textContent).toContain('Operating cash flow covered net income by 1.4x.')

    wrapper.unmount()
  })

  it('exports memo artifacts and copies analyst handoff text', async () => {
    const store = useAgentStore()
    store.run = {
      run_id: 'run-export',
      workflow: 'investment_research',
      question: 'Analyze export',
      session_id: null,
      market: 'us',
      language: 'en',
      document_ids: ['doc-export'],
      portfolio_id: null,
      model_policy: {},
      workflow_context: null,
      identity_snapshot: null,
      status: 'completed',
      events: [
        {
          event_id: 'evt-export',
          run_id: 'run-export',
          event_type: 'tool_result',
          payload: {
            result: {
              data: {
                results: [{
                  evidence_id: 'evd-event-export',
                  document_id: 'doc-event',
                  page_number: 9,
                  text: 'Event citation text.',
                }],
              },
            },
          },
          sequence: 1,
          schema_version: '1.0',
          created_at: 'now',
        },
      ],
      artifacts: [
        {
          artifact_id: 'art-export',
          kind: 'investment_memo',
          title: 'Export Memo',
          content: `# Memo

## Findings
- Revenue growth was supported by source evidence.

## IC Questions
1. Which reported figures require source-page confirmation?
2. What unresolved data gaps remain?

## Sources
- evd-export`,
          run_id: 'run-export',
          data: {
            usage: { total_tokens: 84 },
            citation_precision: 1,
            numerical_consistency: 1,
            tool_execution_success: 1,
            citations: [
              {
                evidence_id: 'evd-export',
                document_id: 'doc-export',
                page_number: 4,
                snippet: 'Revenue growth was supported by source evidence.',
              },
            ],
            structured_claims: [
              {
                claim_id: 'claim-export',
                claim_text: 'Revenue growth was supported by source evidence.',
                status: 'supported',
                evidence_refs: [
                  {
                    evidence_id: 'evd-export',
                    source: 'doc-export p.4',
                    document_id: 'doc-export',
                    page_number: 4,
                    snippet: 'Revenue growth was supported by source evidence.',
                  },
                ],
                numeric_check_status: 'checked',
                risk_level: 'low',
              },
            ],
          },
          created_at: 'now',
        },
      ],
      approvals: [],
      cancel_requested_at: null,
      schema_version: '1.0',
      created_at: 'now',
      updated_at: 'now',
    }

    const originalCreateObjectUrl = URL.createObjectURL
    const originalRevokeObjectUrl = URL.revokeObjectURL
    const createObjectURL = vi.fn((_blob: Blob | MediaSource) => 'blob:memo-export')
    const revokeObjectURL = vi.fn((_url: string) => undefined)
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL })
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const writeText = vi.fn(async (_text: string) => undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
    const print = vi.spyOn(window, 'print').mockImplementation(() => {})

    const wrapper = mount(ResearchAgentView, { attachTo: document.body })

    await wrapper.find('button[aria-label="Export memo as Markdown"]').trigger('click')
    await wrapper.find('button[aria-label="Export memo as JSON"]').trigger('click')

    expect(anchorClick).toHaveBeenCalledTimes(2)
    expect(revokeObjectURL).toHaveBeenCalledTimes(2)
    const markdownBlob = createObjectURL.mock.calls[0][0] as Blob
    const jsonBlob = createObjectURL.mock.calls[1][0] as Blob
    await expect(readBlobText(markdownBlob)).resolves.toContain('## IC Questions')
    const payload = JSON.parse(await readBlobText(jsonBlob))
    expect(payload).toMatchObject({
      schema_version: 'doge.web.memo_export.v1',
      export_kind: 'investment_memo',
      run: {
        run_id: 'run-export',
        workflow: 'investment_research',
        question: 'Analyze export',
      },
      artifact: {
        artifact_id: 'art-export',
        content_markdown: expect.stringContaining('Revenue growth'),
      },
      ic_questions: [
        '1. Which reported figures require source-page confirmation?',
        '2. What unresolved data gaps remain?',
      ],
      metrics: {
        usage: { total_tokens: 84 },
        citation_precision: 1,
      },
    })
    expect(JSON.stringify(payload)).not.toContain('tool_result')
    expect(payload.citations).toEqual(expect.arrayContaining([
      expect.objectContaining({
        evidence_id: 'evd-export',
        source: 'doc-export p.4',
        snippet: 'Revenue growth was supported by source evidence.',
      }),
      expect.objectContaining({
        evidence_id: 'evd-event-export',
        source: 'doc-event p.9',
        snippet: 'Event citation text.',
      }),
    ]))

    await wrapper.find('button[aria-label="Copy IC questions"]').trigger('click')
    await wrapper.find('button[aria-label="Copy citations"]').trigger('click')
    expect(writeText).toHaveBeenNthCalledWith(
      1,
      '1. Which reported figures require source-page confirmation?\n2. What unresolved data gaps remain?',
    )
    expect(writeText.mock.calls[1][0]).toContain('doc-export p.4 | evd-export')
    expect(writeText.mock.calls[1][0]).toContain('Revenue growth was supported by source evidence.')

    await wrapper.find('button[aria-label="Print memo"]').trigger('click')
    expect(print).toHaveBeenCalledTimes(1)

    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: originalCreateObjectUrl })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: originalRevokeObjectUrl })
    wrapper.unmount()
  })

  it('disables export actions when no memo is available', () => {
    const wrapper = mount(ResearchAgentView)

    expect(wrapper.find('button[aria-label="Export memo as Markdown"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('button[aria-label="Export memo as JSON"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('button[aria-label="Copy IC questions"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('button[aria-label="Copy citations"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('button[aria-label="Print memo"]').attributes('disabled')).toBeDefined()

    wrapper.unmount()
  })
})

function readBlobText(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsText(blob)
  })
}
