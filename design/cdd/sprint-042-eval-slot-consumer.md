# Sprint 042 CDD: Eval Slot Consumer

Status: Ready for Acceptance
Date: 2026-07-07

## 1. Overview

Sprint 042 makes the Slot Platform consume the `eval` facet for offline eval
suite selection.

The sprint adds a built-in `eval.local_cases` slot, an `EvalSuiteRegistry`, and
runner `--suite` support so slot-contributed cases can be selected by suite ID
when `DOGE_FEATURE_SLOT_PLATFORM` is enabled.

The sprint does not change the existing `run(cases_path)` behavior, add new
gold cases, or close any live eval gates.

## 2. User Promise / JTBD

An eval owner can register deterministic local eval suites as slots and run
them by ID instead of manually passing file paths.

A platform engineer can keep the existing explicit-cases runner path while
proving eval suite contribution and discovery.

## 3. Detailed Behavior

- `EvalSuiteRegistry` lives in `doge.eval.suites`.
- `EvalSuiteRegistry` accepts `EvalSuiteContribution` values.
- Each eval suite contribution must have a unique `suite_id`.
- Cases paths are resolved relative to the current repo root unless absolute.
- Missing cases paths raise `SlotConfigurationError`.
- Unknown suite IDs raise `SlotConfigurationError`.
- `LocalEvalCasesSlot` lives in `doge.eval.slot`.
- `eval.local_cases` contributes `tests/eval/cases.json`.
- The built-in slot registry includes `eval.local_cases`.
- `build_slot_aware_eval_suites()` returns `EvalSuiteRegistry` when eval suite
  slots are enabled, otherwise `None`.
- `run(cases_path)` remains unchanged.
- `run_suite(suite_id)` resolves the cases path through slot contributions and
  delegates to `run(cases_path)`.
- CLI `doge.eval.runner --suite eval.local_cases` is accepted through the
  runner's mutually exclusive `--cases` / `--suite` group.
- CLI/API/doged slot discovery shows `eval.local_cases` as resolved when slot
  platform is enabled.

## 4. Contracts / Data Model

Eval suite contribution:

```python
EvalSuiteContribution(
    suite_id="eval.local_cases",
    gold_set_path="tests/eval/cases.json",
    execution_profile="local_alpha",
    eval_policy=("offline", "deterministic"),
)
```

Runner API:

```python
def run_suite(suite_id: str, runtime_factory: RuntimeFactory | None = None) -> dict:
    ...
```

Feature flag:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
```

No new feature flag is added for this sprint.

## 5. Edge Cases

- Slot platform off: no eval suite registry is assembled.
- Explicit `run(cases_path)`: unchanged.
- Unknown suite ID: `SlotConfigurationError`.
- Duplicate suite ID: eval suite assembly fails fast.
- Missing cases path: eval suite assembly fails fast.
- `--cases` and `--suite` are mutually exclusive.
- Local suite selection does not imply W3-live benchmark closure.

## 6. Dependencies

- ADR-0042 Slot Platform Foundation.
- ADR-0043 Slot Contribution Facets.
- ADR-0045 Slot Discovery Surfaces.
- ADR-0050 Gateway Slot Consumer.
- Existing `doge.eval.runner` and `tests/eval/cases.json`.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; gates slot-aware eval suite
  selection.

No `DOGE_FEATURE_SLOT_EVAL` flag is introduced.

## 8. Acceptance Criteria

- Built-in registry includes `eval.local_cases`.
- Eval slot manifest/status is visible through `doge slots`, `doged slots`, and
  `/v1/slots`.
- Slot-aware eval suite assembly returns no registry when slot platform is off.
- Slot-aware eval suite assembly returns a registry when slot platform is on.
- `eval.local_cases` resolves to an existing local cases file.
- `run_suite()` delegates to existing `run(cases_path)` behavior.
- Duplicate suite IDs fail fast.
- Missing cases paths fail fast.
- No new eval cases, live benchmark labels, analyst thresholds, W3-live
  closure, route/API changes, Web Slot Center, SDK slot client, persistence
  schema, SlotKernel, SlotBundle, SlotPolicy, SlotLoader, third-party install,
  signing, or enterprise allowlist is added.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## 9. Validation Plan

```bash
py -3 -m pytest tests/unit/platform/slots/test_builtin_eval_slot.py tests/unit/eval/test_eval_suite_registry.py tests/contract/test_eval_slot_parity.py tests/cli/test_cli_slots.py tests/contract/test_slot_api.py tests/cli/test_doged_cli.py -q
py -3 -m pytest tests/unit/platform/slots tests/unit/eval tests/contract/test_eval_slot_parity.py tests/contract/test_gateway_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_tool_registry_slot_parity.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0051-eval-slot-consumer.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-042-eval-slot-consumer.md
py -3 scripts/validate_no_stale_counts.py
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-042-eval-slot-consumer-manifest.md`.

## 11. Out of Scope

- New gold cases, analyst labels, thresholds, W3-live evidence, or live eval
  closure.
- Eval metric plugin model, suite health probes, or eval policy enforcement.
- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, and `SlotLoader`.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- Persistence schema, ModelRouter/ProfileRegistry, external auth, route
  behavior, or worker behavior changes.
- Production readiness declaration or external/operator gate closure.
