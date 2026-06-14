<template>
  <div class="scanner-view">
    <div class="scanner-header">
      <span class="scanner-title">Data Source Manager</span>
      <n-button size="tiny" quaternary @click="store.fetchServers">Refresh</n-button>
    </div>

    <!-- Server config rows -->
    <div class="config-sections">
      <!-- CN -->
      <div class="config-section cn-section">
        <div class="section-head">
          <span class="section-label cn-label">A-Share (CN)</span>
          <span v-if="store.lastCnScan" class="last-scan">last: {{ store.lastCnScan }}</span>
        </div>
        <div class="section-controls">
          <n-select
            size="small"
            :value="store.selectedCnServer"
            :options="cnServerOptions"
            :loading="store.cnTesting"
            placeholder="Auto (fastest)"
            :render-tag="renderServerTag"
            :render-label="renderServerLabel"
            consistent-menu-width
            style="flex: 1; min-width: 0"
            @update:value="v => store.selectedCnServer = v"
          />
          <n-button size="small" :loading="store.cnTesting" @click="store.doTestServers('cn')">
            Test
          </n-button>
          <n-button
            size="small"
            type="error"
            :loading="store.cnStatus === 'running'"
            :disabled="store.cnStatus === 'running'"
            @click="store.scanCn"
          >
            {{ store.cnStatus === 'error' ? '↻ Retry' : '▶ Scan' }}
          </n-button>
        </div>
        <div class="section-auto">
          <n-switch size="small" :value="store.cnAutoEnabled" @update:value="v => store.toggleAutoScan('cn', v)" />
          <span class="auto-text">Auto</span>
          <n-select
            size="tiny"
            :value="store.cnAutoInterval"
            @update:value="v => store.setInterval_('cn', v)"
            :options="intervalOptions"
            :disabled="!store.cnAutoEnabled"
            style="width: 90px"
          />
        </div>
      </div>

      <!-- US -->
      <div class="config-section us-section">
        <div class="section-head">
          <span class="section-label us-label">US Market</span>
          <span v-if="store.lastUsScan" class="last-scan">last: {{ store.lastUsScan }}</span>
        </div>
        <div class="section-controls">
          <n-select
            size="small"
            :value="store.selectedUsServer"
            :options="usServerOptions"
            :loading="store.usTesting"
            placeholder="Auto (fastest)"
            :render-tag="renderServerTag"
            :render-label="renderServerLabel"
            consistent-menu-width
            style="flex: 1; min-width: 0"
            @update:value="v => store.selectedUsServer = v"
          />
          <n-button size="small" :loading="store.usTesting" @click="store.doTestServers('us')">
            Test
          </n-button>
          <n-button
            size="small"
            type="info"
            :loading="store.usStatus === 'running'"
            :disabled="store.usStatus === 'running'"
            @click="store.scanUs"
          >
            {{ store.usStatus === 'error' ? '↻ Retry' : '▶ Scan' }}
          </n-button>
        </div>
        <div class="section-auto">
          <n-switch size="small" :value="store.usAutoEnabled" @update:value="v => store.toggleAutoScan('us', v)" />
          <span class="auto-text">Auto</span>
          <n-select
            size="tiny"
            :value="store.usAutoInterval"
            @update:value="v => store.setInterval_('us', v)"
            :options="intervalOptions"
            :disabled="!store.usAutoEnabled"
            style="width: 90px"
          />
        </div>
      </div>
    </div>

    <!-- Shared progress / log -->
    <div class="scanner-bottom">
      <div aria-live="polite">
        <n-progress
          v-if="store.isRunning"
          :percentage="store.progress"
          :indicator-placement="'inside'"
          processing
          style="margin-bottom: 6px"
        />
      </div>
      <!-- Terminal-error banner: a dropped stream surfaces here instead of an
           infinite spinner. The watchdog (useSSE.ts) guarantees isRunning is
           false when status==='error', so the n-progress above is hidden. -->
      <div role="alert" aria-live="assertive">
        <n-alert
          v-if="terminalError"
          type="error"
          :title="terminalError.title"
          style="margin-bottom: 6px"
          closable
        >
          {{ terminalError.message }}
          <n-button
            size="tiny"
            type="error"
            style="margin-left: 8px"
            @click="terminalError.retry()"
          >
            Retry
          </n-button>
        </n-alert>
      </div>
      <n-log
        :rows="8"
        :log="logText"
        language="log"
        trim
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted } from 'vue'
import { NButton, NProgress, NLog, NSwitch, NSelect, NAlert, type SelectOption } from 'naive-ui'
import { useScannerStore } from '../stores/scanner'
import type { ServerEntry } from '../stores/scanner'

const store = useScannerStore()

const logText = computed(() => store.messages.join('\n'))

/**
 * Terminal-error banner payload. Surfaced when a scan stream drops without a
 * terminal event and the watchdog trips (status === 'error'). CN takes
 * priority over US when both are errored (arbitrary but deterministic).
 * Returning null hides the banner when no market is in an error state.
 */
const terminalError = computed(() => {
  const err = store.error
  const detail = err && typeof err === 'object' && 'message' in err
    ? err.message
    : 'live data stream stalled'
  if (store.cnStatus === 'error') {
    return {
      title: 'A-Share (CN) scan failed',
      message: detail,
      retry: () => store.scanCn(),
    }
  }
  if (store.usStatus === 'error') {
    return {
      title: 'US Market scan failed',
      message: detail,
      retry: () => store.scanUs(),
    }
  }
  return null
})

const intervalOptions = [
  { label: '15 min', value: 15 },
  { label: '30 min', value: 30 },
  { label: '1 hour', value: 60 },
  { label: '4 hours', value: 240 },
  { label: 'Daily', value: 1440 },
]

// Sort servers: tested-ok first (by latency asc), then untested, then failed
function sortServers(servers: ServerEntry[]): ServerEntry[] {
  return [...servers].sort((a, b) => {
    const aOk = a.ok === true && a.latency_ms != null
    const bOk = b.ok === true && b.latency_ms != null
    if (aOk && !bOk) return -1
    if (!aOk && bOk) return 1
    if (aOk && bOk) return a.latency_ms! - b.latency_ms!
    // Both untested or both failed
    if (a.latency_ms != null && b.latency_ms != null) return a.latency_ms - b.latency_ms
    if (a.latency_ms != null) return -1
    if (b.latency_ms != null) return 1
    return 0
  })
}

function toOptions(servers: ServerEntry[]): SelectOption[] {
  const sorted = sortServers(servers)
  const auto: SelectOption = { label: 'Auto (fastest)', value: '' }
  const items: SelectOption[] = sorted.map(s => {
    const latency = s.latency_ms != null
      ? (s.ok ? `${s.latency_ms}ms` : '✗')
      : '-'
    return {
      label: `${s.host}  ${latency}`,
      value: s.host,
      // store raw data for custom rendering
      srv: s,
    } as SelectOption & { srv: ServerEntry }
  })
  return [auto, ...items]
}

const cnServerOptions = computed(() => toOptions(store.cnServers))
const usServerOptions = computed(() => toOptions(store.usServers))

// Custom renderers
function renderServerLabel(option: SelectOption) {
  const srv = (option as any).srv as ServerEntry | undefined
  if (!srv) {
    // Auto option
    return h('span', { style: 'opacity: 0.5; font-style: italic' }, 'Auto (fastest)')
  }
  const latencyText = srv.latency_ms != null
    ? (srv.ok ? `${srv.latency_ms}ms` : '✗')
    : ''
  const color = srv.ok === true ? 'var(--dgm-status-ok)' : srv.ok === false ? 'var(--dgm-status-fail)' : 'var(--dgm-status-unknown)'
  return h('div', { style: 'display: flex; justify-content: space-between; align-items: center; width: 100%; gap: 12px' }, [
    h('span', { style: 'font-family: var(--dgm-font-mono); font-size: 12px' }, srv.host),
    latencyText
      ? h('span', { style: `font-size: 11px; color: ${color}; flex-shrink: 0` }, latencyText)
      : null,
  ])
}

function renderServerTag({ option }: { option: SelectOption }) {
  return h('span', { style: 'font-size: 12px' },
    option.value ? String(option.value) : 'Auto'
  )
}

onMounted(() => store.fetchServers())
</script>

<style scoped>
.scanner-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.scanner-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  flex-shrink: 0;
}
.scanner-title {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* Config sections */
.config-sections {
  display: flex;
  gap: 10px;
  padding: 0 12px;
  flex-shrink: 0;
}
.config-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--dgm-border);
  border-radius: 6px;
  overflow: hidden;
}
.section-head {
  padding: 5px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
}
.cn-section .section-head { background: color-mix(in srgb, var(--dgm-market-cn) 12%, transparent); }
.us-section .section-head { background: color-mix(in srgb, var(--dgm-market-us) 12%, transparent); }
.cn-label { color: var(--dgm-market-cn); }
.us-label { color: var(--dgm-market-us); }
.last-scan { font-weight: 400; font-size: 11px; opacity: 0.5; }

.section-controls {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
}

.section-auto {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
  border-top: 1px solid var(--dgm-border);
  font-size: 12px;
}
.auto-text { opacity: 0.6; }

/* Bottom log */
.scanner-bottom {
  flex: 1;
  min-height: 120px;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
}
</style>
