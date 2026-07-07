# Sprint 038 CDD: Watcher Slot Consumer

Status: Ready for Acceptance
Date: 2026-07-07

## 1. Overview

Sprint 038 makes the Slot Platform consume the `watcher` facet for runtime event
middleware.

The sprint adds a built-in `watcher.runtime_events` slot, a slot-aware runtime
event watcher middleware, and an optional `TransitionRecorder` dependency that
can block events before outbox staging and transaction commit.

The sprint does not implement concrete cost, secret-leak, citation, tenant, or
Python-executor policies.

## 2. User Promise / JTBD

A platform engineer can wire watcher slots into the runtime event stream without
turning them into prompt-visible tools.

A safety engineer can later add watchers that observe runtime events and block
high-risk state changes before those events are committed or published.

## 3. Detailed Behavior

- `IRuntimeEventWatcher` lives in `doge.core.ports.runtime_services`.
- `TransitionRecorder` accepts an optional `event_watcher`.
- The default watcher is no-op and preserves direct construction behavior.
- `TransitionRecorder.record()` invokes watcher enforcement after event append
  and before outbox staging.
- `RuntimeEventWatcherMiddleware` evaluates watcher contributions.
- Supported watcher actions:
  - `allow`: continue
  - `warn`: continue
  - `pause`: fail closed in this sprint
  - `block`: fail closed
  - `fail`: fail closed
- Blocking actions raise `WatcherDecisionError`.
- Unknown actions raise `SlotConfigurationError`.
- Watcher exceptions are converted to `WatcherDecisionError(action="fail")`.
- `build_slot_aware_runtime_event_watcher()` resolves watcher slots when their
  feature flags are on.
- Duplicate watcher IDs raise `SlotConfigurationError`.
- `watcher.runtime_events` contributes one allow-only watcher.
- CLI/API/doged slot discovery shows `watcher.runtime_events` as disabled until
  both slot feature flags are satisfied.

## 4. Contracts / Data Model

Runtime watcher protocol:

```python
class IRuntimeEventWatcher(Protocol):
    def enforce(self, event: AgentEvent) -> None:
        ...
```

Watcher contribution:

```python
WatcherContribution(
    watcher_id="watcher.runtime_events.allow_all",
    on_event=lambda event, context: WatcherDecision(action="allow"),
)
```

Feature flags:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_WATCHER=1
```

## 5. Edge Cases

- Slot platform off: runtime factory passes no watcher middleware.
- Slot platform on but slot watcher off: no watcher slot is resolved.
- Built-in watcher on: event append/outbox/commit/publish behavior is unchanged.
- Custom blocking watcher: transaction rolls back, outbox is not staged, and
  publisher is not called.
- Duplicate watcher ID: middleware assembly fails fast.
- Unsupported watcher action: configuration error before commit.

## 6. Dependencies

- ADR-0011 Agent Runtime Levels.
- ADR-0025 Runtime Streaming Semantics.
- ADR-0042 Slot Platform Foundation.
- ADR-0043 Slot Contribution Facets.
- ADR-0046 Governance Slot Consumer.
- Existing `TransitionRecorder` transaction boundary.
- Existing `WatcherContribution` facet.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; gates slot-aware runtime
  factory paths.
- `DOGE_FEATURE_SLOT_WATCHER`: default `false`; gates watcher slot resolution.

Both flags remain off by default.

## 8. Acceptance Criteria

- Built-in registry includes `watcher.runtime_events`.
- Watcher slot manifest/status is visible through `doge slots`, `doged slots`,
  and `/v1/slots`.
- Watcher slot remains disabled unless both slot flags are on.
- Slot-aware runtime event watcher middleware is assembled when enabled.
- Built-in watcher preserves event persistence, outbox staging, commit, and
  publish behavior.
- Custom watcher can block an event before outbox staging and publishing.
- Duplicate watcher IDs fail fast.
- Capability registry exposes slot watcher lifecycle metadata.
- No concrete cost/secret/citation/tenant/Python-executor watcher policy,
  permission/health enforcement, Web Slot Center, SDK slot client, persistence
  schema, SlotKernel, SlotBundle, SlotPolicy, SlotLoader, third-party install,
  signing, or enterprise allowlist is added.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## 9. Validation Plan

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

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-038-watcher-slot-consumer-manifest.md`.

## 11. Out of Scope

- Concrete cost, secret-leak, high-risk action, citation, tenant-boundary, or
  Python-executor watcher policies.
- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, and `SlotLoader`.
- Runtime permission/health enforcement and active health probes.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- Persistence schema, ModelRouter/ProfileRegistry, external auth, or worker
  behavior changes.
- Production readiness declaration or external/operator gate closure.
