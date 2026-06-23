<template>
  <section class="panel" aria-labelledby="template-config-title">
    <div id="template-config-title" class="section-title">Template</div>
    <n-select
      v-model:value="selectedTemplateId"
      size="small"
      :options="templateOptions"
      placeholder="Choose template"
      aria-label="Workflow template"
      :input-props="{ 'aria-label': 'Workflow template' }"
    />
    <n-input
      v-model:value="question"
      size="small"
      placeholder="Question"
      aria-label="Execution question"
      :input-props="{ 'aria-label': 'Execution question' }"
    />
    <n-input
      v-model:value="inputsText"
      type="textarea"
      :autosize="{ minRows: 5, maxRows: 8 }"
      placeholder="{ &quot;ticker&quot;: &quot;NVDA&quot; }"
      aria-label="Template inputs"
      :input-props="{ 'aria-label': 'Template inputs' }"
    />
    <n-alert v-if="parseError" type="warning" :show-icon="false">{{ parseError }}</n-alert>
    <div class="actions">
      <n-button size="small" :disabled="!canSubmit" @click="emitPreflight">Preflight</n-button>
      <n-button size="small" type="primary" :disabled="!canSubmit" @click="emitExecute">Execute</n-button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NAlert, NButton, NInput, NSelect } from 'naive-ui'
import type { WorkflowTemplate } from '../../types/platform'

const props = defineProps<{ templates: WorkflowTemplate[] }>()
const emit = defineEmits<{
  preflight: [payload: { template_id: string; question: string; inputs: Record<string, unknown> }]
  execute: [payload: { template_id: string; question: string; inputs: Record<string, unknown> }]
}>()

const selectedTemplateId = ref<string | null>(null)
const question = ref('')
const inputsText = ref('{}')
const parseError = ref('')

const templateOptions = computed(() => props.templates.map(template => ({
  label: `${template.name} · ${template.slug}`,
  value: template.template_id,
})))
const canSubmit = computed(() => Boolean(selectedTemplateId.value) && !parseError.value)

function parsedInputs(): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(inputsText.value || '{}')
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      parseError.value = ''
      return parsed as Record<string, unknown>
    }
    parseError.value = 'Inputs must be a JSON object'
    return null
  } catch {
    parseError.value = 'Inputs must be valid JSON'
    return null
  }
}

function emitPreflight() {
  const inputs = parsedInputs()
  if (!selectedTemplateId.value || !inputs) return
  emit('preflight', {
    template_id: selectedTemplateId.value,
    question: question.value.trim(),
    inputs,
  })
}

function emitExecute() {
  const inputs = parsedInputs()
  if (!selectedTemplateId.value || !inputs) return
  emit('execute', {
    template_id: selectedTemplateId.value,
    question: question.value.trim(),
    inputs,
  })
}
</script>

<style scoped>
.panel {
  display: grid;
  gap: 8px;
}

.section-title {
  color: var(--dgm-text-faint);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
