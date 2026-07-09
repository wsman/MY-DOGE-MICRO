# P8 CDD: Code-String Isolation Prototype

Status: Ready for Local Acceptance
Date: 2026-07-08

## 1. Overview

P8 adds a default-off resource isolation prototype for `run_python_analysis`
code strings only. It does not isolate installed provider contribution objects.

The implementation uses the existing `ICodeExecutor.execute(code, timeout)`
port because its inputs and outputs are marshalable. The callable-shaped
`ISlotRuntimeExecutor.run()` port remains an in-process slot permission runner
and is not redesigned in P8.

## 2. User Promise / JTBD

An operator can keep Python analysis disabled by default, explicitly enable it
for local experiments, and optionally enable Windows Job Object resource limits
for code strings.

A security reviewer can verify that P8 improves one code-string path without
claiming production plugin sandboxing or provider contribution isolation.

## 3. Scope

Included:

- `DOGE_FEATURE_SLOT_CODE_STRING_ISOLATION`, default `false`.
- Capability discovery row `feature.slot_code_string_isolation`.
- Windows Job Object process memory, job memory, per-process CPU time, and
  kill-on-job-close limits for `SubprocessCodeExecutor`.
- Existing env scrub, scratch cwd, timeout clamp, and Windows process group.
- Fail-closed behavior when isolation is requested on non-Windows hosts.
- Best-effort `slot_resource_limit_exceeded` audit events.
- Direct-import red-team tests for `os`, `socket`, `sqlite3`, and `subprocess`.

Excluded:

- Provider contribution-object isolation.
- Filesystem mediation for absolute paths or raw `open()` bypasses.
- Raw network denial or socket sandboxing.
- Malicious-code containment.
- Container, WASM, seccomp, chroot, or POSIX rlimit runner.
- Marketplace, SDK install API, HTTP install API, YAML manifests, remote CI
  promotion, external gate closure, or production maturity.

## 4. Configuration

Default behavior:

```text
DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED=0
DOGE_PYTHON_ANALYSIS_EXECUTOR=disabled
DOGE_FEATURE_SLOT_CODE_STRING_ISOLATION=0
```

Local Windows prototype:

```text
DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED=1
DOGE_PYTHON_ANALYSIS_EXECUTOR=subprocess
DOGE_FEATURE_SLOT_CODE_STRING_ISOLATION=1
```

The P8 flag alone must not make Python analysis executable.

## 5. Runtime Behavior

When Python analysis is disabled, `DisabledCodeExecutor` returns the existing
default-off error.

When Python analysis uses subprocess without P8 isolation, the existing P4 path
continues:

- `python -I -c <code>`;
- scratch cwd;
- sanitized env;
- timeout clamped to `[1.0, 10.0]`;
- Windows `CREATE_NEW_PROCESS_GROUP`;
- POSIX `start_new_session`.

When P8 isolation is enabled on Windows, `SubprocessCodeExecutor` additionally
creates a Job Object, sets memory and CPU limits, assigns the child process to
the job, and closes the job after completion. If Job Object setup or assignment
fails, execution returns `ok=False`.

When P8 isolation is enabled off Windows, execution returns `ok=False` with an
explicit unavailable-isolation error. It does not silently run unisolated.

## 6. Contribution Residual

Provider contributions remain in-process Python objects. P8 does not change the
ADR-0064 `InstalledProviderSlot` model, which imports trusted provider
entrypoints in-process after local alpha gates pass.

Current provider contribution residuals:

- direct filesystem APIs are not mediated;
- direct socket/network APIs are not OS-denied;
- direct sqlite/database imports can bypass guarded ports;
- direct subprocess or OS APIs are not contained;
- package identity is covered by P7/ADR-0065, but it is identity binding only,
  not runtime containment.

These residuals must stay visible in runtime maturity and evidence until a
separate provider-runner/container/WASM decision closes them.

## 7. Acceptance Criteria

- `slot_code_string_isolation` defaults to `false`.
- Capability discovery includes lifecycle metadata and high-risk scope.
- Python analysis remains disabled unless `python_analysis_enabled` is true and
  `python_analysis_executor=subprocess`.
- P8 flag-on factory construction injects a `SubprocessCodeExecutor` with
  `isolation_enabled=True`.
- Direct code-string imports of `os`, `socket`, `sqlite3`, and `subprocess` are
  rejected.
- Env-secret scrub and scratch cwd behavior remain green.
- Resource-limit failure returns `ok=False` and emits
  `slot_resource_limit_exceeded`.
- Real Windows Python smoke succeeds under Job Object setup.
- Docs and maturity files do not claim provider isolation, filesystem
  mediation, malicious-code containment, or production readiness.
- Maturity posture remains explicitly unchanged:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 8. Verification Plan

Focused tests:

```text
py -3 -m pytest tests/unit/capabilities/test_code_executor.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py -q
```

Regression tests:

```text
py -3 -m pytest tests/unit/platform/slots/test_slot_runtime_access.py tests/unit/platform/slots/test_slot_provider_execution.py tests/cli/test_cli_slots.py -q
```

Governance:

```text
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/progress/runtime-maturity.yaml
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_adr_index_completeness.py
git diff --check
```
