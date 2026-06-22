<template>
  <div
    class="document-uploader"
    :class="{ dragging }"
    @dragenter.prevent="dragging = true"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="onDrop"
  >
    <input
      ref="input"
      class="file-input"
      type="file"
      multiple
      @change="onChange"
    >
    <n-button size="small" :loading="store.loading" @click="input?.click()">Upload</n-button>
    <span class="upload-copy">Drop research files here</span>
  </div>
  <n-alert v-if="store.error" class="upload-error" type="error" :show-icon="false">
    {{ store.error.message }}
  </n-alert>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NAlert, NButton } from 'naive-ui'
import { useDocumentStore } from '../../stores/documents'

const store = useDocumentStore()
const input = ref<HTMLInputElement | null>(null)
const dragging = ref(false)

async function onChange(event: Event) {
  const target = event.target as HTMLInputElement
  await uploadFiles(target.files)
  target.value = ''
}

async function onDrop(event: DragEvent) {
  dragging.value = false
  await uploadFiles(event.dataTransfer?.files ?? null)
}

async function uploadFiles(files: FileList | null) {
  if (!files?.length) return
  for (const file of Array.from(files)) {
    try {
      await store.upload(file)
    } catch {
      return
    }
  }
}
</script>

<style scoped>
.document-uploader {
  min-height: 48px;
  border: 1px dashed var(--dgm-border-strong);
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: var(--dgm-surface);
}

.document-uploader.dragging {
  border-color: var(--dgm-accent);
  background: var(--dgm-surface-hover);
}

.file-input {
  display: none;
}

.upload-copy {
  color: var(--dgm-text-faint);
  font-size: 12px;
}

.upload-error {
  margin-top: 8px;
}
</style>
