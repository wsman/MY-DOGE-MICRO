export interface FeatureLifecycle {
  envVar: string
  introduced: string
  currentDefault: boolean
  targetDefaultOn: string
  targetRemoval: string
  replacementBehavior: string
  regressionCommands: string[]
  rollbackCriterion: string
}

export const platformShellLifecycle = {
  envVar: 'VITE_DOGE_FEATURE_PLATFORM_SHELL',
  introduced: 'platformization Phase F; docs/archive/audits/platformization-consolidation-phase-f-web-2026-06-23.md',
  currentDefault: true,
  targetDefaultOn: 'completed locally after ADR-0020 review, case workspace browser/AX evidence, and web navigation regressions passed',
  targetRemoval: 'one release cycle after default-on with approved legacy route compatibility removal story',
  replacementBehavior: 'product-domain shell becomes the default web entry while /research-agent remains an approved compatibility route',
  regressionCommands: [
    'npm test',
    'npm run build',
  ],
  rollbackCriterion: 'set VITE_DOGE_FEATURE_PLATFORM_SHELL=0 or restore currentDefault false if product navigation, accessibility evidence, or legacy deep links regress',
} as const satisfies FeatureLifecycle

export const featureLifecycles = {
  platformShell: platformShellLifecycle,
} as const

export function isPlatformShellEnabled(value: unknown): boolean {
  if (value === undefined || value === null || value === '') {
    return platformShellLifecycle.currentDefault
  }
  if (typeof value !== 'string') {
    return Boolean(value)
  }
  const normalized = value.trim().toLowerCase()
  if (['0', 'false', 'off', 'no'].includes(normalized)) {
    return false
  }
  if (['1', 'true', 'on', 'yes'].includes(normalized)) {
    return true
  }
  return platformShellLifecycle.currentDefault
}

export const platformShellEnabled = isPlatformShellEnabled(import.meta.env.VITE_DOGE_FEATURE_PLATFORM_SHELL)
