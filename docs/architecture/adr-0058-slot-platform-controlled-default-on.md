# ADR-0058: Slot Platform Controlled Default On

## Status

Accepted

## Date

2026-07-08

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P0 promotes the local built-in Slot Platform consumer path from opt-in preview to
the controlled default path for local runs. The decision is limited to four
feature defaults:

- `DOGE_FEATURE_WORKFLOW_TEMPLATES=1`
- `DOGE_FEATURE_SLOT_PLATFORM=1`
- `DOGE_FEATURE_SLOT_GOVERNANCE=1`
- `DOGE_FEATURE_SLOT_WATCHER=1`

The promotion does not enable SlotLoader, bundle activation, slot install,
runtime permission/health enforcement, UI slot metadata, Python analysis,
provider entrypoint import, sandboxing, signing, YAML manifests, SDK install
APIs, HTTP install APIs, marketplace behavior, remote CI promotion, or
production readiness.

## Status Update - 2026-07-08

ADR-0060 supersedes this ADR's `slot_loader` default-off posture and the P0
block that said persistent bundle activation was not delivered. Current local
alpha behavior defaults `slot_loader` on and persists one active built-in bundle
record in SQLite. ADR-0058 remains controlling for the rest of the safety
boundary: no auto-activated bundle, no provider execution, no install
execution, no sandboxing, no signing, no YAML manifests, no marketplace, no
remote CI promotion, and no production-ready declaration.

ADR-0064 later adds `DOGE_FEATURE_SLOT_PROVIDER_EXECUTION`, but that flag
defaults off and requires installed trusted-provider gates. ADR-0058 remains
controlling for the default local path: provider execution is not default-on and
does not imply production plugin readiness.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing dataclass settings, FastAPI 0.123.8, pytest 9.0.1 |
| **Domain** | Runtime configuration / Slot Platform default posture |
| **Knowledge Risk** | LOW - local configuration defaultization over already-shipped paths |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/architecture/adr-0018-workflow-template-system.md`, `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0043-slot-contribution-facets.md`, `docs/architecture/adr-0044-workflow-slot-consumer.md`, `docs/architecture/adr-0045-slot-discovery-surfaces.md`, `docs/architecture/adr-0046-governance-slot-consumer.md`, `docs/architecture/adr-0047-watcher-slot-consumer.md`, `docs/architecture/adr-0048-document-slot-consumer.md`, `docs/architecture/adr-0049-data-slot-consumer.md`, `docs/architecture/adr-0050-gateway-slot-consumer.md`, `docs/architecture/adr-0051-eval-slot-consumer.md`, `docs/architecture/adr-0052-slot-kernel-bundles-policy.md`, `docs/architecture/adr-0053-ui-slot-consumer.md`, `docs/architecture/adr-0056-slot-loader-bundle-activation.md`, `docs/architecture/adr-0057-third-party-slot-install-preview.md`, `production/qa/evidence/slot-platform-sprints-035-048-local-acceptance-2026-07-07.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | settings defaults, CLI/doged slot discovery, slot parity, workflow-template route/seed behavior, opt-out regressions, docs maturity validators, plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0018 (Workflow Template System), ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0044 (Workflow Slot Consumer), ADR-0045 (Slot Discovery Surfaces), ADR-0046 (Governance Slot Consumer), ADR-0047 (Watcher Slot Consumer), ADR-0048 (Document Slot Consumer), ADR-0049 (Data Slot Consumer), ADR-0050 (Gateway Slot Consumer), ADR-0051 (Eval Slot Consumer), ADR-0052 (Slot Kernel, Bundles, Policy, and Lifecycle), ADR-0053 (UI Slot Consumer) |
| **Extends** | ADR-0042 by making the built-in Slot Platform path the local default while preserving opt-out fallback |
| **Supersedes** | Default-off guidance in ADR-0042 through ADR-0053 for the four promoted flags only; it does not supersede default-off guidance for `slot_ui`, loader, install, enforcement, bundle activation, provider execution, signing, sandboxing, or marketplace behavior |
| **Enables** | Later legacy-direct-wiring sunset stories after additional release evidence |
| **Blocks** | Any claim that third-party provider execution, persistent bundle activation, signing, sandboxing, or marketplace behavior is production-ready |

## Context

### Problem Statement

Slot Platform Sprints 035-048 have local acceptance evidence across the major
facet consumers: workflow templates, discovery, governance, watcher, document,
data, gateway, eval, kernel/bundle rows, UI metadata, Web Slot Center,
enforcement, loader, activation, and manifest-only install preview. Keeping the
core built-in consumers default-off now hides the intended runtime shape and
keeps tests dependent on opt-in environment setup rather than the local product
default.

The project still must not cross the OpenClaw-style safety boundary. Third-party
slot execution, persistent activation, install execution, sandboxing, signing,
and marketplace semantics are explicitly not mature enough for default enablement.

### Constraints

- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.
- Preserve `latest_remotely_verified_sha`; this local decision does not assert
  remote CI.
- Keep external/operator gates `S017-003`, `W3-live`, `AUTH-prod`, and
  `S017-007` open.
- Keep `DOGE_FEATURE_SLOT_LOADER`, `DOGE_FEATURE_SLOT_INSTALL`,
  `DOGE_FEATURE_SLOT_ENFORCEMENT`, `DOGE_FEATURE_SLOT_UI`, and
  `DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED` default-off.
- Preserve explicit rollback through `DOGE_FEATURE_SLOT_PLATFORM=0`,
  `DOGE_FEATURE_WORKFLOW_TEMPLATES=0`, `DOGE_FEATURE_SLOT_GOVERNANCE=0`, and
  `DOGE_FEATURE_SLOT_WATCHER=0`.
- Do not make `bundle.local_analyst` or any other bundle persistently active by
  default.

### Requirements

- Default local runs should resolve the built-in tool/model/data/document/
  workflow/eval/governance/watcher/gateway consumers.
- Workflow-template platform APIs and seeding should use the slot-backed template
  definitions by default while retaining explicit opt-out fallback.
- CLI, doged, and `/v1` discovery should surface built-in slots by default.
- Tests must explicitly opt out when they need the old direct-wiring branch.

## Decision

Change `src/doge/config/settings.py` so both `FEATURE_LIFECYCLES` and
`FeatureConfig` default these four features to `True`:

- `workflow_templates`
- `slot_platform`
- `slot_governance`
- `slot_watcher`

Keep these features default `False`:

- `slot_loader`
- `slot_install`
- `slot_enforcement`
- `slot_ui`
- `python_analysis_enabled`
- `runtime_outbox_publisher`
- `platform_objects`
- `capability_registry`
- `run_summary_api`

Complete the runtime settings injection seam for the three older slot-aware
builders:

```python
build_slot_aware_tool_registry(..., settings: Any | None = None)
build_slot_aware_agent_backends(..., *, settings: Any | None = None)
build_slot_aware_workflow_templates(*, settings: Any | None = None)
```

The runtime factory callers read settings once, branch on the effective feature
posture, and pass the same settings object into the slot-aware builder. Tests
that need the old direct path must set the relevant feature env var to `0` or
inject `Settings(features=FeatureConfig(...False...))`.

### Architecture Diagram

```text
Settings defaults
  workflow_templates=true
  slot_platform=true
  slot_governance=true
  slot_watcher=true
        |
        v
Built-in SlotKernel contribution resolution
        |
        +-- tools/model/data/document/workflow/eval/gateway resolved by default
        +-- governance.tool_policy resolved by default
        +-- watcher.runtime_events resolved by default
        |
        +-- ADR-0060 later defaults slot_loader on for manifest-only loading
        +-- install/enforcement/ui remain default-off
        +-- third-party provider entrypoints remain never imported
```

### Key Interfaces

- Env opt-out:
  - `DOGE_FEATURE_SLOT_PLATFORM=0`
  - `DOGE_FEATURE_WORKFLOW_TEMPLATES=0`
  - `DOGE_FEATURE_SLOT_GOVERNANCE=0`
  - `DOGE_FEATURE_SLOT_WATCHER=0`
- Discovery by default:
  - `doge slots list`
  - `doged slots`
  - `GET /v1/slots`
  - `GET /v1/slot-bundles`
- Still gated by default-off flags:
  - `doge slots install`
  - `POST /v1/slot-bundles/{bundle_id}/activate`
  - `GET /v1/ui-panels`

## Alternatives Considered

### Alternative 1: Keep all Slot Platform flags default-off

- **Description**: Preserve the Sprints 033-048 preview posture unchanged.
- **Pros**: Lowest rollout risk and no default behavior shift.
- **Cons**: Hides the intended platform composition path after broad local
  parity evidence and lets tests silently rely on opt-in setup.
- **Rejection Reason**: The local acceptance evidence supports making the
  built-in consumer path the default while keeping explicit opt-out.

### Alternative 2: Default-activate `bundle.local_analyst`

- **Description**: Enable SlotLoader and activate the local analyst bundle by
  default.
- **Pros**: Closer to a full bundle-oriented platform.
- **Cons**: Bundle activation is process-local, depends on `slot_loader`, and
  has no persistent enable/disable state or operator policy yet.
- **Rejection Reason**: P0 is defaultizing built-in contribution resolution, not
  persistent bundle activation.

### Alternative 3: Default-enable loader, install, enforcement, and UI slots too

- **Description**: Treat the entire Slot Platform preview as the default.
- **Pros**: More complete platform behavior in one change.
- **Cons**: Expands blast radius into manifest disk loading, local install
  writes, runtime enforcement, and UI metadata surfaces before dedicated default
  evidence exists for each.
- **Rejection Reason**: P0 deliberately keeps unsafe and higher-blast-radius
  surfaces default-off.

## Consequences

### Positive

- The default local runtime path now reflects the slotified platform architecture.
- Core slot consumers get coverage without requiring every test/operator path to
  set feature env vars.
- Legacy direct wiring remains available through explicit opt-out.
- The default state is clearer for demos and interviews: built-in modules are
  progressively slotified, while third-party execution remains blocked.

### Negative

- Tests that used deleted env vars to mean "off" must be made explicit.
- Operators who expected no slot discovery by default must opt out with
  `DOGE_FEATURE_SLOT_PLATFORM=0`.
- The docs must distinguish "slot contribution resolution default-on" from
  "bundle activation and third-party execution default-on."

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Default slot resolution changes runtime behavior | LOW | HIGH | Slot parity tests compare tool/model/workflow/governance/watcher/document/data/gateway/eval behavior and preserve opt-out fallback. |
| Operators mistake this for full plugin execution | MEDIUM | HIGH | ADR/docs/evidence state that provider execution, sandboxing, signing, install execution, and marketplace are out of scope. |
| Loader/install accidentally become default-on | LOW | HIGH | P0 originally kept loader off; ADR-0060 later defaults `slot_loader` on only for manifest-only loading and persisted local activation, while settings tests keep `slot_install`, `slot_enforcement`, `slot_ui`, and Python analysis false. |
| Bundle activation is misrepresented as auto-default | LOW | MEDIUM | ADR-0060 persists operator-selected activation but still does not auto-activate any bundle. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-033-slot-platform.md` | Slot Platform must keep explicit rollback and parity with legacy tool wiring. | Makes the built-in path default while preserving `DOGE_FEATURE_SLOT_PLATFORM=0`. |
| `design/cdd/sprint-035-workflow-slot-consumer.md` | Workflow templates can be supplied by slot contributions while preserving seed parity. | Defaults both slot platform and workflow templates on, with opt-out tests for the legacy seed path. |
| `design/cdd/sprint-037-governance-slot-consumer.md` | Governance slot policy composition must remain parity-preserving. | Defaults `slot_governance` on only after parity coverage and keeps unsafe enforcement off. |
| `design/cdd/sprint-038-watcher-slot-consumer.md` | Watcher middleware must preserve default runtime behavior. | Defaults the allow-only watcher on while keeping concrete high-risk watcher policies future work. |
| `design/cdd/sprint-043-slot-kernel-bundles-policy.md` | SlotKernel should be the first-class contribution resolution path. | Makes built-in SlotKernel-backed contribution resolution the local default without activating bundles. |

## Performance Implications

- **CPU**: Default registry/backend/template construction now builds the small
  built-in slot registry/kernel unless explicitly opted out.
- **Memory**: Small in-memory slot registry/context objects are allocated on
  default construction paths.
- **Load Time**: Default CLI/API discovery includes built-in slot status rows;
  SlotLoader disk scanning remains off.
- **Network**: None.

## Migration Plan

1. Flip the four `FeatureConfig` and `FEATURE_LIFECYCLES` defaults.
2. Add settings injection to the three older slot-aware builders and update
   runtime callers.
3. Update tests to assert new defaults and explicit opt-out behavior.
4. Update configuration docs, ADR pointers, runtime maturity, session state, and
   evidence.
5. Run focused tests, full local gates, docs validators, plan closure, and
   whitespace checks.

## Validation Criteria

- `FeatureConfig()` defaults the four promoted flags to true and keeps all
  unsafe/higher-blast-radius flags false.
- `doge slots list` and `doged slots` show built-in core slots resolved by
  default, with `ui.research_workspace` still disabled by default.
- `DOGE_FEATURE_SLOT_PLATFORM=0` restores disabled slot discovery/fallback.
- `workflow.templates`, `governance.tool_policy`, and
  `watcher.runtime_events` resolve by default.
- `doge slots install` remains disabled by default.
- `POST /v1/slot-bundles/{bundle_id}/activate` remains disabled by default.
- Local evidence preserves open external gates and non-production posture.

## Related Decisions

- ADR-0018: Workflow Template System
- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0044: Workflow Slot Consumer
- ADR-0045: Slot Discovery Surfaces
- ADR-0046: Governance Slot Consumer
- ADR-0047: Watcher Slot Consumer
- ADR-0048: Document Slot Consumer
- ADR-0049: Data Slot Consumer
- ADR-0050: Gateway Slot Consumer
- ADR-0051: Eval Slot Consumer
- ADR-0052: Slot Kernel, Bundles, Policy, and Lifecycle
- ADR-0053: UI Slot Consumer
- ADR-0056: Slot Loader and Bundle Activation
- ADR-0057: Third-party Slot Install Preview
