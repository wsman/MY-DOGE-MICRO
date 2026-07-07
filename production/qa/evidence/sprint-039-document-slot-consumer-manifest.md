# Sprint 039 - Document Slot Consumer Manifest

> Sprint: 039 (Document Slot Consumer)
> Date: 2026-07-07
> Status: Local implementation complete; verification passed.

## Scope

This manifest records local evidence for the document slot consumer sprint:
`document.local_parser` contributes the existing deterministic local document
parser, and the slot-aware runtime factory composes a `ParserDispatcher` behind
`DOGE_FEATURE_SLOT_PLATFORM`.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0048-document-slot-consumer.md` records the document-consumer decision. |
| CDD | `design/cdd/sprint-039-document-slot-consumer.md` records behavior, contracts, and acceptance criteria. |
| Parser dispatcher | `src/doge/platform/evidence/document_parsers.py` adds `ParserDispatcher`. |
| Built-in document slot | `src/doge/infrastructure/documents/slot.py` adds `LocalDocumentParserSlot`. |
| Built-in registry | `src/doge/bootstrap/runtime_factories/slots.py` registers `LocalDocumentParserSlot`. |
| Document consumer | `src/doge/bootstrap/runtime_factories/slots.py` adds `build_slot_aware_document_parser()`. |
| Gateway factory wiring | `src/doge/bootstrap/gateway_factories/documents.py` uses the slot-aware parser when slot platform is enabled. |
| Platform facade | `src/doge/platform/evidence/__init__.py` exports `ParserDispatcher`. |
| Unit tests | `tests/unit/platform/slots/test_builtin_document_slot.py` and `tests/unit/platform/evidence/test_document_parser_dispatcher.py` cover manifest, contribution, dispatch, and fail-fast behavior. |
| Contract tests | `tests/contract/test_document_slot_parity.py` covers flag posture, default parity, custom parser dispatch, legacy fallback, and duplicate parser fail-fast. |
| Slot discovery tests | `tests/cli/test_cli_slots.py`, `tests/cli/test_doged_cli.py`, and `tests/contract/test_slot_api.py` cover `document.local_parser` status. |
| Session state | `production/session-state/active.md` records Sprint 039 as the current local implementation. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` adds the document slot consumer evidence record. |

## Verification Commands

```bash
py -3 -m pytest tests/unit/platform/slots/test_builtin_document_slot.py tests/unit/platform/evidence/test_document_parser_dispatcher.py tests/contract/test_document_slot_parity.py tests/unit/test_page_extraction.py tests/unit/test_file_upload_service.py tests/cli/test_cli_slots.py tests/contract/test_slot_api.py tests/cli/test_doged_cli.py -q
py -3 -m pytest tests/unit/platform/slots tests/unit/platform/evidence tests/contract/test_document_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_tool_registry_slot_parity.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0048-document-slot-consumer.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-039-document-slot-consumer.md
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
| Document slot / dispatcher / parity focused suite | Passed: 11 tests. |
| CLI/API/doged slot discovery focused suite | Passed: 43 tests, 2 existing FastAPI deprecation warnings. |
| Page extraction and file upload focused suite | Passed: 14 tests. |
| Broader slot/document regression suite | Passed: 97 tests. |
| Architecture boundary gates | Passed: 13 tests. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 106 markdown files. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0048 and Sprint 039 CDD. |
| Stale counts / ADR index / governance YAML | Passed. |
| Plan closure | Acceptable controlled-open: 4 open gates, 2 passed gates. |
| Whitespace | Passed in WSL Git and Windows Git. |

## Posture

- Production posture unchanged: `production_ready: false`,
  `stable_declaration: forbidden`, `level_3_sdk_platform: experimental`.
- No external/operator gates are closed by this sprint.
- No SDK package source, Web source, persistence schema, ModelRouter,
  ProfileRegistry, Kimi parser, OCR, vision chart parser, lifecycle hook
  invocation, runtime permission/health enforcement, bundle activation,
  third-party slot install, signing, or enterprise allowlist is part of this
  sprint.
- Slot Platform remains experimental and feature-flagged off by default.
- Sprint 039 completes the document-facet consumer proof only; it does not
  complete the full OpenClaw-like Slot Platform.
