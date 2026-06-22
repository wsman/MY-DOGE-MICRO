from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_plan_closure_gate import GATES


RUNBOOK = ROOT / "docs" / "progress" / "9b77f9c-external-closure-runbook.md"


def validate(text: str) -> list[str]:
    errors: list[str] = []
    path_text = text.replace("\\", "/")
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

    for gate in GATES:
        fallback = _rel(gate.path)
        validator_script = _validator_script(gate.strict_command)
        row = _gate_row(path_text, gate.gate_id)
        if gate.gate_id not in text:
            errors.append(f"runbook missing gate id: {gate.gate_id}")
        if not row:
            errors.append(f"{gate.gate_id}: runbook missing remaining-gates table row")
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

    return errors


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _validator_script(command: str) -> str:
    for part in command.split():
        if part.startswith("scripts\\") or part.startswith("scripts/"):
            return part.replace("\\", "/")
    return command


def _gate_row(text: str, gate_id: str) -> str:
    for line in text.splitlines():
        if f"| {gate_id} |" in line:
            return line
    return ""


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
