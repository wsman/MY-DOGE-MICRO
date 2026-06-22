import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { listDocuments, uploadDocument, type ResearchDocument } from '../api/documents'
import { toFetchError, type FetchError } from '../utils/fetchError'

export const useDocumentStore = defineStore('documents', () => {
  const documents = ref<ResearchDocument[]>([])
  const selectedIds = ref<string[]>([])
  const loading = ref(false)
  const error = ref<FetchError | null>(null)

  const selectedDocuments = computed(() => {
    const selected = new Set(selectedIds.value)
    return documents.value.filter(document => selected.has(document.document_id))
  })

  async function loadDocuments() {
    loading.value = true
    error.value = null
    try {
      documents.value = await listDocuments()
    } catch (e) {
      error.value = toFetchError(e)
    } finally {
      loading.value = false
    }
  }

  async function upload(file: File) {
    loading.value = true
    error.value = null
    try {
      const document = await uploadDocument(file)
      upsertDocument(document)
      select(document.document_id)
      return document
    } catch (e) {
      error.value = toFetchError(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  function select(documentId: string) {
    if (!selectedIds.value.includes(documentId)) {
      selectedIds.value = [...selectedIds.value, documentId]
    }
  }

  function toggleSelection(documentId: string, checked?: boolean) {
    const selected = selectedIds.value.includes(documentId)
    const next = checked ?? !selected
    if (next && !selected) {
      selectedIds.value = [...selectedIds.value, documentId]
    } else if (!next && selected) {
      selectedIds.value = selectedIds.value.filter(id => id !== documentId)
    }
  }

  function selectAll() {
    selectedIds.value = documents.value.map(document => document.document_id)
  }

  function clearSelection() {
    selectedIds.value = []
  }

  function upsertDocument(document: ResearchDocument) {
    const index = documents.value.findIndex(item => item.document_id === document.document_id)
    if (index >= 0) {
      documents.value[index] = document
    } else {
      documents.value = [document, ...documents.value]
    }
  }

  return {
    documents,
    selectedIds,
    selectedDocuments,
    loading,
    error,
    loadDocuments,
    upload,
    toggleSelection,
    selectAll,
    clearSelection,
  }
})
