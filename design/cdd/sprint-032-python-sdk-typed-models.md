# Sprint 032 CDD: Python SDK Typed Result Models

Status: Ready for Acceptance
Date: 2026-07-06

## 1. User Promise

A Python SDK integrator can keep using run responses as dictionaries while also
getting typed, discoverable properties for the core run result shapes.

The sprint improves developer ergonomics without changing daemon routes, HTTP
payloads, SDK method names, package dependencies, or production maturity
posture.

## 2. Product Context

The TypeScript SDK already exposes run-resource interfaces for `AgentRun`,
`AgentArtifact`, `AgentApproval`, `AgentEvent`, and `RunListItem`. Python SDK
users currently receive raw dictionaries from the corresponding runs resource
methods and must remember string keys.

Existing Python consumers depend on dict behavior. This CDD therefore treats
dict compatibility as a first-class product requirement rather than an
implementation detail.

## 3. Delivered Contract

Sprint 032 implements the Python SDK typed run model plan in
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`:

- Add `packages/doge-sdk-python/doge_sdk/run_models.py`.
- Add dict-subclass models:
  - `Run`
  - `RunListItem`
  - `Artifact`
  - `Approval`
  - `RunEvent`
- Wrap sync `RunsResource` return values:
  - `get`, `approve`, `resume`, `cancel` return `Run`.
  - `list` returns `list[RunListItem]`.
  - `events` returns `list[RunEvent]`.
- Wrap async `AsyncRunsResource` return values with the same model classes.
- Keep `stream` yielding the existing `DogeEvent` dataclass.
- Keep `summary`, `claims`, `citations`, and `evaluation` as raw dict/list
  payloads.
- Re-export the new model classes from `doge_sdk.__init__`.
- Document typed attribute access in the Python SDK README while preserving the
  canonical dict examples.

## 4. Model Field Table

| Model | Required Accessors | Optional / Nullable Accessors | Nested Model Accessors |
|-------|--------------------|-------------------------------|------------------------|
| `Run` | `run_id`, `status` | `workflow`, `question`, `session_id`, `market`, `language`, `document_ids`, `portfolio_id`, `model_policy`, `workflow_context`, `identity_snapshot`, `cancel_requested_at`, `schema_version`, `created_at`, `updated_at` | `events`, `artifacts`, `approvals` |
| `RunListItem` | `run_id`, `status` | `workflow`, `question`, `session_id`, `market`, `language`, `portfolio_id`, `event_count`, `artifact_count`, `approval_count`, `created_at`, `updated_at` | None |
| `Artifact` | `artifact_id` | `kind`, `title`, `content`, `run_id`, `data`, `created_at` | None |
| `Approval` | `approval_id`, `status` | `action`, `risk_level`, `run_id`, `created_at`, `resolved_at`, `why_needed`, `impact`, `deny_consequence`, `publish_target` | None |
| `RunEvent` | `event_type`, `sequence` | `event_id`, `run_id`, `payload`, `schema_version`, `created_at` | None |

The implementation may return `None` for missing scalar fields because tests and
older daemon snapshots can use minimal payloads. Dict access remains the source
of truth for exact raw payload contents.

## 5. Compatibility Requirements

- `isinstance(run, dict)` remains true for `Run`.
- `run == {"run_id": "...", "status": "..."}` remains true for minimal
  payloads.
- `run["run_id"]`, `run.get("status")`, `run.keys()`, `run.items()`, and dict
  iteration remain valid.
- Nested lists are only inserted when the original payload includes them.
- Nested `Approval`, `Artifact`, and `RunEvent` objects are themselves dict
  subclasses and compare equal to the original nested plain dictionaries.
- `DogeEvent` remains a frozen dataclass and is not converted to a dict
  subclass.

## 6. Non-Goals

- Maturity posture remains:
  - `production_ready: false`
  - `stable_declaration: forbidden`
  - `level_3_sdk_platform: experimental`
- No `/v1` route, request, response, or OpenAPI change.
- No TypeScript SDK source change.
- No SDK method-surface bump.
- No dependency change in `packages/doge-sdk-python/pyproject.toml`.
- No typed Python models for `documents.*` or `platform.*`.
- No `Citation` model in this sprint.
- No `MemoExport` aggregate model.
- No `client.research.create_memo(...)` happy-path helper.
- No production-ready declaration or external gate closure.

## 7. Acceptance Criteria

- Existing Python SDK contract tests continue to assert dict equality and dict
  access.
- New contract tests prove sync and async run resources return the new model
  classes.
- New model unit tests prove dict methods and typed properties coexist.
- Approval explanation fields are optional and return `None` when absent.
- README states that typed attribute access is additive and dict access remains
  supported.
- SDK contract check remains 15 surfaces / 15 parity.
- Import boundaries and docs/maturity validators pass.
- Active session state and QA evidence record Local Alpha posture.

## 8. Validation Plan

```bash
PYTHONPATH=packages/doge-sdk-python python3 -m py_compile \
  packages/doge-sdk-python/doge_sdk/run.py \
  packages/doge-sdk-python/doge_sdk/run_models.py \
  packages/doge-sdk-python/doge_sdk/__init__.py \
  tests/contract/test_python_sdk.py \
  tests/unit/sdk/test_python_sdk_run_models.py

cmd.exe /c py -3 -m pytest tests/contract/test_python_sdk.py tests/unit/sdk/test_python_sdk_run_models.py -q
cmd.exe /c py -3 tools/ci/sdk-contract-check.py
cmd.exe /c py -3 scripts/validate_import_boundaries.py
cmd.exe /c py -3 scripts/validate_docs_authority.py
cmd.exe /c py -3 scripts/validate_docs_links.py
cmd.exe /c py -3 scripts/validate_docs_maturity_claims.py
cmd.exe /c py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0041-python-sdk-typed-models.md
cmd.exe /c py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-032-python-sdk-typed-models.md
cmd.exe /c py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/a038a698-harmonic-mango.md
git diff --check
```

## 9. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-032-python-sdk-typed-models-manifest.md`.

## 10. Out of Scope

- Web UX changes.
- CLI command changes.
- Daemon operator command changes.
- SDK packaging/release automation.
- Live Kimi smoke tests.
- Production storage, queue, monitoring, audit, backup, or restore work.
