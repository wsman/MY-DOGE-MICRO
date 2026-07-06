import { DogeClient } from 'doge-sdk'

const runId = process.env.DOGE_RUN_ID
if (!runId) throw new Error('DOGE_RUN_ID is required')

const client = new DogeClient({
  baseUrl: process.env.DOGE_DAEMON_URL ?? 'http://127.0.0.1:8901',
  apiToken: process.env.DOGE_API_TOKEN,
})

for await (const event of client.runs.stream(runId)) {
  console.log(event.type, event.data)
}

const run = await client.runs.get(runId)
const pending = run.approvals.filter(item => item.status === 'pending')
if (pending.length > 0) {
  await client.runs.resume(runId, { approvalId: pending[0].approval_id, approved: true })
  console.log(`approved=${pending[0].approval_id}`)
}
