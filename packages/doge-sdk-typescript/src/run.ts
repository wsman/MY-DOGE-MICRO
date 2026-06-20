export interface DogeEvent {
  id?: string
  type: string
  data: Record<string, unknown>
}

export class DogeApiError extends Error {
  readonly statusCode: number

  constructor(statusCode: number, message: string) {
    super(message)
    this.name = 'DogeApiError'
    this.statusCode = statusCode
  }
}
