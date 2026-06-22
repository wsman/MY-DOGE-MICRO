# CDD: Document Evidence Pipeline (Module #14)

> **Status**: In Review
> **Created**: 2026-06-21
> **Last Verified**: 2026-06-21
> **Governing ADRs**: ADR-0011, ADR-0014, ADR-0015, ADR-0001, ADR-0003, ADR-0005
> **Traceability**: TR-051, TR-052, TR-053, TR-054, TR-057

---

## Overview

Document Evidence Pipeline owns document upload metadata, page extraction,
chunking, evidence persistence, and provider-bound file/vision serialization.
It supports the Research Copilot by turning uploaded files into citeable local
evidence rather than ungrounded prompt text.

The pipeline exists in release-follow-up implementation slices from S009/S010.
It remains experimental until parser coverage, live-provider evidence, and
runtime maturity gates are complete.

## User Promise

An operator can attach a document, preserve its source metadata, inspect parsed
pages/chunks, and let the copilot ground answers in local evidence with source
references.

## Detailed Design

Document ingestion has four stages:

1. upload/register document metadata through CLI or API.
2. persist file metadata and optional provider file ID.
3. extract pages/chunks into local storage.
4. expose source-backed evidence to agent tools and RAG/evidence lookup.

Kimi Files and Kimi Vision integrations stay behind adapter boundaries. The
pipeline records provider IDs and request-shape evidence without making the
provider a storage owner.

Enterprise deployments must apply tenant ACL filters before any document,
chunk, evidence, or citation is returned to a run, RAG query, tool call, API
client, or UI. ADR-0015 owns the identity boundary; this module owns document
ACL enforcement once a trusted `EnterpriseContext` is available.

## Data Model

- document: ID, filename, content type, size, checksum, source surface,
  provider file ID when present.
- page: document ID, page number, extracted text, parser metadata.
- chunk: document ID, page range, chunk index, normalized text, token/character
  metadata.
- evidence: source document/page/chunk IDs, quote/snippet, retrieval score, tool
  or run provenance.
- ACL metadata: tenant ID, allowed actor/group references, classification, and
  policy version needed to reconstruct why a document was visible.

## Edge Cases

- Unsupported file types must fail with operator-safe errors and keep metadata
  consistent.
- Empty or image-only files may create metadata without text chunks.
- Provider file upload success without local parse success must remain a
  partial state, not evidence availability.
- Page/chunk IDs must remain stable enough for citations after re-open.
- Missing ACL metadata in enterprise mode must deny access by default.
- Citation drill-down must verify document access again instead of trusting the
  run artifact alone.

## Dependencies

- Market Data Storage (#2) for local SQLite/DuckDB persistence patterns.
- Research Insight Knowledge Base (#7) for source-backed notes/evidence
  coexistence.
- Research Copilot Agent Runtime (#13) for tool calls and run artifacts.

## Configuration

- Document storage remains under the configured local data directory.
- Provider API keys are optional; local parser tests must run without live
  network access.
- Parser support and limits are documented in
  `docs/progress/document-parser-support-matrix.md`.

## Integration Requirements

- CLI `/attach` and API upload metadata must converge on the same document
  registry.
- `/api/documents` compatibility and `/v1/documents` daemon routes must not
  diverge in persisted metadata semantics.
- Kimi adapters may serialize file IDs and vision messages, but the canonical
  evidence store remains local.
- RAG, evidence lookup, citation assembly, and document APIs must apply the same
  tenant ACL predicate in enterprise mode.

## UI Requirements

UI surfaces should show upload status, parser availability, and citation source
metadata. They must distinguish "uploaded", "parsed", and "available as
evidence" states.

## Acceptance Criteria

- [ ] TR-051 covers upload metadata and document registration.
- [ ] TR-052 covers page/chunk/evidence persistence.
- [ ] TR-053 covers Kimi file/vision provider boundary.
- [ ] Unsupported or partially parsed documents do not appear as complete
      evidence.
- [ ] No documentation declares document evidence production-ready while
      runtime maturity remains false.
- [ ] TR-057 covers tenant ACL persistence and deny-by-default document/evidence
      retrieval in enterprise mode.

## Open Questions

1. Which parser formats are required before operator-facing promotion?
2. Should provider file IDs be pruned with local documents or retained for
   audit?
3. What citation granularity is required for PDF pages versus plain text chunks?
4. Which ACL model should be persisted first: per-document allowlist, inherited
   portfolio/client policy, or both?
