# Sprint 038 - Watcher Slot Consumer Manifest

> Sprint: 038 (Watcher Slot Consumer)
> Date: 2026-07-07
> Status: Local implementation complete; verification passed.

## Scope

This manifest records local evidence for the watcher slot consumer sprint:
`watcher.runtime_events` contributes the default allow-only runtime event
watcher, and the slot-aware runtime factory composes watcher middleware behind
`DOGE_FEATURE_SLOT_PLATFORM` + `DOGE_FEATURE_SLOT_WATCHER`.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0047-watcher-slot-consumer.md` records the watcher-consumer decision. |
| CDD | `design/cdd/sprint-038-watcher-slot-consumer.md` records behavior, contracts, and acceptance criteria. |
| Runtime protocol | `src/doge/core/ports/runtime_services.py` adds `IRuntimeEventWatcher`. |
| Transition recorder seam | `src/doge/application/agent/transition_recorder.py` invokes watcher enforcement before outbox staging. |
| Watcher middleware | `src/doge/platform/runtime/watchers.py` adds `RuntimeEventWatcherMiddleware` and `WatcherDecisionError`. |
| Built-in watcher slot | `src/doge/platform/runtime/slot.py` adds `RuntimeEventWatcherSlot`. |
| Built-in registry | `src/doge/bootstrap/runtime_factories/slots.py` registers `RuntimeEventWatcherSlot`. |
| Watcher consumer | `src/doge/bootstrap/runtime_factories/slots.py` adds `build_slot_aware_runtime_event_watcher()`. |
| Runtime wiring | `src/doge/bootstrap/runtime_factories/runtime_kernel.py` injects watcher middleware into `TransitionRecorder` when slot platform is enabled. |
| Feature lifecycle | `src/doge/config/settings.py` adds `DOGE_FEATURE_SLOT_WATCHER`. |
| Capability discovery | `src/doge/application/capabilities/registry.py` exposes `feature.slot_watcher`. |
| Unit tests | `tests/unit/platform/slots/test_builtin_watcher_slot.py` covers manifest, contribution, middleware block, and unsupported action behavior. |
| Contract tests | `tests/contract/test_watcher_slot_parity.py` covers no-middleware flag posture, default parity, blocking rollback, and duplicate watcher fail-fast. |
| Slot discovery tests | `tests/cli/test_cli_slots.py`, `tests/cli/test_doged_cli.py`, and `tests/contract/test_slot_api.py` cover `watcher.runtime_events` status. |
| Session state | `production/session-state/active.md` records Sprint 038 as the current local implementation. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` adds the watcher slot consumer evidence record. |

## Verification Commands

```bash
py -3 -m pytest tests/unit/platform/slots/test_builtin_watcher_slot.py tests/contract/test_watcher_slot_parity.py tests/unit/agent/test_transition_recorder.py tests/cli/test_cli_slots.py tests/contract/test_slot_api.py tests/cli/test_doged_cli.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py -q
py -3 -m pytest tests/unit/platform/slots tests/contract/test_watcher_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_tool_registry_slot_parity.py -q
py -3 -m pytest tests/unit/agent/test_transition_recorder.py tests/unit/agent/test_runtime_transaction.py tests/unit/agent/test_runtime_kernel.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0047-watcher-slot-consumer.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-038-watcher-slot-consumer.md
py -3 scripts/validate_no_stale_counts.py
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## Verification Results

| Gate | Result |
|---|---|
| Focused watcher slot / parity / recorder / CLI / API / doged / settings / capability suite | Passed: 94 tests, 2 existing FastAPI deprecation warnings. |
| Broader slot/watchers regression suite | Passed: 86 tests. |
| Runtime recorder/kernel regression suite | Passed: 41 tests, 75 existing runtime deprecation warnings. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 105 markdown files. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0047 and Sprint 038 CDD. |
| Stale counts / ADR index / governance YAML | Passed. |
| Plan closure | Acceptable controlled-open: 4 open gates, 2 passed gates. |
| Whitespace | Passed in WSL Git and Windows Git. |

## Posture

- Production posture unchanged: `production_ready: false`,
  `stable_declaration: forbidden`, `level_3_sdk_platform: experimental`.
- No external/operator gates are closed by this sprint.
- No SDK package source, Web source, persistence schema, ModelRouter,
  ProfileRegistry, concrete watcher policy, lifecycle hook invocation, runtime
  permission/health enforcement, bundle activation, third-party slot install,
  signing, or enterprise allowlist is part of this sprint.
- Slot Platform remains experimental and feature-flagged off by default.
- Sprint 038 completes the watcher-facet consumer proof only; it does not
  complete the full OpenClaw-like Slot Platform.
