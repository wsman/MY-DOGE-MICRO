import { readFile } from 'node:fs/promises'
import { basename } from 'node:path'

import { DogeClient } from 'doge-sdk'

const client = new DogeClient({
  baseUrl: process.env.DOGE_DAEMON_URL ?? 'http://127.0.0.1:8901',
  apiToken: process.env.DOGE_API_TOKEN,
})

const source = process.env.DOGE_SAMPLE_DOC ?? 'README.md'
const file = new Blob([await readFile(source)], { type: 'text/markdown' })
const document = await client.documents.upload(file, basename(source))
const session = await client.sessions.create('Document-backed research')
const runId = await session.run('Summarize the uploaded document and identify evidence gaps.', {
  document_ids: [document.document_id],
  workflow: 'investment_research',
})

console.log(`run_id=${runId}`)
