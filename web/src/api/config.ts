import api from './client'

export async function getConfig() {
  const { data } = await api.get('/config')
  return data
}

export async function getSettings() {
  const { data } = await api.get('/config/settings')
  return data
}

export async function updateSettings(settings: { tdx_path?: string }) {
  const { data } = await api.put('/config/settings', settings)
  return data
}

export async function validateTdx(tdxPath: string) {
  const { data } = await api.post('/config/validate-tdx', { tdx_path: tdxPath })
  return data
}

// --- Server management ---

export interface ServerInfo {
  host: string
  port: number
  latency_ms: number | null
}

export interface ServerTestResult {
  host: string
  ok: boolean
  latency_ms: number | null
  error?: string
}

export async function getServers(): Promise<{ cn: ServerInfo[]; us: ServerInfo[] }> {
  const { data } = await api.get('/scan/servers')
  return data
}

export async function testServers(market: 'cn' | 'us'): Promise<{ results: ServerTestResult[] }> {
  const { data } = await api.post('/scan/servers/test', { market })
  return data
}
