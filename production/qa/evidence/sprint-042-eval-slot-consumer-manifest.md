# Sprint 042 - Eval Slot Consumer Manifest

> Sprint: 042 (Eval Slot Consumer)
> Date: 2026-07-07
> Status: Local implementation complete; verification passed.

## Scope

This manifest records local evidence for the eval slot consumer sprint:
`eval.local_cases` contributes the existing deterministic local cases file, and
the slot-aware runtime factory composes an `EvalSuiteRegistry` behind
`DOGE_FEATURE_SLOT_PLATFORM`.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0051-eval-slot-consumer.md` records the eval-consumer decision. |
| CDD | `design/cdd/sprint-042-eval-slot-consumer.md` records behavior, contracts, and acceptance criteria. |
| Eval suite registry | `src/doge/eval/suites.py` adds `EvalSuiteRegistry`. |
| Built-in eval slot | `src/doge/eval/slot.py` adds `LocalEvalCasesSlot`. |
| Built-in registry | `src/doge/bootstrap/runtime_factories/slots.py` registers `eval.local_cases`. |
| Eval consumer | `src/doge/bootstrap/runtime_factories/slots.py` adds `build_slot_aware_eval_suites()`. |
| Runner wiring | `src/doge/eval/runner.py` adds `run_suite()` and CLI `--suite`. |
| Public facade | `src/doge/eval/__init__.py` and `tests/eval/run_eval.py` export `run_suite()`. |
| Unit tests | `tests/unit/platform/slots/test_builtin_eval_slot.py` and `tests/unit/eval/test_eval_suite_registry.py` cover manifest, contribution, selection, and fail-fast behavior. |
| Contract tests | `tests/contract/test_eval_slot_parity.py` covers flag posture, built-in suite path, runner delegation, and duplicate suite fail-fast. |
| Slot discovery tests | `tests/cli/test_cli_slots.py`, `tests/cli/test_doged_cli.py`, and `tests/contract/test_slot_api.py` cover `eval.local_cases` status. |
| Session state | `production/session-state/active.md` records Sprint 042 as the current local implementation. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` adds the eval slot consumer evidence record. |

## Verification Commands

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

## Verification Results

| Gate | Result |
|---|---|
| Eval slot / registry / parity / discovery focused suite | Passed: 53 tests, 2 existing FastAPI deprecation warnings. |
| Broader slot/eval regression suite | Passed: 119 tests, 2 existing FastAPI deprecation warnings. |
| Architecture boundary gates | Passed: 24 tests. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 109 markdown files. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0051 and Sprint 042 CDD. |
| Stale counts / ADR index / governance YAML | Passed. |
| Plan closure | Acceptable controlled-open: 4 open gates, 2 passed gates. |
| Whitespace | Passed in WSL Git and Windows Git. |

## Posture

- Production posture unchanged: `production_ready: false`,
  `stable_declaration: forbidden`, `level_3_sdk_platform: experimental`.
- No external/operator gates are closed by this sprint.
- No SDK package source, Web source, persistence schema, ModelRouter,
  ProfileRegistry, new gold cases, W3-live evidence, eval policy enforcement,
  bundle activation, third-party slot install, signing, or enterprise allowlist
  is part of this sprint.
- Slot Platform remains experimental and feature-flagged off by default.
- Sprint 042 completes the eval-facet consumer proof only; it does not complete
  the full OpenClaw-like Slot Platform.
