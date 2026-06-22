import type { DogeEvent } from './run.js'

export async function* parseSse(stream: ReadableStream<Uint8Array>): AsyncGenerator<DogeEvent> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let eventId: string | undefined
  let eventType = 'message'
  let dataLines: string[] = []

  const flush = function* (): Generator<DogeEvent> {
    if (dataLines.length === 0) return
    const data = JSON.parse(dataLines.join('\n')) as Record<string, unknown>
    yield { id: eventId, type: eventType, data }
    eventId = undefined
    eventType = 'message'
    dataLines = []
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line === '') {
        yield* flush()
      } else if (line.startsWith('id:')) {
        eventId = line.slice(3).trim()
      } else if (line.startsWith('event:')) {
        eventType = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim())
      }
    }
  }
  yield* flush()
}
