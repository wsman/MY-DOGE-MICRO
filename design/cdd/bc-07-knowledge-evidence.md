# Bounded Context 07: Knowledge & Evidence

> **Status**: In Review
> **Author**: Codex
> **Last Updated**: 2026-06-23
> **Related ADRs**: ADR-0014, ADR-0017, ADR-0021
> **Source Baseline**: docs/progress/platformization-consolidation-baseline.md

## Overview

Knowledge & Evidence owns documents, pages, chunks, retrieval, claims,
citations, provenance, and the run-summary read model. It provides source
grounding and evidence inspection for research and runtime outputs.

## User Promise

An operator can trace important claims back to source material, inspect support
status, and separate grounded evidence from unsupported generated text.

## Responsibilities

- Own Document, Page, Chunk, Claim, Citation, Provenance, and Eval read-model
  semantics.
- Own document ingestion, retrieval, RAG context, citation extraction, and run
  summary query contracts.
- Preserve source-backed snippets with ACL-safe access rules.
- Expose evidence and summary query APIs to Web, SDK, and workflows.
- Provide deterministic eval profiles for citation coverage and numeric
  consistency.

## Out of Scope

- Does not own Research narrative generation or product-domain calculations.
- Does not own runtime run state transitions or model/tool execution loops.
- Does not own tenant policy, ACL decisions, audit persistence, or secrets.
- Does not own vector or persistence adapters directly as product modules.

## Public Contract

| Contract | Shape | Consumers |
|----------|-------|-----------|
| Document ingestion | File/source -> document/page/chunk records | Research cases, API |
| Retrieval | Query + scope -> grounded context snippets | Runtime, research |
| Claim/citation assembly | Run outputs -> claims and citations | Run summary API |
| Run summary read model | Run id -> summary, claims, citations, evals | Web, SDK, API |
| Eval profile | Artifact/summary -> deterministic eval records | Governance, runtime |

## Current Source Surfaces

| Existing Artifact | Treatment |
|-------------------|-----------|
| `design/cdd/document-evidence-pipeline.md` | Detailed design input for ingestion and evidence. |
| `design/cdd/run-summary-citation-api.md` | Detailed design input for query API and read model. |
| Research Insight Knowledge Base | Split: evidence storage moves here; research notes remain Research. |
| Run summary router | Query delivery surface over evidence services. |
| Vector and persistence code | Adapter concerns behind ports. |

## Dependencies

- Depends on Governance & Evaluation for ACL, audit, retention, and maturity
  checks through ports.
- Depends on Agent Runtime for run ids, artifacts, and generated outputs.
- Serves Research, Workspace & Workflow, Web, API, SDK, and CLI through query
  contracts.
- Must not directly call product-domain services for business decisions.

## Migration Acceptance Criteria

- Run Summary Citation API is documented as a Knowledge & Evidence query API.
- ACL is applied before source snippets leave the evidence boundary.
- Unsupported claims are preserved as unsupported, not silently dropped.
- Retrieval and citation tests remain deterministic and network-free.
- Eval profiles are named and linked from workflow templates where required.

## Governance Notes

- Summary and citation outputs are experimental until citation coverage gates
  pass.
- Missing citation support must be visible to clients.
- Evidence access must preserve tenant/user/document scoping once enterprise
  identity is accepted.
