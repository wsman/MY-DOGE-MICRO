import { describe, expect, it } from 'vitest'

import router from './index'
import { VIEW_REGISTRY } from '../views/registry'

describe('product navigation routes', () => {
  it('exposes the consolidated product-domain shell routes', () => {
    const routeNames = router.getRoutes().map(route => String(route.name))

    expect(routeNames).toEqual(expect.arrayContaining([
      'home-dashboard',
      'research-domain',
      'market-domain',
      'portfolio-domain',
      'quant-domain',
      'admin-center',
    ]))
  })

  it('keeps legacy deep links available behind the product domains', () => {
    const paths = router.getRoutes().map(route => route.path)

    expect(paths).toEqual(expect.arrayContaining([
      '/research-agent',
      '/scanner',
      '/cn-archive',
      '/us-archive',
      '/insights',
      '/analysis',
    ]))
  })

  it('registers the product-domain views for split panels', () => {
    expect(VIEW_REGISTRY['home-dashboard'].label).toBe('Home')
    expect(VIEW_REGISTRY['research-domain'].label).toBe('Research')
    expect(VIEW_REGISTRY['market-domain'].label).toBe('Market')
    expect(VIEW_REGISTRY['portfolio-domain'].label).toBe('Portfolio')
    expect(VIEW_REGISTRY['quant-domain'].label).toBe('Quant')
  })
})
