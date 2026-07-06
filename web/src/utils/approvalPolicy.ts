import type { WorkflowTemplate } from 'doge-sdk'

export interface PolicyRow {
  key: string
  label: string
  value: string
}

export type ApprovalPolicy = Record<string, string>

export function readTemplatePolicy(template: WorkflowTemplate | null | undefined): ApprovalPolicy | undefined {
  const metadata = asRecord(template?.metadata)
  const contract = asRecord(metadata.contract)
  const policy = asRecord(contract.approval_policy)
  const rows = Object.entries(policy).flatMap(([key, value]) => {
    const text = scalarText(value)
    return key && text ? [[key, text] as const] : []
  })
  return rows.length ? Object.fromEntries(rows) : undefined
}

export function formatPolicyRows(policy: ApprovalPolicy | undefined): PolicyRow[] {
  if (!policy) return []
  return Object.entries(policy)
    .filter(([key, value]) => key && value)
    .map(([key, value]) => ({
      key: `policy-${key}`,
      label: `Policy · ${key}`,
      value,
    }))
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function scalarText(value: unknown): string {
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return ''
}
