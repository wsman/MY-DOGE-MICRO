import { afterEach, describe, expect, it, vi } from 'vitest'

describe('feature lifecycle metadata', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('documents the platform shell feature flag lifecycle', async () => {
    const { featureLifecycles, platformShellLifecycle } = await import('./features')

    expect(featureLifecycles.platformShell).toBe(platformShellLifecycle)
    expect(platformShellLifecycle.envVar).toBe('VITE_DOGE_FEATURE_PLATFORM_SHELL')
    expect(platformShellLifecycle.currentDefault).toBe(false)
    expect(platformShellLifecycle.targetDefaultOn).toBeTruthy()
    expect(platformShellLifecycle.targetRemoval).toBeTruthy()
    expect(platformShellLifecycle.replacementBehavior).toBeTruthy()
    expect(platformShellLifecycle.regressionCommands).toEqual(['npm test', 'npm run build'])
    expect(platformShellLifecycle.rollbackCriterion).toBeTruthy()
  })

  it('parses the platform shell env var as exact opt-in only', async () => {
    const { isPlatformShellEnabled } = await import('./features')

    expect(isPlatformShellEnabled('1')).toBe(true)
    expect(isPlatformShellEnabled('true')).toBe(false)
    expect(isPlatformShellEnabled('on')).toBe(false)
    expect(isPlatformShellEnabled('0')).toBe(false)
    expect(isPlatformShellEnabled('')).toBe(false)
    expect(isPlatformShellEnabled(undefined)).toBe(false)
  })

  it('keeps the module-level platform shell flag behind exact env value 1', async () => {
    vi.stubEnv('VITE_DOGE_FEATURE_PLATFORM_SHELL', '1')
    expect((await import('./features')).platformShellEnabled).toBe(true)

    vi.resetModules()
    vi.stubEnv('VITE_DOGE_FEATURE_PLATFORM_SHELL', 'true')
    expect((await import('./features')).platformShellEnabled).toBe(false)
  })
})
