# ADR-0048: Document Slot Consumer

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 039 consumes the `document` slot facet at the document parsing seams used
by file upload and page extraction. The sprint adds a slot-aware
`ParserDispatcher` and a built-in `document.local_parser` slot that contributes
the existing deterministic `LocalDocumentParser`.

When `DOGE_FEATURE_SLOT_PLATFORM` is off, document factories keep constructing
`LocalDocumentParser` directly. When it is on, the same factories ask the
built-in slot registry for document parser contributions and receive a
dispatcher. The default slot is parity preserving: text and binary fallback
parsing remain equivalent to the legacy local parser.

## Status Update - 2026-07-08

ADR-0058 makes the built-in Slot Platform consumer path default-on for local
runs, so the document parser slot path is now the default when not explicitly
opted out. This does not add OCR, Kimi file parsing, active health probes, or
third-party provider execution.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing document services; existing slot facet dataclasses |
| **Domain** | Knowledge & Evidence, document parsing, file upload, page extraction |
| **Knowledge Risk** | LOW - local factory and protocol work over existing parser behavior |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0043-slot-contribution-facets.md`, `docs/architecture/adr-0047-watcher-slot-consumer.md`, `src/doge/bootstrap/gateway_factories/documents.py`, `src/doge/application/services/file_upload_service.py`, `src/doge/application/services/page_extraction_service.py`, `src/doge/platform/slots/facets.py`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | document slot unit tests, parser-dispatcher tests, document slot parity tests, page extraction/file upload regressions, CLI/API/doged slot status tests, import boundaries, docs validators, maturity honesty, plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0045 (Slot Discovery Surfaces), ADR-0047 (Watcher Slot Consumer) |
| **Extends** | ADR-0043 by adding a runtime consumer for the `document_parsers` facet |
| **Supersedes** | None |
| **Enables** | Later Kimi file parser, vision chart parser, parser health checks, and SlotKernel document orchestration |
| **Blocks** | None |

## Context

The Slot Platform roadmap requires document parsing to become a controlled slot
contribution. Before this sprint, `DocumentParserContribution` existed as a
typed facet, but file upload and page extraction still constructed
`LocalDocumentParser` directly in `bootstrap/gateway_factories/documents.py`.

The correct first consumer is the existing parser port, not a new extraction
pipeline. `FileUploadService` and `PageExtractionService` already depend on a
small `parse(path, max_chars=...)` protocol, so the slot consumer can preserve
service behavior while moving parser selection behind a dispatcher.

## Constraints

- Keep `DOGE_FEATURE_SLOT_PLATFORM` default `false`.
- Preserve flag-off document parsing behavior.
- Keep `doge.platform.slots` pure and framework-free.
- Keep `doge.platform.evidence` free of direct infrastructure imports.
- Place the concrete local parser slot beside the infrastructure parser it
  wraps.
- Do not add Kimi file parsing, vision extraction, OCR, parser health probes,
  active permission enforcement, or external network behavior.
- Do not add Web Slot Center, SDK slot client, bundle activation, third-party
  install, signing, or SlotKernel lifecycle orchestration.
- Do not close external/operator gates or change production maturity posture.

## Decision

Add `doge.platform.evidence.document_parsers.ParserDispatcher`. It consumes
`DocumentParserContribution` values and exposes the same parser port:

```python
def parse(self, path: str | Path, *, max_chars: int = 12000) -> str: ...
```

The dispatcher builds parser instances from contribution factories, rejects
duplicate parser IDs, rejects empty parser sets, and selects a parser by suffix.
Exact suffix matches beat wildcard matches, and priority breaks ties within the
same match class. If no parser supports the suffix, it raises
`SlotConfigurationError`.

Add `doge.infrastructure.documents.slot.LocalDocumentParserSlot`. It declares
`document.local_parser`, type `document`, owner `knowledge-evidence`, and
capabilities `document.parse` and `document.local_parser`. The slot contributes
one wildcard parser backed by `LocalDocumentParser`. The provider lives in
`doge.infrastructure.documents` because it wraps an infrastructure parser;
bootstrap registers it in the built-in slot registry.

Add `build_slot_aware_document_parser()` to
`src/doge/bootstrap/runtime_factories/slots.py`. It resolves document slots
whose feature flags are satisfied, rejects duplicate parser IDs, and returns
`ParserDispatcher` or `None` when no document parsers are enabled.

Update `src/doge/bootstrap/gateway_factories/documents.py` so
`build_file_upload_service()` and `build_page_extraction_service()` call a small
`_build_document_parser(settings)` helper. With `slot_platform` off it returns
`LocalDocumentParser`; with `slot_platform` on it returns the slot-aware
dispatcher when available, otherwise falls back to the local parser.

## Alternatives Considered

### Alternative 1: Put `LocalDocumentParserSlot` in `doge.platform.evidence`

- **Description**: Place the built-in document slot beside platform evidence
  services.
- **Pros**: The slot owner name and bounded context are visually aligned.
- **Cons**: It would force `doge.platform.evidence` to import
  `doge.infrastructure.documents.local_parser`, violating the platform
  dependency graph.
- **Rejection Reason**: The concrete provider belongs beside the infrastructure
  implementation, while the dispatcher belongs in the platform evidence layer.

### Alternative 2: Replace `PageExtractionService` with a slot-owned extractor

- **Description**: Move page extraction and chunking behind a document slot.
- **Pros**: More of the document pipeline becomes pluggable immediately.
- **Cons**: Larger behavioral blast radius and unnecessary for consuming the
  existing `DocumentParserContribution` facet.
- **Rejection Reason**: Sprint 039 proves parser contribution consumption only;
  extraction/chunking ownership remains unchanged.

### Alternative 3: Add a separate `DOGE_FEATURE_SLOT_DOCUMENTS` flag

- **Description**: Gate document slot resolution behind a second facet-specific
  flag.
- **Pros**: More granular rollout switch.
- **Cons**: Adds config lifecycle noise for a low-risk local parser parity path.
- **Rejection Reason**: The default document slot is parity-preserving and has
  no network, shell, database, or secret access. `DOGE_FEATURE_SLOT_PLATFORM`
  is enough for this consumer proof.

## Consequences

### Positive

- The `document` facet now has a real runtime consumer.
- File upload and page extraction can receive parser contributions without
  changing their application service contracts.
- Default slot behavior is equivalent to the legacy local parser.
- Parser ID collisions fail fast.
- Exact suffix parsers can override the wildcard local fallback.

### Negative

- Only parser selection is slot-backed; page extraction and chunking are still
  owned by the existing application service.
- The default local parser remains deterministic and shallow for binary files.
- Parser permissions and health remain declarative only.
- The dispatcher is assembled through current runtime factories rather than a
  first-class `SlotKernel`.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Parser dispatch changes local extraction output | LOW | MEDIUM | Default slot wraps `LocalDocumentParser`; parity tests compare text and binary output. |
| Platform layer imports infrastructure accidentally | LOW | MEDIUM | Dispatcher is pure platform code; provider lives in infrastructure; architecture gates validate boundaries. |
| A custom parser shadows local fallback unexpectedly | MEDIUM | MEDIUM | Exact suffix and priority rules are deterministic and covered by tests. |
| Operators mistake document slot for full document platform completion | LOW | MEDIUM | ADR/CDD/evidence keep Kimi parser, vision/OCR, health, permission enforcement, bundles, and third-party slots out of scope. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-039-document-slot-consumer.md` | Document parser slots can contribute parsers consumed by file upload and page extraction. | Adds `ParserDispatcher`, `document.local_parser`, and slot-aware document parser factory wiring. |
| `design/cdd/bc-07-knowledge-evidence.md` | Knowledge & Evidence owns documents, pages, chunks, and evidence extraction contracts. | Keeps parser dispatch in the evidence platform and preserves page/chunk service contracts. |
| `design/cdd/document-evidence-pipeline.md` | Document parsing must remain deterministic and citeable in local alpha. | Default slot wraps the deterministic `LocalDocumentParser` and keeps extraction output equivalent. |

## Performance Implications

- **CPU**: one small suffix-selection loop per file parse when slot platform is
  enabled.
- **Memory**: one dispatcher plus parser instances in the document service
  factory.
- **Load Time**: imports the local document parser slot when the built-in slot
  registry is built.
- **Network**: none.

## Migration Plan

1. Add `ParserDispatcher`.
2. Add `LocalDocumentParserSlot`.
3. Register the document slot in the built-in slot registry.
4. Add `build_slot_aware_document_parser()`.
5. Wire document gateway factories to use the dispatcher when slot platform is
   enabled.
6. Extend CLI/API/doged slot discovery expectations for `document.local_parser`.
7. Keep concrete Kimi parser, vision parser, OCR, active health, permission
   enforcement, SlotKernel, bundles, loaders, signing, and third-party install
   deferred.

## Validation Criteria

- `document.local_parser` manifest is typed as `document`, declares
  `slot_platform`, and provides document parser capabilities.
- With slot platform off, no slot-aware parser is assembled and document
  factories keep legacy behavior.
- With slot platform on, default parser dispatch matches `LocalDocumentParser`
  for text and binary fallback files.
- A custom document parser slot can be selected by suffix.
- Duplicate parser IDs fail fast.
- CLI/API/doged slot discovery lists `document.local_parser`.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0045: Slot Discovery Surfaces
- ADR-0047: Watcher Slot Consumer
