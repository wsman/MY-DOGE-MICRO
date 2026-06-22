# Research Agent Doged Reconnect Smoke

Generated: 2026-06-21T23:00:53.134212+00:00
Result: PASSED

## Scope

This smoke starts a real local doged daemon, starts the Vite Research Agent UI,
drives Chrome through the ResearchAgentView, forces the first SSE stream to
drop after one complete event, and verifies browser reconnect with
`Last-Event-ID` before completing the approval path.

It is browser-level automated evidence. It does not replace a true manual
operator interruption session or screen-reader pass.

## Observed

- Run ID: `run-b4739e0dd7b2`
- Final status: `completed`
- Stream Last-Event-ID headers: `[None, '1', '14']`
- Forced disconnects: `1`
- Event types: `['run_created', 'run_queued', 'model_response', 'tool_call', 'tool_result', 'model_response', 'tool_call', 'tool_result', 'model_response', 'tool_call', 'tool_result', 'approval_requested', 'approval_resolved', 'run_queued', 'model_response', 'artifact_created']`
- Screenshot: `production\qa\evidence\manual\research-agent-doged-reconnect-2026-06-22.png`

## Checks

| Check | Result |
|---|---|
| research_agent_view_loaded | PASS |
| first_stream_forced_disconnect_after_event | PASS |
| browser_reconnected_with_last_event_id | PASS |
| approval_path_completed_after_reconnect | PASS |
| no_duplicate_run_events_in_final_fetch | PASS |
| single_terminal_artifact_event | PASS |
