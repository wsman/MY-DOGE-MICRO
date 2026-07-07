# ADR-0056: Slot Loader and Bundle Activation

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 046 adds the first local SlotLoader and mutable bundle activation
surface. The loader validates JSON SlotManifest files from
`DOGE_SLOT_MANIFEST_DIRS` and registers them as manifest-only slots for
discovery, policy, and health diagnostics. It does not import provider code or
execute third-party entrypoints.

The sprint also adds process-local bundle activation behind
`DOGE_FEATURE_SLOT_LOADER`. Operators can list bundles and activate one through
CLI or `POST /v1/slot-bundles/{bundle_id}/activate`; the active bundle
constrains `SlotKernel` contribution resolution through `SlotPolicy`.

This sprint does not add YAML parsing, third-party install, signature
verification, enterprise allowlists, persistent activation state, SDK slot
client methods, or OS sandboxing.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; stdlib JSON manifest loading; existing FastAPI/CLI surfaces |
| **Domain** | Slot Platform discovery, local activation, and operator diagnostics |
| **Knowledge Risk** | MEDIUM - process root settings and feature-flag interactions |
| **References Consulted** | `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0052-slot-kernel-bundles-policy.md`, `docs/architecture/adr-0055-slot-enforcement.md`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Slot loader/activation tests, CLI/API activation tests, route authority sync, settings/capability tests, import/docs/maturity validators |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0052 (Slot Kernel, Bundles, Policy, and Lifecycle), ADR-0055 (Slot Permission and Health Enforcement) |
| **Extends** | ADR-0042 by loading manifest-only slots from disk; ADR-0052 by applying activated bundle policy to SlotKernel; ADR-0055 by preserving enforcement before contribution resolution |
| **Supersedes** | None |
| **Enables** | Third-party local slot preview, signing policy, enterprise allowlist checks |
| **Blocks** | None |

## Context

Built-in slots are now discoverable, enforceable, and grouped into bundles, but
the platform still cannot read an operator-provided manifest from disk or
activate a scenario bundle. The OpenClaw-like plan calls for a SlotLoader and
bundle activation, but the existing architecture intentionally avoids arbitrary
Python plugin execution until manifest validation, permissions, health, and
watcher policy are in place.

ADR-0042 kept manifest parsing in stdlib JSON only. Adding a YAML dependency is
a separate dependency decision, so this sprint implements JSON-first loading and
documents YAML as out of scope.

## Constraints

- Keep `DOGE_FEATURE_SLOT_LOADER` default `false`.
- Require `DOGE_FEATURE_SLOT_PLATFORM=1` before loader/activation surfaces can
  operate.
- Load disk manifests as manifest-only slots; do not import provider
  entrypoints.
- Keep activation process-local and non-persistent.
- Keep bundle activation limited to registered built-in bundles.
- Fail fast if the active bundle id is not registered.
- Do not add third-party install, signing, enterprise allowlists, YAML parsing,
  SDK slot methods, or sandboxing.

## Decision

Add `SlotLoader` and `ManifestOnlySlot` to `doge.platform.slots.loader`.
`SlotLoader.load()` accepts JSON files or directories. Direct `*.json` files and
nested `*/slot.json` files are discovered deterministically and de-duplicated by
resolved path. Invalid or missing sources raise `SlotConfigurationError` with
path context.

Add `SlotConfig` and `DOGE_SLOT_MANIFEST_DIRS` to settings. The loader is gated
by `DOGE_FEATURE_SLOT_LOADER`; when disabled, built-in registry construction is
unchanged.

Add `SlotBundleActivationState` and `policy_for_activation()`. Activation is an
in-memory process-local record. When `DOGE_FEATURE_SLOT_LOADER=1` and no
explicit `SlotPolicy` is passed, `build_builtin_slot_kernel()` constrains
resolution to the active bundle's enabled and disabled slot sets.

Expose activation through:

- `doge slots bundle list [--json]`;
- `doge slots bundle activate <bundle_id> [--json]`;
- `GET /v1/slot-bundles` with an `active` field;
- `POST /v1/slot-bundles/{bundle_id}/activate`.

The new POST route is feature-gated by `DOGE_FEATURE_SLOT_LOADER` and remains
operator-local alpha behavior. It returns 404 while the loader flag is off.

## Alternatives Considered

### Alternative 1: Import provider entrypoints during load

- **Description**: Resolve `entrypoint.python` and instantiate slot providers
  from disk manifests.
- **Pros**: Closer to a full plugin system.
- **Cons**: Executes operator-provided Python before signing, allowlist, and
  sandbox decisions exist.
- **Rejection Reason**: Sprint 046 is a manifest-only preview. Provider imports
  belong to the third-party install/signing sprint.

### Alternative 2: Persist active bundle state

- **Description**: Store active bundle ids in SQLite or config files.
- **Pros**: Activation survives process restarts.
- **Cons**: Requires authorization, migration, conflict, and rollback policy.
- **Rejection Reason**: Process-local activation is enough for local alpha and
  avoids claiming a durable operations contract.

### Alternative 3: Add YAML manifest parsing now

- **Description**: Add a YAML parser and load `slot.yaml` directly.
- **Pros**: Matches the long-term OpenClaw-like plan examples.
- **Cons**: Adds a dependency and security parsing surface not covered by an
  ADR.
- **Rejection Reason**: ADR-0042 intentionally uses stdlib JSON until a
  separate dependency decision accepts YAML.

## Consequences

### Positive

- Operators can preview local manifest-only slots without executing plugin code.
- Built-in bundles can be activated and visibly constrain runtime resolution.
- `/v1/slot-bundles` and CLI bundle output show active state.
- The API route authority now includes the activation route.
- The next third-party install sprint can build on manifest validation and
  bundle policy instead of starting from scratch.

### Negative

- Manifest-only slots do not contribute tools, routes, workflows, UI, models,
  data sources, watchers, or eval suites.
- Activation is not durable and is not shared across processes.
- YAML examples in planning docs still require conversion or a later parser
  decision.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Operators assume disk manifests execute code | MEDIUM | HIGH | ADR/CDD/API docs state manifest-only loading and no provider import. |
| Active bundle surprises existing tests or local flows | LOW | MEDIUM | Activation is gated by `DOGE_FEATURE_SLOT_LOADER` and can be cleared in tests. |
| Route authority drifts after POST addition | LOW | MEDIUM | Route coverage and governance sync tests now expect 96 routes. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-046-slot-loader-bundle-activation.md` | Disk manifests must be loadable without provider execution. | Adds JSON `SlotLoader` and `ManifestOnlySlot`. |
| `design/cdd/sprint-046-slot-loader-bundle-activation.md` | Bundle activation must constrain SlotKernel resolution locally. | Adds process-local activation state, activation policy, CLI, and API route. |
| `docs/progress/runtime-maturity.yaml` | Slot Platform maturity remains experimental. | Records Sprint 046 as local experimental only. |

## Performance Implications

- **CPU**: deterministic manifest discovery and JSON validation during registry
  construction when loader is enabled.
- **Memory**: process-local active bundle id and manifest-only slot records.
- **I/O**: reads manifest JSON files from configured directories only when
  `DOGE_FEATURE_SLOT_LOADER=1`.
- **HTTP**: one new feature-gated POST route under `/v1/slot-bundles`.

## Migration Plan

1. Add loader and activation contracts in `doge.platform.slots`.
2. Add `DOGE_FEATURE_SLOT_LOADER` and `DOGE_SLOT_MANIFEST_DIRS` settings.
3. Register manifest-only slots during built-in registry construction when the
   loader flag is enabled.
4. Apply active bundle policy in `build_builtin_slot_kernel()`.
5. Add CLI bundle list/activate commands.
6. Add feature-gated API activation route and route docs.
7. Add focused tests and governance evidence.

## Validation Criteria

- Loader flag defaults off and is visible in capability discovery.
- `DOGE_SLOT_MANIFEST_DIRS` parses as CSV paths.
- `SlotLoader` loads direct JSON manifest files and nested `slot.json` files.
- Invalid or missing manifest sources fail with path context.
- Manifest-only slots appear in status rows when loader is enabled.
- Bundle activation marks one bundle active and filters `SlotKernel`
  contribution resolution.
- CLI activation is blocked while `DOGE_FEATURE_SLOT_LOADER` is off.
- API activation is blocked while `DOGE_FEATURE_SLOT_LOADER` is off.
- Route authority and governance registries agree on 96 HTTP routes.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0052: Slot Kernel, Bundles, Policy, and Lifecycle
- ADR-0055: Slot Permission and Health Enforcement
