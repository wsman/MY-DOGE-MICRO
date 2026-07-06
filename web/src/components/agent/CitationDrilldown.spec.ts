import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'

import CitationDrilldown, { type CitationRecord } from './CitationDrilldown.vue'

describe('CitationDrilldown', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('emits the selected record and renders controlled details', async () => {
    const record: CitationRecord = {
      key: 'evd-controlled',
      label: 'Evidence controlled',
      source: 'controlled source',
      snippet: 'Controlled evidence snippet.',
      document_id: 'doc-controlled',
      page_number: 12,
      evidence_id: 'evd-controlled',
    }

    const wrapper = mount(CitationDrilldown, {
      attachTo: document.body,
      props: {
        records: [record],
        modelValue: null,
      },
    })

    expect(wrapper.find('.citation-row').text()).toContain('Evidence controlled')
    await wrapper.find('.citation-row').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([record])

    await wrapper.setProps({ modelValue: record })
    await nextTick()

    expect(document.body.textContent).toContain('controlled source')
    expect(document.body.textContent).toContain('doc-controlled')
    expect(document.body.textContent).toContain('12')
    expect(document.body.textContent).toContain('Controlled evidence snippet.')

    wrapper.unmount()
  })

  it('keeps the uncontrolled artifact/event/memo scan behavior', async () => {
    const wrapper = mount(CitationDrilldown, {
      attachTo: document.body,
      props: {
        memo: 'Memo cites evd-memo',
        artifacts: [
          {
            artifact_id: 'art-1',
            kind: 'investment_memo',
            title: 'Memo',
            content: '# Memo',
            run_id: 'run-1',
            data: {
              citations: [
                {
                  evidence_id: 'evd-artifact',
                  source: 'artifact source',
                  document_id: 'doc-artifact',
                  page_number: 4,
                  snippet: 'Artifact citation snippet.',
                },
              ],
            },
            created_at: 'now',
          },
        ],
        events: [
          {
            event_id: 'evt-1',
            run_id: 'run-1',
            event_type: 'tool_result',
            payload: {
              result: {
                data: {
                  results: [
                    {
                      evidence_id: 'evd-event',
                      source: 'event source',
                      snippet: 'Event citation snippet.',
                    },
                  ],
                },
              },
            },
            sequence: 1,
            schema_version: '1.0',
            created_at: 'now',
          },
        ],
      },
    })

    const rows = wrapper.findAll('.citation-row')
    expect(rows.map(row => row.text()).join(' ')).toContain('evd-artifact')
    expect(rows.map(row => row.text()).join(' ')).toContain('evd-event')
    expect(rows.map(row => row.text()).join(' ')).toContain('evd-memo')

    await rows[0].trigger('click')
    await nextTick()

    expect(document.body.textContent).toContain('Artifact citation snippet.')

    wrapper.unmount()
  })
})
