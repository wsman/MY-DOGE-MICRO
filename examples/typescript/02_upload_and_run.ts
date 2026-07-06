import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { basename, dirname, isAbsolute, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { DogeClient } from 'doge-sdk'

const client = new DogeClient({
  baseUrl: process.env.DOGE_DAEMON_URL ?? 'http://127.0.0.1:8901',
  apiToken: process.env.DOGE_API_TOKEN,
})

const scriptDir = dirname(fileURLToPath(import.meta.url))

function sampleDocPath(): string {
  const raw = process.env.DOGE_SAMPLE_DOC
  if (!raw) return resolve(scriptDir, '../../README.md')
  if (isAbsolute(raw) || existsSync(raw)) return raw
  const scriptRelative = resolve(scriptDir, raw)
  if (existsSync(scriptRelative)) return scriptRelative
  const repoRelative = resolve(scriptDir, '../..', raw)
  if (existsSync(repoRelative)) return repoRelative
  return raw
}

const source = sampleDocPath()
const file = new Blob([await readFile(source)], { type: 'text/markdown' })
const document = await client.documents.upload(file, basename(source))
const session = await client.sessions.create('Document-backed research')
const runId = await session.run('Summarize the uploaded document and identify evidence gaps.', {
  document_ids: [document.document_id],
  workflow: 'investment_research',
})

console.log(`run_id=${runId}`)
