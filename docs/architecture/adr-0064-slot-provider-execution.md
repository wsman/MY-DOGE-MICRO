# ADR-0064: Slot Provider Execution

## Status

Accepted

## Date

2026-07-08

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P5 releases the previous blanket "no provider entrypoint import" invariant only
for a narrow, default-off local alpha path: installed slots may execute an
in-process importlib provider entrypoint when all provider-execution gates pass.

The default discovery path remains manifest-only. `SlotLoader` still returns
`ManifestOnlySlot` and does not import provider code. P5 adds a bootstrap-owned
`InstalledProviderSlot` wrapper because execution eligibility depends on
settings, trusted publisher keys, signing-key revocation storage, SlotKernel
admission, and runtime permission interception.

Provider execution is limited to these contribution facets:

- tools;
- model backends;
- workflow templates;
- data sources;
- document parsers.

Gateway routes, UI panels, watchers, eval suites, and governance policies were
not executable from installed third-party providers in P5. ADR-0068 later
releases `eval_suites`; ADR-0069 later releases static `ui_panels` metadata.
ADR-0070 later releases slot-scoped `watchers`. The other restricted facets
remained blocked at ADR-0070 acceptance; ADR-0071 later releases
`governance_policies`; ADR-0072 later releases provider `routes` with
namespace/auth constraints.

This ADR does not add OS/container/WASM sandboxing, filesystem mediation,
provider package signing, malicious-code containment, marketplace behavior,
HTTP install APIs, SDK install APIs, YAML manifests, remote CI promotion,
external gate closure, or production maturity.

Status Update - 2026-07-08: ADR-0065 closes ADR-0064's package identity gap for
local installed providers. Provider execution now requires a v3 package-aware
signature and loads entrypoint code from the installed signed `package/`
directory. ADR-0065 does not change this ADR's remaining runtime boundary: the
provider still runs in-process.

Status Update - 2026-07-09: ADR-0066 adds default-off Windows Job Object
resource limits only for `run_python_analysis` code strings. It does not isolate
ADR-0064 provider contribution objects, which remain trusted-publisher,
package-identified, in-process Python objects under the P4 guarded-port model.

Status Update - 2026-07-09: ADR-0067 adds HTTP, Python SDK, TypeScript SDK, and
Web install surfaces for local slot install. Those surfaces do not change this
ADR's provider execution gates: provider import remains default off and still
requires slot install, runtime interception, verified v3 package-aware signature,
revocation check, enterprise allowlist when applicable, and SlotKernel admission.

Status Update - 2026-07-09: ADR-0068 releases only the `eval_suites` restricted
facet for installed, v3 package-signed, operator-gated providers. Gateway
routes, UI panels, watchers, and governance policies remain restricted.

Status Update - 2026-07-09: ADR-0069 releases only the `ui_panels` restricted
facet for installed, v3 package-signed, operator-gated providers, as static
metadata consumed by the existing UI registry. Gateway routes, watchers, and
governance policies remain restricted.

Status Update - 2026-07-09: ADR-0070 releases only the `watchers` restricted
facet for installed, v3 package-signed, operator-gated providers. Gateway
routes and governance policies remain restricted.

Status Update - 2026-07-09: ADR-0071 releases only the `governance_policies`
restricted facet for installed, v3 package-signed, operator-gated providers.
Provider policies use monotonic tool-entitlement composition and slot-scoped
factory/checker execution. Gateway routes remain restricted.

Status Update - 2026-07-09: ADR-0072 releases the final `routes` restricted
facet for installed, v3 package-signed, operator-gated providers. Non-built-in
provider routes must mount under `/v1/slot-providers/<slot_id>`, require the
existing API token dependency, and run route handlers under slot permission
context when runtime interception is enabled.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; importlib; Ed25519 manifest signatures; SQLite revocation repository; existing Slot Platform contracts |
| **Domain** | Slot Platform local alpha provider execution |
| **Knowledge Risk** | HIGH - importing provider code runs in-process Python top-level code |
| **References Consulted** | `docs/architecture/adr-0057-third-party-slot-install-preview.md`, `docs/architecture/adr-0062-slot-cryptographic-signing.md`, `docs/architecture/adr-0063-slot-runtime-permission-interception.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | provider execution gate tests, settings/capability tests, CLI/API status tests, slot boundary tests, install/signing tests, docs/governance validators, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0055 (Slot Permission and Health Enforcement), ADR-0056 (Slot Loader and Bundle Activation), ADR-0057 (Third-party Slot Install Preview), ADR-0062 (Slot Cryptographic Signing), ADR-0063 (Slot Runtime Permission Interception and Subprocess Hardening) |
| **Extends** | ADR-0057 by adding an execution-eligible installed-provider path; ADR-0062 by consuming verified Ed25519 trust and revocation; ADR-0063 by requiring runtime interception before provider execution |
| **Supersedes** | The blanket "provider entrypoints are never imported" statement only for P5's explicit, installed, trusted, revocation-checked, runtime-intercepted, default-off local path |
| **Enables** | Later hardened sandbox, package signing, and operator-governed third-party slot lifecycle work |
| **Blocks** | Any claim that P5 is production plugin execution, OS/container/WASM sandboxing, marketplace install, HTTP/SDK install, provider package signing, filesystem mediation, malicious-code containment, external gate closure, or maturity promotion |

## Context

Sprints 046 and 047 deliberately separated manifest loading/install from code
execution. P3 added Ed25519 manifest signatures and key revocation. P4 added
in-process db/secret/network runtime interception for guarded ports.

Those prerequisites make a constrained local alpha provider execution path
testable, but they do not make third-party Python safe. Importing an entrypoint
still runs top-level code in the current process. P5 therefore makes execution
explicit, default off, restricted by facet type, and visibly reported through
slot discovery status.

## Constraints

- Keep `DOGE_FEATURE_SLOT_PROVIDER_EXECUTION` default `false`.
- Require `slot_platform`, `slot_loader`, and `slot_install` to be enabled.
- Execute only installed manifests under `DOGE_SLOT_INSTALL_DIR`; manifests
  loaded from `DOGE_SLOT_MANIFEST_DIRS` stay manifest-only.
- Reverify the installed manifest and package-aware signature at resolve time.
- Require v3 signature status `verified`, trusted publisher key configuration,
  `revocation_checked=true`, and a non-revoked signing key.
- In `DOGE_AUTH_MODE=enterprise`, require `DOGE_SLOT_ENTERPRISE_ALLOWLIST`.
- Require `DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION=1`.
- Preserve SlotKernel admission/enforcement before `resolve()`.
- Keep `doge.platform.slots` pure; execution wrapper lives in bootstrap.
- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.

## Decision

Add `DOGE_FEATURE_SLOT_PROVIDER_EXECUTION` and expose it through lifecycle
metadata and capability discovery.

Add `doge.bootstrap.runtime_factories.provider_slot.InstalledProviderSlot`.
It:

1. returns the installed manifest for discovery without importing provider
   code;
2. evaluates provider-execution eligibility without import;
3. reverifies the Ed25519 sidecar and signing-key revocation at resolve time;
4. imports the dotted provider entrypoint with importlib only after all gates
   pass;
5. requires the entrypoint to instantiate `doge.platform.slots.ISlot`;
6. verifies provider manifest id, type, and `provides` match the installed
   manifest;
7. rejects restricted contribution facets after provider resolve.

`build_slot_status_rows()` now reports:

- `execution_eligible`;
- `execution_blockers`;
- `execution.mode`;
- `execution.signature`.

CLI `doge slots list --json`, `doge slots show`, and `/v1/slots` inherit the
same status rows. These discovery surfaces do not import providers.

## Alternatives Considered

### Alternative 1: Keep all installed slots manifest-only

- **Pros**: Lowest execution risk.
- **Cons**: Cannot test the OpenClaw-like provider seam after signing and
  runtime interception work.
- **Rejection Reason**: P5 needs a narrow proof path while keeping the default
  and non-installed discovery paths manifest-only.

### Alternative 2: Import provider entrypoints in `SlotLoader`

- **Pros**: Simpler loader semantics.
- **Cons**: Violates `doge.platform.slots` purity and turns discovery into code
  execution.
- **Rejection Reason**: Loader must remain a pure manifest validator. Execution
  needs bootstrap-owned settings, signing, revocation, and runtime guards.

### Alternative 3: Enable all contribution facets

- **Pros**: Closer to a full plugin ecosystem.
- **Cons**: Gateway routes, watchers, eval, governance, and UI panels have
  broader policy and blast-radius concerns.
- **Rejection Reason**: P5 only proves the lower-risk local execution facets.

## Consequences

### Positive

- The platform can prove a real installed-provider execution seam without
  changing default behavior.
- Discovery surfaces show why a slot is or is not execution eligible.
- Signature, revocation, enterprise allowlist, runtime interception, and
  SlotKernel admission are all part of the execution gate.
- The pure slot contract package remains free of settings/infrastructure
  dependencies.

### Negative

- In-process provider import is not malicious-code containment.
- P5 originally signed only the manifest. ADR-0065 requires v3 package-aware
  signatures for provider execution; transitive dependency packages remain
  unsigned by slot sidecars.
- Active bundle policy can still disable installed slots because built-in
  bundles do not include third-party slot ids.
- Filesystem, socket, raw sqlite, subprocess, and direct OS APIs are not
  mediated unless provider code voluntarily uses guarded ports.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Operators mistake P5 for production-safe plugins | MEDIUM | HIGH | ADR/CDD/config/maturity/evidence repeat default-off local alpha and no OS sandbox. |
| Signed manifest points at swapped local package code | MEDIUM | HIGH | ADR-0065 resolves the local package identity gap with v3 package-aware signatures and path-confined imports. |
| Provider import side effects bypass guards | HIGH | HIGH | P5 requires runtime interception but documents it as in-process guarded-port mediation only. |
| Restricted facet sneaks into execution | LOW | HIGH | `InstalledProviderSlot` rejects restricted contribution fields after resolve. |

## Validation Criteria

- `slot_provider_execution` defaults off and appears in lifecycle/capability
  metadata.
- Installed slots remain manifest-only when the flag is off.
- Status rows report execution eligibility and blockers without importing
  provider code.
- Missing, untrusted, invalid, revoked, or manifest-only v2 signatures block
  execution.
- Resolve-time verification repeats package-aware signature and revocation
  checks.
- Enterprise mode requires `DOGE_SLOT_ENTERPRISE_ALLOWLIST`.
- Runtime interception must be enabled before provider import.
- Only tools, model backends, workflow templates, data sources, and document
  parsers are allowed.
- `doge.platform.slots` boundary tests remain green.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0057: Third-party Slot Install Preview
- ADR-0062: Slot Cryptographic Signing
- ADR-0063: Slot Runtime Permission Interception and Subprocess Hardening
- ADR-0065: Provider Package Identity
- ADR-0066: Code-String Isolation Prototype and Contribution Residual
