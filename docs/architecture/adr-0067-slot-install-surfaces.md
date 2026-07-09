# ADR-0067: Slot Install Surfaces and Operator Controls

## Status

Accepted

## Date

2026-07-09

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P9 releases the previous "no HTTP install API" and "no SDK install API"
deferrals for the local Slot Platform alpha. The install operation remains a
local-path, default-off, server-side operation gated by
`DOGE_FEATURE_SLOT_INSTALL`.

The new surface is:

- `POST /v1/slots/install` with JSON `{ "source": "<local path or slot dir>" }`;
- Python SDK `PlatformResource.list_slots()`, `get_slot()`, and
  `install_slot(source)` plus async equivalents;
- TypeScript SDK `platform.listSlots()`, `getSlot()`, and
  `installSlot(source)`;
- Web Slot Center install modal gated by `VITE_DOGE_FEATURE_SLOT_INSTALL_UI`;
- active built-in bundle policy that still filters unrelated built-ins while
  allowing explicitly installed slot ids.

P9 does not add URL fetch, upload install, YAML manifests, marketplace/catalog
behavior, client-side provider import, default-on install, production readiness,
or external gate closure. Provider execution remains governed separately by
ADR-0064 and ADR-0065 and still requires its own default-off gates.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; FastAPI; existing Python SDK; TypeScript SDK; Vue 3 + Pinia + Naive UI |
| **Domain** | Slot Platform install / SDK / Web operator controls |
| **Knowledge Risk** | MEDIUM - write API for local slot installation must preserve auth, ACL, audit, rollback, and signing gates |
| **References Consulted** | `docs/architecture/adr-0054-web-slot-center.md`, `docs/architecture/adr-0057-third-party-slot-install-preview.md`, `docs/architecture/adr-0065-provider-package-identity.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | HTTP install contract tests, install rollback tests, SDK contract parity, TS SDK tests, Web store/modal tests, route-doc coverage, docs/governance validators |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0015 (Enterprise Identity and Access Boundary), ADR-0054 (Web Slot Center), ADR-0057 (Third-party Slot Install Preview), ADR-0060 (Persistent Slot Bundle Activation), ADR-0061 (Enterprise Bundle ACL Gate), ADR-0062 (Slot Cryptographic Signing), ADR-0065 (Provider Package Identity) |
| **Extends** | ADR-0054 by adding a default-off install UI, ADR-0057 by adding HTTP/SDK install surfaces, ADR-0065 by preserving package-aware install copying, and ADR-0060 by allowing explicit installed slot ids under active built-in bundles |
| **Supersedes** | ADR-0057's HTTP install route and SDK slot-client deferral; ADR-0058's "no HTTP install APIs / SDK install APIs" statement only for default-off local install surfaces |
| **Enables** | Later operator-governed install lifecycle, persistent per-slot enablement, and marketplace/catalog decisions |
| **Blocks** | Any claim that P9 adds marketplace install, YAML manifests, remote URL install, upload install, default-on third-party execution, OS/container/WASM sandboxing, external gate closure, or production plugin readiness |

## Context

Before P9, local operators could install slots only through `doge slots install`.
That command already validated manifests, enforced local install policy, verified
v2/v3 sidecars, and copied v3 package directories when package identity was
available. The daemon, SDKs, and Web Slot Center could discover slots but could
not initiate an install.

That left four practical gaps:

1. no audited HTTP write path for daemon operators;
2. no SDK methods for install/list/get slot workflows;
3. no Web install UX;
4. active built-in bundle policy could accidentally hide explicitly installed
   slots because bundle allowlists contain only built-in slot ids.

P9 closes those local operator-surface gaps while preserving the safety boundary:
the server still performs installation, SDK/Web clients do not parse or import
provider code, and provider execution remains separately gated.

## Constraints

- Keep `DOGE_FEATURE_SLOT_INSTALL` default `false`.
- Keep `VITE_DOGE_FEATURE_SLOT_INSTALL_UI` default `false`.
- Require `DOGE_FEATURE_SLOT_PLATFORM=1` and `DOGE_FEATURE_SLOT_LOADER=1` for
  install.
- Install from local filesystem path only; do not fetch URLs or accept uploads.
- Read and validate the manifest id before mutating `DOGE_SLOT_INSTALL_DIR`.
- In enterprise mode, require both `DOGE_SLOT_ENTERPRISE_ALLOWLIST` and an
  enterprise ACL grant for `resource_type=slot`, `resource_id=<slot id>`,
  `permission=write`.
- Append `slot_install` audit metadata for successful HTTP/SDK/CLI install paths
  that flow through bootstrap.
- Use staged install writes and cleanup on copy failure.
- Preserve JSON canonical manifest/signature semantics; YAML remains deferred.
- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.

## Decision

### HTTP Install

Add `POST /v1/slots/install` to the slot gateway router.

The route:

1. is gated by API token auth and `DOGE_FEATURE_SLOT_INSTALL`;
2. accepts `{ "source": "<path>" }`;
3. validates the source manifest before mutation;
4. applies enterprise ACL `slot:<slot id>:write` before install;
5. delegates to bootstrap `install_slot()`;
6. returns `SlotInstallResult.to_dict()`;
7. maps configuration and validation errors to safe HTTP errors.

The route is a local path install. It does not fetch remote URLs and does not
accept uploaded packages.

### Installer Rollback

`SlotInstaller.install()` writes new installs into a stage directory and promotes
that directory into `DOGE_SLOT_INSTALL_DIR` only after all required files are
copied. If copying fails, the stage directory is removed and no partial final
slot directory is left behind.

Existing same-digest installs keep the previous `already_installed` behavior.

### SDKs

Python and TypeScript SDKs extend their existing platform resources. P9 does not
introduce a separate slot-specific client namespace.

SDK install methods call the server route. They do not run local install policy,
verify signatures client-side, or import provider code.

### Web Install UI

The Web Slot Center adds a default-off "Install slot" button controlled by
`VITE_DOGE_FEATURE_SLOT_INSTALL_UI`. The modal accepts a source path, calls the
platform store install action, refreshes slot and bundle snapshots, and displays
`signature.status` plus install warnings.

### Active Bundle Policy

An active built-in bundle still filters unrelated built-in slots. P9 adds an
explicit installed-slot id set to `SlotPolicy`, supplied by bootstrap from slots
installed under `DOGE_SLOT_INSTALL_DIR`. Those explicit installed ids are allowed
under an active built-in bundle unless otherwise disabled by policy.

This is not a wildcard. Installed-slot allowance is derived from concrete
installed ids, and `disabled_slots` still wins.

## Alternatives Considered

### Alternative 1: Keep install CLI-only

- **Pros**: Smaller write surface.
- **Cons**: SDK/Web operators cannot perform the existing local install workflow.
- **Rejection Reason**: P9 needs operator controls, but can keep them default-off,
  audited, ACL-gated, and server-side.

### Alternative 2: Add remote URL install

- **Pros**: Closer to marketplace-like distribution.
- **Cons**: Requires fetch policy, digest pinning, trust roots, cache handling,
  and network abuse controls.
- **Rejection Reason**: URL install is a marketplace/trust-pipeline decision, not
  a P9 local surface.

### Alternative 3: Add YAML manifests

- **Pros**: Friendlier authoring format.
- **Cons**: Anchors, aliases, tags, parser dependency, and canonicalization risk
  complicate signed-manifest semantics.
- **Rejection Reason**: JSON remains canonical for signed manifests. YAML stays
  deferred.

## Consequences

### Positive

- Install is available from daemon, SDK, and Web operator surfaces.
- Enterprise install writes now have both allowlist and ACL checks.
- Successful install operations are auditable.
- Partial-copy failure no longer leaves a final install directory.
- Installed slots remain visible when a built-in bundle is active.

### Negative

- The daemon now has a write endpoint for local slot install.
- The Web install UI depends on a separate frontend flag and backend flag.
- Route authority and SDK parity need one more surface to maintain.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| HTTP install is mistaken for marketplace support | MEDIUM | HIGH | ADR/config/evidence state local path only; URL/upload/marketplace deferred. |
| Enterprise install bypasses governance | LOW | HIGH | Route validates manifest id before mutation and checks `resource_type=slot` ACL plus install allowlist. |
| Active-bundle policy admits too much | LOW | HIGH | Allowance uses explicit installed ids; disabled policy still wins; tests prove built-in filtering remains. |
| Partial install leaves inconsistent state | LOW | MEDIUM | Stage directory promotion and rollback tests. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/p9-install-surfaces.md` | Operators need HTTP/SDK/Web install controls for the existing local install workflow. | Adds default-off server route, SDK methods, and Web modal. |
| `design/cdd/p9-install-surfaces.md` | Install writes must be governed and auditable. | Adds enterprise slot ACL, existing allowlist/signature policy, and `slot_install` audit. |
| `design/cdd/p9-install-surfaces.md` | Installed slots must remain resolvable under active built-in bundles. | Adds explicit installed-slot ids to SlotPolicy. |

## Validation Criteria

- `POST /v1/slots/install` returns 404 when `slot_install` is disabled.
- Local-demo HTTP install returns install result and records `slot_install` audit.
- Invalid source maps to a safe 400.
- Enterprise deny fails before install directory mutation.
- Enterprise allow requires allowlist, verified signature, and slot ACL.
- Installer copy failure cleans the stage directory and leaves no final slot dir.
- Python SDK exposes sync and async `list/get/install` slot methods.
- TypeScript SDK exposes `listSlots/getSlot/installSlot` and passes SDK contract
  parity.
- Web install modal is default-off, calls the store action, refreshes slots and
  bundles, and surfaces signature status/warnings/errors.
- Active built-in bundle still filters unrelated built-ins while allowing
  explicit installed slot ids.
- Maturity posture remains experimental and all external gates remain open.

## Related Decisions

- [ADR-0054: Web Slot Center](adr-0054-web-slot-center.md)
- [ADR-0057: Third-party Slot Install Preview](adr-0057-third-party-slot-install-preview.md)
- [ADR-0060: Persistent Slot Bundle Activation](adr-0060-persistent-slot-bundle-activation.md)
- [ADR-0061: Enterprise Bundle ACL Gate](adr-0061-enterprise-bundle-acl.md)
- [ADR-0062: Slot Cryptographic Signing](adr-0062-slot-cryptographic-signing.md)
- [ADR-0065: Provider Package Identity](adr-0065-provider-package-identity.md)
