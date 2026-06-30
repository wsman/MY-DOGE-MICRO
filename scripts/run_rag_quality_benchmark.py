#!/usr/bin/env python3
"""Run the deterministic local RAG retrieval benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for path in (REPO_ROOT, REPO_ROOT / "src", REPO_ROOT / "packages" / "doge-sdk-python"):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from tests.eval.gold_set_runner import GOLD_CASES_PATH
from tests.eval.rag_retrieval_benchmark import run_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic local RAG retrieval quality benchmark over the gold set.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("production/qa/evidence/eval"),
        help="Directory for benchmark JSON and markdown summary.",
    )
    parser.add_argument(
        "--gold-cases",
        type=Path,
        default=GOLD_CASES_PATH,
        help="Gold-set cases JSON path.",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Date suffix for output filenames, in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Retrieval cutoff for recall/linkage metrics.",
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Skip writing the markdown summary.",
    )
    args = parser.parse_args()

    result = run_benchmark(gold_cases_path=args.gold_cases, top_k=args.top_k)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"rag-retrieval-quality-baseline-{args.date}.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    markdown_path = None
    if not args.no_markdown:
        markdown_path = args.output_dir / f"rag-retrieval-quality-baseline-{args.date}.md"
        markdown_path.write_text(_markdown_summary(result), encoding="utf-8")

    print(json.dumps({
        "passed": _passed(result),
        "baseline": str(json_path),
        "summary": str(markdown_path) if markdown_path is not None else None,
        "case_count": result["gold_set"]["case_count"],
        "observed_case_count": result["observed_case_count"],
        "metrics": result["metrics"],
        "external_gate_closure_allowed": False,
    }, indent=2, ensure_ascii=False))
    return 0 if _passed(result) else 1


def _passed(result: dict[str, Any]) -> bool:
    metrics = result["metrics"]
    return all(
        metrics[key] is not None and metrics[key] >= 0.95
        for key in (
            "retrieval_recall_at_k",
            "retrieval_precision_at_expected",
            "citation_linkage",
            "numerical_consistency",
        )
    )


def _markdown_summary(result: dict[str, Any]) -> str:
    metrics = result["metrics"]
    lines = [
        "# RAG Retrieval Quality Baseline",
        "",
        f"- Schema: `{result['schema_version']}`",
        f"- Source: `{result['source']}`",
        f"- Case count: {result['gold_set']['case_count']}",
        f"- Observed case count: {result['observed_case_count']}",
        f"- Top K: {result['top_k']}",
        f"- External gate closure allowed: `{str(result['external_gate_closure_allowed']).lower()}`",
        "",
        "## Metrics",
        "",
    ]
    for key in (
        "retrieval_recall_at_k",
        "retrieval_precision_at_expected",
        "citation_linkage",
        "numerical_consistency",
    ):
        lines.append(f"- `{key}`: {metrics.get(key)}")
    lines.extend([
        "",
        "## Gate Posture",
        "",
        "This is a local deterministic RAG quality baseline. It proves that the",
        "local text/image/parser-to-chunk retrieval path can be measured without a",
        "live model or external vector backend. It does not close W3-live, Kimi",
        "Files/Vision, OCR, or production vector backend gates.",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
