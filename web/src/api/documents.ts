import { dogeClient } from './client'

export interface ResearchDocument {
  document_id: string
  filename: string
  original_filename?: string
  mime_type?: string | null
  size_bytes?: number | null
  parsing_status?: string
  status?: string
  parser_error?: string | null
  created_at?: string
}

export async function listDocuments(): Promise<ResearchDocument[]> {
  const documents = await dogeClient.documents.list()
  return documents.map(toResearchDocument)
}

export async function uploadDocument(file: File): Promise<ResearchDocument> {
  const document = await dogeClient.documents.upload(file, file.name)
  return toResearchDocument(document)
}

function toResearchDocument(payload: Record<string, unknown>): ResearchDocument {
  return {
    document_id: stringField(payload.document_id),
    filename: stringField(payload.filename || payload.original_filename, 'document'),
    original_filename: optionalString(payload.original_filename),
    mime_type: optionalNullableString(payload.mime_type),
    size_bytes: optionalNumber(payload.size_bytes),
    parsing_status: optionalString(payload.parsing_status),
    status: optionalString(payload.status),
    parser_error: optionalNullableString(payload.parser_error),
    created_at: optionalString(payload.created_at),
  }
}

function stringField(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value ? value : fallback
}

function optionalString(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined
}

function optionalNullableString(value: unknown): string | null | undefined {
  if (value === null) return null
  return optionalString(value)
}

function optionalNumber(value: unknown): number | null | undefined {
  if (value === null) return null
  return typeof value === 'number' ? value : undefined
}
