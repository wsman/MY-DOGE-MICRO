import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useSSE } from '../composables/useSSE'
import type { SSEError } from '../composables/useSSE'
import { getServers, testServers } from '../api/config'
import type { ServerTestResult } from '../api/config'

const STORAGE_KEY = 'my-doge-scanner-settings'

export interface ServerEntry {
  host: string
  port: number
  latency_ms: number | null
  ok?: boolean
  testing?: boolean
}

interface AutoSettings {
  cnEnabled: boolean
  usEnabled: boolean
  cnInterval: number
  usInterval: number
  selectedCnServer: string | null
  selectedUsServer: string | null
}

function loadSettings(): AutoSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return {
    cnEnabled: false, usEnabled: false,
    cnInterval: 30, usInterval: 30,
    selectedCnServer: null, selectedUsServer: null,
  }
}

export const useScannerStore = defineStore('scanner', () => {
  const { progress, messages, isRunning, error, status, start } = useSSE()

  // -- Server state --
  const cnServers = ref<ServerEntry[]>([])
  const usServers = ref<ServerEntry[]>([])
  const selectedCnServer = ref<string | null>(null)
  const selectedUsServer = ref<string | null>(null)
  const cnTesting = ref(false)
  const usTesting = ref(false)

  // -- Auto scan --
  const cnAutoEnabled = ref(false)
  const usAutoEnabled = ref(false)
  const cnAutoInterval = ref(30) // minutes
  const usAutoInterval = ref(30)
  const lastCnScan = ref<string | null>(null)
  const lastUsScan = ref<string | null>(null)
  const cnStatus = ref<'idle' | 'running' | 'error'>('idle')
  const usStatus = ref<'idle' | 'running' | 'error'>('idle')

  // Timer handles
  let cnTimer: ReturnType<typeof setInterval> | null = null
  let usTimer: ReturnType<typeof setInterval> | null = null

  // -- Persistence --
  function saveSettings() {
    const s: AutoSettings = {
      cnEnabled: cnAutoEnabled.value,
      usEnabled: usAutoEnabled.value,
      cnInterval: cnAutoInterval.value,
      usInterval: usAutoInterval.value,
      selectedCnServer: selectedCnServer.value,
      selectedUsServer: selectedUsServer.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
  }

  function restoreSettings() {
    const s = loadSettings()
    cnAutoEnabled.value = s.cnEnabled
    usAutoEnabled.value = s.usEnabled
    cnAutoInterval.value = s.cnInterval
    usAutoInterval.value = s.usInterval
    selectedCnServer.value = s.selectedCnServer
    selectedUsServer.value = s.selectedUsServer
  }

  // -- Server API --
  async function fetchServers() {
    try {
      const data = await getServers()
      cnServers.value = data.cn.map(s => ({ ...s }))
      usServers.value = data.us.map(s => ({ ...s }))
    } catch { /* ignore */ }
  }

  async function doTestServers(market: 'cn' | 'us') {
    const testingRef = market === 'cn' ? cnTesting : usTesting
    const serversRef = market === 'cn' ? cnServers : usServers
    testingRef.value = true
    try {
      const { results } = await testServers(market)
      // Update servers with test results
      const resultMap = new Map<string, ServerTestResult>()
      results.forEach(r => resultMap.set(r.host, r))
      serversRef.value = serversRef.value.map(s => {
        const r = resultMap.get(s.host)
        if (r) return { ...s, latency_ms: r.latency_ms, ok: r.ok }
        return s
      })
    } catch { /* ignore */ }
    testingRef.value = false
  }

  // -- Scan --
  // Scan is operator-initiated and idempotent: a dropped scan surfaces a
  // terminal error + Retry affordance; we do NOT auto-reconnect (a retry is an
  // explicit operator action). See ADR-0008 watchdog amendment.
  async function scanCn() {
    // Reset any prior terminal-error state so the spinner shows on Retry.
    cnStatus.value = 'running'
    lastCnScan.value = new Date().toLocaleTimeString()
    await start('/api/scan/cn', {
      tdx_path: '',
      use_server: true,
      server: selectedCnServer.value,
    }, {
      onComplete: () => { cnStatus.value = 'idle' },
      onError: (_err: SSEError) => {
        // Terminal failure — surface it (do NOT silently reset to 'idle').
        cnStatus.value = 'error'
        // Stop the auto-scan timer so the next tick doesn't silently restart
        // into another stuck stream.
        stopAutoScan('cn')
      },
    })
  }

  async function scanUs() {
    usStatus.value = 'running'
    lastUsScan.value = new Date().toLocaleTimeString()
    await start('/api/scan/us', {
      tdx_path: '',
      use_server: true,
      server: selectedUsServer.value,
    }, {
      onComplete: () => { usStatus.value = 'idle' },
      onError: (_err: SSEError) => {
        usStatus.value = 'error'
        stopAutoScan('us')
      },
    })
  }

  // -- Auto scan timers --
  function startAutoScan(market: 'cn' | 'us') {
    stopAutoScan(market)
    const interval = market === 'cn' ? cnAutoInterval : usAutoInterval
    const scanFn = market === 'cn' ? scanCn : scanUs
    const statusRef = market === 'cn' ? cnStatus : usStatus
    cnTimer = setInterval(() => {
      if (statusRef.value !== 'running') scanFn()
    }, interval.value * 60 * 1000)
  }

  function stopAutoScan(market: 'cn' | 'us') {
    if (market === 'cn' && cnTimer) {
      clearInterval(cnTimer)
      cnTimer = null
    }
    if (market === 'us' && usTimer) {
      clearInterval(usTimer)
      usTimer = null
    }
  }

  function toggleAutoScan(market: 'cn' | 'us', enabled: boolean) {
    if (market === 'cn') cnAutoEnabled.value = enabled
    else usAutoEnabled.value = enabled
    if (enabled) startAutoScan(market)
    else stopAutoScan(market)
    saveSettings()
  }

  function setInterval_(market: 'cn' | 'us', minutes: number) {
    if (market === 'cn') cnAutoInterval.value = minutes
    else usAutoInterval.value = minutes
    // Restart timer if auto is enabled
    const enabled = market === 'cn' ? cnAutoEnabled.value : usAutoEnabled.value
    if (enabled) startAutoScan(market)
    saveSettings()
  }

  // Watch server selection changes and persist
  watch([selectedCnServer, selectedUsServer], () => saveSettings())

  // Restore on init
  restoreSettings()
  // Start auto timers if they were enabled
  if (cnAutoEnabled.value) startAutoScan('cn')
  if (usAutoEnabled.value) startAutoScan('us')

  return {
    progress, messages, isRunning, error, status,
    cnServers, usServers, selectedCnServer, selectedUsServer,
    cnTesting, usTesting,
    cnAutoEnabled, usAutoEnabled, cnAutoInterval, usAutoInterval,
    lastCnScan, lastUsScan,
    cnStatus, usStatus,
    fetchServers, doTestServers,
    scanCn, scanUs,
    toggleAutoScan, setInterval_: setInterval_,
  }
})
