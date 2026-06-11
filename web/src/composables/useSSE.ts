import { ref } from 'vue'

interface SSEOptions {
  onProgress?: (pct: number, msg: string) => void
  onComplete?: () => void
  onError?: (msg: string) => void
}

export function useSSE() {
  const progress = ref(0)
  const messages = ref<string[]>([])
  const isRunning = ref(false)
  const error = ref<string | null>(null)

  async function start(url: string, body: object, opts: SSEOptions = {}) {
    progress.value = 0
    messages.value = []
    isRunning.value = true
    error.value = null

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(`HTTP ${resp.status}: ${text}`)
      }

      const reader = resp.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data:')) {
            try {
              const payload = JSON.parse(line.slice(5).trim())
              const pct = payload.progress ?? 0
              const msg = payload.message ?? ''

              if (pct === -1) {
                error.value = msg
                opts.onError?.(msg)
              } else {
                progress.value = pct
                messages.value.push(msg)
                opts.onProgress?.(pct, msg)

                if (pct >= 100) {
                  opts.onComplete?.()
                }
              }
            } catch {
              // skip malformed data lines
            }
          }
        }
      }
    } catch (e: unknown) {
      error.value = String(e)
      opts.onError?.(String(e))
    } finally {
      isRunning.value = false
    }
  }

  return { progress, messages, isRunning, error, start }
}
