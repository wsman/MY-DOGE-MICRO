#!/usr/bin/env python3
"""Generate phase artifact checklists from workflow-catalog.yaml."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "workflow" / "workflow-catalog.yaml"
OUTPUT = REPO_ROOT / "docs" / "PHASE-CHECKLISTS.md"
MEMORY_BANK_OUTPUT = REPO_ROOT / "memory_bank" / "t2_execution" / "phase_checklists.md"


@dataclass
class Step:
    name: str = ""
    command: str = ""
    required: bool = False
    required_when: str = ""
    applies_to: str = ""
    glob: str = ""
    min_count: str = ""
    note: str = ""


@dataclass
class Phase:
    key: str
    label: str = ""
    steps: list[Step] = field(default_factory=list)


def parse_catalog(path: Path) -> list[Phase]:
    phases: list[Phase] = []
    current_phase: Phase | None = None
    current_step: Step | None = None
    in_phases = False
    in_steps = False
    in_artifact = False

    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip(" "))

        if stripped == "phases:":
            in_phases = True
            continue
        if not in_phases:
            continue
        if indent == 0 and stripped and stripped != "phases:":
            break

        if indent == 2 and stripped.endswith(":"):
            if current_step and current_phase:
                current_phase.steps.append(current_step)
            current_step = None
            current_phase = Phase(key=stripped[:-1])
            phases.append(current_phase)
            in_steps = False
            in_artifact = False
            continue

        if current_phase is None:
            continue

        if indent == 4 and stripped.startswith("label:"):
            current_phase.label = stripped.split(":", 1)[1].strip().strip('"')
            continue
        if indent == 4 and stripped == "steps:":
            in_steps = True
            continue
        if not in_steps:
            continue

        if indent == 6 and stripped.startswith("- id:"):
            if current_step:
                current_phase.steps.append(current_step)
            current_step = Step()
            in_artifact = False
            continue
        if current_step is None:
            continue

        if indent == 8 and stripped.startswith("name:"):
            current_step.name = stripped.split(":", 1)[1].strip().strip('"')
        elif indent == 8 and stripped.startswith("command:"):
            current_step.command = stripped.split(":", 1)[1].strip()
        elif indent == 8 and stripped.startswith("required:"):
            current_step.required = stripped.split(":", 1)[1].strip().lower() == "true"
        elif indent == 8 and stripped.startswith("required_when:"):
            current_step.required_when = stripped.split(":", 1)[1].strip().strip('"')
        elif indent == 8 and stripped.startswith("applies_to:"):
            current_step.applies_to = stripped.split(":", 1)[1].strip()
        elif indent == 8 and stripped == "artifact:":
            in_artifact = True
        elif in_artifact and indent == 10 and stripped.startswith("glob:"):
            current_step.glob = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        elif in_artifact and indent == 10 and stripped.startswith("min_count:"):
            current_step.min_count = stripped.split(":", 1)[1].strip()
        elif in_artifact and indent == 10 and stripped.startswith("note:"):
            current_step.note = stripped.split(":", 1)[1].strip().strip('"')
        elif indent <= 8 and stripped and not stripped.startswith(("glob:", "min_count:", "note:")):
            in_artifact = False

    if current_step and current_phase:
        current_phase.steps.append(current_step)
    return phases


def evidence_text(step: Step) -> str:
    if step.glob:
        suffix = f" (minimum {step.min_count})" if step.min_count else ""
        return f"`{step.glob}`{suffix}"
    if step.note:
        return step.note
    return "Manual evidence from the command output or review record"


def render(phases: list[Phase]) -> str:
    lines: list[str] = [
        "# Phase Checklists",
        "",
        "> Generated from `workflow/workflow-catalog.yaml` by `scripts/generate_phase_checklists.py`.",
        "> Do not hand-maintain phase requirements here; update the catalog, then regenerate this file.",
        "",
        "Use this as a customer-facing view of what should exist after each phase.",
        "Domain-specific rows are marked when a step applies only to Game or Product projects.",
        "",
    ]

    for phase in phases:
        required_steps = [step for step in phase.steps if step.required]
        if not required_steps:
            continue
        lines.extend(
            [
                f"## {phase.label or phase.key}",
                "",
                "| Required Step | Command | Evidence Generated From Catalog | Applies To |",
                "| ------------- | ------- | ------------------------------- | ---------- |",
            ]
        )
        for step in required_steps:
            applies = step.applies_to or "game, product"
            if step.required_when:
                applies = f"{applies}; conditional"
            command = f"`{step.command}`" if step.command else "Manual / template"
            lines.append(
                f"| {step.name} | {command} | {evidence_text(step)} | {applies} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help=f"Write {OUTPUT.relative_to(REPO_ROOT)}")
    parser.add_argument(
        "--memory-bank",
        action="store_true",
        help="When used with --write, also write memory_bank/t2_execution/phase_checklists.md if that directory exists.",
    )
    args = parser.parse_args()

    content = render(parse_catalog(CATALOG))
    if args.write:
        OUTPUT.write_text(content, encoding="utf-8")
        if args.memory_bank:
            if MEMORY_BANK_OUTPUT.parent.exists():
                MEMORY_BANK_OUTPUT.write_text(
                    memory_bank_render(content, "docs/PHASE-CHECKLISTS.md"),
                    encoding="utf-8",
                )
            else:
                print(
                    f"Skipping {MEMORY_BANK_OUTPUT.relative_to(REPO_ROOT)} because memory_bank/t2_execution does not exist.",
                )
    else:
        print(content, end="")
    return 0


def memory_bank_render(content: str, source: str) -> str:
    header = [
        "# Phase Checklists",
        "",
        f"> Governance memory mirror generated from `{source}`.",
        "> Do not edit by hand; update `workflow/workflow-catalog.yaml` and regenerate.",
        "",
    ]
    body = content.split("\n", 1)[1] if "\n" in content else content
    return "\n".join(header) + body


if __name__ == "__main__":
    raise SystemExit(main())
