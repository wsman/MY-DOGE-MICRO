# Sprint 039 CDD: Document Slot Consumer

Status: Ready for Acceptance
Date: 2026-07-07

## 1. Overview

Sprint 039 makes the Slot Platform consume the `document` facet for document
parser selection.

The sprint adds a built-in `document.local_parser` slot, a slot-aware
`ParserDispatcher`, and document factory wiring so file upload and page
extraction can use slot-contributed parsers when `DOGE_FEATURE_SLOT_PLATFORM`
is enabled.

The sprint does not add Kimi file parsing, OCR, vision chart extraction, parser
health probes, or permission enforcement.

## 2. User Promise / JTBD

A platform engineer can add document parser slots without modifying
`FileUploadService` or `PageExtractionService`.

A research workflow owner can keep the current deterministic local document
behavior while gaining a controlled contribution point for future Kimi, vision,
or specialized parser slots.

## 3. Detailed Behavior

- `ParserDispatcher` lives in `doge.platform.evidence.document_parsers`.
- `ParserDispatcher` accepts `DocumentParserContribution` values.
- Each parser contribution must have a unique `parser_id`.
- Parser factories are resolved against `SlotContext`.
- Parser instances must expose `parse(path, max_chars=...)`.
- Exact suffix matches beat wildcard parser matches.
- Priority breaks ties within the same match class.
- Unsupported suffixes raise `SlotConfigurationError`.
- `LocalDocumentParserSlot` lives in `doge.infrastructure.documents.slot`.
- `document.local_parser` contributes the existing `LocalDocumentParser`.
- The built-in slot registry includes `document.local_parser`.
- `build_slot_aware_document_parser()` returns `ParserDispatcher` when document
  parser slots are enabled, otherwise `None`.
- `build_file_upload_service()` and `build_page_extraction_service()` use the
  slot-aware parser only when `DOGE_FEATURE_SLOT_PLATFORM` is enabled.
- CLI/API/doged slot discovery shows `document.local_parser` as resolved when
  slot platform is enabled.

## 4. Contracts / Data Model

Document parser contribution:

```python
DocumentParserContribution(
    parser_id="document.local_parser",
    factory=lambda context: LocalDocumentParser(),
    supported_suffixes=("*",),
    priority=0,
)
```

Parser dispatcher port:

```python
def parse(self, path: str | Path, *, max_chars: int = 12000) -> str:
    ...
```

Feature flag:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
```

No new feature flag is added for this sprint.

## 5. Edge Cases

- Slot platform off: direct `LocalDocumentParser` construction remains in use.
- Slot platform on: default dispatcher output equals local parser output.
- Duplicate parser ID: document parser assembly fails fast.
- Exact parser and wildcard parser both match: exact parser wins.
- Multiple exact parsers match: higher priority wins.
- No parser matches: `SlotConfigurationError`.
- Parser returns no instance: `SlotConfigurationError`.

## 6. Dependencies

- ADR-0042 Slot Platform Foundation.
- ADR-0043 Slot Contribution Facets.
- ADR-0045 Slot Discovery Surfaces.
- ADR-0047 Watcher Slot Consumer.
- Existing `LocalDocumentParser`.
- Existing `FileUploadService` and `PageExtractionService` parser ports.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; gates slot-aware document
  parser factory usage.

No `DOGE_FEATURE_SLOT_DOCUMENTS` flag is introduced.

## 8. Acceptance Criteria

- Built-in registry includes `document.local_parser`.
- Document slot manifest/status is visible through `doge slots`, `doged slots`,
  and `/v1/slots`.
- Slot-aware document parser assembly returns no parser when slot platform is
  off.
- Slot-aware document parser assembly returns a dispatcher when slot platform is
  on.
- Default dispatcher output matches `LocalDocumentParser` for text and binary
  fallback files.
- Gateway document factories use slot-contributed parsers when slot platform is
  on.
- Gateway document factories preserve legacy parser behavior when slot platform
  is off.
- Duplicate parser IDs fail fast.
- No Kimi parser, OCR, vision chart parser, runtime permission/health
  enforcement, Web Slot Center, SDK slot client, persistence schema, SlotKernel,
  SlotBundle, SlotPolicy, SlotLoader, third-party install, signing, or
  enterprise allowlist is added.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## 9. Validation Plan

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

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-039-document-slot-consumer-manifest.md`.

## 11. Out of Scope

- Kimi file parser, OCR, vision chart parser, page-layout extraction, or
  multimodal parser policy.
- Parser active health probes or runtime permission enforcement.
- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, and `SlotLoader`.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- Persistence schema, ModelRouter/ProfileRegistry, external auth, or worker
  behavior changes.
- Production readiness declaration or external/operator gate closure.
