"""Offline batch execution command for deterministic eval cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from doge.eval.runner import run


def cmd_batch(args) -> None:
    cases_path = Path(args.cases)
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    for case in cases:
        case.setdefault("auto_approve", bool(args.auto_approve))
        case.setdefault("max_tool_rounds", int(args.max_tool_rounds))
    tmp_cases = cases_path
    if cases != json.loads(cases_path.read_text(encoding="utf-8")):
        tmp_cases = cases_path.with_suffix(cases_path.suffix + ".resolved.tmp")
        tmp_cases.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
    try:
        result = run(tmp_cases)
    finally:
        if tmp_cases != cases_path and tmp_cases.exists():
            tmp_cases.unlink()

    rendered = _render_markdown(result) if args.format == "markdown" else json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


def _render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# OpenDoge Batch Results",
        "",
        f"- Cases: {result['case_count']}",
        f"- Passed: {result['passed']}",
        "",
        "## Metrics",
        "",
    ]
    for key, value in sorted(result["metrics"].items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Cases", ""])
    for item in result["results"]:
        status = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- `{item['id']}`: {status} ({item['status']})")
    return "\n".join(lines)
