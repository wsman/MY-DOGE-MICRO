# Sprint C Acceptance Report — Kimi Live Smoke Closure

> Date: 2026-06-29
> Plan: design/cdd/sprint-c-kimi-live-smoke.md
> Story: S017-002
> Verdict: **GO**

## Scope

Sprint C closes the local implementation and governance gaps for the S017-002
Kimi live smoke gate, and defines the **Kimi Coding v1** closure semantics:

- **Required**: `text_k26` (text chat) and `vision_base64` (base64 image chat)
  must pass against the live provider.
- **Optional**: `files_upload` and `agent_sdk_optional` must be documented with
  `passed` or `skipped` + `reason`.

This matches the product's actual Kimi Coding v1 endpoint, which does not expose
`/files` and does not require the optional `kimi_agent_sdk` package.

## Local Changes

1. **Kimi live smoke runner**
   - `scripts/run_kimi_live_smoke.py`
   - Always emits all four scenarios (including `agent_sdk_optional` as skipped
     when env/SDK are not enabled).
   - Adds `--coding-v1` flag; labels evidence with `gate: coding-v1`.
   - Uses date-based evidence filename.

2. **Kimi live smoke validator**
   - `scripts/validate_kimi_live_smoke_evidence.py`
   - Adds `--coding-v1` flag.
   - Validates required text + Vision pass and optional scenarios are documented.

3. **Validator tests**
   - `tests/unit/qa/test_validate_kimi_live_smoke_evidence.py`
   - Added coding-v1 pass, missing optional, skipped-without-reason, required
     failure, and CLI flag tests.

4. **Design document**
   - `design/cdd/sprint-c-kimi-live-smoke.md`
   - Full 8-section product CDD.

5. **Runtime maturity**
   - `docs/progress/runtime-maturity.yaml`
   - Added `sprint_c_kimi_live_smoke_gates`.
   - `kimi_coding_v1_local_readiness` marked `passed`.
   - `kimi_coding_v1_live_execution` initially marked `pending_operator_action`,
     then closed as `passed` after live evidence validated.

6. **Readiness and live evidence**
   - `production/qa/evidence/live/kimi-live-smoke-2026-06-28.json`
   - `production/qa/evidence/live/kimi-live-smoke-2026-06-28.md`
   - Blocked evidence showing the runner/validator are functional and the only
     missing items are the operator env gates.
   - `production/qa/evidence/live/kimi-live-smoke-2026-06-29.json`
   - `production/qa/evidence/live/kimi-live-smoke-2026-06-29.md`
   - Passed Kimi Coding v1 live evidence with text + Vision passed and optional
     scenarios documented.

## Live Evidence

The closing Kimi Coding v1 live evidence is:

- `production/qa/evidence/live/kimi-live-smoke-2026-06-29.json`
- `production/qa/evidence/live/kimi-live-smoke-2026-06-29.md`

It records:

| Scenario | Status | Notes |
|---|---|---|
| text_k26 | passed | Live text chat against `kimi-k2.6` |
| files_upload | skipped | Configured Kimi Coding endpoint does not support the Files API |
| vision_base64 | passed | Live base64 image chat against `kimi-k2.6` |
| agent_sdk_optional | skipped | Optional Agent SDK smoke not enabled/installed |

Strict validation passed without `--allow-blocked`:

```text
py -3 scripts\validate_kimi_live_smoke_evidence.py production\qa\evidence\live\kimi-live-smoke-2026-06-29.json --coding-v1
```

## Historical Live Evidence

The earlier partial live evidence remains available:

- `production/qa/evidence/live/kimi-live-smoke-2026-06-22.json`
- `production/qa/evidence/live/kimi-live-smoke-2026-06-22.md`

It records:

| Scenario | Status | Notes |
|---|---|---|
| text_k26 | passed | Live text chat against `kimi-k2.6` |
| files_upload | skipped | Configured Kimi endpoint does not support the Files API |
| vision_base64 | passed | Live base64 image chat against `kimi-k2.6` |
| agent_sdk_optional | not present | Agent SDK was not enabled/installed |

Because `agent_sdk_optional` is not present, this historical evidence does not
satisfy the new coding-v1 shape. It has been superseded by the 2026-06-29
passed evidence above.

## Test Results

- `tests/unit/qa/test_validate_kimi_live_smoke_evidence.py`: **19 passed**
- `tests/unit/qa/test_run_kimi_live_smoke.py`: **6 passed**
- `tests/unit/governance/test_docs_sha_alignment.py` + `test_docs_consistency.py`: **11 passed**
- `scripts/validate_kimi_live_smoke_evidence.py production/qa/evidence/live/kimi-live-smoke-2026-06-28.json --coding-v1 --allow-blocked`: **passed**
- `scripts/validate_kimi_live_smoke_evidence.py production/qa/evidence/live/kimi-live-smoke-2026-06-29.json --coding-v1`: **passed**
- `scripts/validate_governance_yaml_shape.py docs/progress/runtime-maturity.yaml`: **passed**
- `scripts/validate_alpha_maturity_honesty.py` (runtime-maturity, README, acceptance report): **passed**
- Full Python regression: **1784 passed, 2 failed, 8 skipped**
- New failures introduced by Sprint C: **0**
- Pre-existing failures: 2
  - `tests/test_yfinance_adapter.py::test_download_kline_normalizes_columns_and_dtypes` — yfinance StringDtype drift (unrelated).
  - `tests/unit/qa/test_validate_alpha_pre_commit_readiness.py::test_alpha_pre_commit_readiness_cli_fast` — handoff workspace template SHA256 mismatch from prior commit `b11b2e3` (unrelated; `validate_plan_closure_handoff.py` reports source template hashes out of sync).

Live smoke was executed with operator-provided Kimi Coding credentials and
validated successfully. The API key is not stored in evidence.

## Review Approvals

| Review | Approved | Notes |
|---|---|---|
| Architecture Review | YES | No new cross-layer imports; runner/validator remain in scripts/ layer. |
| Test Review | YES | New validator tests deterministic and isolated; live tests remain env-gated. |
| Gate Review | YES | Live gate closed by redacted Kimi Coding v1 evidence and strict validator pass. |

## Production Posture

Unchanged. `production_ready: false`, `stable_declaration: forbidden`, Level 3
`experimental`. Sprint C closes S017-002 Kimi Coding v1 live smoke only; it does
not promote the overall product to production readiness.

## Recommended Next Steps

1. Rotate the operator-provided Kimi API key because it was exposed in chat.
2. Choose next work: Sprint D (enterprise auth hardening) or remaining S017
   external gates (S017-003 provider approval, S017-007 SDK release, etc.).

## Sign-off

- **Test Review**: Approved
- **Runtime/Gate Review**: Approved
- **Overall Sprint C Verdict**: **GO**
