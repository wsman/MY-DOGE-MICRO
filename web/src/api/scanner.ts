import api from './client'

export async function startScan(market: 'cn' | 'us', tdxPath: string) {
  // SSE endpoint — use fetch directly for streaming
  const resp = await fetch(`/api/scan/${market}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tdx_path: tdxPath, use_server: true }),
  })
  return resp
}

export async function getScanStatus() {
  const { data } = await api.get('/scan/status')
  return data
}
