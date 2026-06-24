import type { DogeClient } from './client.js'

export class DocumentsResource {
  private readonly root: DogeClient

  constructor(root: DogeClient) {
    this.root = root
  }

  create(filename: string, content = ''): Promise<Record<string, unknown>> {
    return this.root.request('POST', '/v1/documents', { filename, content })
  }

  upload(file: Blob, filename?: string): Promise<Record<string, unknown>> {
    const form = new FormData()
    form.append('file', file, filename ?? blobFilename(file))
    return this.root.requestForm('POST', '/v1/documents', form)
  }

  async list(limit = 100): Promise<Record<string, unknown>[]> {
    const payload = await this.root.request<{ documents: Record<string, unknown>[] }>(
      'GET',
      `/v1/documents?limit=${limit}`,
    )
    return payload.documents
  }

  get(documentId: string): Promise<Record<string, unknown>> {
    return this.root.request('GET', `/v1/documents/${documentId}`)
  }
}

function blobFilename(file: Blob): string {
  const maybeNamed = file as Blob & { name?: unknown }
  return typeof maybeNamed.name === 'string' && maybeNamed.name ? maybeNamed.name : 'document'
}
