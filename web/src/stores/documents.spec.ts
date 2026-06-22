import { setActivePinia, createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listDocuments, uploadDocument } from '../api/documents'
import { useDocumentStore } from './documents'

vi.mock('../api/documents', () => ({
  listDocuments: vi.fn(async () => ([
    { document_id: 'doc-1', filename: 'memo.md', parsing_status: 'parsed' },
  ])),
  uploadDocument: vi.fn(async () => ({
    document_id: 'doc-2',
    filename: 'report.txt',
    parsing_status: 'parsed',
  })),
}))

describe('document store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(listDocuments).mockClear()
    vi.mocked(uploadDocument).mockClear()
  })

  it('loads documents and manages selection', async () => {
    const store = useDocumentStore()

    await store.loadDocuments()
    store.toggleSelection('doc-1', true)

    expect(store.documents[0].document_id).toBe('doc-1')
    expect(store.selectedDocuments[0].document_id).toBe('doc-1')

    store.clearSelection()
    expect(store.selectedIds).toEqual([])
  })

  it('uploads and auto-selects the new document', async () => {
    const store = useDocumentStore()

    await store.upload(new File(['alpha'], 'report.txt', { type: 'text/plain' }))

    expect(uploadDocument).toHaveBeenCalled()
    expect(store.documents[0].document_id).toBe('doc-2')
    expect(store.selectedIds).toEqual(['doc-2'])
  })
})
