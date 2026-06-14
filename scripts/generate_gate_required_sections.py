#!/usr/bin/env python3
"""Generate gate required-artifact sections from workflow-catalog.yaml."""

from __future__ import annotations

import argparse
from pathlib import Path

from generate_phase_checklists import CATALOG, REPO_ROOT, Phase, Step, evidence_text, parse_catalog


OUTPUT = REPO_ROOT / "workflow" / "generated" / "gate-required-artifacts.md"
MEMORY_BANK_OUTPUT = REPO_ROOT / "memory_bank" / "t2_execution" / "gate_required_artifacts.md"

TARGET_LABELS = {
    "concept": {"game": "Systems Design", "product": "Specification"},
    "systems-design": {"game": "Technical Setup", "product": "Architecture"},
    "technical-setup": {"game": "Pre-Production", "product": "Pre-Implementation"},
    "pre-production": {"game": "Production", "product": "Implementation"},
    "production": {"game": "Polish", "product": "Verification"},
    "polish": {"game": "Release", "product": "Release"},
}

SOURCE_LABELS = {
    "concept": {"game": "Concept", "product": "Concept"},
    "systems-design": {"game": "Systems Design", "product": "Specification"},
    "technical-setup": {"game": "Technical Setup", "product": "Architecture"},
    "pre-production": {"game": "Pre-Production", "product": "Pre-Implementation"},
    "production": {"game": "Production", "product": "Implementation"},
    "polish": {"game": "Polish", "product": "Verification"},
}

DOMAIN_LABELS = {
    "game": "Game",
    "product": "Product",
}


def applies_to_domain(step: Step, domain: str) -> bool:
    if not step.applies_to:
        return True
    return domain in step.applies_to.strip("[]").replace(" ", "").split(",")


def command_text(step: Step) -> str:
    return f"`{step.command}`" if step.command else "Manual / template"


def render_step(step: Step) -> str:
    suffix = f" Conditional: {step.required_when}" if step.required_when else ""
    evidence = evidence_text(step).rstrip(".")
    return f"- [ ] **{step.name}** ({command_text(step)}): {evidence}.{suffix}".rstrip()


def render_domain_section(phase: Phase, domain: str) -> list[str]:
    required_steps = [
        step for step in phase.steps if step.required and applies_to_domain(step, domain)
    ]
    if not required_steps:
        return []

    source = SOURCE_LABELS[phase.key][domain]
    target = TARGET_LABELS[phase.key][domain]
    lines = [
        f"### {DOMAIN_LABELS[domain]}: {source} -> {target}",
        "",
    ]
    lines.extend(render_step(step) for step in required_steps)
    lines.append("")
    return lines


def render(phases: list[Phase]) -> str:
    lines = [
        "# Gate Required Artifacts",
        "",
        "> Generated from `workflow/workflow-catalog.yaml` by `scripts/generate_gate_required_sections.py`.",
        "> Do not hand-maintain gate required artifacts in `/gate-check`; update the catalog, then regenerate this file.",
        "",
        "Use the section matching the active gate and detected project domain.",
        "`/gate-check` may add hand-authored Quality / Risk Checks, but normal-progression blockers come from this generated file.",
        "",
    ]

    for phase in phases:
        if phase.key not in TARGET_LABELS:
            continue
        lines.extend(
            [
                f"## Gate: {phase.label}",
                "",
            ]
        )
        for domain in ["game", "product"]:
            lines.extend(render_domain_section(phase, domain))

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help=f"Write {OUTPUT.relative_to(REPO_ROOT)}")
    parser.add_argument(
        "--memory-bank",
        action="store_true",
        help="When used with --write, also write memory_bank/t2_execution/gate_required_artifacts.md if that directory exists.",
    )
    args = parser.parse_args()

    content = render(parse_catalog(CATALOG))
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(content, encoding="utf-8")
        if args.memory_bank:
            if MEMORY_BANK_OUTPUT.parent.exists():
                MEMORY_BANK_OUTPUT.write_text(
                    memory_bank_render(content, "workflow/generated/gate-required-artifacts.md"),
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
        "# Gate Required Artifacts",
        "",
        f"> Governance memory mirror generated from `{source}`.",
        "> Do not edit by hand; update `workflow/workflow-catalog.yaml` and regenerate.",
        "",
    ]
    body = content.split("\n", 1)[1] if "\n" in content else content
    return "\n".join(header) + body


if __name__ == "__main__":
    raise SystemExit(main())
