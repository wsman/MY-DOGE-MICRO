# ADR-0014: Multimodal Financial Evidence

## Status

Accepted

## Date

2026-06-21

## Context

Kimi K2.6 can analyze long, multimodal financial material, but finance claims
need page-level evidence and deterministic validation. Tables, chart images,
PDF pages, PPT pages, CSVs, and RAG snippets must be auditable after a run.

## Decision

Use three evidence paths together:

- deterministic parsing for text, CSV, SQL, and financial fields
- Kimi native multimodal understanding for images, charts, page layout, and PPT
- RAG evidence for historical research, announcements, and internal policies

`MultimodalEvidenceService` assembles evidence records that can carry document,
page, chunk, bounding box, source type, parser version, retrieval score, quote,
tool call id, and run id. Final material numbers must be verified by
deterministic tools or marked `insufficient_evidence`.

## Consequences

- Kimi explains and synthesizes; deterministic tools calculate and verify.
- Citation precision and numerical consistency are Eval metrics, not marketing
  claims.
- Live Kimi Files/Vision smoke remains a maturity blocker before production
  claims.

## Verification

- `tests/unit/test_citation_service.py`
- `tests/unit/test_numerical_consistency.py`
- `tests/eval/test_run_eval.py`
- `tests/integration/test_multimodal_chat.py`
