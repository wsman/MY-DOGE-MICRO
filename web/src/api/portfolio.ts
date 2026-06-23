import { DogeApiError } from '../../../packages/doge-sdk-typescript/src/run'

export interface ImportedPortfolio {
  portfolio_id: string
  name: string
  total_market_value: number
  holdings: Array<Record<string, unknown>>
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
