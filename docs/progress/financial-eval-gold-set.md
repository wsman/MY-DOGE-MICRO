# Financial Eval Gold Set

Generated: 2026-06-21

## Purpose

Wave 3 establishes a first local-reference financial research evaluation set.
It is designed to measure whether the Research Copilot can ground claims in
documents, cite the right evidence, preserve key numbers, and record cost and
latency metadata.

This is not yet a production human-labeled benchmark. It is a structured seed
set that can be replaced or expanded with analyst-reviewed annual reports,
presentations, chart images, and portfolio files.

## Current Coverage

Source: `tests/eval/gold_cases.json`

| Area | Count |
|---|---:|
| Total cases | 30 |
| Required categories | 6 |
| Citation labels | 26 |
| Numerical labels | 26 |
| Unsupported-claim labels | 5 |

Required categories covered:

- `annual_report`
- `presentation`
- `chart_image`
- `portfolio_csv`
- `unsupported_claim`
- `multi_turn`

## Scoring Harness

Source: `tests/eval/gold_eval.py`

The harness validates required fields and scores observation files with:

- retrieval recall
- retrieval precision
- citation precision
- numerical consistency
- usage/cost/latency coverage
- average cost
- average latency

The observation shape is intentionally simple so future runtime jobs, manual
notebooks, or CI smoke runs can emit comparable JSON without coupling the gold
set directly to one model backend.

## Current Boundary

The cases use local reference IDs such as `doc-*`, `evd-*`, and `page-*`.
They are suitable for harness and regression development, but they do not prove
live Kimi quality, OCR quality, vision quality, or analyst acceptance.

Wave 3 is only complete when a later operator run attaches real documents or
fixtures, captures model observations, and records acceptance thresholds against
this schema.

Analyst-labeled live benchmark evidence template:
`production/qa/evidence/eval/analyst-benchmark-template-2026-06-22.json`

Analyst-labeled live benchmark validator:
`scripts/validate_analyst_benchmark_evidence.py`

Analyst-labeled live benchmark evidence builder:
`scripts/build_analyst_benchmark_evidence.py`

The builder reads a redacted observations JSON plus an approved threshold JSON,
scores the gold cases with `tests/eval/gold_eval.py`, and writes passed or
failed evidence for the validator. Failed evidence is allowed only when it
contains issue references; this keeps benchmark regressions recordable without
pretending they passed.

The template validates only with `--allow-template`; default validation requires
completed analyst review, live Kimi observations, approved thresholds, and trend
history evidence.
