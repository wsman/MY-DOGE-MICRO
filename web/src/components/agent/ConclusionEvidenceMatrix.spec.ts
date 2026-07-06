import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ConclusionEvidenceMatrix, {
  type ConclusionClaimDisplay,
  type ConclusionEvidenceRef,
} from './ConclusionEvidenceMatrix.vue'

describe('ConclusionEvidenceMatrix', () => {
  it('renders claim rows with support tags and evidence chips', () => {
    const claims: ConclusionClaimDisplay[] = [
      claim({
        claim_id: 'claim-1',
        claim_text: 'Revenue growth was supported by accelerator demand.',
        status: 'supported',
        numeric_check_status: 'passed',
        risk_level: 'low',
        evidence_refs: [
          evidence({
            key: 'evd-1',
            evidence_id: 'evd-1',
            source: 'annual report p.3',
            snippet: 'Revenue grew 18%.',
          }),
        ],
      }),
      claim({
        claim_id: 'claim-2',
        claim_text: 'Margin pressure is unresolved.',
        status: 'partial',
        numeric_check_status: 'not_checked',
        risk_level: 'medium',
        evidence_refs: [],
      }),
    ]

    const wrapper = mount(ConclusionEvidenceMatrix, {
      props: { claims },
    })

    expect(wrapper.text()).toContain('Revenue growth was supported by accelerator demand.')
    expect(wrapper.text()).toContain('supported')
    expect(wrapper.text()).toContain('passed')
    expect(wrapper.text()).toContain('low')
    expect(wrapper.find('.evidence-chip').text()).toBe('annual report p.3')
    expect(wrapper.text()).toContain('Margin pressure is unresolved.')
    expect(wrapper.text()).toContain('No evidence')
  })

  it('emits the selected evidence with its owning claim id', async () => {
    const ref = evidence({
      key: 'evd-cash',
      evidence_id: 'evd-cash',
      source: 'cash-flow-report p.8',
      snippet: 'Operating cash flow covered net income.',
    })
    const wrapper = mount(ConclusionEvidenceMatrix, {
      props: {
        claims: [
          claim({
            claim_id: 'claim-cash',
            claim_text: 'Operating cash flow covered net income.',
            evidence_refs: [ref],
          }),
        ],
      },
    })

    await wrapper.find('.evidence-chip').trigger('click')

    expect(wrapper.emitted('select-evidence')?.[0]).toEqual([
      {
        claimId: 'claim-cash',
        ref,
      },
    ])
  })
})

function claim(overrides: Partial<ConclusionClaimDisplay>): ConclusionClaimDisplay {
  return {
    claim_id: 'claim',
    claim_text: 'Claim text',
    status: 'supported',
    numeric_check_status: 'not_applicable',
    risk_level: 'low',
    evidence_refs: [],
    ...overrides,
  }
}

function evidence(overrides: Partial<ConclusionEvidenceRef>): ConclusionEvidenceRef {
  return {
    key: 'evd',
    label: 'Evidence',
    source: 'source',
    snippet: 'snippet',
    ...overrides,
  }
}
