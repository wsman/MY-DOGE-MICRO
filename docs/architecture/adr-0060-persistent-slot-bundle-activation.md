# ADR-0060: Persistent Slot Bundle Activation

## Status

Accepted

## Date

2026-07-08

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P2 upgrades Slot Center activation from process-local preview state to a
persistent local alpha contract. Slot bundle activation is now stored in SQLite
as a single active bundle record, exposed through HTTP, CLI, and Web Slot
Center controls, and mirrored into the in-process `SlotBundleActivationState`
cache used by `SlotKernel` policy construction.

This decision also promotes `DOGE_FEATURE_SLOT_LOADER` to default on for local
runs. The loader still loads JSON manifests as manifest-only records and never
imports provider entrypoints.

P2 does not auto-activate any bundle. A fresh database has no active bundle
until an operator activates one. `slot_install`, `slot_enforcement`, `slot_ui`,
`python_analysis_enabled`, provider execution, sandboxing, signing, YAML
manifests, marketplace behavior, enterprise bundle ACL policy, remote CI
promotion, and production readiness remain out of scope.

## Status Update - 2026-07-08

ADR-0061 closes the P2-deferred enterprise bundle ACL policy for HTTP
activate/deactivate controls only. Enterprise-mode HTTP activation now requires
`enterprise_acl_grants` authorization for `resource_type="slot_bundle"`,
`resource_id=<target bundle id>`, and `permission="write"` before the activation
factory is called. Enterprise-mode HTTP deactivation checks the current active
bundle id with the same permission when an active bundle exists.

This update does not rewrite the P2 scope: CLI remains a local-operator trust
path, local-demo behavior remains unchanged, denied requests do not add
deny-audit events, no schema migration is added, and provider execution,
sandboxing, signing, YAML manifests, install APIs, SDK install APIs,
marketplace behavior, external gate closure, remote CI promotion, and maturity
promotion remain outside ADR-0060 and ADR-0061.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; SQLite through existing database bootstrap; FastAPI 0.123.8; Vue 3 + Vite |
| **Domain** | Slot Platform activation state, operator controls, and local governance audit |
| **Knowledge Risk** | MEDIUM - changes a feature default and adds persistent local state |
| **References Consulted** | `docs/reference/python/VERSION.md`, `standards/technical-preferences.md`, `docs/architecture/adr-0056-slot-loader-bundle-activation.md`, `docs/architecture/adr-0058-slot-platform-controlled-default-on.md`, `docs/architecture/adr-0059-tool-slot-domain-migration.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | settings defaults, SQLite repository and migration tests, bundle activation persistence integration tests, API/CLI activate-deactivate tests, Web store/view tests, route authority sync, docs/governance validators, plan maturity honesty, full local regression |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0052 (Slot Kernel, Bundles, Policy, and Lifecycle), ADR-0056 (Slot Loader and Bundle Activation), ADR-0058 (Slot Platform Controlled Default On), ADR-0059 (Tool Slot Domain Migration) |
| **Extends** | ADR-0056 by replacing process-local-only activation with persisted local alpha activation and adding deactivate surfaces |
| **Supersedes** | ADR-0056's non-persistent activation decision and default-off loader posture; ADR-0058's default-off loader guidance and "persistent bundle activation is not delivered by P0" block |
| **Enables** | Later operator policy, enterprise allowlist, and durable Slot Center management stories |
| **Blocks** | Any claim that third-party provider execution, sandboxing, cryptographic signing, YAML manifests, marketplace behavior, enterprise bundle ACL policy, or full plugin runtime is delivered by P2 |

## Context

ADR-0056 intentionally rejected persistence because authorization, migration,
conflict, and rollback policy were not yet defined. ADR-0058 then kept
`slot_loader` default off while promoting only the built-in consumer path.

P2 now needs a real Slot Center control loop: backend activation already
existed, but Web could only read slot and bundle rows, and process restarts lost
the active bundle. The platform still remains local alpha, so this decision
keeps the persistent state narrow: one active built-in bundle id, no automatic
activation, and no third-party code execution.

## Constraints

- Keep `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.
- Preserve `latest_remotely_verified_sha`; this is local evidence only until
  remote CI is actually run.
- Keep external/operator gates `S017-003`, `W3-live`, `AUTH-prod`, and
  `S017-007` open.
- Do not auto-activate `bundle.local_analyst` or any other bundle.
- Keep bundle activation limited to registered built-in bundles.
- Keep disk manifests manifest-only; do not import provider entrypoints.
- Keep `slot_install`, `slot_enforcement`, `slot_ui`, and
  `python_analysis_enabled` default off.
- Defer enterprise bundle ACL and allowlist enforcement to a later decision.

## Decision

Add the `ISlotActivationRepository` port and a SQLite implementation backed by
`slot_activation_state`:

```sql
CREATE TABLE IF NOT EXISTS slot_activation_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  bundle_id TEXT,
  activated_at TEXT,
  actor_hash TEXT
)
```

Activation writes one row, overwriting any previous active bundle. Deactivation
clears the row. `build_builtin_slot_kernel()` and bundle row construction read
the repository when `slot_loader` is enabled and hydrate the in-process
activation cache before applying `SlotPolicy`.

Expose operator controls through:

- `POST /v1/slot-bundles/{bundle_id}/activate`;
- `POST /v1/slot-bundles/active/deactivate`;
- `doge slots bundle activate <bundle_id> [--json]`;
- `doge slots bundle deactivate [--json]`;
- Web Slot Center activate/deactivate buttons.

Activation and deactivation append local governance audit events through
`enterprise_audit_events` when a governance repository is available. The event
records the action, bundle id, tenant id, actor hash, and request id context
available from the caller.

Change `DOGE_FEATURE_SLOT_LOADER` default to on. Operators can still opt out
with `DOGE_FEATURE_SLOT_LOADER=0`, which disables loader/activation routes and
commands.

## Answers To ADR-0056 Rejection Reasons

| Concern | P2 Answer |
|---------|-----------|
| Authorization | HTTP controls use the existing gateway auth context and record audit metadata; enterprise bundle ACL policy is explicitly deferred to P2.5 rather than silently implied. |
| Migration | The state table is added through an idempotent `Migration("slots", "bundle_activation_state", ...)` and the canonical `agent_schema.sql`. |
| Conflict | Local alpha assumes one daemon operator path. Multiple writers use last-writer-wins SQLite state plus audit events; startup reads the stored active bundle. |
| Rollback | `DOGE_FEATURE_SLOT_LOADER=0` disables activation surfaces and ignores persisted active state. SQLite writes are transactional through the existing connection layer. |

## Alternatives Considered

### Alternative 1: Keep activation process-local

- **Description**: Leave ADR-0056 unchanged and only add Web buttons over the
  existing in-memory state.
- **Pros**: Smallest persistence blast radius.
- **Cons**: Web Slot Center would still lose state on restart and would not be a
  real operator control surface.
- **Rejection Reason**: P2's purpose is persistent bundle activation.

### Alternative 2: Persist per-slot enable/disable state

- **Description**: Store individual slot enablement and calculate bundles as
  presets over that state.
- **Pros**: More flexible long-term Slot Center model.
- **Cons**: Requires conflict resolution, dependency validation, partial bundle
  UX, and enterprise policy semantics not yet designed.
- **Rejection Reason**: P2 only needs one active built-in bundle record.

### Alternative 3: Auto-activate `bundle.local_analyst`

- **Description**: Make the local analyst bundle active by default when
  `slot_loader` is on.
- **Pros**: Demonstrates bundle policy without operator action.
- **Cons**: It can exclude route/discovery slots from the active policy and
  make Slot Center self-inconsistent.
- **Rejection Reason**: Default empty activation is safer; operators activate
  bundles explicitly.

## Consequences

### Positive

- Slot Center is now an actual local control surface, not read-only metadata.
- Active bundle state survives process restart.
- Operators can roll back through either deactivation or
  `DOGE_FEATURE_SLOT_LOADER=0`.
- Default local behavior better matches the OpenClaw-like slot platform alpha
  story while preserving the provider-execution safety boundary.

### Negative

- Local startup now reads one additional SQLite table when `slot_loader` is on.
- Operators with `DOGE_SLOT_MANIFEST_DIRS` set will load manifest-only disk
  records by default unless they opt out.
- Persistent state can be stale if a future build removes a bundle id; startup
  must fail closed or ignore invalid activation according to existing bundle
  validation behavior.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Loader default-on is mistaken for provider execution | MEDIUM | HIGH | ADR/docs/evidence repeat that manifests remain manifest-only and entrypoints are never imported. |
| Persisted bundle excludes discovery routes | MEDIUM | MEDIUM | No bundle is auto-activated; operators can deactivate; Web still lists configured bundles before explicit activation. |
| Audit repository unavailable in local tests | MEDIUM | LOW | Activation still succeeds; audit append is best-effort through the injected/default governance repository. |
| Route docs drift after deactivate endpoint | LOW | MEDIUM | Route coverage and governance sync tests assert the 97-route table. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/fastapi-service.md` | API route table must remain the auditable FastAPI contract. | Adds the deactivate route to the canonical 97-route authority. |
| `docs/architecture/adr-0056-slot-loader-bundle-activation.md` | SlotLoader and bundle activation must remain safe and manifest-only. | Keeps loader manifest-only while adding persisted activation state. |
| `docs/architecture/adr-0058-slot-platform-controlled-default-on.md` | Local defaults must preserve safety boundaries. | Defaults loader on only after activation persistence tests, while keeping install/enforcement/UI/execution off. |

## Migration Plan

1. Add the activation repository port, SQLite implementation, schema, and
   migration manifest.
2. Hydrate `SlotBundleActivationState` from persistence inside slot kernel and
   bundle row builders.
3. Write-through activation/deactivation to the repository and local audit log.
4. Add HTTP/CLI deactivate surfaces and Web Slot Center activate/deactivate
   controls.
5. Flip `slot_loader` defaults in settings and lifecycle metadata.
6. Update route authority, configuration, maturity, session state, evidence, and
   the P2 source plan.
7. Run focused tests, full local gates, docs validators, plan closure, and
   whitespace checks.

## Validation Criteria

- `FeatureConfig()` defaults `slot_loader` to true and keeps install,
  enforcement, UI slots, and Python analysis false.
- A bundle activated through repository-backed construction remains active after
  rebuilding the kernel with the same database.
- Deactivation clears the repository and all bundle rows report inactive.
- API and CLI activate/deactivate paths are gated by `slot_loader` and return a
  disabled response or 404 when explicitly opted out.
- Web Slot Center can activate and deactivate bundles through store actions.
- Route authority documents 97 product routes and matches live FastAPI routes.
- Full local Python/Web/SDK/governance validation remains green.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0052: Slot Kernel, Bundles, Policy, and Lifecycle
- ADR-0056: Slot Loader and Bundle Activation
- ADR-0058: Slot Platform Controlled Default On
- ADR-0059: Tool Slot Domain Migration
