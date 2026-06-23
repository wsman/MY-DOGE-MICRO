import { afterEach, describe, expect, it, vi } from 'vitest'

import router from './index'
import { VIEW_REGISTRY } from '../views/registry'

describe('product navigation routes', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

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

  it('uses the product-domain shell as the default root entry', () => {
    const root = router.getRoutes().find(route => route.path === '/')

    expect(root?.redirect).toBe('/home')
  })

  it('keeps the legacy root fallback available through an explicit rollback env value', async () => {
    vi.stubEnv('VITE_DOGE_FEATURE_PLATFORM_SHELL', '0')
    vi.resetModules()

    const { default: rollbackRouter } = await import('./index')
    const root = rollbackRouter.getRoutes().find(route => route.path === '/')

    expect(root?.redirect).toBe('/research-agent')
  })

  it('redirects platform routes to the legacy agent route when the rollback env value is set', async () => {
    vi.stubEnv('VITE_DOGE_FEATURE_PLATFORM_SHELL', '0')
    vi.resetModules()

    const { default: rollbackRouter } = await import('./index')
    await rollbackRouter.push('/home')
    await rollbackRouter.isReady()

    expect(rollbackRouter.currentRoute.value.path).toBe('/research-agent')
  })


  it('registers the product-domain views for split panels', () => {
    expect(VIEW_REGISTRY['home-dashboard'].label).toBe('Home')
    expect(VIEW_REGISTRY['research-domain'].label).toBe('Research')
    expect(VIEW_REGISTRY['market-domain'].label).toBe('Market')
    expect(VIEW_REGISTRY['portfolio-domain'].label).toBe('Portfolio')
    expect(VIEW_REGISTRY['quant-domain'].label).toBe('Quant')
  })
})
