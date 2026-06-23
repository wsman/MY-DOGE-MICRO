from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_alpha_remote_ci_success import (
    success_run_urls,
    validate as validate_remote_ci_success,
)


PLAN = Path(r"C:\Users\Aby\.claude\plans\alpha-magical-peach.md")
MATURITY = ROOT / "docs" / "progress" / "runtime-maturity.yaml"


def apply_updates(
    *,
    remote_ci_payload: dict[str, Any],
    evidence_path: str | Path,
    expected_head_sha: str,
    plan_text: str,
    maturity_text: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    errors = validate_remote_ci_success(
        remote_ci_payload,
        expected_head_sha=expected_head_sha,
        evidence_path=evidence_path,
        require_canonical_path=True,
        root=root,
    )
    if errors:
        return {"passed": False, "errors": errors}

    success_urls = success_run_urls(remote_ci_payload)
    if not success_urls:
        return {"passed": False, "errors": ["remote CI success run URL is required"]}

    short_sha = expected_head_sha[:7]
    evidence_ref = _canonical_evidence_ref(evidence_path)
    run_url = success_urls[0]
    plan_result = _update_plan_text(
        plan_text,
        head_sha=expected_head_sha,
        short_sha=short_sha,
        run_url=run_url,
        evidence_ref=evidence_ref,
    )
    maturity_result = _update_maturity_text(
        maturity_text,
        head_sha=expected_head_sha,
        evidence_ref=evidence_ref,
        run_url=run_url,
    )
    errors.extend(plan_result["errors"])
    errors.extend(maturity_result["errors"])

    return {
        "passed": not errors,
        "errors": errors,
        "plan_text": plan_result["text"],
        "maturity_text": maturity_result["text"],
        "head_sha": expected_head_sha,
        "short_sha": short_sha,
        "run_url": run_url,
        "evidence_ref": evidence_ref,
    }


def _update_plan_text(
    text: str,
    *,
    head_sha: str,
    short_sha: str,
    run_url: str,
    evidence_ref: str,
) -> dict[str, Any]:
    errors: list[str] = []
    replacements = [
        (
            r"^- \[[ x]\] Target HEAD is recorded:.*$",
            f"- [x] Target HEAD is recorded: `{short_sha}` / `{head_sha}`.",
            "target HEAD checklist item",
        ),
        (
            r"^- \[[ x]\] Remote CI success is linked for the repaired target SHA.*$",
            (
                "- [x] Remote CI success is linked for the repaired target SHA: "
                f"`{run_url}` with `{evidence_ref}`."
            ),
            "repaired target SHA remote CI checklist item",
        ),
        (
            r"^- \[[ x]\] Remote CI success is linked for the target HEAD.*$",
            (
                "- [x] Remote CI success is linked for the target HEAD: "
                f"`{run_url}` and `{evidence_ref}`."
            ),
            "target HEAD remote CI checklist item",
        ),
    ]
    updated = text
    for pattern, replacement, label in replacements:
        updated, count = re.subn(pattern, replacement, updated, count=1, flags=re.M)
        if count != 1:
            errors.append(f"could not update {label}")
    return {"text": updated, "errors": errors}


def _update_maturity_text(
    text: str,
    *,
    head_sha: str,
    evidence_ref: str,
    run_url: str,
) -> dict[str, Any]:
    block = (
        "alpha_magical_peach_final_closure:\n"
        "  result: passed\n"
        f"  head_sha: {head_sha}\n"
        f"  evidence: {evidence_ref}\n"
        f"  run_url: {run_url}\n"
    )
    pattern = r"(?ms)^alpha_magical_peach_final_closure:\n(?:  .*\n)*"
    if re.search(pattern, text):
        updated = re.sub(pattern, block, text, count=1)
    else:
        updated = text.rstrip() + "\n\n" + block
    return {"text": updated, "errors": []}


def _canonical_evidence_ref(evidence_path: str | Path) -> str:
    return (Path("production/qa/evidence/ci") / Path(evidence_path).name).as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply passed exact-SHA remote CI evidence to the Alpha Magical Peach plan and maturity record."
    )
    parser.add_argument("--remote-ci-evidence", required=True, type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--plan", default=str(PLAN))
    parser.add_argument("--maturity", default=str(MATURITY))
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root for canonical evidence path validation.")
    parser.add_argument("--write", action="store_true", help="Write updated plan and maturity files.")
    args = parser.parse_args(argv)

    evidence = json.loads(args.remote_ci_evidence.read_text(encoding="utf-8"))
    plan_path = Path(args.plan)
    maturity_path = Path(args.maturity)
    result = apply_updates(
        remote_ci_payload=evidence,
        evidence_path=args.remote_ci_evidence,
        expected_head_sha=args.expected_head,
        plan_text=plan_path.read_text(encoding="utf-8"),
        maturity_text=maturity_path.read_text(encoding="utf-8"),
        root=args.root,
    )
    if result["passed"] and args.write:
        plan_path.write_text(result["plan_text"], encoding="utf-8")
        maturity_path.write_text(result["maturity_text"], encoding="utf-8")

    printable = {
        key: value
        for key, value in result.items()
        if key not in {"plan_text", "maturity_text"}
    }
    printable["written"] = bool(result["passed"] and args.write)
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
