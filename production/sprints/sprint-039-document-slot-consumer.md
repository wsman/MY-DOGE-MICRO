# Sprint 039 - Document Slot Consumer

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-07

## Summary

Sprint 039 implements the document-facet consumer slice from
`C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint adds a built-in `document.local_parser` slot and wires document
parser contributions into the file upload and page extraction parser seam
through a slot-aware `ParserDispatcher`. The built-in slot wraps the existing
`LocalDocumentParser`, so default behavior is parity preserving.

This sprint makes document parsers an actual slot contribution point. It does
not complete the full OpenClaw-like Slot Platform.

## Scope

- Add ADR-0048 and this sprint CDD/governance trail.
- Add `ParserDispatcher` in `doge.platform.evidence.document_parsers`.
- Add `LocalDocumentParserSlot` in `doge.infrastructure.documents.slot`.
- Register `document.local_parser` in the built-in slot registry.
- Add `build_slot_aware_document_parser()` in
  `src/doge/bootstrap/runtime_factories/slots.py`.
- Wire document gateway factories to use slot-aware parser dispatch when
  `DOGE_FEATURE_SLOT_PLATFORM` is enabled.
- Extend CLI, doged, and `/v1/slots` tests to cover `document.local_parser`
  status.
- Add document slot unit tests, parser-dispatcher tests, and document parity
  tests.
- Update the OpenClaw-like plan file.

## Explicitly Out of Scope

- Kimi file parser, OCR, vision chart parser, page-layout extraction, or
  multimodal parser policy.
- Parser active health probes or runtime permission enforcement.
- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, or `SlotLoader`.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- Persistence schema, ModelRouter/ProfileRegistry, external auth, or worker
  behavior changes.
- Production readiness declaration or external/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows the
recent local platform sprint precedent where no new story-status tracking is
introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-039-document-slot-consumer-manifest.md`.

Initial verification result:

- Document slot / dispatcher / parity focused suite passed: 11 tests.
- CLI/API/doged slot discovery focused suite passed: 43 tests.
- Page extraction and file upload focused suite passed: 14 tests.

Final broad validation is recorded in the evidence manifest.
