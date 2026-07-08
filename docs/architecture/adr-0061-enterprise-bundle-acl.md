# ADR-0061: Enterprise Bundle ACL Gate

## Status

Accepted

## Date

2026-07-08

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P2.5 closes the enterprise HTTP authorization gap left open by ADR-0060.
Enterprise-mode bundle activation and deactivation now require an
`enterprise_acl_grants` match before the router calls the activation factory.

The gate applies only to HTTP activate/deactivate controls:

- `POST /v1/slot-bundles/{bundle_id}/activate`
- `POST /v1/slot-bundles/active/deactivate`

It does not change local-demo behavior, CLI local-operator behavior,
third-party install preview policy, provider execution, sandboxing, signing,
YAML manifest parsing, marketplace behavior, remote CI posture, or the
platform maturity posture.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; FastAPI 0.123.8; SQLite enterprise governance repository; pytest 9.0.1 |
| **Domain** | API Design, Security, Slot Platform operator controls |
| **Knowledge Risk** | LOW - reuses existing enterprise ACL and FastAPI dependency patterns |
| **References Consulted** | `docs/reference/python/VERSION.md`, `standards/technical-preferences.md`, `docs/registry/architecture.yaml`, `docs/architecture/adr-0060-persistent-slot-bundle-activation.md`, `src/doge/interfaces/api/enterprise_access.py`, `src/doge/interfaces/gateway/routers/slots.py`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | enterprise HTTP activate/deactivate allow and deny tests, wildcard grant tests, tenant isolation tests, deny-does-not-persist test, local-demo and CLI regressions, docs/governance validators, source-plan maturity honesty, plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0015 (Enterprise Auth and Audit), ADR-0042 (Slot Platform Foundation), ADR-0052 (Slot Kernel, Bundles, Policy, and Lifecycle), ADR-0060 (Persistent Slot Bundle Activation) |
| **Extends** | ADR-0060 by adding enterprise HTTP write ACL checks before bundle activation/deactivation reaches the activation factory |
| **Supersedes** | ADR-0060's P2 deferral for enterprise bundle ACL policy, limited to HTTP activate/deactivate controls |
| **Enables** | Later operator policy and enterprise bundle governance work over the same `slot_bundle` resource type |
| **Blocks** | Any claim that P2.5 enables third-party provider execution, sandboxing, cryptographic slot signing, YAML manifests, HTTP install APIs, SDK install APIs, marketplace behavior, install allowlist expansion, remote CI closure, external gate closure, or production maturity promotion |
| **Ordering Note** | ADR-0060 remains the activation persistence decision. This ADR adds only the enterprise HTTP gate over that surface. |

## Context

### Problem Statement

ADR-0060 made bundle activation durable and exposed activation/deactivation
through HTTP, CLI, and Web Slot Center controls. It intentionally deferred
enterprise bundle ACL policy so that P2 would not silently imply a security
model that had not been tested.

After P2, an authenticated enterprise HTTP caller with access to the route could
activate or deactivate any built-in bundle. That was acceptable for local alpha
P2, but it left a direct mismatch with existing enterprise resource gates for
documents, tools, approvals, portfolios, and workflow templates.

P2.5 adds the missing gate without broadening the platform surface.

### Constraints

- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.
- Keep local-demo bundle activation/deactivation unchanged.
- Keep CLI activation/deactivation as a local-operator trust path outside HTTP
  enterprise ACL checks.
- Add no schema migration; `enterprise_acl_grants` already stores arbitrary
  `resource_type` values and `slot_bundle` is already used by slot-bundle audit
  events.
- Add no deny audit event because the shared `ensure_resource_access` pattern
  raises before backend work and does not record denied attempts.
- Keep frontend structure unchanged; existing generic error handling surfaces
  HTTP 403 responses.
- Do not change bundle definitions, activation persistence semantics, feature
  defaults, provider execution posture, install policy, signing, sandboxing, or
  marketplace behavior.

### Requirements

- Enterprise HTTP activate requires `resource_type="slot_bundle"`,
  `resource_id=<target bundle id>`, and `permission="write"`.
- Enterprise HTTP deactivate requires the same permission over the current
  active bundle id.
- Deactivate remains idempotent when there is no active bundle; no resource
  exists to authorize in that case.
- Denied activation must not write `slot_activation_state` and must not append a
  slot-bundle activate audit event.
- Granted activation/deactivation keeps the ADR-0060 audit behavior.
- Wildcard grant behavior remains owned by the existing enterprise governance
  repository: `resource_id="*"` and/or `permission="*"` can satisfy the check,
  while tenant and subject remain exact.

## Decision

Use the existing HTTP-layer `ensure_resource_access()` helper in
`src/doge/interfaces/gateway/routers/slots.py`.

Activation checks the target bundle before calling `deps.activate_slot_bundle`:

```python
ensure_resource_access(request, governance_repo, "slot_bundle", bundle_id, "write")
```

Deactivation reads the current active bundle from the injected activation
repository. If one exists, it checks that bundle before calling
`deps.deactivate_slot_bundle`:

```python
active_id = activation_repo.get_active().bundle_id
if active_id:
    ensure_resource_access(request, governance_repo, "slot_bundle", active_id, "write")
```

The gate is deliberately placed in the HTTP router instead of the activation
factory because the router owns `EnterpriseContext` through
`TenantContextMiddleware`, while the activation factory intentionally accepts
plain `tenant_id` and `actor_hash` values for HTTP and CLI callers.

### Architecture Diagram

```text
Enterprise HTTP caller
        |
        v
TenantContextMiddleware
        |
        v
/v1/slot-bundles/... route
        |
        v
ensure_resource_access(slot_bundle, bundle_id, write)
        |
        +--> deny: HTTP 403, no activation write, no slot-bundle audit
        |
        v
deps.activate_slot_bundle / deps.deactivate_slot_bundle
        |
        v
slot_activation_state + slot_bundle_* audit event
```

Local-demo requests pass through the existing helper's no-op local behavior.
CLI commands continue to call the backend factory directly as local operator
actions.

### Key Interfaces

Enterprise ACL grant shape:

```text
tenant_id=<exact tenant>
subject_hash=<exact caller hash>
resource_type=slot_bundle
resource_id=<bundle id> or *
permission=write or *
```

HTTP denial:

```json
{"detail": "slot_bundle access denied"}
```

Successful activation/deactivation payloads remain the ADR-0060 payloads.

## Alternatives Considered

### Alternative 1: Put ACL in the activation factory

- **Description**: Pass enterprise context into `activate_slot_bundle()` and
  `deactivate_slot_bundle()` and enforce there.
- **Pros**: Centralizes checks for all callers.
- **Cons**: Changes factory signatures, forces CLI to model enterprise
  identity, and mixes HTTP authorization context into local operator helpers.
- **Rejection Reason**: P2.5 only governs enterprise HTTP access. Existing
  HTTP resource gates already enforce at the router boundary.

### Alternative 2: Add a new slot-bundle permission vocabulary

- **Description**: Use separate permissions such as `activate` and
  `deactivate`.
- **Pros**: More expressive future policy.
- **Cons**: Introduces a new vocabulary before any consumer needs asymmetric
  control and diverges from existing write-style resource gates.
- **Rejection Reason**: `write` is sufficient for this alpha operator control
  surface and aligns with existing ACL usage.

### Alternative 3: Add deny-audit events

- **Description**: Append an audit row when an enterprise caller lacks the
  grant.
- **Pros**: More forensic detail.
- **Cons**: Diverges from the current `ensure_resource_access` contract and
  risks making P2.5 broader than the authorization gap it is closing.
- **Rejection Reason**: Keep P2.5 scoped to the existing ACL helper pattern.

## Consequences

### Positive

- Enterprise HTTP bundle activation/deactivation now requires explicit
  per-tenant, per-subject grant evidence.
- Denied HTTP activation fails before any persistent activation write or
  slot-bundle activate audit event.
- The implementation reuses the existing enterprise ACL contract instead of
  introducing a parallel policy system.
- Local-demo and CLI local-operator paths remain compatible with ADR-0060.

### Negative

- CLI still bypasses enterprise ACL by design. Operators must not treat the CLI
  as a multi-tenant HTTP authorization boundary.
- Deactivation authorization is based on the current active bundle. If a caller
  has no grant for that active bundle, they cannot deactivate it through HTTP.
- There is still no dedicated Web copy for the 403; the existing alert surfaces
  the generic error.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Enterprise operators expect CLI parity with HTTP ACL | MEDIUM | MEDIUM | ADR, configuration docs, maturity notes, and evidence state that CLI is a local-operator trust path. |
| Wildcard grant is too broad | MEDIUM | MEDIUM | Reuse existing governance repository semantics and keep tenant/subject exact. Operator policy can narrow grants. |
| Denied requests are not audit-recorded | MEDIUM | LOW | This matches current `ensure_resource_access`; future deny-audit should be a separate governance decision. |
| P2.5 is mistaken for a broader slot security release | MEDIUM | HIGH | ADR and evidence repeat the unchanged posture and the absence of provider execution, sandboxing, signing, install API, SDK install API, and marketplace behavior. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/fastapi-service.md` | HTTP routes must keep explicit auth/governance boundaries. | Adds `ensure_resource_access` at the slot-bundle activate/deactivate router boundary. |
| `docs/architecture/adr-0060-persistent-slot-bundle-activation.md` | P2 deferred enterprise bundle ACL policy rather than implying it. | Closes that deferral only for enterprise HTTP activate/deactivate controls. |
| `docs/architecture/adr-0015-enterprise-auth-and-audit.md` | Enterprise resource access should be tenant/subject scoped and auditable. | Reuses `enterprise_acl_grants` and preserves successful slot-bundle audit events. |

## Performance Implications

- **CPU**: One ACL lookup per enterprise HTTP activate/deactivate request.
- **Memory**: No material change.
- **Load Time**: No startup change.
- **Network**: No additional network dependency.
- **Storage**: No schema change; denied requests do not write activation state.

## Migration Plan

1. Import `ensure_resource_access` into the slot-bundle router.
2. Gate activate on the target bundle id with `slot_bundle`/`write`.
3. Gate deactivate on the currently active bundle id when one exists.
4. Extend route tests with enterprise allow, deny, wildcard, tenant isolation,
   deactivate allow/deny, audit, and idempotent no-active cases.
5. Extend persistence integration coverage so denied activation does not
   persist active state.
6. Update ADR-0060 status, architecture registry, maturity notes, session
   state, configuration reference, QA evidence, and the source plan.
7. Run focused tests, full local gates, docs/governance validators, plan
   closure, maturity honesty, and whitespace checks.

## Validation Criteria

- Enterprise HTTP activate without a matching grant returns 403.
- The same activate request with a matching exact grant returns 200 and writes
  one successful `slot_bundle_activate` audit event.
- Wildcard resource or permission grants behave according to the existing
  enterprise governance repository semantics.
- Tenant-scoped grants do not cross tenants or subjects.
- Enterprise HTTP deactivate without a grant for the active bundle returns 403.
- Enterprise HTTP deactivate with a grant for the active bundle returns 200 and
  clears persisted active state.
- Denied activation does not persist active bundle state after repository
  rebuild.
- Local-demo HTTP activation/deactivation and CLI activation/deactivation remain
  compatible with ADR-0060.

## Related Decisions

- ADR-0015: Enterprise Auth and Audit
- ADR-0042: Slot Platform Foundation
- ADR-0052: Slot Kernel, Bundles, Policy, and Lifecycle
- ADR-0060: Persistent Slot Bundle Activation
