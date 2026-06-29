#!/usr/bin/env python3
"""Run the local runtime-backed citation quality benchmark."""

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

from tests.eval.gold_set_runner import GOLD_CASES_PATH, run_all


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the deterministic local citation-quality baseline through the persisted runtime.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("production/qa/evidence/eval"),
        help="Directory for baseline JSON and markdown summary.",
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
        "--observations-output",
        type=Path,
        default=None,
        help="Optional path for W3-live observation-input JSON mapped from the local baseline.",
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Skip writing the markdown summary.",
    )
    args = parser.parse_args()

    result = run_all(gold_cases_path=args.gold_cases)
    score = result["score"]
    incomplete = [
        item
        for item in result["runs"]
        if item.get("status") != "completed" or item.get("artifact_count") == 0
    ]
    if score["observed_case_count"] != score["case_count"] or incomplete:
        print(json.dumps({
            "error": "citation benchmark did not complete all cases",
            "observed_case_count": score["observed_case_count"],
            "case_count": score["case_count"],
            "incomplete": incomplete,
        }, indent=2, ensure_ascii=False))
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"citation-quality-baseline-{args.date}.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    markdown_path = None
    if not args.no_markdown:
        markdown_path = args.output_dir / f"citation-quality-baseline-{args.date}.md"
        markdown_path.write_text(_markdown_summary(result), encoding="utf-8")

    if args.observations_output is not None:
        args.observations_output.parent.mkdir(parents=True, exist_ok=True)
        args.observations_output.write_text(
            json.dumps(result["w3_live_observation_input"], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    print(json.dumps({
        "passed": True,
        "baseline": str(json_path),
        "summary": str(markdown_path) if markdown_path is not None else None,
        "observations_output": str(args.observations_output) if args.observations_output else None,
        "case_count": score["case_count"],
        "observed_case_count": score["observed_case_count"],
        "metrics": score["metrics"],
        "w3_live_closure_allowed": False,
    }, indent=2, ensure_ascii=False))
    return 0


def _markdown_summary(result: dict[str, Any]) -> str:
    metrics = result["score"]["metrics"]
    lines = [
        "# Citation Quality Baseline",
        "",
        f"- Schema: `{result['schema_version']}`",
        f"- Source: `{result['source']}`",
        f"- Runtime path: `{result['runtime_path']}`",
        f"- Case count: {result['score']['case_count']}",
        f"- Observed case count: {result['score']['observed_case_count']}",
        f"- W3-live closure allowed: `{str(result['w3_live_closure_allowed']).lower()}`",
        "",
        "## Metrics",
        "",
    ]
    for key in [
        "retrieval_recall",
        "retrieval_precision",
        "citation_precision",
        "claim_evidence_precision",
        "support_classification_accuracy",
        "numerical_consistency",
        "usage_cost_record_coverage",
        "avg_cost_usd",
        "avg_latency_ms",
    ]:
        lines.append(f"- `{key}`: {metrics.get(key)}")
    lines.extend([
        "",
        "## Gate Posture",
        "",
        "This is a local deterministic engineering baseline. It can be mapped into",
        "the W3-live observation input shape, but it does not close W3-live analyst",
        "benchmark requirements without approved materials, human labels, live Kimi",
        "observations, approved thresholds, and trend history.",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
