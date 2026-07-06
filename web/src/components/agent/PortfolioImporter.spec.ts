import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import PortfolioImporter from './PortfolioImporter.vue'
import { uploadPortfolioCsv } from '../../api/portfolio'

vi.mock('../../api/portfolio', () => ({
  uploadPortfolioCsv: vi.fn(),
}))

const fileTextDescriptor = Object.getOwnPropertyDescriptor(File.prototype, 'text')

describe('PortfolioImporter', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    if (fileTextDescriptor) {
      Object.defineProperty(File.prototype, 'text', fileTextDescriptor)
    } else {
      Reflect.deleteProperty(File.prototype, 'text')
    }
  })

  it('renders the imported portfolio auto-summary', async () => {
    const csv = [
      'symbol,asset_class,sector,quantity,market_value,currency',
      'AAPL,equity,technology,10,2500,USD',
      'TLT,bond,rates,5,900,USD',
    ].join('\n')
    vi.mocked(uploadPortfolioCsv).mockResolvedValue({
      portfolio_id: 'portfolio-test',
      name: 'Operator book',
      total_market_value: 3400,
      holdings: [],
      summary: {
        portfolio_id: 'portfolio-test',
        name: 'Operator book',
        total_market_value: 3400,
        holdings_count: 2,
        top_concentration: [
          {
            symbol: 'AAPL',
            asset_class: 'equity',
            sector: 'technology',
            market_value: 2500,
            weight: 0.735294,
          },
        ],
        by_sector: [
          { name: 'rates', market_value: 900, weight: 0.264706 },
          { name: 'technology', market_value: 2500, weight: 0.735294 },
        ],
        missing_prices: [],
        suggested_run: {
          workflow: 'portfolio_risk_review',
          question: 'Analyze concentration and rate-shock risk for portfolio portfolio-test.',
        },
      },
    })
    Object.defineProperty(File.prototype, 'text', {
      configurable: true,
      value: vi.fn(async () => csv),
    })
    const wrapper = mount(PortfolioImporter)
    const file = new File([csv], 'operator.csv', { type: 'text/csv' })
    const input = wrapper.find('input[type="file"]')

    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()

    expect(uploadPortfolioCsv).toHaveBeenCalledWith(file, { name: 'operator' })
    expect(wrapper.emitted('imported')?.[0][0]).toMatchObject({ portfolio_id: 'portfolio-test' })
    expect(wrapper.find('[aria-label="Portfolio summary"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Holdings')
    expect(wrapper.text()).toContain('2')
    expect(wrapper.text()).toContain('AAPL')
    expect(wrapper.text()).toContain('technology')
    expect(wrapper.text()).toContain('None')
    expect(wrapper.text()).toContain('Analyze concentration and rate-shock risk for portfolio portfolio-test.')
  })
})
