# Sprint 034 CDD: Slot Contribution Facets

Status: Ready for Acceptance
Date: 2026-07-07

## 1. Overview

Sprint 034 extends the Slot Platform Foundation from a tool-only contribution
contract into a multi-facet contribution contract. It adds pure dataclass
representations for model, workflow, data, document, gateway, UI, watcher, eval,
and governance contributions, then proves one runtime path by migrating the
existing `kimi_agent_sdk` agent backend behind the slot registry when
`DOGE_FEATURE_SLOT_PLATFORM` is enabled.

The sprint remains local, experimental, and feature-flagged. It does not claim
the full OpenClaw-like Slot Platform is complete.

## 2. User Promise / JTBD

A platform integrator can now see a concrete Python contract for every planned
slot contribution kind, and a runtime maintainer can verify that one model
backend is assembled through the same slot registry pattern as the existing
`market.core` tool slot.

The sprint increases composability without changing HTTP contracts, SDK public
surfaces, Web source, daemon commands, persistence, model dispatch, or external
operator gates.

## 3. Detailed Behavior

- `doge.platform.slots.facets` defines the 9 non-tool facet dataclasses and
  `WatcherDecision`.
- `SlotContribution` keeps the existing tool fields and adds tuple fields for
  every new facet.
- `SlotContext.tool_application_service` becomes optional so non-tool slots can
  resolve without a tool service.
- `ISlot.start(context)` and `ISlot.stop(context)` are defined as no-op hooks for
  future lifecycle work.
- `MarketCoreSlot.resolve()` raises `SlotConfigurationError` when called without
  `tool_application_service`.
- `ModelKimiAgentSdkSlot` contributes a `ModelBackendContribution` for
  `kimi_agent_sdk`.
- `build_builtin_slot_registry()` registers both built-in slots:
  `market.core` and `model.kimi_agent_sdk`.
- `build_slot_aware_tool_registry()` resolves only `SlotType.TOOL` slots and
  raises if a tool contribution has no executor.
- `build_slot_aware_agent_backends()` resolves only `SlotType.MODEL` slots,
  constructs backend objects through facet factories, and raises on duplicate
  backend ids.
- `build_agent_backends()` delegates to the slot-aware helper only when
  `slot_platform` is enabled.

## 4. Contracts / Data Model

New facet contracts:

- `ModelBackendContribution(backend_id, factory, capabilities, profiles)`
- `WorkflowTemplateContribution(slug, template_factory, capabilities)`
- `DataSourceContribution(source_id, factory, markets, metadata_port, capabilities)`
- `DocumentParserContribution(parser_id, factory, supported_suffixes, mime_types, priority)`
- `GatewayRouteContribution(router_id, router_factory, prefix, tags, requires_auth)`
- `UIPanelContribution(panel_id, zone, component_module, order, modes, required_artifact_fields, label)`
- `WatcherDecision(action, reason, approval_required)`
- `WatcherContribution(watcher_id, on_event, event_types)`
- `EvalSuiteContribution(suite_id, gold_set_path, metrics, execution_profile, eval_policy)`
- `GovernancePolicyContribution(policy_id, kind, payload, entitlement_checker_factory)`

`SlotContribution` fields:

- Existing: `slot_id`, `tools`, `executor`, `capabilities`
- New: `model_backends`, `workflows`, `data_sources`, `document_parsers`,
  `routes`, `ui_panels`, `watchers`, `eval_suites`, `governance_policies`

Well-known service ids include `SLOT_SERVICE_SECRET_PROVIDER` and placeholders
for future agent-backend, platform-repository, data-source, document-parser,
FastAPI-app, event-bus, and governance-repository lookup.

`SlotManifest` schema version remains 1 because the manifest schema is not
changed in this sprint.

## 5. Edge Cases

- Feature flag off: `build_agent_backends()` uses the legacy body.
- Feature flag on: model slot construction returns an equivalent backend dict
  with `kimi_agent_sdk`.
- Tool registry construction ignores model slot contributions because it filters
  by `SlotType.TOOL` before resolution.
- Model backend construction ignores tool slot contributions because it filters
  by `SlotType.MODEL` before resolution.
- Duplicate model backend ids raise `SlotConfigurationError`.
- Tool contributions with populated `tools` and missing `executor` raise
  `SlotConfigurationError`.
- `ModelKimiAgentSdkSlot.resolve()` does not require a Kimi key and performs no
  network I/O.
- The model backend factory gets the secret provider through
  `SlotContext.locate(SLOT_SERVICE_SECRET_PROVIDER)`.

## 6. Dependencies

- Upstream: ADR-0042 slot foundation, `doge.platform.slots`,
  `doge.infrastructure.agent.backends.KimiAgentSdkBackend`, runtime factory
  wiring, `doge.config` feature settings.
- Downstream: future workflow/data/document/gateway/UI/watcher/eval/governance
  slot migrations.
- ADRs: ADR-0013, ADR-0019, ADR-0021, ADR-0027, ADR-0042, ADR-0043.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; reused from Sprint 033.
  - Flag off: legacy `build_agent_backends()` and legacy tool registry path.
  - Flag on: tool registry and agent backend construction consume built-in slot
    contributions.

No new feature flag is introduced in this sprint. Future watcher/eval/gateway
runtime consumers should add their own gates when they are wired.

## 8. Acceptance Criteria

- `SlotContribution` can carry all 9 non-tool facets while `platform/slots`
  remains a pure contract package.
- Existing `market.core` tool slot still passes parity and fail-fast tests.
- `model.kimi_agent_sdk` is registered in the built-in registry and contributes
  `kimi_agent_sdk` through a model facet.
- `build_agent_backends()` returns equivalent flag-off and flag-on backend
  summaries.
- Duplicate backend ids and tool contributions without executors fail fast.
- `/v1` routes, OpenAPI, SDK sources, Web source, daemon command source,
  persistence, ModelRouter, ProfileRegistry, and runtime dispatch are unchanged.
- SDK contract remains 15/15.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.
- Plan closure remains acceptable open; external/operator gates remain open.

## 9. Validation Plan

```bash
py -3 -m pytest tests/unit/platform/slots tests/unit/architecture/test_slot_boundary.py \
  tests/contract/test_agent_backends_slot_parity.py tests/contract/test_tool_registry_slot_parity.py -q
py -3 -m pytest tests/test_settings.py tests/unit/agent tests/contract/test_tool_registry.py \
  tests/contract/test_golden_runtime_contract.py tests/unit/architecture -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0043-slot-contribution-facets.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-034-slot-contribution-facets.md
py -3 scripts/validate_no_stale_counts.py
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-034-slot-contribution-facets-manifest.md`.

## 11. Out of Scope

- Runtime consumers for workflow, data, document, gateway, UI, watcher, eval, and
  governance facets.
- Slot lifecycle `start`/`stop` invocation by runtime or bootstrap.
- `/v1/slots` API, `doged slots`, Web Slot Center, YAML manifests, bundles,
  third-party slot install, signature validation, or marketplace behavior.
- CapabilityRegistry unification with slots.
- ModelRouter, ProfileRegistry, or runtime dispatch changes.
- Production readiness declaration or external/operator gate closure.
