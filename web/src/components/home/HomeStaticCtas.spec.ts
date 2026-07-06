import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import HomeStaticCtas from './HomeStaticCtas.vue'
import { useAgentStore } from '../../stores/agent'

const pushMock = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}))

describe('HomeStaticCtas', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    pushMock.mockReset()
  })

  it('renders static portfolio and demo-pack entries without live list APIs', () => {
    const wrapper = mount(HomeStaticCtas)
    const text = wrapper.text()

    expect(text).toContain('Import portfolio')
    expect(text).toContain('No portfolio imported')
    expect(text).toContain('Generate demo pack')
    expect(text).toContain('doge demo-pack')
    expect(text).toContain('Local CLI')
    expect(wrapper.find('a[href^="/docs/"]').exists()).toBe(false)
  })

  it('shows the in-memory portfolio id and routes import to the research workspace', async () => {
    const store = useAgentStore()
    store.setPortfolioId('portfolio-123')

    const wrapper = mount(HomeStaticCtas)

    expect(wrapper.text()).toContain('portfolio-123')
    await wrapper.findAll('button').find(button => button.text().includes('Import'))?.trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/research-agent')
  })
})
