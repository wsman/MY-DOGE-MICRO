# SDK Package Compatibility Evidence

Generated: 2026-06-22

## Scope

This evidence closes the local package-compatibility check for the Python and
TypeScript SDKs. It does not publish either package to a public registry.

## Python SDK

Package: `packages/doge-sdk-python`

Evidence:

- `.\.venv\Scripts\python.exe -m ensurepip --upgrade`
  - PASS: installed `pip 25.0.1` into the local venv so PEP 517 build checks can run.
- `.\.venv\Scripts\python.exe -m pip wheel packages\doge-sdk-python --no-deps -w %TEMP%\doge-sdk-python-wheel-check`
  - PASS: built `doge_sdk-0.1.0-py3-none-any.whl`.
  - Wheel size: `9678` bytes.

Compatibility notes:

- `pyproject.toml` declares `setuptools.build_meta` with `setuptools>=61.0`
  and `wheel`.
- Runtime dependency is `httpx>=0.28.0`.
- Publishing still requires repository credentials, package name ownership, and
  release approval.

## TypeScript SDK

Package: `packages/doge-sdk-typescript`

Evidence:

- `cd packages/doge-sdk-typescript && npm test`
  - PASS: `1 file, 11 tests`.
- `cd packages/doge-sdk-typescript && npm run build`
  - PASS.
- `cd packages/doge-sdk-typescript && npm pack --dry-run --json`
  - PASS: dry-run package contains only `dist/*` and `package.json`.
  - Package size: `3728` bytes.
  - Unpacked size: `13350` bytes.
  - Entry count: `11`.
- `.\.venv\Scripts\python.exe scripts\sdk_external_consumer_smoke.py --node-path C:\Users\Aby\AppData\Local\Temp\codex-node-v24.17.0\node-v24.17.0-win-x64 --workspace .tmp\sdk-external-consumer-smoke --output-dir production\qa\evidence\sdk`
  - PASS: Python wheel installs and imports from a clean venv.
  - PASS: TypeScript tarball installs and imports from a clean Node ESM
    project.
  - Evidence: `production/qa/evidence/sdk/sdk-external-consumer-smoke.json`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\sdk\test_package_metadata.py tests\unit\governance\test_s017_planning_docs.py tests\unit\core\test_redaction.py tests\contract\test_enterprise_acl_api.py tests\cli\test_cli_session.py tests\contract\test_python_sdk.py -q`
  - PASS: `44 passed in 7.85s`.

Compatibility notes:

- `package.json` exposes `main`, `types`, and ESM `exports`.
- Source relative imports/exports now use `.js` module specifiers so emitted
  ESM works in a clean Node tarball consumer.
- `files` is restricted to `dist`, so tests and TypeScript source are not
  included in the package tarball.
- `private: true` remains set intentionally to prevent accidental registry
  publication before package name, registry, and release policy are approved.

## Review Decision

Local SDK package compatibility is complete. Registry publication, package name
ownership, changelog/version policy, and external consumer compatibility remain
release-management decisions, not local code blockers. The approval packet is
recorded at `docs/progress/sdk-release-approval-packet.md`.
