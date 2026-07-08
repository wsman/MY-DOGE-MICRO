# ADR-0063: Slot Runtime Permission Interception and Subprocess Hardening

## Status

Accepted

## Date

2026-07-08

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P4 extends the Slot Platform from resolution-time permission checks to a
feature-flagged in-process runtime interception layer for built-in slot calls.
The new `DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION` flag defaults off and is
independent from `DOGE_FEATURE_SLOT_ENFORCEMENT`.

When enabled, slot-owned tool executors and slot factories run with a
context-var carrying the current slot id and `SlotPermissions`. Guard wrappers
then mediate known ports:

- secret access through `ISecretProvider.get_secret(name)`;
- database-backed service/repository calls through read/write method
  classification;
- network calls through model/backend `chat()` and market data
  `connect()` / `download_kline()`.

P4 also hardens the existing `SubprocessCodeExecutor` used by optional Python
analysis. It now runs in a scratch cwd and with a sanitized environment that
removes canonical and pattern-matched secret variables.

This ADR releases only the prior "no db/secret/network interception" invariant
for built-in slot-aware in-process paths, plus the prior un-hardened subprocess
cwd/env behavior. It does not add provider entrypoint execution, OS/container or
WASM isolation, filesystem mediation, YAML manifests, HTTP install APIs, SDK
install APIs, marketplace behavior, external gate closure, remote CI promotion,
or maturity promotion.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; contextvars; existing Slot Platform contracts; subprocess Python analysis executor |
| **Domain** | Slot Platform runtime governance / local alpha sandboxing baseline |
| **Knowledge Risk** | MEDIUM - in-process guard semantics and subprocess hardening boundaries |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/architecture/adr-0055-slot-enforcement.md`, `docs/architecture/adr-0062-slot-cryptographic-signing.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | runtime access unit tests, subprocess env/cwd tests, settings/capability tests, slot boundary/parity tests, docs/governance validators, alpha maturity honesty, acceptable-open plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0055 (Slot Permission and Health Enforcement), ADR-0062 (Slot Cryptographic Signing) |
| **Extends** | ADR-0055 by adding runtime resource interception behind a separate flag |
| **Supersedes** | ADR-0055 Alternative 3 rejection only for the limited P4a in-process db/secret/network guard and P4b-lite subprocess env/cwd hardening |
| **Enables** | Later P5 provider execution analysis after signing, guard seams, audit events, and stronger sandbox design are evaluated |
| **Blocks** | Any claim that P4 is OS/container/WASM sandboxing, filesystem mediation, malicious-code containment, third-party provider execution, marketplace install, or an external plugin ecosystem |
| **Ordering Note** | ADR-0055 remains the SlotKernel resolution-time admission decision. ADR-0063 adds an independent runtime context/guard layer. |

## Context

Before P4, `SlotPermissions` declared filesystem, network, shell, database, and
secret needs, but runtime code could still call available process ports after a
slot contribution resolved. ADR-0055 intentionally stopped at SlotKernel
admission checks for forbidden risk, shell permission, and health.

P3 added cryptographic manifest signing, but signing alone is not enough to
permit provider execution. The platform needs a local guard seam that makes
built-in slot declarations coherent during runtime execution and produces audit
evidence for denied access before any P5 execution decision.

The existing Python analysis path is not slot-owned. It remains separately
gated by `DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED`, but it was the one code
execution surface already present in the repository, so P4 hardens its
subprocess env/cwd behavior without changing its default-off posture.

## Constraints

- Keep `DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION` default `false`.
- Keep `DOGE_FEATURE_SLOT_ENFORCEMENT`, `DOGE_FEATURE_SLOT_INSTALL`,
  `DOGE_FEATURE_SLOT_UI`, and `DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED` default
  off.
- Keep flag-off and no-slot-context legacy paths unchanged.
- Keep `doge.platform.slots` pure: no config, infrastructure, bootstrap,
  interface, application-tool, or product imports.
- Denied accesses raise `SlotPermissionViolation` and emit best-effort
  `slot_permission_violation` audit events.
- P4 guards only known ports. Direct `os`, `sqlite3`, `socket`, or filesystem
  imports by trusted in-process code are not contained.
- Filesystem mediation, provider package execution, process/container/WASM
  isolation, and Windows hard sandboxing remain P5 or later work.
- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.

## Decision

Add `doge.platform.slots.runtime_access` with:

- `SlotPermissionContext`;
- `SlotAccessEvent`;
- `SlotPermissionViolation`;
- `slot_permission_context()`;
- `current_slot_permissions()`;
- `guard_secret_provider()`;
- `guard_database_port()`;
- `guard_network_port()`;
- `slot_scoped_executor()` and `slot_scoped_object()`;
- `SandboxedSlotRuntimeExecutor`.

Add the core port `ISlotRuntimeExecutor` and a fail-closed
`DisabledSlotRuntimeExecutor`. Bootstrap exposes `build_slot_runtime_executor()`
and returns the disabled executor unless
`DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION=1`.

Bootstrap slot factories wrap built-in slot execution paths:

- tool slot executors are wrapped at `ToolRegistry.include_descriptors()`;
- model slot factories receive a guarded secret provider, construct under slot
  context, and return a slot-scoped network-guarded backend;
- data source factories construct under slot context and return slot-scoped
  network-guarded sources;
- workflow, document, gateway, eval, and UI facet factories or metadata reads
  run under slot context where applicable.

Tool service dependency factories return database-guarded service/repository
objects when runtime interception is enabled. The DB guard classifies method
names as read or write. `database=none` denies all DB-port calls;
`database=read` allows reads and denies writes; `database=write` allows both.

Secret access is exact-name based. A slot declaring
`secrets=("kimi.api_key",)` may read only `kimi.api_key`.

Network access is opt-in. `network="allow"` permits guarded network methods;
`network="none"` denies guarded `chat`, `connect`, and `download_kline` calls.

`SubprocessCodeExecutor` now:

- uses a scratch directory as child cwd;
- passes a minimal sanitized env;
- removes canonical secret-bearing env vars such as `DEEPSEEK_API_KEY`,
  `MOONSHOT_API_KEY`, `KIMI_API_KEY`,
  `DOGE_AUTH_STATIC_BEARER_TOKEN`, and
  `DOGE_SLOT_TRUSTED_PUBLISHER_KEYS`;
- removes variables matching API-key, secret, or token patterns;
- keeps the existing [1.0, 10.0] timeout clamp and substring denylist.

## Alternatives Considered

### Alternative 1: Wait for full OS/container/WASM sandboxing

- **Pros**: Avoids any ambiguity about the security boundary.
- **Cons**: Leaves SlotPermissions incoherent during built-in runtime execution
  and gives P5 no tested guard seam.
- **Rejection Reason**: P4 deliberately creates a limited, honest, default-off
  in-process baseline before provider execution.

### Alternative 2: Merge runtime interception into `slot_enforcement`

- **Pros**: Fewer feature flags.
- **Cons**: Confuses SlotKernel admission checks with per-call resource
  mediation and makes rollback less precise.
- **Rejection Reason**: ADR-0055 remains resolution-time enforcement. Runtime
  interception is a separate risk surface.

### Alternative 3: Guard filesystem access in P4

- **Pros**: More complete permission coverage.
- **Cons**: The codebase does not yet have a single `IFilesystem` port, so a
  filesystem guard would either be partial or would require a broader port
  migration.
- **Rejection Reason**: Filesystem mediation is deferred to P5 with real
  sandbox design.

## Consequences

### Positive

- Built-in slot `network`, `database`, and `secrets` declarations now have a
  runtime enforcement path when the P4 flag is enabled.
- Permission violations are explicit and auditable.
- Secret-provider and data/model network seams are ready for P5 hardening.
- Python analysis subprocesses no longer inherit the operator's secret env or
  project cwd.

### Negative

- The guard is not malicious-code containment; in-process code can bypass it by
  skipping guarded ports.
- DB read/write classification is method-name based and must be refined as more
  repositories are slot-owned.
- Audit emission is best-effort to avoid masking the original denial.
- Windows subprocess hardening remains a soft boundary.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Operators read P4 as a full sandbox | MEDIUM | HIGH | ADR, CDD, maturity, configuration docs, and evidence repeat the in-process/soft-boundary limits. |
| A write method is misclassified as read | MEDIUM | MEDIUM | Conservative write prefixes cover common mutations; focused tests cover denial behavior; P5 must replace this with stronger mediation. |
| Direct legacy/MCP factories bypass slot context | MEDIUM | MEDIUM | P4 documents bypasses and keeps legacy no-context paths allowed for parity. |
| Env scrub removes a needed child-process variable | LOW | MEDIUM | Safe essentials are preserved; Python analysis remains default off. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/p4-slot-runtime-interception.md` | Built-in slot permissions need runtime coherence before P5 provider execution. | Adds context-var slot identity, port guards, runtime executor builder, and violation audit payloads. |
| `design/cdd/sprint-045-slot-enforcement.md` | Sprint 045 admission enforcement should remain distinct. | Adds a later status note; does not change ADR-0055's SlotKernel contract. |
| `docs/progress/runtime-maturity.yaml` | Slot Platform maturity must remain experimental. | Records P4 as local experimental without closing production or external gates. |

## Performance Implications

- **CPU**: one lightweight context lookup and method-name classification for
  guarded calls.
- **Memory**: negligible wrapper/context state.
- **I/O**: denied calls may append one audit event to local SQLite governance
  state.
- **Network**: no additional network calls are introduced.

## Migration Plan

1. Add runtime access context and guard wrappers in `doge.platform.slots`.
2. Add `ISlotRuntimeExecutor`, `DisabledSlotRuntimeExecutor`, and
   `SandboxedSlotRuntimeExecutor`.
3. Add `DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION`, lifecycle metadata, and
   capability discovery.
4. Wrap slot-aware tool, model, data, and factory paths in bootstrap.
5. Wrap tool-service dependency factories with DB guards.
6. Harden `SubprocessCodeExecutor` env and cwd behavior.
7. Add focused runtime/subprocess/settings/capability tests.
8. Update ADR/CDD/maturity/configuration/session/evidence/source-plan records.

## Validation Criteria

- `slot_runtime_interception` defaults off.
- Flag-off and no-slot-context paths keep legacy behavior.
- Declared secrets are allowed and undeclared secrets are denied with audit.
- `database=read` allows read methods and denies write methods with audit.
- `database=none` denies DB-port calls with audit.
- `network=none` denies guarded network methods with audit.
- `network=allow` permits guarded network methods.
- Disabled slot runtime executor fails closed.
- Sandboxed slot runtime executor sets the current slot permission context.
- Subprocess Python analysis strips secret env vars and runs from a scratch cwd.
- Slot boundary, slot parity, and existing install/enforcement tests remain
  green.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0055: Slot Permission and Health Enforcement
- ADR-0057: Third-party Slot Install Preview
- ADR-0062: Slot Cryptographic Signing
