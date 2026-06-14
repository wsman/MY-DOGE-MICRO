export interface KlineData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
  ma_5?: number
  ma_10?: number
  ma_20?: number
  ma_60?: number
  atr_14?: number
}

export interface PaginatedResponse {
  columns: string[]
  rows: Record<string, unknown>[]
  total: number
  page: number
  page_size: number
}
