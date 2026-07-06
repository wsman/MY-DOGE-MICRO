<template>
  <div v-if="detailRows.length" class="approval-details">
    <div v-for="row in detailRows" :key="row.key" class="detail-row">
      <span>{{ row.label }}</span>
      <strong>{{ row.value }}</strong>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatPolicyRows, type ApprovalPolicy } from '../../utils/approvalPolicy'

const props = defineProps<{
  approval: unknown
  policy?: ApprovalPolicy
}>()

const detailFields = [
  { key: 'why_needed', label: 'Why needed' },
  { key: 'impact', label: 'Impact' },
  { key: 'deny_consequence', label: 'Deny consequence' },
  { key: 'publish_target', label: 'Publish target' },
] as const

const detailRows = computed(() => [
  ...detailFields
    .map(field => ({
      key: field.key,
      label: field.label,
      value: textValue(approvalRecord.value[field.key]),
    }))
    .filter(row => row.value),
  ...formatPolicyRows(props.policy).map(row => ({
    key: row.key,
    label: row.label,
    value: row.value,
  })),
])

const approvalRecord = computed(() => {
  return isRecord(props.approval) ? props.approval : {}
})

function textValue(value: unknown) {
  if (value === undefined || value === null) return ''
  return String(value).trim()
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
</script>

<style scoped>
.approval-details {
  display: grid;
  gap: 8px;
  margin-bottom: 8px;
}

.detail-row {
  display: grid;
  grid-template-columns: 104px minmax(0, 1fr);
  gap: 8px;
  font-size: 12px;
}

.detail-row span {
  color: var(--dgm-text-faint);
  overflow-wrap: anywhere;
}

.detail-row strong {
  min-width: 0;
  overflow-wrap: anywhere;
}
</style>
