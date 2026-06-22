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


AUDIT = ROOT / "docs" / "progress" / "kimi-plan-completion-audit.md"


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
    open_count = summary.get("open")

    required_global = [
        "C:\\Users\\Aby\\.claude\\plans\\9b77f9c-kimi-twinkly-map.md",
        "not yet provably complete",
        "`production_ready` must remain `false`",
        "`stable_declaration` must remain",
        "scripts/validate_plan_closure_gate.py --allow-open",
        "strict mode",
        "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json",
    ]
    for snippet in required_global:
        if snippet not in text and snippet not in normalized_text:
            errors.append(f"audit missing global snippet: {snippet}")
    if not _has_controlled_open_count(text, normalized_text, open_count):
        errors.append(f"audit missing controlled open gate count: {open_count}")

    expected_total = len(GATES)
    if summary["total"] != expected_total:
        errors.append(f"closure gate must report exactly {expected_total} total gates")
    if not gate_output["acceptable"]:
        errors.append("closure gate must be acceptable under --allow-open")

    rows = _remaining_external_rows(path_text)
    gate_by_id = {gate.gate_id: gate for gate in GATES}
    missing_rows = [gate_id for gate_id in expected_remaining_ids if gate_id not in rows]
    extra_rows = sorted(set(rows) - set(expected_remaining_ids))
    for gate_id in missing_rows:
        errors.append(f"audit missing remaining external item row: {gate_id}")
    for gate_id in extra_rows:
        errors.append(f"audit has unexpected remaining external item row: {gate_id}")

    for gate_id in expected_remaining_ids:
        row = rows.get(gate_id, "")
        if not row:
            continue
        gate = gate_by_id[gate_id]
        fallback = _rel(gate.path)
        validator_script = _validator_script(gate.strict_command)
        if gate.title not in row:
            errors.append(f"{gate_id}: audit row missing gate title '{gate.title}'")
        for passing_result in gate.passing_results:
            if f"`{passing_result}`" not in row:
                errors.append(f"{gate_id}: audit row missing required result {passing_result}")
        if fallback not in row:
            errors.append(f"{gate_id}: audit row missing fallback evidence {fallback}")
        if validator_script not in row:
            errors.append(f"{gate_id}: audit row missing validator {validator_script}")
        if gate.completed_glob:
            completed_pattern = _rel(gate.path.parent / gate.completed_glob)
            if completed_pattern not in row:
                errors.append(f"{gate_id}: audit row missing completed pattern {completed_pattern}")
        elif "same evidence file" not in row:
            errors.append(f"{gate_id}: audit row missing same evidence file live-run note")

    for gate_id in sorted(passed_gate_ids):
        evidence = gate_results.get(gate_id, {}).get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            errors.append(f"{gate_id}: passed gate missing completed evidence path")
            continue
        normalized_evidence = evidence.replace("\\", "/")
        if normalized_evidence not in path_text:
            errors.append(f"{gate_id}: audit missing completed evidence {normalized_evidence}")

    return errors


def _has_controlled_open_count(text: str, normalized_text: str, count: Any) -> bool:
    if not isinstance(count, int):
        return False
    snippets = [
        f"{count} controlled open gate",
        f"{count} controlled open gates",
    ]
    return any(snippet in text or snippet in normalized_text for snippet in snippets)


def _remaining_external_rows(text: str) -> dict[str, str]:
    section = _section(text, "## Remaining External Items")
    rows: dict[str, str] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or cells[0] in {"ID", "---"} or set(cells[0]) <= {"-"}:
            continue
        if len(cells) < 4:
            rows[cells[0]] = stripped
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


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _validator_script(command: str) -> str:
    for part in command.split():
        if part.startswith("scripts\\") or part.startswith("scripts/"):
            return part.replace("\\", "/")
    return command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate that the Kimi plan completion audit matches the 9b77f9c closure gate."
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
