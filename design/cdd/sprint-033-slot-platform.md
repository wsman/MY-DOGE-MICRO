# Sprint 033 CDD: Slot Platform Foundation

Status: Ready for Acceptance
Date: 2026-07-06

## 1. Overview

Sprint 033 introduces the Slot Platform Foundation: a declarative slot contract
(`SlotManifest` v1 plus `ISlot`/`SlotContribution`/`SlotContext`/`SlotRegistry`) and
one built-in tool slot (`market.core`) wired into the existing tool registry through
an additive, feature-flagged dual path. The sprint ships under
`DOGE_FEATURE_SLOT_PLATFORM` (default off); flag-off tool-registry and runtime
behavior are byte-identical to today.

## 2. User Promise / JTBD

A platform integrator can declare a unit of capability through a manifest and have
it discovered via `doge slots list` / `doge slots show`, while the runtime assembles
tool contributions through the canonical `ToolRegistry` without changing existing
behavior when the flag is off.

The sprint improves platform pluggability without changing daemon routes, HTTP
payloads, SDK surfaces, Web UI, daemon command source, persistence, or production
maturity posture.

## 3. Detailed Behavior

- `doge.platform.slots` exposes the contract; built-in slots construct
  `SlotManifest` directly in Python (no on-disk YAML this sprint).
- `MarketCoreSlot` (in `doge.products.market.slot`) declares `market.core` and
  resolves six tool descriptors from `ToolApplicationService.tool_descriptors()`,
  returning the same service as executor.
- `bootstrap/runtime_factories/slots.py` adds `build_builtin_slot_registry()` and
  `build_slot_aware_tool_registry(...)`. `bootstrap/runtime_factories/tools.py`
  branches on `DOGE_FEATURE_SLOT_PLATFORM`: flag on delegates to the slot-aware
  builder; flag off runs the legacy factory unchanged.
- Slot-owned descriptors are registered first via `ToolRegistry.include_descriptors`
  against the same service; the remaining descriptors are registered afterward so
  nothing is double-registered.
- `doge slots list` prints `id|status|type|tools`; `doge slots show <id>` prints the
  manifest, static health, and declared tool names. Both read manifests only.
- Flag-off CLI prints a graceful disabled message (stdout, exit 0); `--json` emits
  `{"status":"disabled","feature_flag":"DOGE_FEATURE_SLOT_PLATFORM"}`.

## 4. Contracts / Data Model

- `SlotManifest` v1 (frozen dataclass): `schema_version`(=1), `id`
  (`^[a-z][a-z0-9]*(?:[.-][a-z][a-z0-9]*)*$`, max 64), `name`, `version`, `type`
  (enum), `owner`, `maturity`, `description`, `entrypoint`, `provides`, `requires`,
  `permissions`, `health`, `feature_flags`, `compatibility`.
- `load_slot_manifest(dict | path)` validates the schema and rejects unknown
  top-level keys; raises `SlotManifestValidationError`.
- `ISlot.manifest()` / `ISlot.resolve(context)`; `SlotContribution{slot_id, tools,
  executor, capabilities}`.
- `SlotContext` exposes `settings`, `feature_flags`, `tool_application_service`,
  `audit`, `permission_checker`, and `locate(service_id)`; raises
  `SlotConfigurationError` when no locator is configured.
- `SlotRegistry.register/unregister/get/all/manifests/status/resolve_contributions`;
  duplicate id -> `SlotAlreadyRegisteredError`; unknown id -> `UnknownSlotError`.
- Slot errors are normal exceptions carrying `code`/`public_message` and a
  `to_safe_error()` helper backed by `doge.shared.errors.SafeError.create`.
- CLI exit codes: 0 success (including flag-off disabled); 1 unknown slot id;
  2 argparse rejection.

## 5. Edge Cases

- Flag off: the factory never constructs `SlotRegistry`/`SlotContext`; `/v1/tools`,
  capability records, and execution are byte-identical to the legacy path.
- Flag on but a slot-owned tool name is absent from the service: `resolve` raises
  `SlotConfigurationError` so manifest/runtime tool drift fails fast.
- Duplicate slot id registration raises `SlotAlreadyRegisteredError`.
- `load_slot_manifest` rejects unknown top-level keys, bad id/type/maturity/
  risk_level, missing required fields, and non-JSON file content.
- `SlotContext.locate` raises `SlotConfigurationError` when no locator is configured
  or the locator returns `None`/raises.
- `list_views` is contributed by the quant bounded context but grouped under
  `market.core` for discovery; no code is moved (recorded in `provides.metadata`).

## 6. Dependencies

- Upstream: `doge.application.tools` (registry/factory seam), `doge.application.agent`
  (`ToolApplicationService`), `doge.config` (feature flag), `doge.core.domain`
  (`ToolDescriptor`), `doge.shared.errors` (`SafeError`).
- Downstream: future model/workflow/data/document/ui/gateway/governance/eval/watcher
  slot sprints (034+).
- ADRs: ADR-0013, ADR-0019 (relationship documented; unification deferred),
  ADR-0021 (bounded contexts referenced), ADR-0027, ADR-0042.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: env-owned feature flag, default `false`.
  - `FeatureLifecycle`: `introduced` = Sprint 033 / ADR-0042;
    `current_default=False`; `target_default_on` = after ADR-0042 parity evidence
    and full regression are green; `target_removal` = one release cycle after
    slot-backed registration is byte-equivalent with an approved removal story;
    `replacement_behavior` = built-in slots register through `SlotRegistry`;
    `regression_commands` = slot/parity tests; `rollback_criterion` = restore
    default false if `/v1/tools` payload or execution differs from the flag-off
    baseline.
- `feature_flags[]` in a manifest stores Settings field keys (e.g. `slot_platform`),
  not raw env-var names; the registry receives an already-resolved flag map from
  bootstrap and never reads `os.environ` directly.
- Operational risk: LOW - additive, default-off, dual-path; flag-off behavior is
  unchanged except diagnostics may list the new flag.

## 8. Acceptance Criteria

- Slot contract unit tests pass (manifest validation, registry, context facade,
  `MarketCoreSlot`).
- Boundary ratchet proves `platform/slots` imports only `core`/`shared`/stdlib.
- Parity test proves flag-off byte-identical to the frozen baseline and flag-on
  equivalent (equal schemas, records, count == 23).
- `doge slots list/show` behaves correctly flag-off (disabled) and flag-on
  (`market.core` row/manifest); unknown id exits 1.
- Settings lifecycle tests pass with `slot_platform` included.
- SDK contract remains 15 surfaces / 15 parity.
- Import-boundary, docs authority/links/maturity, ADR/CDD maturity-honesty, plan
  closure, and whitespace validators pass.
- `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental` are preserved; no external gate is closed.

## 9. Validation Plan

```bash
py -3 -m pytest tests/unit/platform/slots tests/unit/architecture/test_slot_boundary.py \
  tests/cli/test_cli_slots.py tests/contract/test_tool_registry_slot_parity.py -q
py -3 -m pytest tests/test_settings.py tests/contract/test_tool_registry.py \
  tests/contract/test_golden_runtime_contract.py tests/unit/architecture -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0042-slot-platform.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-033-slot-platform.md
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
```

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-033-slot-platform-manifest.md`.

## 11. Out of Scope

- Model/workflow/data/document/ui/gateway/governance/eval/watcher slot types.
- `/v1/slots` HTTP API and `doged slots` daemon command.
- ADR-0019 CapabilityRegistry unification into slots.
- Migrating the remaining 17 tool methods into slots.
- YAML-on-disk manifest parsing and third-party slot install/bundles.
- Watcher slots and runtime permission/health enforcement.
- Web UI changes.
- Production readiness declaration or external gate closure.
