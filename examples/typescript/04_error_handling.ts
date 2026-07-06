import { DogeApiError, DogeClient } from 'doge-sdk'

const client = new DogeClient({
  baseUrl: process.env.DOGE_DAEMON_URL ?? 'http://127.0.0.1:8901',
  apiToken: process.env.DOGE_API_TOKEN,
})

try {
  await client.runs.get('run-does-not-exist')
} catch (error) {
  if (error instanceof DogeApiError) {
    console.log(`status=${error.statusCode}`)
    console.log(`message=${error.message}`)
  } else {
    throw error
  }
}
