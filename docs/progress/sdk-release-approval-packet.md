# SDK Release Approval Packet

Generated: 2026-06-22

## Scope

This packet prepares the Python and TypeScript SDKs for release approval. It
does not publish either package and does not remove the TypeScript SDK's
`private: true` guard.

## Current Local Evidence

| Package | Local Evidence | Status |
|---|---|---|
| Python `doge-sdk` | PEP 517 wheel build passed; package metadata test covers `setuptools.build_meta`, `wheel`, package name, and dependency floor. | Locally compatible. |
| TypeScript `doge-sdk` | Tests/build passed; `npm pack --dry-run --json` contains only `dist/*` and `package.json`; `exports`, `main`, and `types` are declared. | Locally compatible; publish guard remains enabled. |
| External consumer smoke | Python wheel installed in a clean venv; TypeScript tarball installed in a clean Node project and imported through Node ESM. | Local artifact consumer smoke passed; registry consumer smoke still requires release approval. |

Source evidence:

- `docs/progress/sdk-package-compatibility.md`
- `packages/doge-sdk-python/pyproject.toml`
- `packages/doge-sdk-typescript/package.json`
- `tests/unit/sdk/test_package_metadata.py`
- `tests/unit/sdk/test_external_consumer_smoke_script.py`
- `tests/unit/governance/test_s017_planning_docs.py`
- `scripts/sdk_external_consumer_smoke.py`
- `scripts/validate_sdk_release_approval_evidence.py`
- `scripts/build_sdk_release_approval_evidence.py`
- `production/qa/evidence/sdk/sdk-external-consumer-smoke.json`
- `production/qa/evidence/sdk/sdk-release-approval-template-2026-06-22.json`

Latest local verification:

- `.\.venv\Scripts\python.exe -m pytest tests\unit\governance\test_s017_planning_docs.py tests\unit\sdk\test_package_metadata.py -q`
  - PASS: `9 passed in 0.06s`.
- `.\.venv\Scripts\python.exe -m pytest tests\contract\test_python_sdk.py tests\unit\core\test_redaction.py tests\cli\test_cli_session.py -q`
  - PASS: `22 passed in 3.16s`.
- `npm test` from `packages/doge-sdk-typescript` with temporary Node on PATH.
  - PASS: `1 file, 11 tests`.
- `npm run build` from `packages/doge-sdk-typescript` with temporary Node on PATH.
  - PASS.
- `npm pack --dry-run --json` from `packages/doge-sdk-typescript`.
  - PASS: package size `3728`, unpacked size `13350`, entry count `11`.
- `.\.venv\Scripts\python.exe scripts\sdk_external_consumer_smoke.py --node-path C:\Users\Aby\AppData\Local\Temp\codex-node-v24.17.0\node-v24.17.0-win-x64 --workspace .tmp\sdk-external-consumer-smoke --output-dir production\qa\evidence\sdk`
  - PASS: Python clean venv consumer `python-consumer-ok`; TypeScript clean project consumer `typescript-consumer-ok`.
  - Evidence: `production/qa/evidence/sdk/sdk-external-consumer-smoke.json`.
  - The smoke caught and fixed a Node ESM package bug: emitted `dist/index.js`
    needed `.js` relative exports for tarball consumers.
- `.\.venv\Scripts\python.exe scripts\validate_sdk_release_approval_evidence.py production\qa\evidence\sdk\sdk-release-approval-template-2026-06-22.json --allow-template`
  - PASS: approval template validates only as a preflight artifact.

Evidence builder:

- `scripts/build_sdk_release_approval_evidence.py` reads compact release-manager decisions, merges them with the approval template, runs the validator, and writes completed evidence only if the result is structurally valid.
- Supported outcomes are `approved`, `needs_revision`, and `rejected`.
  Non-approved evidence must include `issue_refs`.

## Release Decision Required

The release manager must explicitly approve all of the following before
publication:

1. Registry targets:
   - Python: PyPI, private index, or internal artifact registry.
   - TypeScript: npm, GitHub Packages, private npm registry, or internal
     artifact registry.
2. Package names:
   - Confirm ownership/availability for `doge-sdk` or approve scoped/internal
     alternatives.
3. Version policy:
   - Keep `0.1.0` only for an internal preview, or bump before external
     consumers depend on it.
   - Confirm SemVer rules for breaking API changes.
4. Changelog/release notes:
   - Include bearer/request-id pass-through, JSON/multipart/SSE support,
     document APIs, approval/cancel helpers, and redaction behavior.
5. Registry-backed consumer smoke:
   - Local artifact smoke passed for Python wheel and TypeScript tarball.
   - After registry target/name approval, repeat install from the chosen
     registry or artifact repository.
   - Run session create, document upload/register, run start, SSE stream,
     approval/cancel, and error-redaction checks against doged.
6. Security posture:
   - No bearer tokens or model API keys are stored in package config.
   - No source/tests are included in the TypeScript package tarball.
   - Redaction covers bearer strings, key-value secrets, and provider-style
     `sk-*` values.

## Publication Guard

`packages/doge-sdk-typescript/package.json` intentionally keeps `private: true`.
The guard must remain until the release manager approves registry target,
package name, version/changelog policy, and external consumer smoke evidence.

Python publication also remains blocked until repository credentials and package
name ownership are approved.

## Approval Status

Pending release-manager approval. Local external-consumer artifact smoke is complete, and the release approval evidence template/builder/validator are ready, but SDK registry publication/release approval is ready for review, not done. The template validates only with `--allow-template`; default validation requires completed release-manager approval evidence.
