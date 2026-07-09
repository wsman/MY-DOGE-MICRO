# ADR-0066: Code-String Isolation Prototype and Contribution Residual

## Status

Accepted

## Date

2026-07-08

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P8 adds a default-off isolation prototype for the one execution shape that can
be marshalled safely today: `run_python_analysis` code strings executed through
`ICodeExecutor.execute(code, timeout) -> ExecutionResult`.

The new `DOGE_FEATURE_SLOT_CODE_STRING_ISOLATION` flag defaults off. It does
not enable Python analysis by itself; operators must still set
`DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED=1` and
`DOGE_PYTHON_ANALYSIS_EXECUTOR=subprocess`.

When all gates are enabled on Windows, `SubprocessCodeExecutor` assigns the
child Python process to a Windows Job Object with per-process memory, job
memory, per-process user CPU time, kill-on-job-close, scratch cwd, scrubbed env,
wall-clock timeout, and deterministic cleanup. If P8 isolation is requested on
non-Windows hosts, the executor fails closed instead of silently falling back to
plain subprocess execution.

P8 does not isolate provider contribution objects. Installed slot tools, model
backends, workflows, data sources, and document parsers remain in-process Python
objects under the ADR-0064 provider path. P8 also does not add filesystem
mediation, raw network denial, malicious-code containment, container/WASM
sandboxing, marketplace behavior, remote CI promotion, external gate closure,
or production maturity.

This ADR uses the current checkout as the authority. ADR-0065 now covers local
provider package identity and package digest binding for installed provider
execution. P8 intentionally does not turn that package identity into runtime
containment: provider contribution objects remain in-process until a separate
provider-runner/container/WASM decision closes that residual.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python `>=3.10`; stdlib `subprocess`; stdlib `ctypes`; Windows Job Objects |
| **Domain** | Runtime security / code execution boundary |
| **Knowledge Risk** | MEDIUM - Windows Job Object ctypes structures and process-limit semantics |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/architecture/adr-0063-slot-runtime-permission-interception.md`, `docs/architecture/adr-0064-slot-provider-execution.md`, `docs/architecture/adr-0065-provider-package-identity.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md`, Microsoft Learn Job Object documentation |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | code executor unit tests, settings/capability lifecycle tests, provider regression tests, docs/governance validators, alpha maturity honesty, acceptable-open plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0013 (Tool Governance), ADR-0063 (Slot Runtime Permission Interception), ADR-0064 (Slot Provider Execution), ADR-0065 (Provider Package Identity) |
| **Extends** | ADR-0063 by hardening optional Python analysis beyond env/cwd; ADR-0064 by documenting provider contribution residuals; ADR-0065 by clarifying that package identity is not provider runtime containment |
| **Supersedes** | ADR-0063's "Windows subprocess hardening remains a soft boundary" only for Windows code-string resource limits; no provider-object isolation is superseded |
| **Enables** | Later hardened container/WASM/OS runner design for provider contribution objects |
| **Blocks** | Any claim that P8 is hardened provider isolation, filesystem mediation, raw network denial, malicious-code containment, marketplace install, external gate closure, or maturity promotion |
| **Ordering Note** | Provider contribution isolation needs a separate runner protocol. P8 intentionally uses `ICodeExecutor`, not the callable-shaped `ISlotRuntimeExecutor.run()` port. |

## Context

`ISlotRuntimeExecutor.run()` currently accepts a Python callable plus live
arguments. Built-in slot wrappers also rely on live callable, generator, and
async-generator object identity inside the current interpreter. That shape
cannot be moved to a subprocess without defining a new provider protocol.

`run_python_analysis` is different. It already crosses an explicit string-in,
primitive-out port:

```text
code: str + timeout: float -> ExecutionResult
```

That makes it the only current execution surface that can receive an isolation
prototype without changing slot contribution contracts.

P4 already scrubbed child-process environment variables and changed the cwd to
a scratch directory. P8 keeps those protections and adds OS-enforced resource
limits for Windows hosts.

## Constraints

- Keep `DOGE_FEATURE_SLOT_CODE_STRING_ISOLATION` default `false`.
- Keep `DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED` default `false`.
- Do not make Python analysis available when only the P8 flag is enabled.
- Fail closed when P8 isolation is requested on hosts where this prototype
  cannot establish a Windows Job Object.
- Use stdlib `ctypes`; do not add `pywin32`.
- Preserve the existing timeout clamp `[1.0, 10.0]`, scratch cwd, env scrub, and
  Windows `CREATE_NEW_PROCESS_GROUP` behavior.
- Do not claim provider contribution-object isolation.
- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.

## Decision

Add `slot_code_string_isolation` to `FeatureConfig` and `FEATURE_LIFECYCLES`
with env var `DOGE_FEATURE_SLOT_CODE_STRING_ISOLATION`, default `false`.

Expose `feature.slot_code_string_isolation` through capability discovery as a
high-risk runtime feature. Its metadata states:

- required companion gates are `python_analysis_enabled` and
  `python_analysis_executor=subprocess`;
- scope is `run_python_analysis` code strings only;
- provider contribution isolation is `not_provided`;
- non-Windows isolation mode is fail-closed.

Extend `SubprocessCodeExecutor` with:

- `isolation_enabled`;
- `CodeExecutionResourceLimits`;
- optional audit sink;
- `executor_name` values `subprocess`, `subprocess_job_object`, and
  `subprocess_isolation_unavailable`;
- `isolation_mode` values `subprocess_soft`, `windows_job_object`, and
  `unavailable_non_windows`;
- Windows Job Object setup through `ctypes`;
- resource-limit failures returned as `ExecutionResult(ok=False, error=...)`;
- best-effort audit events with `event_type=slot_resource_limit_exceeded`.

Bootstrap injects the isolated executor only when Python analysis is explicitly
enabled and `DOGE_PYTHON_ANALYSIS_EXECUTOR=subprocess`. Otherwise the existing
`DisabledCodeExecutor` or non-isolated subprocess behavior remains unchanged.

## Architecture Diagram

```text
ToolApplicationService.run_python_analysis
  -> QuantToolProvider.run_python_analysis
     -> ICodeExecutor.execute(code, timeout)
        -> DisabledCodeExecutor                       (default)
        -> SubprocessCodeExecutor                     (python analysis enabled)
        -> SubprocessCodeExecutor + Windows JobObject (P8 flag + Windows)
```

Provider contribution objects remain outside this diagram. They still execute
as in-process `ISlot` contributions under ADR-0064.

## Key Interfaces

```python
@dataclass(frozen=True)
class CodeExecutionResourceLimits:
    process_memory_bytes: int
    job_memory_bytes: int
    cpu_seconds: float

class SubprocessCodeExecutor(ICodeExecutor):
    isolation_enabled: bool
    executor_name: str
    isolation_mode: str
    def execute(self, code: str, timeout: float) -> ExecutionResult: ...
```

The audit payload is best-effort and intentionally dictionary-shaped to avoid
making infrastructure code depend on Slot Platform bootstrap types:

```json
{
  "event_type": "slot_resource_limit_exceeded",
  "resource_type": "code_string",
  "resource_id": "run_python_analysis",
  "executor": "subprocess_job_object",
  "isolation_mode": "windows_job_object"
}
```

## Alternatives Considered

### Alternative 1: Move provider contribution objects into subprocesses

- **Description**: Marshal installed slot tool/model/data/document contribution
  objects across an IPC boundary.
- **Pros**: Closer to production plugin isolation.
- **Cons**: Current contributions are live Python callables and objects; no
  provider RPC protocol exists.
- **Rejection Reason**: This would require a separate provider-runner ADR and
  would not be a narrow P8 change.

### Alternative 2: Extend `ISlotRuntimeExecutor.run()` for code strings

- **Description**: Reuse the existing callable-shaped slot runtime executor for
  `run_python_analysis`.
- **Pros**: Keeps the word "slot runtime executor" central.
- **Cons**: The port accepts callables, not code strings; adapting it would
  blur callable-object and code-string execution boundaries.
- **Rejection Reason**: `ICodeExecutor` is already the correct string-in,
  primitive-out port.

### Alternative 3: Add `pywin32`

- **Description**: Use pywin32 wrappers for Job Object APIs.
- **Pros**: Less ctypes structure code.
- **Cons**: Adds a native dependency and packaging surface for a local alpha
  prototype.
- **Rejection Reason**: stdlib `ctypes` is sufficient for the required Job
  Object calls.

## Consequences

### Positive

- Code-string Python analysis can be resource-limited on Windows when explicitly
  enabled.
- Default behavior stays disabled.
- The capability registry tells operators exactly what is and is not isolated.
- No new third-party dependency is introduced.
- Resource-limit failures are non-throwing and auditable.

### Negative

- Job Object assignment uses the stdlib subprocess process handle immediately
  after child creation; this is resource-limit isolation, not a pre-instruction
  malicious-code containment sandbox.
- POSIX hosts fail closed when the P8 flag is enabled because no POSIX hardened
  executor was accepted in this ADR.
- Direct absolute-path filesystem reads, raw network APIs, importlib bypasses,
  and subprocess attempts are not comprehensively sandboxed by P8.
- Provider contribution objects remain in-process.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Operators read P8 as full provider sandboxing | MEDIUM | HIGH | ADR, CDD, evidence, capability metadata, and maturity ledger repeat code-string-only scope. |
| Job Object ctypes structure drift or Windows API mismatch | LOW | HIGH | Focused tests cover setup seams; real Windows Python smoke exercises the Job Object path. |
| Resource-limit detection is conservative | MEDIUM | MEDIUM | Limit failures return fail-closed; future runner can use completion-port notifications. |
| Non-Windows users expect fallback execution under P8 | MEDIUM | MEDIUM | P8 flag fails closed off Windows; flag-off subprocess behavior remains available. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/p8-code-string-isolation.md` | Python analysis code strings need a default-off resource isolation prototype. | Adds `slot_code_string_isolation`, Windows Job Object resource limits, fail-closed non-Windows behavior, and audit metadata. |
| `design/cdd/p4-slot-runtime-interception.md` | P4 subprocess env/cwd hardening must remain honest about sandbox limits. | Extends only the code-string subprocess path and preserves P4 residuals for in-process ports. |
| `design/cdd/p5-slot-provider-execution.md` | Provider execution must not be represented as malicious-code containment. | Documents that provider contribution objects remain in-process and outside P8 isolation. |

## Performance Implications

- **CPU**: P8 can cap per-process user CPU time for the child Python process on
  Windows.
- **Memory**: P8 can cap process and job committed memory for the child Python
  process on Windows.
- **Load Time**: No default-path impact; isolated execution pays the same
  subprocess startup cost plus Job Object setup.
- **Network**: No new network behavior; P8 is not raw network denial.

## Migration Plan

1. Add the new feature flag and capability row.
2. Extend `SubprocessCodeExecutor` with optional Job Object resource limits.
3. Wire the flag through `build_python_analysis_executor()`.
4. Add red-team and resource-limit regression tests.
5. Update governance docs and maturity ledgers without promoting production
   readiness.

## Validation Criteria

- `slot_code_string_isolation` defaults off.
- Python analysis remains disabled unless `python_analysis_enabled` is on.
- Flag-on construction injects an isolated `SubprocessCodeExecutor`.
- Direct `os`, `socket`, `sqlite3`, and `subprocess` imports in code strings are
  denied by the existing demo denylist.
- Env-secret scrub and scratch cwd tests remain green.
- Job Object resource-limit failure path returns `ok=False` and emits
  `slot_resource_limit_exceeded`.
- A real Windows Python smoke can execute simple code under the Job Object path.
- Maturity posture remains experimental and all external gates remain open.

## Related Decisions

- [ADR-0013: Tool Governance](adr-0013-tool-governance.md)
- [ADR-0063: Slot Runtime Permission Interception and Subprocess Hardening](adr-0063-slot-runtime-permission-interception.md)
- [ADR-0064: Slot Provider Execution](adr-0064-slot-provider-execution.md)
- [ADR-0065: Provider Package Identity](adr-0065-provider-package-identity.md)
