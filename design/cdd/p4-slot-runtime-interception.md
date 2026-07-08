# P4 CDD: Slot Runtime Permission Interception

Status: Ready for Acceptance / Local Verification Passed
Date: 2026-07-08

## 1. Overview

P4 adds a default-off runtime permission interception layer for built-in
slot-aware execution and hardens the optional Python analysis subprocess.

The work introduces `DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION`, a context-var
slot permission scope, port guards for secrets/database/network access, a slot
runtime executor port, and subprocess env/cwd hardening.

P4 does not add provider entrypoint execution, filesystem mediation,
OS/container/WASM sandboxing, marketplace behavior, external gate closure, or
production-readiness changes.

## 2. User Promise / JTBD

A platform engineer can enable runtime interception locally and verify that
slot `permissions` are enforced while built-in slot code uses known ports.

A security reviewer can inspect denied db/secret/network access with an audit
payload that names the slot, attempted resource, and declared permission.

A future P5 provider-execution effort has a tested in-process guard seam and a
clear list of remaining sandbox gaps.

## 3. Detailed Behavior

- `DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION` defaults to `false`.
- Capability discovery exposes `feature.slot_runtime_interception`.
- `current_slot_permissions()` returns the active slot permissions inside a
  scoped slot call and `None` outside slot execution.
- Flag off: guards are no-ops and legacy behavior is preserved.
- No slot context: guards allow access to preserve facade and legacy paths.
- Secret guard:
  - allows `get_secret(name)` only when `name` is in
    `permissions.secrets`;
  - raises `SlotPermissionViolation` and audits otherwise.
- Database guard:
  - classifies methods by read/write prefixes;
  - `database=none` denies all guarded DB-port calls;
  - `database=read` allows reads and denies writes;
  - `database=write` allows reads and writes.
- Network guard:
  - denies guarded `chat`, `connect`, and `download_kline` calls unless
    `network=allow`.
- Tool slot executors run under slot permission context.
- Model slots receive a guarded secret provider and return slot-scoped,
  network-guarded backends.
- Data slots return slot-scoped, network-guarded data sources.
- Subprocess Python analysis runs in a scratch cwd and with secret-bearing env
  variables removed.

## 4. Contracts / Data Model

Feature flag:

```text
DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION=1
```

Runtime context:

```python
with slot_permission_context("model.kimi_agent_sdk", manifest.permissions):
    ...
```

Violation audit:

```yaml
event_type: slot_permission_violation
resource_type: db | secret | network
metadata:
  slot_id: model.kimi_agent_sdk
  declared: ...
  attempted: ...
  action: ...
```

Maturity posture:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 5. Edge Cases

- Guarded access without slot context is allowed for compatibility.
- Flag-off guarded access is allowed for rollback.
- A denied guard still raises even if audit append fails.
- Async model backends retain slot context while their async generator is
  consumed.
- DB method classification is conservative but not a substitute for OS-level
  isolation.
- Direct calls to `os`, `sqlite3`, `socket`, or filesystem APIs bypass P4
  unless they go through guarded ports.
- Windows subprocess hardening is a soft boundary.

## 6. Dependencies

- ADR-0042 Slot Platform Foundation.
- ADR-0055 Slot Permission and Health Enforcement.
- ADR-0062 Slot Cryptographic Signing.
- Existing ToolRegistry, SlotKernel, SlotContext, ToolApplicationService, and
  SubprocessCodeExecutor seams.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION`: default `false`; enables P4
  in-process runtime guards for built-in slot-aware execution.
- `DOGE_FEATURE_SLOT_ENFORCEMENT`: remains default `false`; controls
  SlotKernel resolution-time admission, not per-call runtime resource access.
- `DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED`: remains default `false`; P4 only
  hardens subprocess behavior when an operator explicitly enables Python
  analysis.

## 8. Acceptance Criteria

- `SlotPermissionContext`, `SlotPermissionViolation`, runtime guard wrappers,
  and `SandboxedSlotRuntimeExecutor` are exported from `doge.platform.slots`.
- `ISlotRuntimeExecutor` and `DisabledSlotRuntimeExecutor` are available in
  core ports.
- Runtime interception flag is present in settings, lifecycle metadata, and
  capability discovery.
- Secret, DB, and network guards allow declared access and deny undeclared
  access with audit payloads.
- Slot-aware tool, model, and data paths set slot context before runtime port
  access.
- Subprocess Python analysis strips secret env vars and uses a scratch cwd.
- Existing slot boundary, parity, enforcement, install, settings, and
  capability tests remain green.
- No provider execution, filesystem mediation, OS/container/WASM sandboxing,
  marketplace, remote CI promotion, external gate closure, or maturity
  promotion is added.

## 9. Validation Plan

```bash
py -3 -m pytest tests/unit/platform/slots/test_slot_runtime_access.py tests/unit/capabilities/test_code_executor.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py -q
py -3 -m pytest tests/unit/architecture/test_slot_boundary.py tests/contract/test_tool_registry_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_agent_backends_slot_parity.py -q
py -3 -m pytest tests/unit/platform/slots/test_slot_enforcement.py tests/unit/platform/slots/test_slot_install.py tests/cli/test_cli_slots.py -q
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0063-slot-runtime-permission-interception.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/p4-slot-runtime-interception.md
py -3 scripts/validate_alpha_maturity_honesty.py --file C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Local verification passed and is recorded in
`production/qa/evidence/slot-runtime-interception-local-acceptance-2026-07-08.md`.

- Focused runtime/subprocess/settings/capability suite: 53 tests.
- Slot boundary and tool/data/model parity suite: 33 tests.
- Existing slot enforcement/install/CLI/facet regression suite: 83 tests with
  2 known FastAPI deprecation warnings.
- Python full regression: 2167 passed, 8 skipped, 128 warnings.
- Web suite: 168 tests passed; build passed.
- TypeScript SDK: 17 tests passed; build passed.
- SDK contract: 15 surfaces / 15 entity parity checks.
- Import boundaries, docs authority, docs links, docs maturity claims,
  governance YAML, ADR index, ADR/CDD/evidence/source-plan maturity honesty,
  acceptable-open plan closure, and WSL/Windows whitespace checks passed.
- Closure posture remains intentionally open for operator-owned external gates:
  2 passed, 4 open, 0 failed, 0 invalid.

## 11. Out of Scope

- Third-party provider entrypoint execution.
- Filesystem mediation.
- OS/container/WASM sandboxing.
- Strong malicious-code containment.
- Marketplace, HTTP install API, SDK install API, and YAML manifest parser.
- Remote CI assertion, latest remotely verified SHA promotion, external gate
  closure, or production readiness declaration.
