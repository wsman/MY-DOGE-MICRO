# ADR-0026: Artifact Citation Assembly

## Status

Accepted

## Date

2026-06-28

## Last Verified

2026-06-28

## Decision Makers

Implementation agent; project owner approval via `design/cdd/sprint-b-citation-evidence-closure.md`.

## Summary

Introduce `ArtifactCitationAssembler` as a bridge between tool-retrieved evidence and the final research artifact. The assembler extracts claims from artifact content, maps them to evidence chunks via `IEvidenceRepository`, classifies claim-to-evidence support with `CitationSupportClassifier`, injects inline citation markers (`[^evd-xxx]`), appends a citation appendix, and returns structured eval metadata (`claims`, `citations`, `relations`, `coverage_ratio`). The assembler is invoked by `RunStepper` before `ArtifactFinalizer.build_artifact`, and its output is merged into the artifact `data` dict. This closes the citation gap identified in ADR-0017 and enables deterministic eval scoring of claim-evidence relations.

## Engine/Stack Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI 0.123.8, Pydantic 2.12.4, SQLite local persistence |
| **Domain** | Agent Runtime / Evidence / Citation |
| **Knowledge Risk** | LOW — all APIs (dataclasses, Protocol, regex) are stable in Python 3.10+ |
| **References Consulted** | `docs/reference/python/VERSION.md`, `design/cdd/sprint-b-citation-evidence-closure.md`, `design/cdd/document-evidence-pipeline.md`, `design/cdd/run-summary-citation-api.md`, `design/cdd/research-copilot-agent-runtime.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Unit tests for assembler, contract tests for run summary API, benchmark tests for citation precision |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0011, ADR-0014, ADR-0017, ADR-0025 |
| **Enables** | Deterministic claim-evidence eval scoring, Vue citation rendering, SDK structured artifact consumption |
| **Blocks** | Sprint B implementation stories until assembler contract and repository extensions are accepted |
| **Ordering Note** | Must be implemented after ADR-0025 (streaming semantics) because `RunStepper` is the integration point, and after ADR-0017 because the run summary API consumes assembler output. |

## Context

### Problem Statement

The Research Copilot Agent Runtime executes tools that return evidence-bearing data (document chunks, RAG results, market data with source references). However, the final artifact produced by `ArtifactFinalizer` carries only raw text and a `citation_precision` score computed by regex-scanning the artifact for evidence IDs. There is no structured pipeline that:

1. Extracts claims from the artifact text.
2. Maps claims to evidence chunks.
3. Classifies how well each evidence item supports each claim.
4. Injects inline citation markers so downstream renderers can hyperlink.
5. Persists the claim/citation/relation graph for eval and API consumption.

This gap means:
- Eval metrics like `claim_evidence_relation_count` and `supported_relation_count` are computed ad-hoc in `BuildRunSummary` from raw dicts, not from a typed, validated graph.
- The Vue UI and SDK clients cannot reliably show which claims are supported because the artifact text lacks inline markers.
- Unsupported claims may go unnoticed because there is no systematic claim extraction.

### Current State

- `ArtifactFinalizer` (`src/doge/application/agent/artifact_finalizer.py`) creates `AgentArtifact` with `kind="investment_memo"`, `title="Investment Committee Memo"`, and evaluation metrics from `IArtifactEvaluationService.metrics()`.
- `RunStepper` (`src/doge/application/agent/run_stepper.py`) orchestrates model execution, tool execution, and artifact finalization. Tool results are recorded as `TOOL_RESULT` events but their evidence content is not extracted for citation assembly.
- `BuildRunSummary` (`src/doge/application/use_cases/run_summary.py`) assembles summary, claims, citations, and eval from runtime state and evidence repository. It does ad-hoc claim deduplication and citation generation but lacks structured `ClaimEvidenceRelation` ranking.
- `CitationService` (`src/doge/application/services/citation_service.py`) builds `CitationRecord` from raw evidence dicts and computes `citation_precision_score` via regex.
- `ClaimValidationService` (`src/doge/application/services/claim_validation_service.py`) validates claims against evidence using keyword/number overlap.
- `CitationSupportClassifier` (`src/doge/application/services/citation_support_classifier.py`) classifies claim-to-evidence support without external model calls.
- `FinancialEvalService` (`src/doge/application/services/financial_eval_service.py`) aggregates eval metrics including claim-evidence relations.
- Domain models exist: `ClaimRecord`, `CitationRecord`, `ClaimEvidenceRelation`, `EvidenceRecord`, `DocumentChunk` — but there is no `EvidenceChunk` join model and no repository method to efficiently fetch evidence with chunk metadata.
- `IEvidenceRepository` (`src/doge/core/ports/evidence_repository.py`) has `save_page`, `list_pages`, `save_chunk`, `list_chunks`, `save_evidence`, `get_evidence`, `list_evidence` — but no `get_chunk`, `list_evidence_chunks`, or `get_evidence_batch`.

### Constraints

- Runtime remains experimental; production readiness is false.
- All eval metrics must be deterministic and testable without live model calls.
- Enterprise ACL must be enforced at the repository level; the assembler must not see denied evidence.
- The assembler must not block artifact creation on error; it must fall back to citation-free output.
- Inline citation markers must not collide with existing markdown or model-generated markers.
- Multi-turn runs must accumulate tool results across turns, not just the current turn.

### Requirements

1. Introduce `EvidenceChunk` as a read-only join of `EvidenceRecord` and `DocumentChunk`.
2. Extend `IEvidenceRepository` with `get_chunk`, `list_evidence_chunks`, and `get_evidence_batch`.
3. Extend `ToolResult` with `evidence_refs` so tool results carry lightweight citation metadata.
4. Implement `ArtifactCitationAssembler` with a claim-extract -> evidence-fetch -> classify -> rank -> cite -> inject pipeline.
5. Integrate the assembler into `RunStepper` so final artifacts always include citation data when evidence is available.
6. Update `ContextBuilder` system prompt to explicitly request inline citation markers.
7. Add a citation precision benchmark under `tests/benchmark/`.
8. Update `ArtifactFinalizer.build_artifact` to accept and merge `citation_data`.

## Decision

### 1. EvidenceChunk Domain Model

Introduce `EvidenceChunk` as a frozen dataclass in a new module `src/doge/core/domain/evidence_chunk_models.py`. It is a lightweight, read-only evidence view produced from tool results and repository joins. It carries the evidence binding (`evidence_id`, `document_id`, `page_number`, `chunk_id`, `run_id`) and the textual content (`text`) together with provenance metadata (`source_tool`, `created_at`).

```python
@dataclass(frozen=True)
class EvidenceChunk:
    evidence_id: str
    document_id: str
    page_number: int
    chunk_id: str
    text: str
    source_tool: str
    run_id: str | None = None
    created_at: str = field(default_factory=utc_now)
```

Rationale: Tool results and repository queries both produce evidence snippets that the assembler needs in a single object. A typed join model avoids raw-dict passing and makes the assembler's contract explicit. The model is intentionally minimal for Sprint B; additional positional metadata (`page_id`, `start_char`, `end_char`) and scoring fields (`relevance_score`, `support_snippet`) can be added as optional fields when repository joins mature.

### 2. IEvidenceRepository Extension

Add three methods to `IEvidenceRepository`:

- `get_chunk(chunk_id: str, scope: TenantScope) -> DocumentChunk | None`: Direct chunk lookup by ID.
- `list_chunks_for_run(run_id: str, scope: TenantScope) -> list[DocumentChunk]`: List chunks linked to a run via evidence records.
- `list_evidence_chunks(*, scope: TenantScope, run_id: str | None = None, evidence_ids: list[str] | None = None, limit: int = 100) -> list[EvidenceChunk]`: Return evidence chunks for the assembler.
- `get_evidence_batch(evidence_ids: list[str], scope: TenantScope) -> list[EvidenceRecord]`: Batch lookup to avoid N+1.

Rationale: The assembler needs to resolve evidence and chunk metadata for a run. `list_evidence_chunks` is the primary method; the others are supporting lookups for edge cases and future consumers.

### 3. ToolResult Evidence Refs

Add `evidence_refs: list[EvidenceChunk] | None = None` to `ToolResult` (`src/doge/core/ports/runtime_services.py`). `ToolExecutionService.execute` normalizes raw tool result data into this field when the data contains `evidence` or `results` arrays. `ToolResult.to_json()` serializes each `EvidenceChunk` via `to_dict()` so event payloads remain JSON-serializable.

Rationale: Tool results currently carry evidence in ad-hoc dict shapes inside `data`. Normalizing to typed `EvidenceChunk` objects at the service boundary makes the assembler's input contract stable regardless of which tool produced the evidence, while preserving JSON round-tripping for event storage.

### 4. ArtifactCitationAssembler

Implement `ArtifactCitationAssembler` in `src/doge/application/agent/artifact_citation_assembler.py` with a single public method:

```python
def assemble(
    self,
    run: AgentRun,
    content: str,
    tool_results: list[ToolResult],
) -> AgentArtifact:
```

The constructor receives `evidence_repository`, `citation_service`, `claim_validation_service`, and `classifier` via dependency injection. The pipeline:
1. **Extract claims** from `content` using the configured strategy.
2. **Build evidence candidates** from `tool_results` and `evidence_repository.list_evidence_chunks(...)`.
3. **Classify support** with `CitationSupportClassifier.classify(...)` for each claim-evidence pair.
4. **Rank and select** top-N relations per claim by confidence.
5. **Build citations** as `CitationRecord` objects from selected relations.
6. **Validate claims** with `ClaimValidationService.validate(...)`.
7. **Inject inline markers** into `content` using `[^evd-{evidence_id}]`.
8. **Append citation section** with markdown-formatted source entries.
9. **Return** an `AgentArtifact` with the enriched `content` and `data` containing `claims`, `citations`, `relations`, `support_status`, `numeric_validation`, and `coverage_ratio`.

Rationale: The assembler is a pure application service with no side effects. Returning a fully formed `AgentArtifact` keeps the object consistent with `ArtifactFinalizer`'s output and simplifies `RunStepper` integration.

### 5. RunStepper Integration

In `RunStepper.step`, after the tool execution loop completes (line 170 in the current file) and before calling `ArtifactFinalizer.build_artifact`, collect all `ToolResult` objects from the loop and invoke `ArtifactCitationAssembler.assemble(...)`. Pass the resulting `citation_data` to `build_artifact`.

If the assembler raises an exception, `RunStepper` catches it, records an `ERROR` event, and falls back to calling `build_artifact` without `citation_data`. The run still completes.

Rationale: `RunStepper` is the central orchestrator. It already has all tool results and the final response content. This is the cleanest integration point because it avoids modifying `ArtifactFinalizer`'s core logic and keeps the assembler as an optional enrichment step.

### 6. ArtifactFinalizer Extension

Extend `ArtifactFinalizer.build_artifact` and the `IArtifactFinalizer` protocol to accept an optional `citation_data: dict | None = None` parameter. Merge it into the artifact `data` dict:

```python
def build_artifact(
    self,
    run: AgentRun,
    response_content: str,
    events: list[AgentEvent],
    *,
    usage: dict | None = None,
    citation_data: dict | None = None,
) -> AgentArtifact:
    ...

data = {
    **(citation_data or {}),
    **self._evaluation.metrics(content, events),
    "usage": usage or {},
}
```

Rationale: `ArtifactFinalizer` already owns artifact creation. Adding `citation_data` as an optional parameter is the minimal change that preserves backward compatibility with existing callers and alternate implementations of the `IArtifactFinalizer` protocol.

### 7. ContextBuilder System Prompt Update

Strengthen the `_system_prompt` in `ContextBuilder` to explicitly request inline citation markers:

```
You are MY-DOGE Enterprise Research Copilot. Use tools for material numbers.
When citing source material, use inline markers [^evd-{evidence_id}] after each claim.
Preserve evidence IDs from tool results in your response. Do not fabricate evidence IDs.
Request approval for high-risk publication actions.
```

Rationale: The model needs explicit instruction to produce citation markers. The existing prompt says "preserve citations" but does not specify the format. The new prompt ties the chunk format (`[document X; page Y; chunk Z]`) to the citation marker format (`[^evd-xxx]`).

### 8. Citation Precision Benchmark

Add `tests/benchmark/citation_precision_benchmark.py` with a `CitationPrecisionBenchmark` class that measures:

- `claim_coverage`: fraction of claims with at least one citation.
- `citation_validity`: fraction of citations mapping to real `EvidenceRecord` objects.
- `support_classification_accuracy`: fraction of relations matching gold labels.
- `inline_marker_presence`: fraction of claims with `[^evd-xxx]` in the artifact text.

The benchmark runs against synthetic fixtures and the gold case set (`tests/eval/gold_cases.json`). Output is a JSON dict compatible with `tests/eval/run_eval.py`.

Rationale: The benchmark provides a fast, deterministic way to track regression on citation quality without running full end-to-end evals.

## Alternatives Considered

### Alternative 1: Assembler Inside ArtifactFinalizer
- **Description**: Move the assembler logic into `ArtifactFinalizer.build_artifact` so it is invisible to `RunStepper`.
- **Pros**: Fewer files changed; `RunStepper` stays unchanged.
- **Cons**: `ArtifactFinalizer` would need access to `IEvidenceRepository` and `ToolResult` list, bloating its contract. It would also lose the ability to fall back on assembler error because `ArtifactFinalizer` has no event-recording capability.
- **Rejection Reason**: Violates single-responsibility; `ArtifactFinalizer` should create artifacts, not orchestrate evidence lookups.

### Alternative 2: No EvidenceChunk — Use Raw Dicts
- **Description**: Pass raw evidence dicts directly to the assembler and let it resolve chunk metadata client-side.
- **Pros**: No new domain model; no repository extension.
- **Cons**: N+1 chunk lookups; assembler logic becomes coupled to repository internals; type safety is lost.
- **Rejection Reason**: The existing codebase already suffers from raw-dict passing (e.g., `evidence_records_from_results`). Adding a typed join model is a deliberate clean-architecture improvement.

### Alternative 3: Persist Claims/Citations/Relations
- **Description**: Add `IClaimRepository`, `ICitationRepository`, and `IRelationRepository` ports, and persist the assembled graph.
- **Pros**: Enables historical claim tracking, incremental assembly, and cross-run claim deduplication.
- **Cons**: Significant scope increase; requires migration, new tables, and new repository adapters. The current use case only needs in-memory assembly for a single run.
- **Rejection Reason**: Out of scope for Sprint B. Can be revisited when cross-run claim tracking is needed.

### Alternative 4: Model-Based Claim Extraction
- **Description**: Use an LLM call to extract claims from the artifact text instead of heuristics.
- **Pros**: Higher-quality claim extraction; handles complex sentences.
- **Cons**: Adds latency, cost, and non-determinism. Violates the "eval must be deterministic without live model calls" constraint.
- **Rejection Reason**: The default strategy is heuristic. A model-based strategy can be added as a plugin later without changing the assembler contract.

## Consequences

### Positive

- Every artifact can now carry a structured claim/citation/relation graph.
- Eval metrics (`coverage_ratio`, `claim_evidence_relation_count`, `supported_relation_count`) are computed from typed objects, not regex scans.
- Inline citation markers enable downstream hyperlinking in Vue UI, markdown export, and PDF generation.
- The assembler is a pure service with no side effects, making it fully unit-testable.
- The `EvidenceChunk` join model improves type safety and reduces N+1 queries.
- The benchmark provides a fast regression signal for citation quality.

### Negative

- `IEvidenceRepository` gains three new methods; all adapters must implement them.
- `RunStepper` gains a new dependency (`ArtifactCitationAssembler` or `IEvidenceRepository`), increasing constructor parameter count.
- The assembler adds CPU cost to artifact creation (claim extraction + classification + ranking). This is bounded by `evidence_chunk_limit` and `max_citations_per_claim`.
- Inline citation markers increase artifact text size; this is bounded by the number of claims and citations.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Heuristic claim extraction misses material claims | MEDIUM | MEDIUM | Configurable strategy; `[^?]` markers flag unsupported claims; human review is expected. |
| Repository adapter does not implement new methods | LOW | HIGH | Add `NotImplementedError` defaults with fallback; unit tests catch missing implementations. |
| Inline markers collide with model-generated text | LOW | LOW | Assembler detects existing `[^...]` sequences and appends without collision. |
| Assembler error blocks artifact creation | LOW | HIGH | `assembler_fallback_on_error=True` default; `RunStepper` catches exceptions and falls back. |
| Enterprise ACL gaps expose denied evidence | LOW | HIGH | Repository filters at query level; assembler never sees denied chunks. |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|---------------|--------|
| Artifact creation latency | ~10ms (text only) | ~50-200ms (with assembly) | < 500ms per artifact |
| Evidence chunk queries | N/A | 1 query per run | Bounded by `evidence_chunk_limit` (default 100) |
| Claim-evidence classifications | N/A | O(claims * evidence) | Bounded by `max_citations_per_claim` |
| Artifact text size | ~2-5KB | ~2.5-6KB (with markers + appendix) | < 10KB |
| Memory | O(artifact + events) | O(artifact + events + claims + citations) | Bounded by `evidence_chunk_limit` |

## Migration Plan

1. Add `EvidenceChunk` domain model and `evidence_chunk_models.py`.
2. Extend `IEvidenceRepository` port with new methods.
3. Implement new methods in `SQLiteEvidenceRepository` (or the active adapter).
4. Extend `ToolResult` with `evidence_refs`.
5. Update `ToolExecutionService.execute` to populate `evidence_refs`.
6. Implement `ArtifactCitationAssembler`.
7. Extend `ArtifactFinalizer.build_artifact` with `citation_data`.
8. Update `RunStepper.step` to call assembler and pass result to finalizer.
9. Update `ContextBuilder._system_prompt`.
10. Add benchmark module.
11. Add unit tests for all new components.
12. Add contract tests for run summary API with assembled citations.
13. Update `tests/eval/run_eval.py` to collect assembler metrics.
14. Verify gold eval `relation_support` category passes.

**Rollback plan**: Revert `RunStepper` to call `ArtifactFinalizer` without assembler; remove `citation_data` parameter from `build_artifact`. The assembler and benchmark can remain in the codebase but are not invoked. No database migration is required because no new tables are added.

## Validation Criteria

- [ ] `tests/unit/domain/test_evidence_chunk.py` passes.
- [ ] `tests/unit/ports/test_evidence_repository_extension.py` passes (adapter implements new methods).
- [ ] `tests/unit/agent/test_artifact_citation_assembler.py` passes (all pipeline steps).
- [ ] `tests/unit/agent/test_run_stepper.py` includes tests for assembler integration and fallback.
- [ ] `tests/unit/agent/test_artifact_finalizer.py` includes test for `citation_data` parameter.
- [ ] `tests/unit/agent/test_context_builder.py` includes test for updated system prompt.
- [ ] `tests/contract/test_run_summary_api.py` includes tests for claim-evidence relations and redaction.
- [ ] `tests/benchmark/citation_precision_benchmark.py` runs and reports metrics.
- [ ] `tests/eval/test_gold_eval.py` validates `relation_support` category.
- [ ] `docs/architecture/adr-0026-artifact-citation-assembly.md` is accepted.
- [ ] `design/cdd/sprint-b-citation-evidence-closure.md` is accepted.

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `sprint-b-citation-evidence-closure.md` | Introduce `EvidenceChunk`, extend repository, implement assembler, integrate into finalizer, update prompt, add benchmark. | Defines all architectural decisions for the sprint. |
| `document-evidence-pipeline.md` | Citation drill-down must verify document access. | `IEvidenceRepository` filters at query level; assembler only sees accessible evidence. |
| `run-summary-citation-api.md` | Structured claims, citations, and eval endpoints. | Assembler produces the typed graph that `BuildRunSummary` consumes. |
| `research-copilot-agent-runtime.md` | Tool results flow into artifacts with citation provenance. | `RunStepper` passes tool results to assembler; assembler enriches artifact data. |

## Related

- ADR-0011: Agent Runtime Levels
- ADR-0014: Multimodal Financial Evidence
- ADR-0017: Run Summary Citation API
- ADR-0025: Runtime Streaming Semantics
- `design/cdd/sprint-b-citation-evidence-closure.md`
- `design/cdd/document-evidence-pipeline.md`
- `design/cdd/run-summary-citation-api.md`
- `design/cdd/research-copilot-agent-runtime.md`
- `src/doge/application/agent/artifact_finalizer.py`
- `src/doge/application/agent/run_stepper.py`
- `src/doge/application/agent/context_builder.py`
- `src/doge/core/ports/evidence_repository.py`
- `src/doge/core/ports/runtime_services.py`
- `src/doge/platform/runtime/services.py`
