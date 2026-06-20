import axios from 'axios'
import { DogeClient } from 'doge-sdk'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export default api

export const dogeClient = new DogeClient({ baseUrl: '' })
