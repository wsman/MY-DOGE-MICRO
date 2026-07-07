import { describe, expect, it } from 'vitest'

import { panelsFor, visiblePanelIds, type ResearchPanelZone } from './panelRegistry'
import type { UiPanel } from '../api/platform'

describe('research panel registry', () => {
  it('keeps default Analyst panels visible while hiding Developer-only diagnostics', () => {
    const visible = visiblePanelIds({ mode: 'analyst' })

    expect(visible.has('guided_flow')).toBe(true)
    expect(visible.has('conclusion_evidence_matrix')).toBe(true)
    expect(visible.has('cost_eval_panel')).toBe(false)
    expect(visible.has('agent_timeline')).toBe(false)
  })

  it('shows Developer-only diagnostics in Developer mode', () => {
    const visible = visiblePanelIds({ mode: 'developer' })

    expect(visible.has('cost_eval_panel')).toBe(true)
    expect(visible.has('agent_timeline')).toBe(true)
  })

  it('orders panels by slot metadata within a zone', () => {
    const ids = panelsFor('research.input', { mode: 'analyst' }).map(panel => panel.panel_id)

    expect(ids.slice(0, 4)).toEqual([
      'guided_flow',
      'scenario_picker',
      'market_selector',
      'execution_profile_selector',
    ])
  })

  it('uses remote slot metadata when provided', () => {
    const panels: UiPanel[] = [
      uiPanel('run_action', 'research.input', 20),
      uiPanel('guided_flow', 'research.input', 10),
      uiPanel('agent_timeline', 'research.timeline', 10, ['developer']),
    ]

    expect(panelsFor('research.input', { mode: 'analyst', panels }).map(panel => panel.panel_id)).toEqual([
      'guided_flow',
      'run_action',
    ])
    expect(visiblePanelIds({ mode: 'analyst', panels }).has('agent_timeline')).toBe(false)
    expect(visiblePanelIds({ mode: 'developer', panels }).has('agent_timeline')).toBe(true)
  })
})

function uiPanel(
  panelId: UiPanel['panel_id'],
  zone: ResearchPanelZone,
  order: number,
  modes: string[] = ['analyst', 'developer'],
): UiPanel {
  return {
    panel_id: panelId,
    workspace: 'research_workspace',
    zone,
    component_module: `component:${panelId}`,
    order,
    modes,
    required_artifact_fields: [],
    label: panelId,
  }
}
