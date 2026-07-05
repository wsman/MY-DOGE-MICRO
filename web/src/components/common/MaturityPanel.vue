<template>
  <section class="maturity-panel" aria-label="Runtime maturity">
    <div class="mp-row">
      <span class="mp-label">Runtime Level</span>
      <span class="mp-value">{{ runtimeLevel }}</span>
    </div>
    <div class="mp-row">
      <span class="mp-label">Provider</span>
      <span class="mp-value">{{ providerLine }}</span>
    </div>
    <div class="mp-row">
      <span class="mp-label">Readiness gates</span>
      <span class="mp-value">{{ openGates.length }} open</span>
    </div>
    <ul v-if="openGates.length" class="mp-gates">
      <li v-for="gate in openGates" :key="gate.id">
        <code>{{ gate.id }}</code> — {{ gate.label }}
      </li>
    </ul>
    <p class="mp-note">Local Alpha — not production ready.</p>
  </section>
</template>

<script setup lang="ts">
/**
 * MaturityPanel — honest Local-Alpha disclosure (Sprint UX-1 Slice E, WEB-8).
 *
 * Renders Runtime Level (Local Alpha), the live-or-scripted provider line
 * derived from the `/v1/capabilities` snapshot, and the count of open
 * production-readiness gates (operator-owned; surfaced as advisory copy, never
 * closed). Vocabulary is locked to the alpha-maturity safe terms — no
 * "production-ready" / "stable" / "GA" promotion language.
 *
 * The panel is self-contained: it loads the capability snapshot on mount and
 * degrades to an "unknown" provider line if the fetch fails. The open-gate list
 * is static advisory copy sourced verbatim from `docs/progress/runtime-maturity.yaml`,
 * NOT capability metadata, so the `CapabilityResponse` ↔ `Capability`
 * ENTITY_PARITY contract stays untouched.
 */
import { computed, onMounted } from 'vue'

import type { CapabilitySnapshot } from 'doge-sdk'

import { usePlatformStore } from '../../stores/platform'

const platformStore = usePlatformStore()

// Static Local-Alpha vocabulary (the runtime-level labels in
// docs/progress/runtime-maturity.yaml are alpha / alpha / experimental).
const runtimeLevel = 'Local Alpha'

// Open production-readiness gates, sourced verbatim from
// docs/progress/runtime-maturity.yaml (operator-owned; advisory only — never
// closed or fabricated here).
const openGates = [
  { id: 'S017-003', label: 'Financial provider approval' },
  { id: 'W3-live', label: 'Analyst benchmark' },
  { id: 'AUTH-prod', label: 'Live identity provider' },
  { id: 'S017-007', label: 'SDK registry release' },
]

const providerLine = computed(() => deriveProviderLine(platformStore.capabilities))

function deriveProviderLine(caps: CapabilitySnapshot | null): string {
  if (!caps) return 'unknown'
  const items = caps.capabilities ?? []
  const live =
    items.find(c => c.capability_id === 'provider.kimi' && c.status === 'available') ??
    items.find(c => c.capability_id === 'provider.deepseek' && c.status === 'available')
  return live ? `${live.name} (live)` : 'scripted fallback (local_demo)'
}

// Self-contained: ensure the capability snapshot is loaded so the provider line
// is populated. Failures degrade to the "unknown" provider line above.
onMounted(() => {
  platformStore.loadCapabilities().catch(() => undefined)
})
</script>

<style scoped>
.maturity-panel {
  display: grid;
  gap: 6px;
  padding: 8px 10px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
  font-size: 12px;
  color: var(--dgm-text-muted);
}

.mp-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.mp-label {
  color: var(--dgm-text-faint);
  text-transform: uppercase;
  font-size: 11px;
}

.mp-value {
  color: var(--dgm-text);
}

.mp-gates {
  margin: 4px 0 0;
  padding-left: 16px;
}

.mp-gates li {
  line-height: 1.5;
}

.mp-note {
  margin: 4px 0 0;
  color: var(--dgm-text-faint);
}

code {
  font-family: var(--dgm-font-mono);
}
</style>
