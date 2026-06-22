# Research Gold Set Evidence - 2026-06-21

## Scope

This evidence records Wave 3 setup for a financial research evaluation gold set:

- 30 local-reference cases in `tests/eval/gold_cases.json`.
- Coverage across annual reports, presentations, chart images, portfolio CSVs,
  unsupported claims, and multi-turn follow-ups.
- Citation, numerical, and insufficient-evidence labels.
- Offline validation and scoring helpers in `tests/eval/gold_eval.py`.
- Targeted tests in `tests/eval/test_gold_eval.py`.

## Gold Set Summary

| Metric | Value |
|---|---:|
| Case count | 30 |
| Required categories covered | 6 / 6 |
| Citation labels | 26 |
| Numerical labels | 26 |
| Unsupported-claim labels | 5 |
| Execution profiles | `financial_research`, `vision_analysis` |

## Automated Evidence

| Check | Result | Notes |
|---|---:|---|
| `.\.venv\Scripts\python.exe -m json.tool tests\eval\gold_cases.json > $null` | PASS | Gold cases JSON parses successfully. |
| `.\.venv\Scripts\python.exe -m py_compile tests\eval\gold_eval.py` | PASS | Gold scoring helper compiles. |
| `.\.venv\Scripts\python.exe -m pytest tests\eval\test_gold_eval.py tests\eval\test_run_eval.py tests\eval\test_failure_injection.py -q` | PASS | `7 passed`; covers gold-set validation, scoring metrics, and existing eval smoke/failure-injection tests. |
| `git diff --check` | PASS | No whitespace errors; line-ending warnings only. |

## Evaluation Boundary

This is a seed benchmark, not a production acceptance benchmark. The labels are
structured local references rather than analyst-reviewed evidence extracted from
licensed filings or provider data.

The following evidence remains required before claiming business-quality Eval:

- Real annual report, deck, chart image, and portfolio fixtures attached to the
  runtime document pipeline.
- Captured observations from live Kimi K2.6/K2.7 runs.
- Analyst-reviewed citation labels and numeric tolerance decisions.
- Thresholds for retrieval recall, citation precision, numerical consistency,
  cost, and latency.
- Regression trend history across repeated runs.

The operator-facing evidence template for this remaining gate is
`production/qa/evidence/eval/analyst-benchmark-template-2026-06-22.json`.
Validate completed evidence with
`scripts/validate_analyst_benchmark_evidence.py`; the current template only
passes with `--allow-template`.

## Verdict

Wave 3 now has a measurable evaluation schema and a 30-case local-reference
gold set. It can support regression development immediately, but it does not
close the production Eval gap until live observations and analyst-reviewed
labels are added.
