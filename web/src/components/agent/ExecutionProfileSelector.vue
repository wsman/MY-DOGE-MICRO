<template>
  <n-select
    :value="modelValue"
    :options="profileOptions"
    size="small"
    aria-label="Execution profile"
    @update:value="value => emit('update:modelValue', String(value))"
  />
</template>

<script setup lang="ts">
import { NSelect, type SelectOption } from 'naive-ui'

withDefaults(defineProps<{ modelValue?: string }>(), {
  modelValue: 'financial_research',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const profileOptions: SelectOption[] = [
  { label: 'Financial Research', value: 'financial_research' },
  { label: 'Web Research', value: 'web_research' },
  { label: 'Vision Analysis', value: 'vision_analysis' },
  { label: 'Document Extract', value: 'document_extract' },
  { label: 'Python Analysis', value: 'python_analysis' },
  { label: 'SQL Query', value: 'sql_query' },
  { label: 'Backtest', value: 'backtest' },
  { label: 'Data Pipeline', value: 'data_pipeline' },
  { label: 'Batch Eval', value: 'batch_eval' },
  { label: 'Scripted Test', value: 'scripted_test' },
  { label: 'Agent Automation', value: 'agent_automation' },
]
</script>
