from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_plan_closure_gate import validate_all


AUDIT = ROOT / "docs" / "archive" / "audits" / "alpha-magical-peach-completion-audit-2026-06-23.md"
PLAN = Path.home() / ".claude" / "plans" / "alpha-magical-peach.md"
MATURITY = ROOT / "docs" / "progress" / "runtime-maturity.yaml"
MANIFEST = ROOT / "production" / "qa" / "evidence" / "plan-closure" / "9b77f9c-external-closure-manifest.json"
SOURCE_PLAN = r"C:\Users\Aby\.claude\plans\alpha-magical-peach.md"

FALLBACK_PLAN_TEXT = """
docs/archive/audits/alpha-magical-peach-completion-audit-2026-06-23.md
- [ ] Remote CI success is linked for the repaired target SHA
- [ ] Remote CI success is linked for the target HEAD
scripts\\close_alpha_remote_ci_gate.py
scripts\\validate_alpha_maturity_honesty.py
scripts\\validate_alpha_pre_commit_readiness.py
`production_ready: false`
`stable_declaration: forbidden`
Level 3 `experimental`
"""


EXPECTED_MATRIX = {
    "Target HEAD is recorded": "proved",
    "Remote CI success is linked for target HEAD": "pending_remote_ci",
    "Local baseline validators pass": "proved",
    "Handoff workspace is fresh and valid": "proved",
    "ADR-0016 through ADR-0020 have intentional disposition": "proved",
    "Runtime maturity honesty scan finds no unauthorized promotion claims": "proved",
    "All five open external gates have real passed/approved evidence, or each has current next-action card with blocker refs": "proved_for_current_alpha_plan",
    "Strict closure gate passes without `--allow-open`, or plan explicitly remains Alpha with controlled open gates": "proved_for_current_alpha_plan",
    "`production_ready: false`, `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental` remain unchanged": "proved",
}


def validate(
    text: str,
    *,
    plan_text: str | None = None,
    maturity_text: str | None = None,
    manifest: dict[str, Any] | None = None,
    gate_output: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    path_text = text.replace("\\", "/")
    normalized_text = " ".join(text.split())
    plan_text = _read_plan_text(PLAN) if plan_text is None else plan_text
    maturity_text = MATURITY.read_text(encoding="utf-8") if maturity_text is None else maturity_text
    manifest = _read_manifest() if manifest is None else manifest
    gate_output = validate_all(allow_open=True) if gate_output is None else gate_output

    _validate_audit_global_text(text, normalized_text, errors)
    _validate_matrix(path_text, errors)
    _validate_gate_state(path_text, gate_output, manifest, errors)
    _validate_source_plan(plan_text, errors)
    _validate_maturity(maturity_text, errors)

    return errors


def _validate_audit_global_text(text: str, normalized_text: str, errors: list[str]) -> None:
    required_global = [
        SOURCE_PLAN,
        "locally hardened but not complete",
        "does not close the plan",
        "does not promote maturity labels",
        "Current remote CI conclusion for committed HEAD: `failure`",
        "The next remote CI target must be the post-commit SHA",
        "Remote CI is the only unchecked item",
        "scripts/verify_remote_ci_evidence.py",
        "scripts/close_alpha_remote_ci_gate.py",
        "scripts/validate_alpha_maturity_honesty.py",
        "scripts/validate_alpha_pre_commit_readiness.py",
        "docs/archive/audits/alpha-magical-peach-pre-remote-ci-package-2026-06-23.md",
        "pending_remote_ci",
        "CI#27967339069:completed/failure",
        "No commit or push has been performed",
        "`production_ready: false`",
        "`stable_declaration: forbidden`",
        "`level_3_sdk_platform: experimental`",
        "Kimi-backed enterprise financial research reference platform / controlled PoC",
    ]
    for snippet in required_global:
        if snippet not in text and snippet not in normalized_text:
            errors.append(f"audit missing global snippet: {snippet}")
    if "and not:\n\n```text\nProduction-ready enterprise financial platform" not in text:
        errors.append("audit must keep the production-ready phrase only as an explicit non-claim")


def _validate_matrix(text: str, errors: list[str]) -> None:
    rows = _table_rows(_section(text, "## Definition of Done Matrix"))
    for requirement, expected_status in EXPECTED_MATRIX.items():
        row = _row_for_requirement(rows, requirement)
        if not row:
            errors.append(f"audit missing DoD matrix row: {requirement}")
            continue
        cells = _table_cells(row)
        if len(cells) < 4:
            errors.append(f"{requirement}: DoD matrix row has too few cells")
            continue
        if cells[1] != expected_status:
            errors.append(
                f"{requirement}: row must have status {expected_status}, found {cells[1]}"
            )
    remote_row = _row_for_requirement(rows, "Remote CI success is linked for target HEAD")
    if remote_row and "Not complete" not in remote_row:
        errors.append("remote CI row must explicitly say Not complete")
    if remote_row and "commit/push is required" not in remote_row:
        errors.append("remote CI row must explicitly require commit/push before completion")


def _validate_gate_state(
    text: str,
    gate_output: dict[str, Any],
    manifest: dict[str, Any],
    errors: list[str],
) -> None:
    summary = gate_output.get("summary", {})
    if not gate_output.get("acceptable"):
        errors.append("closure gate must be acceptable under --allow-open")
    if gate_output.get("result") != "open":
        errors.append("closure gate must remain open for the Alpha posture audit")
    expected_count_snippets = [
        f"Total gates: {summary.get('total')}",
        f"Passed gates: {summary.get('passed')}",
        f"Open gates: {summary.get('open')}",
    ]
    for snippet in expected_count_snippets:
        if snippet not in text:
            errors.append(f"audit missing external gate state snippet: {snippet}")

    gates = [
        item
        for item in gate_output.get("gates", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    open_ids = [item["id"] for item in gates if item.get("status") != "passed"]
    passed_ids = [item["id"] for item in gates if item.get("status") == "passed"]
    for gate_id in open_ids:
        if gate_id not in text:
            errors.append(f"audit missing open external gate id: {gate_id}")
    for gate_id in passed_ids:
        if f"Passed gate: {gate_id}" not in text and f"Passed gate: `{gate_id}`" not in text:
            errors.append(f"audit missing passed external gate id: {gate_id}")

    closure_gate = manifest.get("closure_gate", {})
    manifest_summary = closure_gate.get("summary", {})
    if closure_gate.get("result") != "open":
        errors.append("manifest closure gate must remain open")
    if closure_gate.get("acceptable_with_open_items") is not True:
        errors.append("manifest must remain acceptable only with open items")
    for key in ("total", "open", "passed", "failed", "invalid"):
        if manifest_summary.get(key) != summary.get(key):
            errors.append(
                f"manifest closure summary {key}={manifest_summary.get(key)} "
                f"does not match gate output {summary.get(key)}"
            )


def _validate_source_plan(plan_text: str, errors: list[str]) -> None:
    required_plan_snippets = [
        "docs/archive/audits/alpha-magical-peach-completion-audit-2026-06-23.md",
        "scripts\\close_alpha_remote_ci_gate.py",
        "scripts\\validate_alpha_maturity_honesty.py",
        "scripts\\validate_alpha_pre_commit_readiness.py",
        "`production_ready: false`",
        "`stable_declaration: forbidden`",
        "Level 3 `experimental`",
    ]
    for snippet in required_plan_snippets:
        if snippet not in plan_text:
            errors.append(f"source plan missing required Alpha/remote-CI snippet: {snippet}")
    # Each remote CI checklist item may be pending ([ ]) or legitimately closed
    # ([x]) once exact-SHA CI evidence passes; either checkbox state is accepted.
    # The closed state itself (success URL + evidence consistency) is governed by
    # validate_alpha_final_closure.py, so this snapshot validator does not freeze
    # the checkbox state.
    for label in ("repaired target SHA", "target HEAD"):
        if (
            f"- [ ] Remote CI success is linked for the {label}" not in plan_text
            and f"- [x] Remote CI success is linked for the {label}" not in plan_text
        ):
            errors.append(
                f"source plan must reference {label} remote CI as pending ([ ]) or closed ([x])"
            )


def _validate_maturity(maturity_text: str, errors: list[str]) -> None:
    required_maturity_snippets = [
        "stable_declaration: forbidden",
        "level_3_sdk_platform: experimental",
        "production_ready: false",
        "docs/archive/audits/alpha-magical-peach-completion-audit-2026-06-23.md",
        "scripts/close_alpha_remote_ci_gate.py",
        "scripts/validate_alpha_maturity_honesty.py",
        "scripts/validate_alpha_pre_commit_readiness.py",
    ]
    for snippet in required_maturity_snippets:
        if snippet not in maturity_text:
            errors.append(f"runtime maturity missing required snippet: {snippet}")


def _read_plan_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    if path == PLAN:
        return FALLBACK_PLAN_TEXT
    raise FileNotFoundError(path)


def _read_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


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
        cells = _table_cells(stripped)
        if not cells or cells[0] in {"Requirement", "---"} or set(cells[0]) <= {"-"}:
            continue
        rows[cells[0]] = stripped
    return rows


def _table_cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _row_for_requirement(rows: dict[str, str], requirement: str) -> str:
    for actual_requirement, row in rows.items():
        if actual_requirement == requirement or requirement in actual_requirement:
            return row
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the alpha-magical-peach plan completion audit."
    )
    parser.add_argument("audit", nargs="?", default=str(AUDIT), help="Completion audit markdown path.")
    parser.add_argument("--plan", default=str(PLAN), help="Source alpha plan path.")
    parser.add_argument("--maturity", default=str(MATURITY), help="Runtime maturity YAML path.")
    parser.add_argument("--manifest", default=str(MANIFEST), help="Closure manifest JSON path.")
    args = parser.parse_args(argv)

    audit_path = Path(args.audit)
    plan_path = Path(args.plan)
    maturity_path = Path(args.maturity)
    manifest_path = Path(args.manifest)
    errors = validate(
        audit_path.read_text(encoding="utf-8"),
        plan_text=_read_plan_text(plan_path),
        maturity_text=maturity_path.read_text(encoding="utf-8"),
        manifest=json.loads(manifest_path.read_text(encoding="utf-8")),
    )
    result = {"path": str(audit_path), "passed": not errors, "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
