# Sprint B: Citation/Evidence Closure

> **Status**: Accepted
> **Created**: 2026-06-28
> **Last Verified**: 2026-06-28
> **Governing ADRs**: ADR-0011, ADR-0014, ADR-0015, ADR-0017, ADR-0026
> **Traceability**: TR-051, TR-052, TR-053, TR-054, TR-057, TR-060, TR-061, TR-062
> **Sprint**: Sprint B (Citation/Evidence Closure)

---

## 1. Overview

The Citation/Evidence Closure module closes the gap between tool-retrieved evidence and the final research artifact. Today, the Research Copilot Agent Runtime executes tools that return evidence (document chunks, market data, RAG results), but the final artifact produced by `ArtifactFinalizer` carries only a raw text memo and a `citation_precision` score. There is no structured pipeline that extracts claims from the artifact, maps them to evidence chunks, classifies support status, injects inline citation markers, or persists the resulting claim/citation/relation graph. This module introduces `ArtifactCitationAssembler` as the bridge: it consumes the generated artifact content, the tool results that produced evidence, and the evidence repository, and returns a fully annotated `AgentArtifact` with inline citations, a citation appendix, and structured eval metadata.

## 2. User Promise / JTBD

**What the user is trying to accomplish:**
An investment researcher or compliance reviewer needs to verify that every material claim in a generated research memo is traceable to a source document, chunk, or market data record. They need to see inline markers (e.g., `[^evd-xxx]`) that can be clicked or resolved to full source metadata, and they need a confidence score for each claim-to-evidence link.

**What the product must reliably do:**
1. Every claim in the artifact must have zero or more supporting citations.
2. Every citation must map to a real `EvidenceRecord` or `DocumentChunk` in the evidence repository.
3. Unsupported claims must be flagged with `insufficient_evidence` status, not silently omitted.
4. The artifact text must contain inline citation markers so downstream renderers (Vue UI, markdown export, PDF) can hyperlink.
5. Eval metrics (`coverage_ratio`, `claim_evidence_relation_count`, `supported_relation_count`) must be computed deterministically from the assembled graph, not estimated from regex scans of the artifact text alone.

## 3. Detailed Behavior

### 3.1 EvidenceChunk Domain Model

Introduce `EvidenceChunk` as a lightweight read-only view that bridges `EvidenceRecord` and `DocumentChunk`.

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

`EvidenceChunk` is not persisted independently; it is assembled from tool results or by joining `EvidenceRecord` with its backing `DocumentChunk`. It exists because tool results and repository queries both produce evidence snippets, and the assembler needs a typed, JSON-serializable object rather than a raw dict.

### 3.2 IEvidenceRepository Extension

Extend the port with these methods:

```python
def get_chunk(self, chunk_id: str, scope: TenantScope) -> DocumentChunk | None: ...
def list_chunks_for_run(self, run_id: str, scope: TenantScope) -> list[DocumentChunk]: ...
def list_evidence_chunks(self, *, scope: TenantScope, run_id: str | None = None, evidence_ids: list[str] | None = None, limit: int = 100) -> list[EvidenceChunk]: ...
def get_evidence_batch(self, evidence_ids: list[str], scope: TenantScope) -> list[EvidenceRecord]: ...
```

`list_evidence_chunks` is the primary method for `ArtifactCitationAssembler`. It returns `EvidenceChunk` objects by joining `EvidenceRecord` with `DocumentChunk` at the repository level (or in-memory if the adapter does not support joins).

`get_chunk` fills the gap where a `CitationRecord` references a `chunk_id` but the assembler needs the full chunk text and position.

`get_evidence_batch` enables efficient N+1 avoidance when the assembler has a list of `evidence_id` values from tool results.

### 3.3 ToolExecutionService Evidence Annotation

`ToolExecutionService.execute` already returns `ToolResult(name, data, ok, error, safe_error)`. Extend `ToolResult` with an optional `evidence_refs` field:

```python
@dataclass(frozen=True)
class ToolResult:
    name: str
    data: dict[str, Any]
    ok: bool = True
    error: str | None = None
    safe_error: dict[str, str] | None = None
    evidence_refs: list[EvidenceChunk] | None = None
```

`evidence_refs` is populated by the tool registry when a tool returns evidence-bearing data (e.g. `data["evidence"]`, `data["results"]`). `ToolExecutionService.execute` normalizes the raw tool result into this field before returning. `ToolResult.to_json()` serializes each `EvidenceChunk` via `to_dict()` so event payloads remain JSON-safe.

In `RunStepper`, after each tool execution, the `TOOL_RESULT` event payload includes `evidence_refs` so that the event history itself carries citation provenance. This enables `ContextBuilder` to surface evidence metadata back to the model in multi-turn conversations.

### 3.4 ArtifactCitationAssembler Pipeline

`ArtifactCitationAssembler` lives at `src/doge/application/agent/artifact_citation_assembler.py` and is constructed with `evidence_repository`, `citation_service`, `claim_validation_service`, and `classifier`. Its public method is:

```python
def assemble(self, run: AgentRun, content: str, tool_results: list[ToolResult]) -> AgentArtifact:
```

**Step 1: Accept inputs**
- `run: AgentRun` — the run object (for `run_id`, `document_ids`).
- `content: str` — the generated artifact text (from `ArtifactFinalizer` or `RunStepper`).
- `tool_results: list[ToolResult]` — all tool results from the run.

**Step 2: Extract claims**
- Primary: Parse `artifact.data.get("claims")` if present (from a prior assembly or model-structured output).
- Fallback: Extract sentences from `content` using lightweight heuristics (numeric presence, assertive verbs, named entity patterns). Each sentence becomes a `ClaimRecord` with `status="insufficient_evidence"`.
- The claim extraction strategy is configurable via constructor parameters (`claim_extraction_strategy`, `max_citations_per_claim`, `min_confidence`).

**Step 3: Build evidence candidate set**
- Collect `evidence_refs` from all `tool_results`.
- Call `evidence_repository.list_evidence_chunks(scope, run_id=run.run_id)` to get full `EvidenceChunk` objects.
- Deduplicate by `evidence_id`.

**Step 4: Classify claim-to-evidence support**
- For each claim and each evidence candidate, call `CitationSupportClassifier.classify(claim.text, evidence.support_snippet)`.
- Produce a `ClaimEvidenceRelation` for each pair.
- Filter out relations with `support_status == "unrelated"` and `confidence < 0.2`.

**Step 5: Rank and select top citations per claim**
- For each claim, sort relations by `confidence` descending.
- Select top-N (default 3) relations.
- Build `CitationRecord` objects from the selected relations, linking `claim_id`, `evidence_id`, `chunk_id`, `document_id`, `page_number`, `snippet`.

**Step 6: Validate claims**
- For each claim, call `ClaimValidationService.validate(report_id=run.run_id, claim_text=claim.text, evidence_results=...)`.
- Update `ClaimRecord.status` based on validation result.

**Step 7: Embed inline citation markers**
- Scan artifact `content` for occurrences of claim text or near-match sentences.
- Append inline citation marker after each claim occurrence: `[^evd-{evidence_id}]`.
- If a claim has multiple supporting citations, append all markers in order: `[^evd-a][^evd-b]`.
- If a claim has no supporting citations, append `[^?]` to flag it for reviewer attention.

**Step 8: Append citation section**
- Append a markdown-formatted "Sources" section to `content` with numbered entries mapping each `evidence_id` to its `document_id`, `page_number`, and `snippet`.

**Step 9: Return enriched artifact**
- Return an `AgentArtifact` with the enriched `content` and `data` dict:
  ```python
  {
      "claims": [claim.to_dict() for claim in claims],
      "citations": [citation.to_dict() for citation in citations],
      "relations": [relation.to_dict() for relation in relations],
      "support_status": "supported" if all(c.status == "supported" for c in claims) else "partial",
      "numeric_validation": {},  # reserved for NumericalConsistencyService
      "coverage_ratio": len(cited_claims) / len(claims) if claims else 0.0,
  }
  ```

### 3.5 ArtifactFinalizer Integration

`ArtifactFinalizer.build_artifact` and the `IArtifactFinalizer` protocol are modified to accept an optional `citation_data` dict:

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
```

In `RunStepper.step`, after the tool execution loop completes and before calling `artifact_finalizer.build_artifact`, the stepper:
1. Collects all `ToolResult` objects from the tool loop.
2. Calls `ArtifactCitationAssembler.assemble(...)` with the content, tool results, run, and evidence repository.
3. Passes the resulting `citation_data` to `build_artifact`.

`ArtifactFinalizer` then merges `citation_data` into the artifact `data` dict alongside evaluation metrics:

```python
data={
    **self._evaluation.metrics(content, events),
    "usage": usage or {},
    **(citation_data or {}),
}
```

### 3.6 ContextBuilder System Prompt Update

The `_system_prompt` method in `ContextBuilder` is strengthened to explicitly request inline citation markers:

```
You are MY-DOGE Enterprise Research Copilot. Use tools for material numbers.
When citing source material, use inline markers [^evd-{evidence_id}] after each claim.
Preserve evidence IDs from tool results in your response. Do not fabricate evidence IDs.
Request approval for high-risk publication actions.
```

The document chunk format (`_format_chunk`) already includes `document_id`, `page_number`, and `chunk_id`. No change needed there, but the system prompt now explicitly ties the chunk format to the citation marker format.

### 3.7 Citation Precision Benchmark

A new benchmark module `tests/benchmark/citation_precision_benchmark.py` measures:

1. **Claim coverage**: fraction of claims in the artifact that have at least one supporting citation.
2. **Citation validity**: fraction of citations that map to real `EvidenceRecord` objects in the repository.
3. **Support classification accuracy**: fraction of `ClaimEvidenceRelation` classifications that match gold-set labels (when available).
4. **Inline marker presence**: fraction of claims that have at least one `[^evd-xxx]` marker in the artifact text.

The benchmark runs against:
- A synthetic fixture set (fast, deterministic, no network).
- The gold eval case set (`tests/eval/gold_cases.json`) when available.

Output is a JSON dict compatible with the eval harness so CI can track regression.

## 4. Contracts / Data Model

### 4.1 New Domain Model

| Model | Location | Fields | Purpose |
|-------|----------|--------|---------|
| `EvidenceChunk` | `src/doge/core/domain/evidence_chunk_models.py` | evidence_id, document_id, page_number, chunk_id, text, source_tool, run_id, created_at | Lightweight evidence view for citation assembly |

### 4.2 Extended Port

| Port | Location | New Methods |
|------|----------|-------------|
| `IEvidenceRepository` | `src/doge/core/ports/evidence_repository.py` | `get_chunk(chunk_id, scope)`, `list_evidence_chunks(scope, run_id, evidence_ids, limit)`, `get_evidence_batch(evidence_ids, scope)` |

### 4.3 Extended Dataclass

| Dataclass | Location | New Field |
|-----------|----------|-----------|
| `ToolResult` | `src/doge/core/ports/runtime_services.py` | `evidence_refs: list[EvidenceChunk] \| None = None` |

### 4.4 New Service

| Service | Location | Public Methods |
|---------|----------|----------------|
| `ArtifactCitationAssembler` | `src/doge/application/agent/artifact_citation_assembler.py` | `assemble(run: AgentRun, content: str, tool_results: list[ToolResult]) -> AgentArtifact` |

### 4.5 Modified Service

| Service | Location | Modified Signature |
|---------|----------|-------------------|
| `ArtifactFinalizer` | `src/doge/application/agent/artifact_finalizer.py` | `build_artifact(..., citation_data: dict \| None = None)` |
| `ToolExecutionService` | `src/doge/platform/runtime/services.py` | `execute` returns `ToolResult` with `evidence_refs` populated |
| `RunStepper` | `src/doge/application/agent/run_stepper.py` | `step` calls assembler before finalizer |

### 4.6 Schema: Artifact Data Dict (enriched)

```python
{
    "numerical_consistency": float | None,
    "citation_precision": float | None,
    "tool_execution_success": float | None,
    "usage": dict[str, Any],
    # --- new fields from assembler ---
    "claims": list[dict],           # ClaimRecord.to_dict()
    "citations": list[dict],        # CitationRecord.to_dict()
    "relations": list[dict],        # ClaimEvidenceRelation.to_dict()
    "support_status": str,         # "supported" | "partial" | "insufficient_evidence"
    "numeric_validation": dict,     # per-claim number validation
    "coverage_ratio": float,
}
```

## 5. Edge Cases

### 5.1 No Evidence Repository Configured
If `IEvidenceRepository` is `None` (local mode without document ingestion), `ArtifactCitationAssembler` falls back to extracting claims from the artifact text but sets all claim statuses to `insufficient_evidence` and all citations to empty. The artifact still gets inline `[^?]` markers for unsupported claims. Coverage ratio is 0.0. No error is raised.

### 5.2 Tool Results Without Evidence
Some tools (e.g., `stock_overview`) return market data without document-backed evidence. Their `ToolResult.evidence_refs` is `None` or empty. The assembler ignores them for citation building but still includes their data in `numeric_validation` if numbers are present.

### 5.3 Claim Extraction Fails or Returns Empty
If the heuristic claim extractor finds no sentences that look like claims, the assembler returns an empty `claims` list, `coverage_ratio: 0.0`, and `support_status: "insufficient_evidence"`. The artifact text is unchanged except for the appended citation section (which will be empty).

### 5.4 Duplicate Evidence Across Tool Calls
If multiple tool calls return the same `evidence_id`, the assembler deduplicates before classification. The `ClaimEvidenceRelation` count reflects unique (claim, evidence) pairs.

### 5.5 Enterprise ACL Denies Document Access
If `list_evidence_chunks` is called with a scope that lacks access to some documents, the repository returns only accessible chunks. The assembler never sees denied chunks, so citations to them are not produced. The `coverage_ratio` and `support_status` reflect only accessible evidence. This is consistent with ADR-0015 and ADR-0017.

### 5.6 Inline Marker Collision
If the artifact text already contains `[^...]` sequences (e.g., from a prior model turn), the assembler scans for existing markers and appends new ones without collision. The regex `\[\^evd-[A-Za-z0-9_-]+\]` is used to detect existing markers.

### 5.7 Multi-Turn Runs
In a multi-turn run, the assembler is called on the final artifact only. Prior tool results from earlier turns are included in the `tool_results` list because `RunStepper` accumulates them across the run. The `ArtifactCitationAssembler` uses all tool results for the run, not just the current turn.

### 5.8 Rollback / Partial Failure
If the assembler raises an exception (e.g., repository timeout), `RunStepper` catches it, logs the error, and falls back to calling `ArtifactFinalizer.build_artifact` without `citation_data`. The artifact is created without citations but the run still completes. The error is recorded as an `ERROR` event.

## 6. Dependencies

### Upstream
- **Document Evidence Pipeline** (`design/cdd/document-evidence-pipeline.md`) — provides `DocumentChunk`, `EvidenceRecord`, `IEvidenceRepository`.
- **Research Copilot Agent Runtime** (`design/cdd/research-copilot-agent-runtime.md`) — provides `RunStepper`, `ArtifactFinalizer`, `ContextBuilder`, `AgentRun`, `AgentEvent`.
- **Run Summary Citation API** (`design/cdd/run-summary-citation-api.md`) — consumes the enriched artifact data produced by this module.
- **Claim Validation Service** (`src/doge/application/services/claim_validation_service.py`) — used by assembler to set claim status.
- **Citation Support Classifier** (`src/doge/application/services/citation_support_classifier.py`) — used by assembler to classify relations.
- **Citation Service** (`src/doge/application/services/citation_service.py`) — used by assembler to build `CitationRecord` objects.
- **Financial Eval Service** (`src/doge/application/services/financial_eval_service.py`) — used by benchmark and `BuildRunSummary` to score relations.

### Downstream
- **Vue Web Console** (`design/cdd/vue-web-console.md`) — renders inline citations and the citation appendix.
- **SDK Daemon Client Interfaces** (`design/cdd/sdk-daemon-client-interfaces.md`) — consumes structured artifact data via `/v1/runs/{run_id}`.
- **Gold Eval Harness** (`tests/eval/gold_eval.py`) — uses benchmark output to score claim-evidence precision and support classification accuracy.

## 7. Configuration Knobs

| Knob | Default | Range | Environment Variable | Description |
|------|---------|-------|---------------------|-------------|
| `claim_extraction_strategy` | `"heuristic"` | `"structured"`, `"heuristic"`, `"none"` | `DOGE_CLAIM_EXTRACTION_STRATEGY` | How claims are extracted from artifact text |
| `max_citations_per_claim` | `3` | 1-10 | `DOGE_MAX_CITATIONS_PER_CLAIM` | Top-N citations to keep per claim after ranking |
| `min_confidence_for_citation` | `0.2` | 0.0-1.0 | `DOGE_MIN_CITATION_CONFIDENCE` | Minimum `ClaimEvidenceRelation.confidence` to include |
| `enable_inline_citations` | `True` | bool | `DOGE_ENABLE_INLINE_CITATIONS` | Whether to inject `[^evd-xxx]` markers into artifact text |
| `citation_marker_format` | `"[^evd-{id}]"` | string | `DOGE_CITATION_MARKER_FORMAT` | Format string for inline markers; `{id}` is replaced |
| `assembler_fallback_on_error` | `True` | bool | `DOGE_ASSEMBLER_FALLBACK` | If True, run completes without citations on assembler error |
| `evidence_chunk_limit` | `100` | 1-500 | `DOGE_EVIDENCE_CHUNK_LIMIT` | Max chunks to fetch from repository per assembly |

## 8. Acceptance Criteria

### 8.1 Unit Tests (BLOCKING)

- [ ] `test_evidence_chunk_create_from_record_and_chunk` — `EvidenceChunk` can be constructed from an `EvidenceRecord` and `DocumentChunk`.
- [ ] `test_evidence_repository_get_chunk_returns_chunk` — `IEvidenceRepository.get_chunk` returns a `DocumentChunk` or `None`.
- [ ] `test_evidence_repository_list_evidence_chunks_joins` — `list_evidence_chunks` returns `EvidenceChunk` objects with both evidence and chunk fields.
- [ ] `test_evidence_repository_get_evidence_batch` — `get_evidence_batch` returns all requested records, omitting missing ones.
- [ ] `test_tool_result_has_evidence_refs` — `ToolResult` can be constructed with `evidence_refs` and serializes correctly via `to_json()`.
- [ ] `test_tool_execution_service_returns_evidence_refs` — `ToolExecutionService.execute` populates `evidence_refs` when tool data contains `evidence` or `results`.
- [ ] `test_artifact_citation_assembler_extracts_claims` — Assembler extracts claims from artifact text using heuristic strategy.
- [ ] `test_artifact_citation_assembler_builds_citations` — Assembler produces `CitationRecord` objects linked to real evidence.
- [ ] `test_artifact_citation_assembler_classifies_relations` — Assembler produces `ClaimEvidenceRelation` with correct `support_status` and `confidence`.
- [ ] `test_artifact_citation_assembler_injects_inline_markers` — Artifact text contains `[^evd-xxx]` after assembly.
- [ ] `test_artifact_citation_assembler_appends_citation_section` — Artifact text ends with a "Sources" section listing citations.
- [ ] `test_artifact_citation_assembler_no_evidence_repo` — Assembler returns empty claims/citations without error when repository is None.
- [ ] `test_artifact_citation_assembler_enterprise_acl_filter` — Assembler only cites evidence from documents the scope can access.
- [ ] `test_artifact_finalizer_accepts_citation_data` — `ArtifactFinalizer.build_artifact` includes `citation_data` in artifact `data`.
- [ ] `test_run_stepper_calls_assembler_before_finalizer` — `RunStepper.step` invokes assembler and passes result to finalizer.
- [ ] `test_run_stepper_assembler_error_fallback` — `RunStepper.step` falls back to citation-free artifact on assembler error.
- [ ] `test_context_builder_prompt_requests_citations` — System prompt contains explicit instruction to use `[^evd-xxx]` markers.

### 8.2 Contract/Integration Tests (BLOCKING)

- [ ] `test_run_summary_api_includes_claim_evidence_relations` — `GET /v1/runs/{run_id}/eval` returns `claim_evidence_relation_count` and `supported_relation_count`.
- [ ] `test_run_summary_api_redacts_inaccessible_citations` — Enterprise ACL denies snippets for citations the tenant cannot access.
- [ ] `test_build_run_summary_with_assembled_citations` — `BuildRunSummary.build` uses assembler-produced `claims`, `citations`, and `relations` from artifact data.

### 8.3 Benchmark Tests (ADVISORY)

- [ ] `test_benchmark_claim_coverage_ratio` — Benchmark reports `claim_coverage >= 0.8` for gold cases with known claims.
- [ ] `test_benchmark_citation_validity` — Benchmark reports `citation_validity == 1.0` (all citations map to real evidence).
- [ ] `test_benchmark_inline_marker_presence` — Benchmark reports `inline_marker_presence >= 0.8` for gold cases.
- [ ] `test_benchmark_support_classification_accuracy` — Benchmark reports `support_classification_accuracy >= 0.75` against gold labels.

### 8.4 Eval Harness Integration (BLOCKING)

- [ ] `tests/eval/run_eval.py` collects `claim_evidence_relations` and `claims` from the assembled artifact data.
- [ ] `tests/eval/gold_eval.py` scores `claim_evidence_precision` and `support_classification_accuracy` against the 35-case gold set.
- [ ] The `relation_support` category in `REQUIRED_CATEGORIES` is validated by `test_gold_eval.py`.

### 8.5 Documentation

- [ ] `docs/architecture/adr-0026-artifact-citation-assembly.md` is accepted and merged.
- [ ] `design/cdd/sprint-b-citation-evidence-closure.md` (this document) is accepted and merged.
- [ ] `docs/progress/runtime-maturity.yaml` is updated to reflect Sprint B completion.

## Open Questions

1. Should `ArtifactCitationAssembler` be called from `ArtifactFinalizer` (inside `build_artifact`) or from `RunStepper` (outside)? The current design places it in `RunStepper` to keep `ArtifactFinalizer` focused on artifact creation and let `RunStepper` own the orchestration. This is consistent with the finding that `RunStepper` is the cleanest integration point.
2. Should claim extraction use a lightweight NLP model (e.g., spaCy sentence segmentation) or remain regex/heuristic-based? The heuristic default keeps the stack dependency-free; a model-based strategy can be added later as a plugin.
3. Should `EvidenceChunk` be a formal domain model or a repository DTO? The current design treats it as a lightweight domain model because it crosses the application-service boundary. Optional positional/scoring fields (`page_id`, `start_char`, `end_char`, `relevance_score`, `support_snippet`) may be added later without breaking the core contract.
