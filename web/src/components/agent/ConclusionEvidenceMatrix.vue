<template>
  <div class="conclusion-evidence-matrix" aria-label="Conclusion evidence matrix">
    <div class="matrix-header" role="row">
      <span>Claim</span>
      <span>Status</span>
      <span>Evidence</span>
    </div>
    <div v-for="claim in claims" :key="claim.claim_id" class="matrix-row" role="row">
      <div class="claim-cell">{{ claim.claim_text }}</div>
      <div class="tag-cell" aria-label="Claim confidence tags">
        <n-tag size="small" :type="statusTone(claim.status)">{{ claim.status }}</n-tag>
        <n-tag size="small" :type="numericTone(claim.numeric_check_status)">
          {{ claim.numeric_check_status }}
        </n-tag>
        <n-tag size="small" :type="riskTone(claim.risk_level)">{{ claim.risk_level }}</n-tag>
      </div>
      <div class="evidence-cell" aria-label="Evidence references">
        <span
          v-for="sourceType in sourceTypes(claim.evidence_refs)"
          :key="sourceType"
          class="source-type-badge"
        >
          {{ evidenceSourceLabel(sourceType) }}
        </span>
        <button
          v-for="(ref, index) in claim.evidence_refs"
          :key="ref.key"
          class="evidence-chip"
          type="button"
          @click="emit('select-evidence', { claimId: claim.claim_id, ref })"
        >
          {{ evidenceLabel(ref, index) }}
        </button>
        <span v-if="!claim.evidence_refs.length" class="empty-evidence">No evidence</span>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import type { CitationRecord } from './CitationDrilldown.vue'

export type ConclusionEvidenceRef = CitationRecord

export interface ConclusionClaimDisplay {
  claim_id: string
  claim_text: string
  status: string
  numeric_check_status: string
  risk_level: string
  evidence_refs: ConclusionEvidenceRef[]
}

export interface EvidenceSelection {
  claimId: string
  ref: ConclusionEvidenceRef
}
</script>

<script setup lang="ts">
import { NTag } from 'naive-ui'
import type { RunStatusTone } from '../../utils/runStatus'
import { evidenceSourceLabel, evidenceSourceType } from '../../utils/evidenceSourceType'

defineProps<{
  claims: ConclusionClaimDisplay[]
}>()

const emit = defineEmits<{
  'select-evidence': [selection: EvidenceSelection]
}>()

function evidenceLabel(ref: ConclusionEvidenceRef, index: number) {
  return ref.source || ref.evidence_id || ref.citation_id || ref.chunk_id || `Evidence ${index + 1}`
}

function sourceTypes(refs: ConclusionEvidenceRef[]) {
  const seen = new Set<string>()
  return refs
    .map(ref => evidenceSourceType(ref as unknown as Record<string, unknown>))
    .filter(sourceType => {
      if (seen.has(sourceType)) return false
      seen.add(sourceType)
      return true
    })
}

function statusTone(status: string): RunStatusTone {
  const normalized = status.toLowerCase()
  if (['supported', 'verified'].includes(normalized)) return 'success'
  if (['contradicted', 'unsupported', 'failed'].includes(normalized)) return 'error'
  if (['partial', 'mixed', 'unverified'].includes(normalized)) return 'warning'
  return 'default'
}

function numericTone(status: string): RunStatusTone {
  const normalized = status.toLowerCase()
  if (['checked', 'consistent', 'matched', 'pass', 'passed'].includes(normalized)) return 'success'
  if (['mismatch', 'inconsistent', 'failed'].includes(normalized)) return 'error'
  if (['not_checked', 'needs_review'].includes(normalized)) return 'warning'
  return 'default'
}

function riskTone(risk: string): RunStatusTone {
  const normalized = risk.toLowerCase()
  if (normalized === 'low') return 'success'
  if (normalized === 'high' || normalized === 'critical') return 'error'
  if (normalized === 'medium') return 'warning'
  return 'default'
}
</script>

<style scoped>
.conclusion-evidence-matrix {
  display: grid;
  gap: 6px;
}

.matrix-header,
.matrix-row {
  display: grid;
  grid-template-columns: minmax(130px, 1.1fr) minmax(120px, 0.9fr) minmax(110px, 0.8fr);
  gap: 8px;
  align-items: start;
}

.matrix-header {
  color: var(--dgm-text-faint);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.matrix-row {
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  background: var(--dgm-surface);
}

.claim-cell {
  min-width: 0;
  color: var(--dgm-text);
  font-size: 12px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.tag-cell,
.evidence-cell {
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.evidence-chip {
  max-width: 100%;
  padding: 3px 7px;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  color: var(--dgm-text);
  background: var(--dgm-surface);
  font-size: 12px;
  line-height: 1.35;
  text-align: left;
  cursor: pointer;
  overflow-wrap: anywhere;
}

.source-type-badge {
  display: inline-block;
  align-self: center;
  padding: 2px 6px;
  border: 1px solid var(--dgm-border);
  border-radius: 999px;
  color: var(--dgm-text-faint);
  font-size: 10px;
  font-weight: 700;
  line-height: 1.3;
  text-transform: uppercase;
}

.evidence-chip:hover {
  background: var(--dgm-surface-hover);
}

.empty-evidence {
  color: var(--dgm-text-faint);
  font-size: 12px;
}

@media (max-width: 900px) {
  .matrix-header {
    display: none;
  }

  .matrix-row {
    grid-template-columns: 1fr;
  }
}
</style>
