# ADR-0055: Slot Permission and Health Enforcement

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 045 turns slot `permissions` and `health` metadata into a first runtime
guard. A new `SlotEnforcementPolicy` is injected into `SlotKernel`; when
`DOGE_FEATURE_SLOT_ENFORCEMENT=1`, the kernel checks declarative permissions
and active health before status, contribution resolve, and lifecycle start.

The guard blocks forbidden-risk slots, shell-permission slots unless explicitly
allowed by policy, and disabled-health slots. Health is actively probed through
`ISlot.health(context)` when enforcement is enabled. Tool slots denied by
enforcement do not fall back to legacy tool registration.

This sprint does not add OS sandboxing, network interception, filesystem
mediation, third-party slot install, signing, enterprise allowlists, bundle
activation, or production-readiness changes.

## Status Update - 2026-07-08

ADR-0063 extends this decision with a separate default-off runtime interception
layer. ADR-0055 remains the SlotKernel resolution-time admission contract for
permissions and health; ADR-0063 adds in-process db/secret/network port guards
for built-in slot-aware execution plus subprocess env/cwd hardening.

The ADR-0055 exclusions remain accurate for Sprint 045 history. As of ADR-0063,
the "no runtime interception" boundary is partially released only for
in-process guarded ports. OS/container/WASM sandboxing, filesystem mediation,
malicious-code containment, and third-party provider execution remain out of
scope.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing SlotKernel and ToolRegistry bootstrap |
| **Domain** | Slot Platform runtime policy and diagnostics |
| **Knowledge Risk** | MEDIUM - runtime assembly path and tool fallback behavior |
| **References Consulted** | `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0052-slot-kernel-bundles-policy.md`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Slot enforcement unit tests, tool-registry parity and denied fallback tests, settings/capability tests, import/docs/maturity validators |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0052 (Slot Kernel, Bundles, Policy, and Lifecycle), ADR-0054 (Web Slot Center) |
| **Extends** | ADR-0042 by enforcing manifest permissions/health; ADR-0052 by adding enforcement to SlotKernel |
| **Supersedes** | None |
| **Enables** | SlotLoader permission previews, third-party install blocking, enterprise allowlist policy |
| **Blocks** | None |

## Context

Earlier sprints made `SlotManifest.permissions` and `SlotManifest.health`
visible but mostly descriptive. That is acceptable for built-in local-alpha
slots, but it is not sufficient before disk loading, third-party installation,
or enterprise allowlists. The runtime needs one common enforcement point before
contributions reach tools, models, data sources, routes, UI panels, watchers,
and eval suites.

`SlotKernel` is now the shared contribution resolver for built-in consumers.
That makes it the right place to apply a common guard. Tool slots also need a
specific fallback fix: if a tool slot is blocked, its declared tool names must
not be re-registered from the legacy `ToolApplicationService` fallback.

## Constraints

- Keep `DOGE_FEATURE_SLOT_ENFORCEMENT` default `false`.
- Keep existing flag-off behavior unchanged.
- Keep enforcement in `doge.platform.slots` pure and framework-free.
- Do not add OS sandboxing or resource interception in this sprint.
- Do not block existing built-in network/database/secrets declarations unless
  they are forbidden-risk, shell-enabled, or disabled-health.
- Do not add bundle activation, SlotLoader, signing, third-party install, or
  production-readiness claims.

## Decision

Add `SlotEnforcementPolicy` and `SlotEnforcementDecision` to
`doge.platform.slots.enforcement` and export them from `doge.platform.slots`.

Add `enforcement` to `SlotKernel`. The kernel uses the policy in:

- `status(context)`;
- `bundle_status(context)`;
- `resolve_contributions(context, slot_type=...)`;
- `start(context, slot_type=...)`.

When health enforcement is enabled, `SlotKernel` calls `slot.health(context)`
and safely converts health-probe exceptions into degraded health records.
Disabled health blocks contribution resolve/start. Degraded health is reported
but allowed by default for local-alpha parity.

Add `DOGE_FEATURE_SLOT_ENFORCEMENT` and `FeatureConfig.slot_enforcement`.
Expose `feature.slot_enforcement` through capability discovery.

Update bootstrap slot factories to pass an enforcement policy built from
settings into `build_builtin_slot_kernel()`. When the flag is off, the policy is
inert. When the flag is on, permission and health checks run for every
slot-aware consumer.

Update `build_slot_aware_tool_registry()` so slot-owned tool names are reserved
from manifests before contribution resolve. If enforcement blocks a tool slot,
its tools are not registered through the legacy fallback.

## Alternatives Considered

### Alternative 1: Enforce inside each facet consumer

- **Description**: Add permission/health checks separately in tool, model,
  workflow, data, document, gateway, UI, watcher, and eval factories.
- **Pros**: Facet-specific behavior could be customized.
- **Cons**: Duplication and higher chance of bypass.
- **Rejection Reason**: `SlotKernel` is the shared resolver and is harder to
  bypass accidentally.

### Alternative 2: Block all medium-risk slots by default

- **Description**: Deny medium-risk network/data slots under enforcement.
- **Pros**: Conservative posture.
- **Cons**: Existing built-in model/data slots would stop resolving in local
  mode, breaking parity too early.
- **Rejection Reason**: This sprint blocks forbidden-risk, shell, and disabled
  health only; enterprise allowlists come later.

### Alternative 3: Add full sandbox enforcement now

- **Description**: Intercept filesystem, network, subprocess, database, and
  secret access at runtime.
- **Pros**: Stronger protection.
- **Cons**: Requires broader adapter and process isolation design.
- **Rejection Reason**: This sprint is the common contract guard; sandboxing is
  later third-party ecosystem work.

## Consequences

### Positive

- Manifest permissions and health now influence slot resolution when the
  enforcement flag is enabled.
- Active health probes can mark slots disabled/degraded before contribution
  resolution.
- Blocked tool slots cannot silently reappear through fallback registration.
- Future SlotLoader/install work has a concrete policy seam.

### Negative

- Health probes may run more than once per status/resolve sequence.
- Enforcement currently guards slot contribution boundaries, not every OS-level
  resource operation.
- Default local behavior remains unchanged until the flag is enabled.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Built-in slot unexpectedly blocked | LOW | HIGH | Enforcement defaults off; focused parity and blocked-fallback tests cover the hot path. |
| Health probe exception breaks status API | LOW | MEDIUM | Kernel converts exceptions to degraded health. |
| Operators assume sandboxing exists | MEDIUM | HIGH | ADR/CDD/evidence state OS sandboxing and third-party install are out of scope. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-045-slot-enforcement.md` | Slot permissions/health must gate runtime contribution resolve. | Adds SlotEnforcementPolicy, kernel checks, active health probes, feature flag, and tool fallback prevention. |
| `docs/progress/runtime-maturity.yaml` | Slot Platform maturity remains experimental. | Records Sprint 045 as local experimental only. |

## Performance Implications

- **CPU**: one small policy check per slot in status/resolve/start.
- **Memory**: no persistent state.
- **I/O**: active health probes run only when enforcement is enabled; current
  built-in probes are static unless a slot overrides `health()`.
- **Tool Registry**: manifest-owned tool names are reserved once during
  slot-aware registry construction.

## Migration Plan

1. Add pure slot enforcement policy contracts.
2. Inject enforcement into `SlotKernel`.
3. Add `DOGE_FEATURE_SLOT_ENFORCEMENT` settings and capability metadata.
4. Pass enforcement policy from bootstrap slot factories.
5. Reserve manifest-owned tool names before registering fallback tools.
6. Add unit and contract tests.
7. Update governance docs, runtime maturity, and roadmap.

## Validation Criteria

- Enforcement flag defaults off.
- `SlotKernel` blocks shell-permission slots when enforcement is enabled.
- `SlotKernel` calls active health probes and blocks disabled-health slots.
- Degraded health is reported and allowed by default.
- A blocked tool slot does not register its declared tools through legacy
  fallback.
- Existing slot parity remains unchanged when enforcement is off.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0052: Slot Kernel, Bundles, Policy, and Lifecycle
- ADR-0054: Web Slot Center
