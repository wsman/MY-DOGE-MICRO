import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import HomeRecentUploads from './HomeRecentUploads.vue'
import { listDocuments } from '../../api/documents'

const pushMock = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}))

vi.mock('../../api/documents', () => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
}))

describe('HomeRecentUploads', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    pushMock.mockReset()
    vi.mocked(listDocuments).mockReset()
  })

  it('loads and renders recent documents', async () => {
    vi.mocked(listDocuments).mockResolvedValue([
      {
        document_id: 'doc-1',
        filename: 'annual-report.pdf',
        mime_type: 'application/pdf',
        parsing_status: 'parsed',
        created_at: '2026-07-06T00:00:00Z',
      },
    ])

    const wrapper = mount(HomeRecentUploads)
    await flushPromises()

    expect(listDocuments).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('Recent Uploads')
    expect(wrapper.text()).toContain('annual-report.pdf')
    expect(wrapper.text()).toContain('application/pdf · parsed')
  })

  it('shows loading then empty state when no documents exist', async () => {
    let resolve: (value: []) => void = () => undefined
    vi.mocked(listDocuments).mockReturnValue(new Promise(res => { resolve = res }))

    const wrapper = mount(HomeRecentUploads)
    await nextTick()
    expect(wrapper.text()).toContain('Loading documents')

    resolve([])
    await flushPromises()

    expect(wrapper.text()).toContain('No uploads')
  })

  it('renders document load errors and routes upload to the research workspace', async () => {
    vi.mocked(listDocuments).mockRejectedValue(new Error('document service offline'))

    const wrapper = mount(HomeRecentUploads)
    await flushPromises()

    expect(wrapper.text()).toContain('document service offline')
    await wrapper.findAll('button').find(button => button.text().includes('Upload'))?.trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/research-agent')
  })
})
