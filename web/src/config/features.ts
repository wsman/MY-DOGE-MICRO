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

export const slotInstallUiLifecycle = {
  envVar: 'VITE_DOGE_FEATURE_SLOT_INSTALL_UI',
  introduced: 'P9 Install Surfaces and Operator Controls; docs/architecture/adr-0067-slot-install-surfaces.md',
  currentDefault: false,
  targetDefaultOn: 'after HTTP install, SDK parity, Web Slot Center install tests, and operator rollback evidence pass',
  targetRemoval: 'after slot install UI is accepted as a governed operator surface for one release cycle',
  replacementBehavior: 'Web Slot Center can call the server-side slot install endpoint for local path manifests',
  regressionCommands: [
    'npm test -- src/stores/platform.spec.ts src/views/AdminCenterView.spec.ts',
    'npm run build',
  ],
  rollbackCriterion: 'set VITE_DOGE_FEATURE_SLOT_INSTALL_UI=0 if install modal, error surfacing, or slot refresh behavior regresses',
} as const satisfies FeatureLifecycle

export const featureLifecycles = {
  platformShell: platformShellLifecycle,
  slotInstallUi: slotInstallUiLifecycle,
} as const

function isFeatureEnabled(value: unknown, currentDefault: boolean): boolean {
  if (value === undefined || value === null || value === '') {
    return currentDefault
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
  return currentDefault
}

export function isPlatformShellEnabled(value: unknown): boolean {
  return isFeatureEnabled(value, platformShellLifecycle.currentDefault)
}

export function isSlotInstallUiEnabled(value: unknown): boolean {
  return isFeatureEnabled(value, slotInstallUiLifecycle.currentDefault)
}

export const platformShellEnabled = isPlatformShellEnabled(import.meta.env.VITE_DOGE_FEATURE_PLATFORM_SHELL)
export const slotInstallUiEnabled = isSlotInstallUiEnabled(import.meta.env.VITE_DOGE_FEATURE_SLOT_INSTALL_UI)
