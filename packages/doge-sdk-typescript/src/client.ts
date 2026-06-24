import { DocumentsResource } from './document.js'
import { CapabilitiesResource, PlatformResource } from './platform.js'
import { DogeApiError, type DogeEvent, RunsResource } from './run.js'
import { SessionsResource } from './session.js'
import { parseSse } from './streaming.js'

export { DocumentsResource } from './document.js'
export { CapabilitiesResource, PlatformResource } from './platform.js'
export { DogeApiError, type DogeEvent, RunsResource, type RunStreamOptions } from './run.js'
export { Session, SessionsResource, type AgentSession } from './session.js'

interface DogeClientOptions {
  baseUrl?: string
  apiToken?: string
  requestId?: string
}

export class DogeClient {
  readonly sessions: SessionsResource
  readonly runs: RunsResource
  readonly documents: DocumentsResource
  readonly platform: PlatformResource
  readonly capabilities: CapabilitiesResource
  private readonly baseUrl: string
  private readonly apiToken?: string
  private readonly requestId?: string

  constructor(options: DogeClientOptions = {}) {
    this.baseUrl = options.baseUrl?.replace(/\/$/, '') ?? ''
    this.apiToken = options.apiToken
    this.requestId = options.requestId
    this.sessions = new SessionsResource(this)
    this.runs = new RunsResource(this)
    this.documents = new DocumentsResource(this)
    this.platform = new PlatformResource(this)
    this.capabilities = new CapabilitiesResource(this)
  }

  async request<T>(method: string, path: string, body?: unknown, extraHeaders: Record<string, string> = {}): Promise<T> {
    const headers = this.headers(extraHeaders)
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!response.ok) {
      const message = await responseErrorMessage(response)
      throw new DogeApiError(response.status, redactMessage(message, this.apiToken))
    }
    return await response.json() as T
  }

  async requestForm<T>(
    method: string,
    path: string,
    form: FormData,
    extraHeaders: Record<string, string> = {},
  ): Promise<T> {
    const headers = this.headers(extraHeaders)
    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: form,
    })
    if (!response.ok) {
      const message = await responseErrorMessage(response)
      throw new DogeApiError(response.status, redactMessage(message, this.apiToken))
    }
    return await response.json() as T
  }

  async stream(path: string, lastEventId?: string): Promise<AsyncGenerator<DogeEvent>> {
    const headers = this.headers()
    if (lastEventId) headers['Last-Event-ID'] = lastEventId
    const response = await fetch(`${this.baseUrl}${path}`, { headers })
    if (!response.ok || !response.body) {
      const message = await responseErrorMessage(response)
      throw new DogeApiError(response.status, redactMessage(message, this.apiToken))
    }
    return parseSse(response.body)
  }

  private headers(extraHeaders: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = { ...extraHeaders }
    if (this.apiToken) headers.Authorization = `Bearer ${this.apiToken}`
    if (this.requestId) headers['X-Request-ID'] = this.requestId
    return headers
  }
}

async function responseErrorMessage(response: Response): Promise<string> {
  let message = response.statusText
  let body = ''
  if (typeof response.text === 'function') {
    try {
      body = await response.text()
    } catch {
      body = ''
    }
  }
  if (body) {
    try {
      const payload = JSON.parse(body) as { error?: { message?: string }, detail?: string }
      return payload.error?.message ?? payload.detail ?? body
    } catch {
      return body
    }
  }
  try {
    const payload = await response.json() as { error?: { message?: string }, detail?: string }
    message = payload.error?.message ?? payload.detail ?? message
  } catch {
    // Keep statusText when the body cannot be read.
  }
  return message
}

function redactMessage(message: string, apiToken?: string): string {
  let redacted = message.replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/g, 'Bearer [REDACTED]')
  redacted = redacted.replace(
    /\b(api[_-]?key|password|secret|token|access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|moonshot_api_key|deepseek_api_key|doge_api_token)\s*([=:])\s*(['"]?)[^&\s,'"}]+/gi,
    (_match, key, separator) => `${key}${separator}[REDACTED]`,
  )
  redacted = redacted.replace(/\bsk-[A-Za-z0-9._-]{6,}/g, 'sk-[REDACTED]')
  if (apiToken) redacted = redacted.split(apiToken).join('[REDACTED]')
  return redacted
}
