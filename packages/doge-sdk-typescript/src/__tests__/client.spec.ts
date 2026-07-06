import { describe, expect, it, vi } from 'vitest'
import { DogeClient } from '../client'
import { DogeApiError } from '../run'

describe('DogeClient', () => {
  it('creates a session through v1 API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: 'ses-test', title: 'Test', turns: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()
    const session = await client.sessions.create('Test')
    expect(session.sessionId).toBe('ses-test')
    expect(fetchMock).toHaveBeenCalledWith('/v1/sessions', expect.objectContaining({ method: 'POST' }))
  })

  it('creates runs with execution profiles through session helper', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session_id: 'ses-test', title: 'Test', turns: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'accepted', run_id: 'run-test' }),
      })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()
    const session = await client.sessions.create('Test')
    const runId = await session.run('Analyze', { execution_profile: 'quant_code', document_ids: ['doc-1'] })

    expect(runId).toBe('run-test')
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/v1/sessions/ses-test/turns',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          message: 'Analyze',
          document_ids: ['doc-1'],
          model_policy: { execution_profile: 'quant_code' },
        }),
      }),
    )
  })

  it('returns queued approval responses from v1 API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ run_id: 'run-test', status: 'queued' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()
    const run = await client.runs.approve('run-test', 'appr-1')
    expect(run.status).toBe('queued')
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/runs/run-test/approvals/appr-1',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('lists compact run rows from v1 API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ runs: [{ run_id: 'run-test', status: 'completed' }] }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    const runs = await client.runs.list({ limit: 3, sessionId: 'ses-1' })

    expect(runs[0].run_id).toBe('run-test')
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/runs?limit=3&session_id=ses-1',
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('streams post-approval resume events from v1 API', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(
          'id: 7\nevent: approval_resolved\ndata: {"event_type": "approval_resolved"}\n\n'
          + 'id: 8\nevent: artifact_created\ndata: {"event_type": "artifact_created"}\n\n',
        ))
        controller.close()
      },
    })
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ run_id: 'run-test', status: 'queued' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        body: stream,
      })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    const run = await client.runs.approve('run-test', 'appr-1')
    const events = []
    for await (const event of client.runs.stream('run-test')) {
      events.push(event.type)
    }

    expect(run.status).toBe('queued')
    expect(events).toEqual(['approval_resolved', 'artifact_created'])
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/v1/runs/run-test/approvals/appr-1',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/v1/runs/run-test/stream',
      expect.objectContaining({ headers: {} }),
    )
  })

  it('resumes runs through explicit v1 resume API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ run_id: 'run-test', status: 'completed' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()
    const run = await client.runs.resume('run-test', { approvalId: 'appr-1' })
    expect(run.status).toBe('completed')
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/runs/run-test/resume',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ approved: true, approval_id: 'appr-1' }),
      }),
    )
  })

  it('reads run summary resources from v1 API', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ summary: { summary_id: 'sum-1' } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ claims: [{ claim_id: 'claim-1' }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ citations: [{ citation_id: 'cit-1' }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ eval: { coverage_ratio: 1 } }),
      })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    const summary = await client.runs.summary('run-test')
    const claims = await client.runs.claims('run-test')
    const citations = await client.runs.citations('run-test')
    const evaluation = await client.runs.evaluation('run-test')

    expect(summary.summary_id).toBe('sum-1')
    expect(claims[0].claim_id).toBe('claim-1')
    expect(citations[0].citation_id).toBe('cit-1')
    expect(evaluation.coverage_ratio).toBe(1)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/v1/runs/run-test/summary', expect.objectContaining({ method: 'GET' }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/v1/runs/run-test/claims', expect.objectContaining({ method: 'GET' }))
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/v1/runs/run-test/citations', expect.objectContaining({ method: 'GET' }))
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/v1/runs/run-test/eval', expect.objectContaining({ method: 'GET' }))
  })

  it('reconnects run streams with Last-Event-ID', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('id: 2\nevent: tool_call\ndata: {"ok": true}\n\n'))
        controller.close()
      },
    })
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError('network dropped'))
      .mockResolvedValueOnce({
        ok: true,
        body: stream,
      })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    const events = []
    for await (const event of client.runs.stream('run-test', {
      lastEventId: '1',
      maxReconnects: 1,
      backoffMs: 0,
      sleep: async () => undefined,
    })) {
      events.push(event)
    }

    expect(events[0].id).toBe('2')
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/v1/runs/run-test/stream',
      expect.objectContaining({ headers: { 'Last-Event-ID': '1' } }),
    )
  })

  it('reconnects after a mid-stream drop with the latest event id', async () => {
    let reads = 0
    const initialStream = new ReadableStream<Uint8Array>({
      pull(controller) {
        reads += 1
        if (reads > 1) {
          controller.error(new Error('socket closed'))
          return
        }
        controller.enqueue(new TextEncoder().encode('id: 2\nevent: tool_call\ndata: {"step": "started"}\n\n'))
      },
    })
    const replayStream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('id: 3\nevent: artifact_created\ndata: {"terminal": true}\n\n'))
        controller.close()
      },
    })
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, body: initialStream })
      .mockResolvedValueOnce({ ok: true, body: replayStream })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    const events = []
    for await (const event of client.runs.stream('run-test', {
      lastEventId: '1',
      maxReconnects: 1,
      backoffMs: 0,
      sleep: async () => undefined,
    })) {
      events.push(event)
    }

    expect(events.map(event => event.id)).toEqual(['2', '3'])
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/v1/runs/run-test/stream',
      expect.objectContaining({ headers: { 'Last-Event-ID': '1' } }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/v1/runs/run-test/stream',
      expect.objectContaining({ headers: { 'Last-Event-ID': '2' } }),
    )
  })

  it('gets and lists documents', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ documents: [{ document_id: 'doc-1' }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ document_id: 'doc-1' }),
      })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    const documents = await client.documents.list()
    const document = await client.documents.get('doc-1')

    expect(documents[0].document_id).toBe('doc-1')
    expect(document.document_id).toBe('doc-1')
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/v1/documents?limit=100', expect.objectContaining({ method: 'GET' }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/v1/documents/doc-1', expect.objectContaining({ method: 'GET' }))
  })

  it('uses platform and capability resources', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ workspace_id: 'w-1' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ projects: [{ project_id: 'p-1' }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ case_id: 'case-1', run_id: 'run-test' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ case_id: 'case-1', run_id: 'run-from-template', template_id: 'tpl-1' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ valid: true }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ execution_id: 'exec-1', run_id: 'run-from-execution' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ executions: [{ execution_id: 'exec-1' }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ case: { case_id: 'case-1' }, executions: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ steps: [{ progress_id: 'cps-1', step_key: 'workflow' }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ asset_link_id: 'asset-link-1' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ decisions: [{ decision_id: 'decision-1' }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ template_id: 'tpl-1' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ capabilities: [{ capability_id: 'maturity.production_ready' }] }),
      })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    const workspace = await client.platform.createWorkspace('Desk')
    const projects = await client.platform.listProjects({ workspaceId: 'w-1', limit: 10 })
    const link = await client.platform.linkResearchCaseRun('case-1', 'run-test')
    const templateRun = await client.platform.createResearchCaseRunFromTemplate('case-1', 'tpl-1', {
      question: 'Analyze NVDA',
      modelPolicy: { max_tool_rounds: 3 },
      inputs: { ticker: 'NVDA' },
    })
    const preflight = await client.platform.preflightCaseExecution('case-1', 'tpl-1', {
      inputs: { ticker: 'NVDA' },
    })
    const execution = await client.platform.executeCaseTemplate('case-1', 'tpl-1', {
      inputs: { ticker: 'NVDA' },
    })
    const executions = await client.platform.listCaseExecutions('case-1', 5)
    const review = await client.platform.getCaseReview('case-1')
    const progress = await client.platform.getCaseProgress('case-1')
    const asset = await client.platform.addCaseAsset('case-1', 'document', 'doc-1', { assetName: '10-K' })
    const decisions = await client.platform.listCaseDecisions('case-1')
    const template = await client.platform.createWorkflowTemplate('stock', 'Stock', {
      requiredCapabilities: ['feature.workflow_templates'],
      evalPolicy: ['tool_success'],
      approvalPolicy: { publish: 'required' },
      uiSchema: { layout: 'stock' },
    })
    const capabilities = await client.capabilities.list()

    expect(workspace.workspace_id).toBe('w-1')
    expect(projects[0].project_id).toBe('p-1')
    expect(link.run_id).toBe('run-test')
    expect(templateRun.run_id).toBe('run-from-template')
    expect(preflight.valid).toBe(true)
    expect(execution.run_id).toBe('run-from-execution')
    expect(executions[0].execution_id).toBe('exec-1')
    expect(review.case).toEqual({ case_id: 'case-1' })
    expect(progress[0].step_key).toBe('workflow')
    expect(asset.asset_link_id).toBe('asset-link-1')
    expect(decisions[0].decision_id).toBe('decision-1')
    expect(template.template_id).toBe('tpl-1')
    expect(capabilities[0].capability_id).toBe('maturity.production_ready')
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/v1/workspaces',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ name: 'Desk', description: '' }) }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/v1/projects?workspace_id=w-1&limit=10', expect.objectContaining({ method: 'GET' }))
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      '/v1/research-cases/case-1/runs',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ run_id: 'run-test', link_type: 'primary' }) }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      '/v1/research-cases/case-1/runs',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          template_id: 'tpl-1',
          question: 'Analyze NVDA',
          model_policy: { max_tool_rounds: 3 },
          inputs: { ticker: 'NVDA' },
          workflow: undefined,
          session_id: undefined,
          market: 'us',
          language: 'en',
          document_ids: [],
          portfolio_id: undefined,
          link_type: 'primary',
        }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      '/v1/research-cases/case-1/executions/preflight',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          template_id: 'tpl-1',
          question: undefined,
          workflow: undefined,
          session_id: undefined,
          market: 'us',
          language: 'en',
          document_ids: [],
          portfolio_id: undefined,
          asset_link_ids: [],
          model_policy: {},
          inputs: { ticker: 'NVDA' },
          skip_preflight: false,
        }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      6,
      '/v1/research-cases/case-1/executions',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      7,
      '/v1/research-cases/case-1/executions?limit=5',
      expect.objectContaining({ method: 'GET' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      8,
      '/v1/research-cases/case-1/review',
      expect.objectContaining({ method: 'GET' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      9,
      '/v1/research-cases/case-1/progress',
      expect.objectContaining({ method: 'GET' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      10,
      '/v1/research-cases/case-1/assets',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          asset_type: 'document',
          asset_id: 'doc-1',
          asset_name: '10-K',
          role: 'source',
          version: undefined,
          metadata: {},
        }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      11,
      '/v1/research-cases/case-1/decisions',
      expect.objectContaining({ method: 'GET' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      12,
      '/v1/workflow-templates',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          slug: 'stock',
          name: 'Stock',
          description: '',
          current_version: '1',
          input_schema: {},
          run_instructions: '',
          tool_policy: {},
          evidence_policy: {},
          output_contract: {},
          metadata: {},
          required_capabilities: ['feature.workflow_templates'],
          eval_policy: ['tool_success'],
          approval_policy: { publish: 'required' },
          ui_schema: { layout: 'stock' },
        }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(13, '/v1/capabilities', expect.objectContaining({ method: 'GET' }))
  })

  it('uploads documents as multipart form data without forcing json headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ document_id: 'doc-upload' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient({ apiToken: 'secret' })

    const document = await client.documents.upload(new Blob(['alpha beta'], { type: 'text/plain' }), 'report.txt')

    expect(document.document_id).toBe('doc-upload')
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/documents',
      expect.objectContaining({
        method: 'POST',
        headers: { Authorization: 'Bearer secret' },
        body: expect.any(FormData),
      }),
    )
  })

  it('sends bearer and request id headers and redacts token from errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      json: async () => ({ error: { message: 'rejected Authorization: Bearer secret-token' } }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient({ apiToken: 'secret-token', requestId: 'req-123' })

    await expect(client.sessions.list()).rejects.toMatchObject({
      name: 'DogeApiError',
      statusCode: 403,
      message: 'rejected Authorization: Bearer [REDACTED]',
    } satisfies Partial<DogeApiError>)
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/sessions?limit=20',
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer secret-token',
          'X-Request-ID': 'req-123',
        },
      }),
    )
  })

  it('redacts key-value secrets from API errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => ({
        detail: 'provider failed MOONSHOT_API_KEY=moonshot-secret client_secret=client-secret sk-live-secret',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    await expect(client.sessions.list()).rejects.toMatchObject({
      name: 'DogeApiError',
      statusCode: 500,
      message: 'provider failed MOONSHOT_API_KEY=[REDACTED] client_secret=[REDACTED] sk-[REDACTED]',
    } satisfies Partial<DogeApiError>)
  })

  it('keeps status text for empty real Response error bodies', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('', {
      status: 404,
      statusText: 'Not Found',
    }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient()

    await expect(client.platform.homeQueue()).rejects.toMatchObject({
      name: 'DogeApiError',
      statusCode: 404,
      message: 'Not Found',
    } satisfies Partial<DogeApiError>)
  })

  it('sends bearer and request id headers on SSE streams', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('id: 2\nevent: tool_call\ndata: {"ok": true}\n\n'))
        controller.close()
      },
    })
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, body: stream })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient({ apiToken: 'secret-token', requestId: 'req-123' })

    const events = []
    for await (const event of client.runs.stream('run-test', { lastEventId: '1' })) {
      events.push(event)
    }

    expect(events[0].id).toBe('2')
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/runs/run-test/stream',
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer secret-token',
          'X-Request-ID': 'req-123',
          'Last-Event-ID': '1',
        },
      }),
    )
  })

  it('redacts bearer tokens from SSE stream errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ detail: 'stream rejected Authorization: Bearer secret-token' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = new DogeClient({ apiToken: 'secret-token' })

    const events = client.runs.stream('run-test')
    await expect(events.next()).rejects.toMatchObject({
      name: 'DogeApiError',
      statusCode: 401,
      message: 'stream rejected Authorization: Bearer [REDACTED]',
    } satisfies Partial<DogeApiError>)
  })
})
