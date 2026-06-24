from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_plan_closure_gate import GATES, validate_all


AUDIT = ROOT / "docs" / "progress" / "my-doge-micro-main-2ffdb66-piped-donut-completion-audit.md"
SOURCE_PLAN = r"C:\Users\Aby\.claude\plans\my-doge-micro-main-2ffdb66-piped-donut.md"


def validate(text: str) -> list[str]:
    errors: list[str] = []
    path_text = text.replace("\\", "/")
    normalized_text = " ".join(text.split())
    gate_output = validate_all(allow_open=True)
    summary = gate_output["summary"]
    gate_results = {
        item["id"]: item
        for item in gate_output.get("gates", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    remaining_gate_ids = [
        gate.gate_id
        for gate in GATES
        if gate_results.get(gate.gate_id, {}).get("status") != "passed"
    ]
    passed_gate_ids = [
        gate.gate_id
        for gate in GATES
        if gate_results.get(gate.gate_id, {}).get("status") == "passed"
    ]

    required_global = [
        SOURCE_PLAN,
        "Workstreams A, B, and C are locally implemented and verified",
        "Workstream D is not complete",
        "`production_ready` remains `false`",
        "`stable_declaration` remains `forbidden`",
        "Alpha / controlled PoC",
        "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json",
        "production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/",
        "not remote CI evidence for the current uncommitted local implementation",
        "docs/archive/audits/piped-donut-pre-remote-ci-package-2026-06-24.md",
        "scripts/validate_piped_donut_pre_remote_ci_package.py",
        "scripts\\validate_plan_closure_gate.py` exits 0 without `--allow-open`",
    ]
    for snippet in required_global:
        if snippet not in text and snippet not in normalized_text:
            errors.append(f"audit missing global snippet: {snippet}")

    if not _has_gate_count(text, normalized_text, summary.get("open"), summary.get("passed")):
        errors.append(
            "audit missing current closure gate summary: "
            f"{summary.get('open')} open / {summary.get('passed')} passed"
        )
    if not gate_output.get("acceptable"):
        errors.append("closure gate must be acceptable under --allow-open")

    matrix_rows = _table_rows(_section(path_text, "## Requirement Matrix"))
    expected_matrix = {
        "P0-01 legacy API boundary",
        "P0-02 identity snapshot boundary",
        "P0-03 runtime transaction and outbox",
        "P0-04 event append semantics",
        "P0-05 SQLite-backed SSE subscriber",
        "P0-06 worker queue leases",
        "P0-07 Python analysis executor boundary",
        "B-01 split composition root",
        "B-02 split workspace service",
        "B-03 unified tool descriptor",
        "B-04 run execution context",
        "C-01 context migrations",
        "C-02 tenant constraints",
        "C-03 CLI gateway SDK path",
        "C-04 SDK contract drift gate",
        "D-01 exact-SHA CI evidence",
        "D-02 real provider and enterprise validation",
        "D-03 production gate criteria",
    }
    missing_matrix = sorted(expected_matrix - set(matrix_rows))
    for row_name in missing_matrix:
        errors.append(f"audit missing requirement matrix row: {row_name}")
    for row_name in sorted(item for item in expected_matrix if not item.startswith("D-")):
        if "Locally complete" not in matrix_rows.get(row_name, ""):
            errors.append(f"{row_name}: row must state local completion")
    if "Blocked on remote CI" not in matrix_rows.get("D-01 exact-SHA CI evidence", ""):
        errors.append("D-01 row must remain blocked on remote CI")
    if "Open pending real operator evidence" not in matrix_rows.get("D-02 real provider and enterprise validation", ""):
        errors.append("D-02 row must remain open pending real operator evidence")
    if "Open pending strict external closure" not in matrix_rows.get("D-03 production gate criteria", ""):
        errors.append("D-03 row must remain open pending strict external closure")

    remaining_rows = _table_rows(_section(path_text, "## Remaining External Gates"))
    missing_remaining = [gate_id for gate_id in remaining_gate_ids if gate_id not in remaining_rows]
    extra_remaining = sorted(set(remaining_rows) - set(remaining_gate_ids))
    for gate_id in missing_remaining:
        errors.append(f"audit missing remaining external gate row: {gate_id}")
    for gate_id in extra_remaining:
        errors.append(f"audit has unexpected remaining external gate row: {gate_id}")

    gate_by_id = {gate.gate_id: gate for gate in GATES}
    for gate_id in remaining_gate_ids:
        row = remaining_rows.get(gate_id, "")
        if not row:
            continue
        gate = gate_by_id[gate_id]
        for passing_result in gate.passing_results:
            if f"`{passing_result}`" not in row:
                errors.append(f"{gate_id}: row missing required result {passing_result}")
        fallback = _rel(gate.path)
        if fallback not in row:
            errors.append(f"{gate_id}: row missing current evidence {fallback}")
        validator = _validator_script(gate.strict_command)
        if validator not in path_text:
            errors.append(f"{gate_id}: audit missing close validator {validator}")

    for gate_id in passed_gate_ids:
        evidence = gate_results.get(gate_id, {}).get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            errors.append(f"{gate_id}: passed gate missing evidence path in closure gate output")
            continue
        if evidence.replace("\\", "/") not in path_text:
            errors.append(f"{gate_id}: audit missing passed evidence {evidence}")

    verified_section = _section(path_text, "## Verified Commands")
    for command in [
        ".venv\\Scripts\\python.exe -m pytest -q",
        ".venv\\Scripts\\python.exe tools\\ci\\sdk-contract-check.py",
        ".venv\\Scripts\\python.exe scripts\\validate_piped_donut_pre_remote_ci_package.py",
        "scripts\\validate_plan_closure_gate.py --allow-open",
        "scripts\\preflight_plan_closure_external.py",
        "1431 passed, 9 skipped, 11 warnings",
        "infrastructure_ready=true",
        "result=pending_external_inputs",
    ]:
        if command.replace("\\", "/") not in verified_section:
            errors.append(f"audit missing verified command: {command}")

    return errors


def _has_gate_count(text: str, normalized_text: str, open_count: Any, passed_count: Any) -> bool:
    if not isinstance(open_count, int) or not isinstance(passed_count, int):
        return False
    snippet = f"{open_count} open / {passed_count} passed"
    return snippet in text or snippet in normalized_text


def _section(text: str, heading: str) -> str:
    if heading not in text:
        return ""
    after_heading = text.split(heading, 1)[1]
    next_heading = after_heading.find("\n## ")
    if next_heading == -1:
        return after_heading
    return after_heading[:next_heading]


def _table_rows(section: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or cells[0] in {"Area", "Gate", "---"} or set(cells[0]) <= {"-"}:
            continue
        rows[cells[0]] = stripped
    return rows


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _validator_script(command: str) -> str:
    for part in command.split():
        if part.startswith("scripts\\") or part.startswith("scripts/"):
            return part.replace("\\", "/")
    return command.replace("\\", "/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the 2ffdb66 piped-donut remediation plan completion audit against current gates."
    )
    parser.add_argument("audit", nargs="?", default=str(AUDIT), help="Completion audit markdown path.")
    args = parser.parse_args(argv)

    path = Path(args.audit)
    errors = validate(path.read_text(encoding="utf-8"))
    result = {"path": str(path), "passed": not errors, "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
