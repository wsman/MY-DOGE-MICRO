export interface MacroReport {
  id: number
  date: string
  timestamp: string
  tags: string
  analyst: string
  risk_signal: string
  volatility: string
  content?: string
}

export interface ResearchReport {
  id: number
  date: string
  timestamp: string
  tags: string
  analyst: string
  title: string
  content?: string
}

export interface StockNote {
  id: number
  ticker: string
  market: string
  created_at: string
  note_type: string
  title: string | null
  content: string
  tags: string | null
}
