# Sprint B Acceptance Report — Citation Evidence Closure

> Date: 2026-06-28
> Plan: design/cdd/sprint-b-citation-evidence-closure.md
> Committed SHA: `28f6a1a751f5fa79714728aece1f6465b2795b5a` (Sprint B remediation on top of prior work)
> Verdict: **GO**

## Summary of Changes

Sprint B implements the artifact citation and evidence closure pipeline:

- **EvidenceChunk domain model** (`src/doge/core/domain/evidence_chunk_models.py`) — frozen dataclass with `evidence_id`, `document_id`, `page_number`, `chunk_id`, `text`, `source_tool`, `run_id`, `created_at`.
- **IEvidenceRepository extensions** (`src/doge/core/ports/evidence_repository.py`) — `get_chunk`, `list_chunks_for_run`, `list_evidence_chunks`, `get_evidence_batch` methods added.
- **SQLiteEvidenceRepository** (`src/doge/infrastructure/database/evidence_repository.py`) — implements all new port methods, including a join query for `list_evidence_chunks`.
- **ToolResult extension** (`src/doge/core/ports/runtime_services.py`) — `evidence_refs: list[EvidenceChunk] | None` carries evidence references from tool execution; `to_json()` serializes via `EvidenceChunk.to_dict()`.
- **ToolExecutionService** (`src/doge/platform/runtime/services.py`) — `_build_evidence_chunks()` populates `evidence_refs` from tool result data.
- **ArtifactCitationAssembler** (`src/doge/application/agent/artifact_citation_assembler.py`) — `assemble(run, content, tool_results)` produces `AgentArtifact` with inline `[evd-<id>]` markers and a Sources section.
- **ArtifactFinalizer** (`src/doge/application/agent/artifact_finalizer.py`) — `build_artifact` accepts optional `citation_data` parameter and merges it into artifact data.
- **IArtifactFinalizer protocol** (`src/doge/core/ports/runtime_services.py`) — updated to include `citation_data` parameter.
- **RunStepper** (`src/doge/application/agent/run_stepper.py`) — calls assembler before finalizer, passes `citation_data`, falls back on assembler error, and cleans up accumulated tool results on terminal/failure/cancellation paths.
- **ContextBuilder** (`src/doge/application/agent/context_builder.py`) — `_system_prompt` explicitly requests `[evd-<id>]` inline citation markers.
- **Benchmark** (`tests/benchmark/citation_precision_benchmark.py`) — deterministic precision/recall benchmark with `FakeClassifier`.
- **Unit tests** — EvidenceChunk, repository extensions, ToolResult evidence_refs, assembler pipeline, finalizer citation_data, run_stepper integration, context_builder prompt.
- **Integration tests** — end-to-end citation assembly through `RuntimeKernel`.
- **Contract tests** — run summary API with claim-evidence relations.
- **Gold eval** — `relation_support` category with `claim_evidence_precision` and `support_classification_accuracy` scoring.
- **ADR-0026** promoted to `Accepted`; Sprint B CDD promoted to `Accepted`.

## Test Results

- Full regression: **1777 passed, 3 failed, 8 skipped**
- New failures: **0**
- Pre-existing failures: 3 (MCP stdio transport timing, yfinance StringDtype, Sprint A plan-closure SHA256 mismatch)
- Targeted Sprint B tests: **all pass**
- Sprint B-specific tests: **50+ pass**

## Review Approvals

| Review | Approved | Notes |
|--------|----------|-------|
| Test Review | YES | Minor notes on benchmark module naming and assertion style |
| Runtime Review | YES | Memory leak fixed; remaining string-matching heuristic is documented as MVP |
| Architecture Review | YES | Port contracts aligned; ADR-0026 and CDD accepted |

## Resolved Architecture Blockers

1. **IEvidenceRepository port** — `list_evidence_chunks` and `get_evidence_batch` added with full type signatures.
2. **SQLiteEvidenceRepository** — implements both methods; assembler `getattr` fallback removed.
3. **EvidenceChunk model shape** — ADR-0026 and CDD updated to match the implemented lightweight domain model.
4. **ToolResult.evidence_refs type** — ADR-0026/CDD updated to `list[EvidenceChunk]`; `to_json()` round-trips via `to_dict()`.
5. **IArtifactFinalizer port** — `citation_data` parameter added to the Protocol.
6. **ADR-0026 status** — promoted to `Accepted`.
7. **Sprint B CDD status** — promoted to `Accepted`.

## Production Posture

Unchanged. `production_ready: false`, `stable_declaration: forbidden`, Level 3 `experimental`. No external gates were closed or opened by this sprint.

## Recommended Next Steps

1. Merge Sprint B implementation and acceptance report.
2. Generate exact-SHA remote CI evidence for the merge commit.
3. Update `docs/progress/runtime-maturity.yaml` `runtime_document_context` gate to `passed` (done in this remediation).
4. Address remaining should-fix items in a follow-up if desired:
   - Replace heuristic sentence/claim matching with a more robust phrase-injection strategy.
   - Standardize benchmark module naming to be collected directly by pytest.
5. Begin Sprint C (Kimi live smoke) or Sprint D (enterprise auth) when ready.

## Sign-off

- **Test Review**: Approved
- **Runtime Review**: Approved
- **Architecture Review**: Approved
- **Overall Sprint B Verdict**: **GO**
