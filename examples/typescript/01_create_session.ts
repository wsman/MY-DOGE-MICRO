import { DogeClient } from 'doge-sdk'

const client = new DogeClient({
  baseUrl: process.env.DOGE_DAEMON_URL ?? 'http://127.0.0.1:8901',
  apiToken: process.env.DOGE_API_TOKEN,
})

const session = await client.sessions.create('Cookbook research session')
console.log(`session_id=${session.sessionId}`)
