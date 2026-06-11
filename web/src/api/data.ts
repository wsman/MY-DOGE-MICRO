import api from './client'
import type { PaginatedResponse, KlineData } from '../types/stock'

export async function listTables(market: string) {
  const { data } = await api.get(`/data/${market}/tables`)
  return data.tables as string[]
}

export async function queryTable(
  market: string, table: string,
  page = 1, pageSize = 50, search?: string
) {
  const { data } = await api.get<PaginatedResponse>(
    `/data/${market}/table/${table}`,
    { params: { page, page_size: pageSize, search } }
  )
  return data
}

export async function getKline(market: string, ticker: string, days = 120) {
  const { data } = await api.get<{ data: KlineData[] }>(
    `/data/${market}/ticker/${ticker}/kline`,
    { params: { days } }
  )
  return data.data
}

export async function fetchTickerNames(market: string): Promise<Record<string, string>> {
  const { data } = await api.get<{ names: Record<string, string>; count: number }>(
    `/data/${market}/ticker-names`
  )
  return data.names
}
