import { DogeApiError } from 'doge-sdk'

export interface ImportedPortfolio {
  portfolio_id: string
  name: string
  total_market_value: number
  holdings: Array<Record<string, unknown>>
  summary?: PortfolioSummary
}

export interface PortfolioSummary {
  portfolio_id: string
  name: string
  total_market_value: number
  holdings_count: number
  top_concentration: PortfolioSummaryHolding[]
  by_sector: PortfolioSummaryExposure[]
  missing_prices: PortfolioMissingPrice[]
  suggested_run: PortfolioSuggestedRun
}

export interface PortfolioSummaryHolding {
  symbol: string
  asset_class: string
  sector: string
  market_value: number
  weight: number
}

export interface PortfolioSummaryExposure {
  name: string
  market_value: number
  weight: number
}

export interface PortfolioMissingPrice {
  symbol: string
  reason: string
}

export interface PortfolioSuggestedRun {
  workflow: string
  question: string
}

export async function uploadPortfolioCsv(
  file: File,
  options: { name?: string; portfolioId?: string } = {},
): Promise<ImportedPortfolio> {
  const form = new FormData()
  form.append('file', file, file.name)
  if (options.name) form.append('name', options.name)
  if (options.portfolioId) form.append('portfolio_id', options.portfolioId)
  const response = await fetch('/v1/portfolios/import', {
    method: 'POST',
    body: form,
  })
  if (!response.ok) {
    let message = response.statusText
    try {
      const payload = await response.json() as { error?: { message?: string }, detail?: string }
      message = payload.error?.message ?? payload.detail ?? message
    } catch {
      message = await response.text()
    }
    throw new DogeApiError(response.status, message)
  }
  return await response.json() as ImportedPortfolio
}
