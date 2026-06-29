# Sprint F CDD: Evaluation Quality Closure

> **Status**: Accepted / Local engineering scope complete
> **Author**: Codex implementation agent
> **Last Updated**: 2026-06-29
> **Governing ADRs**: ADR-0024, ADR-0026
> **Runtime Posture**: `production_ready: false`, `stable_declaration: forbidden`, Level 3 `experimental`

## Overview

Sprint F closes the next honest engineering gap after Sprint E: the platform
has persisted runtime, evidence storage, citation assembly, and governance
gates, but retrieval/citation quality is not yet measured through the real
runtime path. Sprint F creates a deterministic local baseline over the 35-case
financial gold set and packages its observations so they can feed the existing
W3-live analyst benchmark path when real operator inputs are available.

Sprint F is not a feature-expansion sprint. It does not add financial tools,
Web pages, provider adapters, SDK registry releases, or production auth claims.

## User Promise

An operator or solution architect can run one local command and get a complete
35-case citation-quality baseline with traceable runtime runs, events, artifacts,
retrieved evidence IDs, citation markers, support classifications, numerical
labels, and usage fields. The result is useful for engineering quality work, but
it cannot be confused with live analyst evidence or production readiness.

## Detailed Design

### Core Specification

1. Seed deterministic local documents, pages, chunks, and evidence records from
   `tests/eval/gold_cases.json`.
2. Preserve every labeled `expected_citations[].evidence_id` exactly in seeded
   evidence records and runtime observations.
3. Use an isolated temporary SQLite DB and temporary file storage for each
   benchmark run.
4. Build a persisted `PersistedResearchAgentRuntime` with a case-aware scripted
   model and a benchmark-only `lookup_evidence` tool registry.
5. Execute every gold-set case through runtime create-run, tool-call, tool-result,
   model-response, and artifact-finalization paths.
6. Map runtime output into the shape accepted by
   `tests/eval/gold_eval.py::score_observations`.
7. Write `citation-quality-baseline-YYYY-MM-DD.json` and a markdown summary
   under `production/qa/evidence/eval/`.
8. Include a W3-live observation-input mapping with
   `w3_live_closure_allowed: false`.
9. Preserve explicit `evd-*` evidence IDs from tool results through runtime
   evidence chunk conversion and citation injection.
10. Write repeatable local trend-history JSONL rows from the citation baseline
    without recording raw run IDs or claiming W3-live closure.

### States and Transitions

| State | Entry Condition | Exit Condition | Next State |
|-------|-----------------|----------------|------------|
| Draft | CDD, sprint plan, and QA plan are created. | Local benchmark code exists. | Local Baseline |
| Local Baseline | 35 cases run through persisted runtime. | Baseline JSON/summary exists and tests pass. | Quality Tuning |
| Quality Tuning | Baseline identifies concrete failures. | Targeted fixes improve measured metrics. | W3-live Ready |
| W3-live Ready | Local observations can be mapped to W3 input. | Real analyst labels, thresholds, live observations, and trend history exist. | External Review |
| External Review | W3-live evidence is built from real inputs. | Strict validator passes. | Closed |

## Interactions with Other Modules

| Module | Interaction | Boundary |
|--------|-------------|----------|
| Agent Runtime | Runs every case through persisted run/event/artifact flow. | Runtime does not know gold-set scoring rules. |
| Knowledge & Evidence | Stores seeded documents, chunks, and evidence IDs. | Seeding uses temporary storage only. |
| Governance & Evaluation | Scores observations and records maturity posture. | Local baseline does not close external gates. |
| Model Adapters | Uses a case-aware scripted model. | No live Kimi spend or provider dependency. |
| Interfaces | Adds an operator CLI script. | No Web expansion. |

## Data Model

| Artifact | Shape | Purpose |
|----------|-------|---------|
| `SeededEvidence` | evidence ID, case ID, claim ID, document ID, page, chunk, status | Tracks exact gold-set citation labels. |
| `observations` | `retrieved_evidence_ids`, `cited_evidence_ids`, `claim_evidence_relations`, `claims`, `numbers`, `usage` | Input to `score_observations()`. |
| baseline JSON | schema, score, observations, runs, W3 mapping | Durable local evidence. |
| W3 mapping | observations plus `w3_live_closure_allowed: false` | Bridge to analyst benchmark input without closing it. |
| local trend row | redacted hash, profiles, case count, metrics, baseline ref | Repeatable engineering trend history, not live analyst closure. |

## Edge Cases

- **Unsupported claims with no expected citations**: observations may have
  no retrieved or cited evidence; aggregate metrics must still be non-`None`
  because the full set contains supported and numeric cases.
- **Artifact assembler adds synthetic markers**: SF-007 fixed the measured
  issue by preserving explicit evidence IDs, avoiding fallback chunks for empty
  explicit result lists, and preventing doubled inline marker injection.
- **Fixture isolation leak**: every run uses temporary DB/storage by default;
  generated production evidence stores only benchmark output, not the temp DB.
- **W3-live confusion**: output filenames use `citation-quality-baseline-*`,
  not `analyst-benchmark-*`, and the JSON explicitly forbids live closure.
- **Pre-existing regression failures**: Sprint F verification uses targeted
  slices and records full-regression failures separately if full suite is run.

## Dependencies

| Dependency | Use |
|------------|-----|
| `tests/eval/gold_cases.json` | Source of 35 financial cases and labels. |
| `tests/eval/gold_eval.py` | Scoring contract. |
| `PersistedResearchAgentRuntime` | Runtime path under test. |
| `FileUploadService`, `PageExtractionService`, `ChunkingService` | Fixture document/page/chunk seeding. |
| `scripts/build_analyst_benchmark_evidence.py` | Future W3-live builder path. |
| `scripts/validate_analyst_benchmark_evidence.py` | Future strict W3-live validator. |
| `scripts/analyst_trend_history.py` | Local trend-history row generation and validation. |

## Configuration

| Parameter | Default | Behavior |
|-----------|---------|----------|
| `--output-dir` | `production/qa/evidence/eval` | Baseline evidence output directory. |
| `--gold-cases` | `tests/eval/gold_cases.json` | Benchmark case source. |
| `--date` | current local date | Output filename suffix. |
| `--observations-output` | unset | Optional W3 observation-input JSON export. |
| `analyst_trend_history.py append-local-baseline --output` | required | Local trend-history JSONL output. |
| `production_ready` | `false` | Must remain unchanged. |
| `stable_declaration` | `forbidden` | Must remain unchanged. |

## Integration Requirements

- The CLI must run without live Kimi credentials.
- The benchmark must exercise persisted runtime events and artifacts, not only
  direct scoring helpers.
- The W3 mapping must be explicit and non-closing.
- Local trend-history output must validate, be idempotent for the same baseline,
  and keep raw run/session IDs out of the JSONL.
- Governance docs must keep S017-003, AUTH-prod, W3-live, and S017-007 as
  external/operator-gated items.

## UI Requirements

Sprint F has no Web UI scope. Existing Web Research Agent surfaces may later
display evaluation summaries, but this sprint only creates backend/local
evidence and governance artifacts.

## Acceptance Criteria

- **GIVEN** the repository checkout, **WHEN**
  `scripts/run_citation_quality_benchmark.py --output-dir production/qa/evidence/eval`
  runs, **THEN** it writes dated JSON and markdown baseline files and exits 0.
- **GIVEN** the gold set, **WHEN** the runtime runner executes, **THEN** all
  35 cases produce observations and completed runtime runs.
- **GIVEN** the scorer, **WHEN** observations are scored, **THEN** required
  aggregate metrics are not `None` and citation precision is `1.0` for the
  deterministic local benchmark.
- **GIVEN** the W3-live path, **WHEN** local baseline output is inspected,
  **THEN** it includes an observation-input mapping and
  `w3_live_closure_allowed: false`.
- **GIVEN** the local baseline, **WHEN** `analyst_trend_history.py
  append-local-baseline` runs twice for the same baseline, **THEN** the first
  run writes one valid row and the second run reports no duplicate append.
- **GIVEN** external gates, **WHEN** status docs are updated, **THEN** provider,
  SDK, AUTH-prod, and W3-live remain open/deferred/review unless real evidence
  exists.

## Resolved Decisions

- Synthetic assembler-added citation markers were treated as an SF-007 quality
  bug because the first baseline measured citation precision below 1.0.
- The local deterministic benchmark now locks citation precision at `1.0`;
  broader production thresholds still require W3-live analyst review.
- Trend-history automation is complete for local baseline rows, while W3-live
  remains blocked on real analyst labels, approved thresholds, live observations,
  and operator review.
