from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_plan_closure_gate import GATES, validate_all


RUNBOOK = ROOT / "docs" / "progress" / "9b77f9c-external-closure-runbook.md"


def validate(text: str) -> list[str]:
    errors: list[str] = []
    path_text = text.replace("\\", "/")
    gate_output = validate_all(allow_open=True)
    gate_results = {
        item["id"]: item
        for item in gate_output.get("gates", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    passed_gate_ids = {
        gate_id
        for gate_id, item in gate_results.items()
        if item.get("status") == "passed"
    }
    expected_remaining_ids = [
        gate.gate_id
        for gate in GATES
        if gate.gate_id not in passed_gate_ids
    ]
    required_global = [
        "C:\\Users\\Aby\\.claude\\plans\\9b77f9c-kimi-twinkly-map.md",
        "validate_plan_closure_gate.py --allow-open",
        "validate_plan_closure_gate.py",
        "export_plan_closure_manifest.py",
        "validate_plan_closure_manifest.py",
        "build_analyst_benchmark_evidence.py",
        "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json",
        "stale handoff files",
        "strict gate exits 0",
        "production_ready: false",
        "stable_declaration: forbidden",
    ]
    for snippet in required_global:
        if snippet not in text:
            errors.append(f"runbook missing global snippet: {snippet}")

    rows = _remaining_gate_rows(path_text)
    missing_rows = [gate_id for gate_id in expected_remaining_ids if gate_id not in rows]
    extra_rows = sorted(set(rows) - set(expected_remaining_ids))
    for gate_id in missing_rows:
        errors.append(f"{gate_id}: runbook missing remaining-gates table row")
    for gate_id in extra_rows:
        errors.append(f"{gate_id}: runbook has unexpected remaining-gates table row")

    for gate in GATES:
        if gate.gate_id not in text:
            errors.append(f"runbook missing gate id: {gate.gate_id}")

    for gate in GATES:
        if gate.gate_id not in expected_remaining_ids:
            continue
        fallback = _rel(gate.path)
        validator_script = _validator_script(gate.strict_command)
        row = rows.get(gate.gate_id, "")
        if not row:
            continue
        for passing_result in gate.passing_results:
            if f"`{passing_result}`" not in row:
                errors.append(f"{gate.gate_id}: runbook missing required result {passing_result}")
        if fallback not in row:
            errors.append(f"{gate.gate_id}: runbook missing fallback evidence {fallback}")
        if validator_script not in row:
            errors.append(f"{gate.gate_id}: runbook missing validator {validator_script}")
        if gate.completed_glob:
            completed_pattern = _rel(gate.path.parent / gate.completed_glob)
            if completed_pattern not in row:
                errors.append(f"{gate.gate_id}: runbook missing completed pattern {completed_pattern}")
        elif "Same file from live run" not in row:
            errors.append(f"{gate.gate_id}: runbook missing same-file live evidence note")

    for gate_id in sorted(passed_gate_ids):
        evidence = gate_results.get(gate_id, {}).get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            errors.append(f"{gate_id}: passed gate missing completed evidence path")
            continue
        normalized_evidence = evidence.replace("\\", "/")
        if normalized_evidence not in path_text:
            errors.append(f"{gate_id}: runbook missing completed evidence {normalized_evidence}")

    return errors


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _validator_script(command: str) -> str:
    for part in command.split():
        if part.startswith("scripts\\") or part.startswith("scripts/"):
            return part.replace("\\", "/")
    return command


def _remaining_gate_rows(text: str) -> dict[str, str]:
    section = _section(text, "## Remaining Gates")
    rows: dict[str, str] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or cells[0] in {"ID", "---"} or set(cells[0]) <= {"-"}:
            continue
        rows[cells[0]] = stripped
    return rows


def _section(text: str, heading: str) -> str:
    if heading not in text:
        return ""
    after_heading = text.split(heading, 1)[1]
    next_heading = after_heading.find("\n## ")
    if next_heading == -1:
        return after_heading
    return after_heading[:next_heading]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate that the 9b77f9c external closure runbook matches the gate manifest.")
    parser.add_argument("runbook", nargs="?", default=str(RUNBOOK), help="Runbook markdown path.")
    args = parser.parse_args(argv)

    path = Path(args.runbook)
    errors = validate(path.read_text(encoding="utf-8"))
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"{path}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
