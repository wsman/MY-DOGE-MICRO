import { describe, expect, it } from 'vitest'

import { formatPolicyRows, readTemplatePolicy } from './approvalPolicy'

describe('approvalPolicy', () => {
  it('reads approval policy from template metadata contract', () => {
    const policy = readTemplatePolicy({
      metadata: {
        contract: {
          approval_policy: {
            publish: 'required',
            trade_action: 'optional',
            numeric: 1,
            active: true,
          },
        },
      },
    } as never)

    expect(policy).toEqual({
      publish: 'required',
      trade_action: 'optional',
      numeric: '1',
      active: 'true',
    })
  })

  it('returns undefined when policy path is absent or not an object', () => {
    expect(readTemplatePolicy(undefined)).toBeUndefined()
    expect(readTemplatePolicy({ metadata: {} } as never)).toBeUndefined()
    expect(readTemplatePolicy({ metadata: { contract: { approval_policy: 'required' } } } as never)).toBeUndefined()
  })

  it('ignores nested policy values that cannot be rendered honestly', () => {
    const policy = readTemplatePolicy({
      metadata: {
        contract: {
          approval_policy: {
            publish: 'required',
            nested: { mode: 'required' },
            list: ['required'],
            blank: ' ',
          },
        },
      },
    } as never)

    expect(policy).toEqual({ publish: 'required' })
  })

  it('formats policy rows for approval detail rendering', () => {
    expect(formatPolicyRows({ publish: 'required', trade_action: 'optional' })).toEqual([
      { key: 'policy-publish', label: 'Policy · publish', value: 'required' },
      { key: 'policy-trade_action', label: 'Policy · trade_action', value: 'optional' },
    ])
    expect(formatPolicyRows(undefined)).toEqual([])
  })
})
