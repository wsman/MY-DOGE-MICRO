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
    expect(platformShellLifecycle.currentDefault).toBe(true)
    expect(platformShellLifecycle.targetDefaultOn).toContain('completed locally')
    expect(platformShellLifecycle.targetRemoval).toBeTruthy()
    expect(platformShellLifecycle.replacementBehavior).toBeTruthy()
    expect(platformShellLifecycle.regressionCommands).toEqual(['npm test', 'npm run build'])
    expect(platformShellLifecycle.rollbackCriterion).toBeTruthy()
  })

  it('defaults the platform shell on while preserving explicit rollback values', async () => {
    const { isPlatformShellEnabled } = await import('./features')

    expect(isPlatformShellEnabled('1')).toBe(true)
    expect(isPlatformShellEnabled('true')).toBe(true)
    expect(isPlatformShellEnabled('on')).toBe(true)
    expect(isPlatformShellEnabled('yes')).toBe(true)
    expect(isPlatformShellEnabled('0')).toBe(false)
    expect(isPlatformShellEnabled('false')).toBe(false)
    expect(isPlatformShellEnabled('off')).toBe(false)
    expect(isPlatformShellEnabled('no')).toBe(false)
    expect(isPlatformShellEnabled('')).toBe(true)
    expect(isPlatformShellEnabled(undefined)).toBe(true)
  })

  it('keeps the module-level platform shell flag enabled by default', async () => {
    vi.stubEnv('VITE_DOGE_FEATURE_PLATFORM_SHELL', '')
    expect((await import('./features')).platformShellEnabled).toBe(true)

    vi.resetModules()
    vi.stubEnv('VITE_DOGE_FEATURE_PLATFORM_SHELL', '0')
    expect((await import('./features')).platformShellEnabled).toBe(false)
  })
})
