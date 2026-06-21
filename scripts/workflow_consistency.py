#!/usr/bin/env python3
"""Consistency checks for workflow catalog, docs, gates, and skills.

The parser is intentionally lightweight and dependency-free so it can run in a
template repository without installing PyYAML.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD = REPO_ROOT / "AGENTS.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
CODEX_SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
CODEX_DIR = REPO_ROOT / ".codex"
CODEX_AGENTS_DIR = CODEX_DIR / "agents"
CODEX_HOOKS_DIR = CODEX_DIR / "hooks"
CLAUDE_HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
WORKFLOW_DIR = REPO_ROOT / "workflow"
STANDARDS_DIR = REPO_ROOT / "standards"
TEMPLATES_DIR = REPO_ROOT / "templates"
MEMORY_BANK_TEMPLATE_DIR = TEMPLATES_DIR / "memory-bank"
SKILL_TESTING_DIR = REPO_ROOT / "skill_testing"
SKILL_TESTING_T2_MOUNT = MEMORY_BANK_TEMPLATE_DIR / "t2_execution" / "skill_testing"
SKILL_TESTING_T3 = MEMORY_BANK_TEMPLATE_DIR / "t3_archive" / "skill_testing"
LEGACY_SKILL_TESTING_DIRNAME = "CDD Skill Testing" + " Framework"
CATALOG = WORKFLOW_DIR / "workflow-catalog.yaml"
GATE_CHECK = REPO_ROOT / ".claude" / "skills" / "gate-check" / "SKILL.md"
CODEX_GATE_CHECK = REPO_ROOT / ".agents" / "skills" / "gate-check" / "SKILL.md"
FLOW_DIAGRAMS = REPO_ROOT / "docs" / "examples" / "skill-flow-diagrams.md"
WORKFLOW_GUIDE = REPO_ROOT / "docs" / "WORKFLOW-GUIDE.md"
QUICK_START = REPO_ROOT / "docs" / "QUICK-START.md"
SKILLS_REFERENCE = REPO_ROOT / "docs" / "reference" / "skills-reference.md"
PHASE_CHECKLISTS = REPO_ROOT / "docs" / "PHASE-CHECKLISTS.md"
GATE_REQUIRED_ARTIFACTS = WORKFLOW_DIR / "generated" / "gate-required-artifacts.md"
CUSTOMER_ACCEPTANCE = REPO_ROOT / "docs" / "CUSTOMER-ACCEPTANCE.md"
USER_MANUAL = REPO_ROOT / "docs" / "USER-MANUAL.md"
PROJECT_ROADMAP_EXAMPLE = REPO_ROOT / "docs" / "examples" / "project-roadmap.example.md"
GENERATE_PHASE_CHECKLISTS = REPO_ROOT / "scripts" / "generate_phase_checklists.py"
GENERATE_GATE_REQUIRED = REPO_ROOT / "scripts" / "generate_gate_required_sections.py"
DOC_COMMAND_FILES = [
    REPO_ROOT / "docs" / "START-HERE.md",
    QUICK_START,
    USER_MANUAL,
]
DRIFT_SCAN_ROOTS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "UPGRADING.md",
    REPO_ROOT / "docs",
    REPO_ROOT / ".claude" / "skills",
    REPO_ROOT / ".claude" / "docs",
]
DELIVERY_SCAN_ROOTS = [
    AGENTS_MD,
    CLAUDE_MD,
    REPO_ROOT / ".agents",
    REPO_ROOT / ".codex",
    REPO_ROOT / ".github",
    REPO_ROOT / "scripts",
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs",
]

COMMAND_REF = re.compile(r"(?<![\w.:-])/[a-z][a-z0-9-]*\b")
BACKTICK_PATH = re.compile(r"`([^`\n]+)`")
PATH_HINT = re.compile(
    r"^(?:\.claude|\.github|assets|config|db|design|docs|memory_bank|migrations|production|prototypes|schema|src|tests|tools)(?:/|$)"
)

IGNORED_COMMAND_LIKE = {
    "/api",
    "/cli",
    "/config",
    "/contracts",
    "/dev",
    "/docs",
    "/schema",
    "/src",
    "/tests",
    "/tmp",
}

TEXT_SUFFIXES = {".json", ".md", ".py", ".sh", ".toml", ".txt", ".yaml", ".yml"}
REQUIRED_GATE_HEADINGS = {
    "**Required Artifacts:**",
    "**Catalog Required Artifacts:**",
    "**Catalog Required Step Evidence:**",
}


@dataclass
class Finding:
    severity: str
    message: str


@dataclass
class CatalogStep:
    step_id: str
    command: str | None = None
    required: bool = False
    globs: list[str] = field(default_factory=list)
    note: str | None = None


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def collect_known_commands() -> set[str]:
    commands: set[str] = set()
    for skill_file in SKILLS_DIR.glob("*/SKILL.md"):
        commands.add("/" + skill_file.parent.name)
    return commands


def template_exists_for(path_text: str) -> bool:
    if not TEMPLATES_DIR.exists():
        return False
    path = Path(path_text)
    name = path.name
    stem = path.stem
    return any(candidate.name == name or candidate.stem == stem for candidate in TEMPLATES_DIR.rglob("*") if candidate.is_file())


def existing_or_template(path_text: str) -> bool:
    normalized = path_text.rstrip("/").replace("\\", "/")
    if not normalized:
        return False
    if any(ch in normalized for ch in "*[]"):
        return template_exists_for(normalized)
    return (REPO_ROOT / normalized).exists() or template_exists_for(normalized)


def parse_catalog() -> list[CatalogStep]:
    steps: list[CatalogStep] = []
    current: CatalogStep | None = None
    in_artifact = False

    for raw in CATALOG.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- id:"):
            if current:
                steps.append(current)
            current = CatalogStep(step_id=line.split(":", 1)[1].strip().strip('"'))
            in_artifact = False
            continue
        if current is None:
            continue
        if line.startswith("artifact:"):
            in_artifact = True
            continue
        if re.match(r"^[a-zA-Z_-]+:", line) and not line.startswith(("glob:", "note:", "min_count:", "pattern:")):
            in_artifact = False
        if line.startswith("command:"):
            current.command = line.split(":", 1)[1].strip()
        elif line.startswith("required:"):
            current.required = line.split(":", 1)[1].strip().lower() == "true"
        elif in_artifact and line.startswith("glob:"):
            current.globs.append(line.split(":", 1)[1].strip().strip('"').strip("'"))
        elif in_artifact and line.startswith("note:"):
            current.note = line.split(":", 1)[1].strip().strip('"').strip("'")

    if current:
        steps.append(current)
    return steps


def check_catalog_commands(steps: list[CatalogStep], known_commands: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    for step in steps:
        if step.command and step.command not in known_commands:
            findings.append(Finding("ERROR", f"catalog step {step.step_id} references missing skill command {step.command}"))
    return findings


def check_doc_commands(known_commands: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in DOC_COMMAND_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"https?://\S+", "", text)
        for match in COMMAND_REF.finditer(text):
            if match.start() > 0 and text[match.start() - 1] == "<":
                continue
            command = match.group(0)
            if command in IGNORED_COMMAND_LIKE:
                continue
            if command not in known_commands:
                findings.append(Finding("ERROR", f"{rel(path)} references missing skill command {command}"))
    return findings


def check_required_catalog_artifacts(steps: list[CatalogStep], known_commands: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    for step in steps:
        if not step.required:
            continue
        if not step.globs and not step.note:
            continue
        if step.command and step.command in known_commands:
            continue
        missing = [glob for glob in step.globs if not existing_or_template(glob)]
        if missing and not step.note:
            findings.append(
                Finding(
                    "ERROR",
                    f"required catalog step {step.step_id} has artifacts without command/template trace: {', '.join(missing)}",
                )
            )
    return findings


def extract_required_gate_paths() -> set[str]:
    paths: set[str] = set()
    in_required = False
    for raw in GATE_CHECK.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line in REQUIRED_GATE_HEADINGS:
            in_required = True
            continue
        if in_required and line.startswith("**") and line not in REQUIRED_GATE_HEADINGS:
            in_required = False
        if not in_required:
            continue
        for match in BACKTICK_PATH.finditer(line):
            candidate = match.group(1).replace("\\", "/")
            if PATH_HINT.match(candidate):
                paths.add(candidate)
    return paths


def parent_prefix(path_text: str) -> str:
    normalized = path_text.rstrip("/").replace("\\", "/")
    if not normalized:
        return normalized
    if normalized.endswith("*.md"):
        normalized = normalized[:-4]
    if "/" not in normalized:
        return normalized
    return normalized.rsplit("/", 1)[0] + "/"


def check_gate_artifact_trace(steps: list[CatalogStep]) -> list[Finding]:
    findings: list[Finding] = []
    catalog_artifacts = [glob.replace("\\", "/") for step in steps for glob in step.globs]
    catalog_notes = [step.note or "" for step in steps]

    for path in sorted(extract_required_gate_paths()):
        if path.startswith(("docs/engine-reference/", "docs/reference/")) and any(
            step.command == "/setup-engine" for step in steps
        ):
            continue
        if existing_or_template(path):
            continue
        prefix = parent_prefix(path)
        traced = False
        for artifact in catalog_artifacts:
            artifact_prefix = parent_prefix(artifact)
            if path == artifact or path in artifact or artifact in path:
                traced = True
            if path.startswith("production/epics/") and artifact.startswith("production/epics/"):
                traced = True
            if prefix and (prefix == artifact_prefix or prefix.startswith(artifact_prefix) or artifact_prefix.startswith(prefix)):
                traced = True
        if not traced and any(path in note or prefix in note for note in catalog_notes):
            traced = True
        if not traced:
            findings.append(Finding("ERROR", f"gate-check required artifact has no catalog/template trace: {path}"))
    return findings


def iter_text_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
        elif path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in TEXT_SUFFIXES
            )
    return files


def check_story_path_drift() -> list[Finding]:
    findings: list[Finding] = []
    legacy_story_path = "production/" + "stories"
    legacy_story_pattern = re.compile(re.escape(legacy_story_path) + r"(?:/|\b)")
    legacy_design_path = "design/" + "gdd"
    for path in iter_text_files(DRIFT_SCAN_ROOTS):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if legacy_story_pattern.search(line):
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(path)}:{line_no} uses legacy story path; use production/epics/[epic-slug]/story-NNN-[slug].md",
                    )
                )
            if legacy_design_path in line:
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(path)}:{line_no} uses legacy design GDD path; use design/cdd/",
                    )
                )
    return findings


def block_between(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    if start_index == -1:
        return ""
    end_index = text.find(end, start_index)
    if end_index == -1:
        return text[start_index:]
    return text[start_index:end_index]


def check_example_phase_boundaries() -> list[Finding]:
    findings: list[Finding] = []
    if not FLOW_DIAGRAMS.exists():
        findings.append(Finding("ERROR", f"missing examples flow diagram: {rel(FLOW_DIAGRAMS)}"))
        return findings

    text = FLOW_DIAGRAMS.read_text(encoding="utf-8", errors="replace")
    concept = block_between(text, "PHASE 1: CONCEPT", "PHASE 2: SYSTEMS DESIGN")
    pre_production = block_between(text, "PHASE 4: PRE-PRODUCTION", "PHASE 5: PRODUCTION")
    release = block_between(text, "PHASE 7: RELEASE", "```")

    if "/setup-engine" in concept:
        findings.append(
            Finding("ERROR", "docs/examples/skill-flow-diagrams.md places /setup-engine in Concept; it belongs in Technical Setup")
        )
    if "/test-setup" in pre_production:
        findings.append(
            Finding("ERROR", "docs/examples/skill-flow-diagrams.md places /test-setup in Pre-Production; it belongs in Technical Setup")
        )
    release_index = release.find("/release-checklist")
    launch_index = release.find("/launch-checklist")
    team_index = release.find("/team-release")
    if not (0 <= release_index < launch_index < team_index):
        findings.append(
            Finding("ERROR", "docs/examples/skill-flow-diagrams.md must order Release as /release-checklist -> /launch-checklist -> /team-release")
        )
    return findings


def check_accessibility_entry_paths() -> list[Finding]:
    findings: list[Finding] = []
    required_docs = [
        REPO_ROOT / "docs" / "START-HERE.md",
        QUICK_START,
        REPO_ROOT / ".claude" / "skills" / "constitute" / "SKILL.md",
    ]
    for path in required_docs:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "design/accessibility-requirements.md" not in text:
            findings.append(Finding("ERROR", f"{rel(path)} omits Technical Setup accessibility requirements"))
        if "/create-control-manifest" in text and re.search(r"/create-control-manifest[^\n]*/test-setup", text):
            findings.append(
                Finding(
                    "ERROR",
                    f"{rel(path)} places /create-control-manifest and /test-setup in one chain without a separate accessibility step",
                )
            )
    return findings


def check_quick_start_complete_paths() -> list[Finding]:
    findings: list[Finding] = []
    text = QUICK_START.read_text(encoding="utf-8", errors="replace")
    path_blocks = [
        ("Game Path A", "### Path A:", "### Path B:"),
        ("Game Path B", "### Path B:", "### Path C:"),
        ("Product Path A", "### Product Path A:", "### Product Path B:"),
        ("Product Path B", "### Product Path B:", "### Product Path C:"),
    ]
    required_commands = [
        "/architecture-review",
        "/gate-check technical-setup",
        "/gate-check pre-production",
        "/dev-story",
        "/story-done",
        "/gate-check production",
        "/team-polish",
        "/gate-check polish",
        "/release-checklist",
        "/launch-checklist",
        "/team-release",
    ]

    if "Start building" in text:
        findings.append(Finding("ERROR", "docs/QUICK-START.md still stops a path at Start building"))

    for label, start, end in path_blocks:
        block = block_between(text, start, end)
        if not block:
            findings.append(Finding("ERROR", f"docs/QUICK-START.md missing {label} block"))
            continue
        for command in required_commands:
            if command not in block:
                findings.append(Finding("ERROR", f"docs/QUICK-START.md {label} omits {command}"))
        gate_index = block.find("/gate-check technical-setup")
        ux_index = block.find("/ux-design")
        if gate_index == -1 or ux_index == -1:
            continue
        if not gate_index < ux_index:
            findings.append(
                Finding(
                    "ERROR",
                    f"docs/QUICK-START.md {label} starts UX before /gate-check technical-setup",
                )
            )
        release_positions = [block.find(command) for command in ["/release-checklist", "/launch-checklist", "/team-release"]]
        if not all(position >= 0 for position in release_positions) or release_positions != sorted(release_positions):
            findings.append(
                Finding(
                    "ERROR",
                    f"docs/QUICK-START.md {label} must order Release as /release-checklist -> /launch-checklist -> /team-release",
                )
            )
    return findings


def check_old_workflow_drift() -> list[Finding]:
    findings: list[Finding] = []
    banned = [
        ("docs/architecture/master.md", "use docs/architecture/architecture.md"),
        ("/ux-design accessibility", "create design/accessibility-requirements.md from the template"),
        ("production/validation/", "use production/qa/evidence/"),
        ("production/user-testing/", "use production/qa/evidence/user-tests/"),
        ("production/playtests/", "use production/qa/evidence/playtests/"),
        ("tests/evidence/", "use production/qa/evidence/"),
    ]
    for path in iter_text_files(DRIFT_SCAN_ROOTS):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for needle, replacement in banned:
                if needle in line:
                    findings.append(Finding("ERROR", f"{rel(path)}:{line_no} uses {needle}; {replacement}"))
    return findings


def check_art_bible_phase_drift() -> list[Finding]:
    findings: list[Finding] = []
    pattern = re.compile(
        r"(?:art-bible.*Technical Setup.*(?:required|blocker)|Technical Setup.*art-bible)",
        re.IGNORECASE,
    )
    for path in iter_text_files(DRIFT_SCAN_ROOTS):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(path)}:{line_no} treats /art-bible as a Technical Setup requirement; it is Concept optional",
                    )
                )
    return findings


def check_workflow_guide_phase_boundaries() -> list[Finding]:
    findings: list[Finding] = []
    text = WORKFLOW_GUIDE.read_text(encoding="utf-8", errors="replace")
    phase4 = block_between(text, "## Phase 4: Pre-Production", "## Phase 5: Production")
    phase5 = block_between(text, "## Phase 5: Production", "## Phase 6:")

    if "/dev-story" in phase4:
        findings.append(Finding("ERROR", "docs/WORKFLOW-GUIDE.md Phase 4 contains /dev-story; implementation belongs in Phase 5"))
    if "/dev-story" not in phase5:
        findings.append(Finding("ERROR", "docs/WORKFLOW-GUIDE.md Phase 5 must document /dev-story implementation"))
    return findings


def check_validation_quantity_boundaries() -> list[Finding]:
    findings: list[Finding] = []
    guide_text = WORKFLOW_GUIDE.read_text(encoding="utf-8", errors="replace")
    phase4 = block_between(guide_text, "## Phase 4: Pre-Production", "## Phase 5: Production")
    phase5_plus = block_between(guide_text, "## Phase 5: Production", "## Quick Reference:")

    banned_phase4_patterns = [
        r"Played unguided in at least 3 sessions",
        r"Vertical Slice played in 3\+ sessions",
        r"3\+ sessions",
        r"3 unguided sessions",
        r"at least 3 [^\n]*sessions",
    ]
    for pattern in banned_phase4_patterns:
        if re.search(pattern, phase4, flags=re.IGNORECASE):
            findings.append(
                Finding(
                    "ERROR",
                    "docs/WORKFLOW-GUIDE.md Phase 4 makes 3 sessions a Pre-Production gate condition",
                )
            )
            break

    catalog_text = CATALOG.read_text(encoding="utf-8", errors="replace")
    if catalog_text.count("min_count: 3") < 2:
        findings.append(Finding("ERROR", "workflow-catalog.yaml must keep cumulative 3-session validation in Polish / Verification"))
    if not re.search(r"(?:3 sessions|3-session|Three sessions)", phase5_plus):
        findings.append(Finding("ERROR", "docs/WORKFLOW-GUIDE.md must keep cumulative 3-session validation after Pre-Production"))

    gate_required = GATE_REQUIRED_ARTIFACTS.read_text(encoding="utf-8", errors="replace") if GATE_REQUIRED_ARTIFACTS.exists() else ""
    if "production/qa/evidence/playtests/playtest*.md` (minimum 3)" not in gate_required:
        findings.append(Finding("ERROR", "generated gate requirements must require cumulative 3 game playtest reports"))
    if "production/qa/evidence/user-tests/*.md` (minimum 3)" not in gate_required:
        findings.append(Finding("ERROR", "generated gate requirements must require cumulative 3 product validation reports"))
    return findings


def check_gate_required_semantics() -> list[Finding]:
    findings: list[Finding] = []
    in_required = False
    banned_required_patterns = [
        "Art bible exists at `design/art/art-bible.md`",
        "At least 3 distinct user testing sessions",
        "QA plan exists in `production/qa/` (generated by `/qa-plan`)",
        "QA sign-off report exists in `production/qa/`",
        "QA test plan exists",
        "QA sign-off report exists",
        "Smoke check passes cleanly",
        "Release checklist completed",
        "Launch checklist completed",
        "`/release-checklist` run before `/launch-checklist`",
    ]
    for line_no, raw in enumerate(GATE_CHECK.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        line = raw.strip()
        if line in REQUIRED_GATE_HEADINGS:
            in_required = True
            continue
        if in_required and line.startswith("**") and line not in REQUIRED_GATE_HEADINGS:
            in_required = False
        if not in_required:
            continue
        for pattern in banned_required_patterns:
            if pattern in line:
                findings.append(Finding("ERROR", f"{rel(GATE_CHECK)}:{line_no} keeps old non-catalog blocker: {pattern}"))
    return findings


def check_gate_required_artifacts_contract() -> list[Finding]:
    findings: list[Finding] = []
    if not GATE_REQUIRED_ARTIFACTS.exists():
        return [Finding("ERROR", f"missing generated gate requirements: {rel(GATE_REQUIRED_ARTIFACTS)}")]

    try:
        from generate_gate_required_sections import render as render_gate_required
        from generate_phase_checklists import parse_catalog as parse_phase_catalog
    except Exception as exc:  # pragma: no cover - reported through script output
        return [Finding("ERROR", f"cannot import gate requirements generator: {exc}")]

    expected = render_gate_required(parse_phase_catalog(CATALOG))
    actual = GATE_REQUIRED_ARTIFACTS.read_text(encoding="utf-8", errors="replace")
    if actual != expected:
        findings.append(
            Finding(
                "ERROR",
                "workflow/generated/gate-required-artifacts.md is stale; run python scripts/generate_gate_required_sections.py --write",
            )
        )

    for path in [GATE_CHECK, CODEX_GATE_CHECK]:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "workflow/generated/gate-required-artifacts.md" not in text:
            findings.append(Finding("ERROR", f"{rel(path)} must reference generated gate required artifacts"))

        in_required = False
        for line_no, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if line in REQUIRED_GATE_HEADINGS:
                in_required = True
                continue
            if in_required and line.startswith("**") and line not in REQUIRED_GATE_HEADINGS:
                in_required = False
            if in_required and line.startswith("- [ ]"):
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(path)}:{line_no} has hand-authored checklist row under generated Required Artifacts",
                    )
                )

    return findings


def check_customer_delivery_contract() -> list[Finding]:
    findings: list[Finding] = []

    platform_docs = [
        REPO_ROOT / "SUPPORT.md",
        REPO_ROOT / "RELEASE_NOTES.md",
    ]
    stale_platform_patterns = [
        "CI currently verifies",
        "full matrix CI is not yet enabled",
    ]
    for path in platform_docs:
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in stale_platform_patterns:
            if pattern in text:
                findings.append(Finding("ERROR", f"{rel(path)} keeps stale platform support wording: {pattern}"))
        if "Ubuntu, macOS, and Windows" not in text:
            findings.append(Finding("ERROR", f"{rel(path)} must describe Ubuntu, macOS, and Windows CI configuration"))

    release_notes = (REPO_ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8", errors="replace")
    customer_acceptance = CUSTOMER_ACCEPTANCE.read_text(encoding="utf-8", errors="replace")
    if "Validation status:" not in release_notes:
        findings.append(Finding("ERROR", "RELEASE_NOTES.md must include explicit validation status"))
    if "Validation status: Pending" in release_notes:
        findings.append(Finding("ERROR", "RELEASE_NOTES.md must not leave validation status pending after CI success is confirmed"))
    if re.search(r"PASS for commit `[0-9a-f]{7,40}` in GitHub Actions run\s*`\d+`", release_notes):
        findings.append(
            Finding(
                "ERROR",
                "RELEASE_NOTES.md must not hard-code a historical PASS commit/run; record immutable evidence on the GitHub Release or tag",
            )
        )
    for snippet in [
        "GitHub Release or annotated tag",
        "Required workflow: `Template Consistency`",
        "Required release evidence: release commit SHA, GitHub Actions run ID",
    ]:
        if snippet not in release_notes:
            findings.append(Finding("ERROR", f"RELEASE_NOTES.md omits release validation contract: {snippet}"))
    if re.search(r"gh run view \d+", customer_acceptance):
        findings.append(
            Finding(
                "ERROR",
                "docs/CUSTOMER-ACCEPTANCE.md must not hard-code a GitHub Actions run ID; select the run matching the release commit",
            )
        )
    for snippet in [
        'gh run list --workflow "Template Consistency"',
        "gh run view <run-id> --json jobs,headSha,conclusion",
        "The selected run's `headSha` matches the release commit",
        "GitHub Release or annotated tag records the release commit SHA",
    ]:
        if snippet not in customer_acceptance:
            findings.append(Finding("ERROR", f"{rel(CUSTOMER_ACCEPTANCE)} omits release validation step: {snippet}"))

    setup_requirements = (REPO_ROOT / "docs" / "reference" / "setup-requirements.md").read_text(
        encoding="utf-8",
        errors="replace",
    )
    if re.search(r"Hooks \(\d+ of \d+\)", setup_requirements):
        findings.append(Finding("ERROR", "docs/reference/setup-requirements.md must not hard-code hook count fractions"))

    guide_text = WORKFLOW_GUIDE.read_text(encoding="utf-8", errors="replace")
    phase5_gate = block_between(guide_text, "### Phase 5 Gate", "---")
    if re.search(r"\b3\s*(?:sessions|-session)|three sessions", phase5_gate, flags=re.IGNORECASE):
        findings.append(Finding("ERROR", "docs/WORKFLOW-GUIDE.md Phase 5 gate must not require 3 validation sessions"))

    gate_text = GATE_CHECK.read_text(encoding="utf-8", errors="replace")
    gate_sections = [
        (
            "game",
            block_between(
                gate_text,
                "**[游戏专用] Game: Pre-Production → Production**",
                "---\n\n**[通用产品] Product: Pre-Implementation → Implementation**",
            ),
        ),
        (
            "product",
            block_between(
                gate_text,
                "**[通用产品] Product: Pre-Implementation → Implementation**",
                "### Gate: Production → Polish / Implementation → Verification",
            ),
        ),
    ]
    banned_required_terms = [
        "main menu",
        "core gameplay HUD",
        "pause menu",
        "Foundation and Core",
        "Foundation/Core",
        "Foundation layer epics",
        "Core layer epics",
    ]
    for label, section in gate_sections:
        required = block_between(section, "**Catalog Required Artifacts:**", "**Quality / Risk Checks:**")
        for term in banned_required_terms:
            if term in required:
                findings.append(
                    Finding(
                        "ERROR",
                        f"gate-check {label} Pre-Production catalog requirements are stricter than workflow catalog: {term}",
                    )
                )

    return findings


def check_customer_acceptance_contract() -> list[Finding]:
    findings: list[Finding] = []
    if not CUSTOMER_ACCEPTANCE.exists():
        return [Finding("ERROR", f"missing customer acceptance checklist: {rel(CUSTOMER_ACCEPTANCE)}")]

    text = CUSTOMER_ACCEPTANCE.read_text(encoding="utf-8", errors="replace")
    required_snippets = [
        "python scripts/skill_lint.py --self-test",
        "python scripts/skill_lint.py --strict .claude/skills",
        "python scripts/skill_lint.py --strict .agents/skills",
        "python scripts/workflow_consistency.py",
        "ubuntu-latest",
        "macos-latest",
        "windows-latest",
        "docs/USER-MANUAL.md",
        "/cdd-status --dry-run",
        "design/ux/surface-profile.md",
        "docs/examples/project-roadmap.example.md",
    ]
    for snippet in required_snippets:
        if snippet not in text:
            findings.append(Finding("ERROR", f"{rel(CUSTOMER_ACCEPTANCE)} omits acceptance check: {snippet}"))
    return findings


def check_user_manual_contract() -> list[Finding]:
    findings: list[Finding] = []
    if not USER_MANUAL.exists():
        return [Finding("ERROR", f"missing user manual: {rel(USER_MANUAL)}")]

    manual_text = USER_MANUAL.read_text(encoding="utf-8", errors="replace")
    required_snippets = [
        "# User Manual",
        "docs/START-HERE.md",
        "docs/WORKFLOW-GUIDE.md",
        "53 specialized agents",
        "78 slash-command skills",
        "/constitute",
        "/project-stage-detect",
        "/help",
        "/cdd-status",
        "/adopt",
        "/gate-check concept",
        "## Technical Setup",
        "/create-architecture",
        "/architecture-decision",
        "/architecture-review",
        "/create-control-manifest",
        "/test-setup",
        "/gate-check technical-setup",
        "/release-checklist -> /launch-checklist -> /team-release",
        "docs/CUSTOMER-ACCEPTANCE.md",
        "Template Consistency",
        "Ubuntu, macOS, and Windows",
    ]
    for snippet in required_snippets:
        if snippet not in manual_text:
            findings.append(Finding("ERROR", f"{rel(USER_MANUAL)} omits user manual contract: {snippet}"))

    entry_docs = [
        REPO_ROOT / "docs" / "START-HERE.md",
        QUICK_START,
        WORKFLOW_GUIDE,
    ]
    for path in entry_docs:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "docs/USER-MANUAL.md" not in text:
            findings.append(Finding("ERROR", f"{rel(path)} must reference docs/USER-MANUAL.md"))
    return findings


def check_status_dashboard_contract() -> list[Finding]:
    findings: list[Finding] = []
    required_paths = [
        SKILLS_DIR / "cdd-status" / "SKILL.md",
        CODEX_SKILLS_DIR / "cdd-status" / "SKILL.md",
    ]
    for path in required_paths:
        if not path.exists():
            findings.append(Finding("ERROR", f"missing cdd-status skill: {rel(path)}"))
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in [
            "production/project-roadmap.md",
            "workflow/workflow-catalog.yaml",
            "design/ux/surface-profile.md",
            "docs/examples/project-roadmap.example.md",
            "Product Surface Decisions",
            "`design/ux/interaction-patterns.md` | REQUIRED / N/A / MISSING",
            "`design/design-system.md` | REQUIRED / N/A / OPTIONAL",
            "`design/brand/style-guide.md` | OPTIONAL / REQUIRED BY SCOPE / N/A",
        ]:
            if snippet not in text:
                findings.append(Finding("ERROR", f"{rel(path)} omits cdd-status requirement: {snippet}"))

    if not PROJECT_ROADMAP_EXAMPLE.exists():
        findings.append(Finding("ERROR", f"missing project roadmap example: {rel(PROJECT_ROADMAP_EXAMPLE)}"))

    docs_to_check = [
        REPO_ROOT / "docs" / "START-HERE.md",
        CUSTOMER_ACCEPTANCE,
        USER_MANUAL,
        WORKFLOW_GUIDE,
        QUICK_START,
        SKILLS_REFERENCE,
    ]
    for path in docs_to_check:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "/cdd-status" not in text:
            findings.append(Finding("ERROR", f"{rel(path)} must mention /cdd-status"))
    for path in [REPO_ROOT / "docs" / "START-HERE.md", CUSTOMER_ACCEPTANCE, QUICK_START, USER_MANUAL]:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "docs/examples/project-roadmap.example.md" not in text:
            findings.append(Finding("ERROR", f"{rel(path)} must reference docs/examples/project-roadmap.example.md"))
    return findings


def check_memory_bank_entrypoint_contract() -> list[Finding]:
    findings: list[Finding] = []

    readme_path = QUICK_START
    readme_text = readme_path.read_text(encoding="utf-8", errors="replace")
    for snippet in [
        "memory_bank/",
        "project brain",
        "governance control plane",
        "T0",
        "T1",
        "T2",
        "T3",
        "design/",
        "production/",
        "PROCEED/PIVOT/KILL",
        "CUT/KEEP/DEFER",
    ]:
        if snippet not in readme_text:
            findings.append(Finding("ERROR", f"{rel(readme_path)} omits memory-bank entrypoint wording: {snippet}"))

    manual_text = USER_MANUAL.read_text(encoding="utf-8", errors="replace")
    for snippet in [
        "The Project Brain",
        "Where Do I Look?",
        "memory_bank/t0_core/current_state.md",
        "memory_bank/t2_execution/current_roadmap.md",
        "memory_bank/t3_archive/qa_evidence_index.md",
        "PROCEED/PIVOT/KILL",
        "CUT/KEEP/DEFER",
    ]:
        if snippet not in manual_text:
            findings.append(Finding("ERROR", f"{rel(USER_MANUAL)} omits memory-bank user-manual entrypoint: {snippet}"))

    quick_start_text = QUICK_START.read_text(encoding="utf-8", errors="replace")
    memory_pos = quick_start_text.find("memory_bank/")
    hierarchy_pos = quick_start_text.find("### 1. Understand the Hierarchy")
    if memory_pos == -1:
        findings.append(Finding("ERROR", f"{rel(QUICK_START)} must mention memory_bank/"))
    if hierarchy_pos == -1:
        findings.append(Finding("ERROR", f"{rel(QUICK_START)} must retain hierarchy section marker"))
    if memory_pos != -1 and hierarchy_pos != -1 and memory_pos > hierarchy_pos:
        findings.append(Finding("ERROR", f"{rel(QUICK_START)} must introduce memory_bank/ before agent hierarchy"))
    for snippet in ["PROCEED/PIVOT/KILL", "CUT/KEEP/DEFER"]:
        if snippet not in quick_start_text:
            findings.append(Finding("ERROR", f"{rel(QUICK_START)} omits high-impact decision wording: {snippet}"))

    return findings


def check_memory_bank_contract() -> list[Finding]:
    findings: list[Finding] = []
    required_templates = [
        "README.md",
        "document_map.yaml",
        "t0_core/basic_law_index.md",
        "t0_core/active_context.md",
        "t0_core/current_state.md",
        "t0_core/release_state.md",
        "t0_core/amendment_log.md",
        "t1_axioms/tech_context.md",
        "t1_axioms/system_patterns.md",
        "t1_axioms/behavior_context.md",
        "t1_axioms/architecture_context.md",
        "t1_axioms/ux_accessibility_context.md",
        "t1_axioms/qa_context.md",
        "t1_axioms/knowledge_graph.md",
        "t1_axioms/module_support_map.yaml",
        "t2_execution/README.md",
        "t2_execution/workflow_contract.md",
        "t2_execution/phase_checklists.md",
        "t2_execution/gate_required_artifacts.md",
        "t2_execution/current_roadmap.md",
        "t3_archive/README.md",
        "t3_archive/qa_evidence_index.md",
        "t3_archive/release_evidence/README.md",
        "t3_archive/gate_runs/README.md",
        "t3_archive/reviews/README.md",
        "t3_archive/reviews/review-index.md",
        "t3_archive/sprint_snapshots/README.md",
        "t3_archive/sprint_snapshots/story-closure-index.md",
        "t3_archive/amendments/README.md",
    ]
    if not MEMORY_BANK_TEMPLATE_DIR.exists():
        findings.append(Finding("ERROR", f"missing memory-bank template directory: {rel(MEMORY_BANK_TEMPLATE_DIR)}"))
    for path_text in required_templates:
        path = MEMORY_BANK_TEMPLATE_DIR / path_text
        if not path.exists():
            findings.append(Finding("ERROR", f"missing memory-bank template: {rel(path)}"))

    template_readme = (MEMORY_BANK_TEMPLATE_DIR / "README.md")
    if template_readme.exists():
        text = template_readme.read_text(encoding="utf-8", errors="replace")
        for snippet in ["T0 Core", "T1 Axioms", "T2 Execution", "T3 Archive", "canonical", "mirror", "index", "archive"]:
            if snippet not in text:
                findings.append(Finding("ERROR", f"{rel(template_readme)} omits memory-bank layer contract: {snippet}"))

    document_map = MEMORY_BANK_TEMPLATE_DIR / "document_map.yaml"
    if document_map.exists():
        text = document_map.read_text(encoding="utf-8", errors="replace")
        for snippet in [
            "role: canonical",
            "role: source",
            "role: mirror",
            "role: index",
            "role: archive",
            "memory_bank/t0_core/basic_law_index.md",
            "memory_bank/t0_core/amendment_log.md",
            "standards/technical-preferences.md",
            "memory_bank/t1_axioms/tech_context.md",
            "memory_bank/t1_axioms/knowledge_graph.md",
            "workflow/workflow-catalog.yaml",
            "docs/PHASE-CHECKLISTS.md",
            "workflow/generated/gate-required-artifacts.md",
            "memory_bank/t2_execution/phase_checklists.md",
            "memory_bank/t2_execution/gate_required_artifacts.md",
            "production/project-roadmap.md",
            "memory_bank/t2_execution/current_roadmap.md",
            "production/qa/evidence/**",
            "production/qa/bug-triage-*.md",
            "memory_bank/t3_archive/qa_evidence_index.md",
            "memory_bank/t3_archive/gate_runs/",
            "memory_bank/t3_archive/release_evidence/",
            "memory_bank/t3_archive/reviews/",
            "memory_bank/t3_archive/reviews/review-index.md",
            "prototypes/*/REPORT.md",
            "production/code-reviews/code-review-*.md",
            "production/scope/scope-check-*.md",
            "memory_bank/t3_archive/sprint_snapshots/",
            "memory_bank/t3_archive/sprint_snapshots/story-closure-index.md",
            "memory_bank/t3_archive/amendments/",
            "memory_bank/t3_archive/amendments/amendment-v*-*.md",
        ]:
            if snippet not in text:
                findings.append(Finding("ERROR", f"{rel(document_map)} omits document map entry: {snippet}"))

    for path in [SKILLS_DIR / "constitute" / "SKILL.md", CODEX_SKILLS_DIR / "constitute" / "SKILL.md"]:
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in [
            "T0 core",
            "T1 supporting",
            "T2 execution",
            "T3 archive",
            "memory_bank/document_map.yaml",
            "memory_bank/t0_core/current_state.md",
            "memory_bank/t0_core/amendment_log.md",
            "memory_bank/t1_axioms/knowledge_graph.md",
            "memory_bank/t2_execution/workflow_contract.md",
            "memory_bank/t2_execution/phase_checklists.md",
            "memory_bank/t2_execution/gate_required_artifacts.md",
            "memory_bank/t2_execution/current_roadmap.md",
            "memory_bank/t3_archive/README.md",
            "memory_bank/t3_archive/gate_runs/README.md",
            "memory_bank/t3_archive/reviews/README.md",
            "memory_bank/t3_archive/reviews/review-index.md",
            "memory_bank/t3_archive/sprint_snapshots/README.md",
            "memory_bank/t3_archive/sprint_snapshots/story-closure-index.md",
            "memory_bank/t3_archive/amendments/README.md",
            "memory_bank/t3_archive/amendments/amendment-v[version]-[YYYY-MM-DD].md",
            "impacted T1/T2/T3 files",
            "generate_phase_checklists.py --write --memory-bank",
            "deprecated compatibility pointer",
        ]:
            if snippet not in text:
                findings.append(Finding("ERROR", f"{rel(path)} omits memory-bank constitute contract: {snippet}"))

    for path in [SKILLS_DIR / "constitute-check" / "SKILL.md", CODEX_SKILLS_DIR / "constitute-check" / "SKILL.md"]:
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in [
            "T0-T3 Memory Health Audit",
            "memory_bank/t0_core/current_state.md",
            "memory_bank/t1_axioms/knowledge_graph.md",
            "memory_bank/t2_execution/workflow_contract.md",
            "memory_bank/t2_execution/current_roadmap.md",
            "memory_bank/t3_archive/qa_evidence_index.md",
            "memory_bank/t3_archive/gate_runs/README.md",
            "memory_bank/t3_archive/release_evidence/README.md",
            "memory_bank/t3_archive/reviews/README.md",
            "memory_bank/t3_archive/reviews/review-index.md",
            "memory_bank/t3_archive/sprint_snapshots/README.md",
            "memory_bank/t3_archive/sprint_snapshots/story-closure-index.md",
            "memory_bank/t3_archive/amendments/README.md",
            "NEEDS ATTENTION",
            "deprecated compatibility path",
        ]:
            if snippet not in text:
                findings.append(Finding("ERROR", f"{rel(path)} omits memory-bank health contract: {snippet}"))

    for path in [SKILLS_DIR / "cdd-status" / "SKILL.md", CODEX_SKILLS_DIR / "cdd-status" / "SKILL.md"]:
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in [
            "memory_bank/t2_execution/current_roadmap.md",
            "Governance memory mirror generated by `/cdd-status`",
            "--dry-run",
            "Run `/constitute` to establish the memory_bank governance control plane",
        ]:
            if snippet not in text:
                findings.append(Finding("ERROR", f"{rel(path)} omits memory-bank cdd-status contract: {snippet}"))

    workflow_contracts = [
        (
            "setup-engine",
            [
                "memory_bank/t1_axioms/tech_context.md",
                "Selected engine, language, framework, runtime, and database",
                "Reason chosen",
                "Do not create `memory_bank/` from `/setup-engine`",
            ],
        ),
        (
            "gate-check",
            [
                "memory_bank/t3_archive/gate_runs/",
                "gate-[phase]-[YYYY-MM-DD].md",
                "gate-[phase]-[YYYY-MM-DD]-[NN].md",
                "memory_bank/t0_core/current_state.md",
                "establish the memory_bank governance control plane",
            ],
        ),
        (
            "playtest-report",
            [
                "memory_bank/t3_archive/qa_evidence_index.md",
                "production/qa/evidence/...",
                "same evidence path already exists",
                "establish the memory_bank governance control plane",
            ],
        ),
        (
            "team-release",
            [
                "memory_bank/t3_archive/release_evidence/release-[version].md",
                "memory_bank/t0_core/release_state.md",
                "workflow run ID",
                "timestamped evidence",
                "memory_bank/` does not exist",
            ],
        ),
        (
            "prototype",
            [
                "memory_bank/t3_archive/reviews/review-index.md",
                "Review Type: `prototype-decision`",
                "Source Artifact: `prototypes/[concept-name]/REPORT.md`",
                "Verdict: `PROCEED`, `PIVOT`, or `KILL`",
                "prototype code stays isolated",
            ],
        ),
        (
            "design-review",
            [
                "memory_bank/t3_archive/reviews/review-index.md",
                "Review Type: `design-review`",
                "Source Artifact: `design/cdd/reviews/[doc-name]-review-log.md`",
                "Source Artifact` as the dedupe key",
            ],
        ),
        (
            "code-review",
            [
                "memory_bank/t3_archive/reviews/review-index.md",
                "Review Type: `code-review`",
                "Source Artifact: `production/code-reviews/code-review-[scope]-[YYYY-MM-DD].md`",
                "APPROVED WITH SUGGESTIONS",
                "Do not create `memory_bank/` from",
            ],
        ),
        (
            "scope-check",
            [
                "memory_bank/t3_archive/reviews/review-index.md",
                "Review Type: `scope-check`",
                "Source Artifact: `production/scope/scope-check-[target]-[YYYY-MM-DD].md`",
                "Verdict: `PASS`, `CONCERNS`, or `FAIL`",
                "Default behavior is read-only",
            ],
        ),
        (
            "bug-triage",
            [
                "memory_bank/t3_archive/qa_evidence_index.md",
                "Type: `bug-triage`",
                "Path: `production/qa/bug-triage-[date].md`",
                "Verdict: `COMPLETE` or `BLOCKED`",
            ],
        ),
        (
            "hotfix",
            [
                "memory_bank/t3_archive/release_evidence/hotfix-[short-name]-[YYYY-MM-DD].md",
                "memory_bank/t0_core/release_state.md",
                "severity, branch/commit, QA gate, rollback plan",
                "post-incident review link",
            ],
        ),
        (
            "review-all-gdds",
            [
                "memory_bank/t3_archive/reviews/review-index.md",
                "Review Type: `cross-cdd-review`",
                "Source Artifact: `design/cdd/cross-review-[date].md`",
                "Source Artifact` as the dedupe key",
            ],
        ),
        (
            "architecture-review",
            [
                "memory_bank/t3_archive/reviews/review-index.md",
                "Review Type: `architecture-review`",
                "Source Artifact: `docs/architecture/architecture-review-[date].md`",
                "Source Artifact` as the dedupe key",
            ],
        ),
        (
            "ux-review",
            [
                "memory_bank/t3_archive/reviews/review-index.md",
                "Review Type `ux-review`",
                "Do not create `memory_bank/` from `/ux-review`",
            ],
        ),
        (
            "test-evidence-review",
            [
                "memory_bank/t3_archive/reviews/review-index.md",
                "memory_bank/t3_archive/qa_evidence_index.md",
                "Review Type `test-evidence-review`",
                "Type `test-evidence-review`",
            ],
        ),
        (
            "smoke-check",
            [
                "memory_bank/t3_archive/qa_evidence_index.md",
                "Type: `smoke-check`",
                "Evidence path: `production/qa/smoke-[date].md`",
                "Dedupe by evidence path",
            ],
        ),
        (
            "team-qa",
            [
                "memory_bank/t3_archive/qa_evidence_index.md",
                "Type: `qa-signoff`",
                "Evidence path: `production/qa/qa-signoff-[sprint]-[date].md`",
                "Dedupe by evidence path",
            ],
        ),
        (
            "story-done",
            [
                "memory_bank/t3_archive/sprint_snapshots/story-closure-index.md",
                "Completion Verdict: COMPLETE, COMPLETE WITH RISKS, or BLOCKED",
                "Use `Story Path` as the dedupe key",
            ],
        ),
        (
            "retrospective",
            [
                "memory_bank/t3_archive/sprint_snapshots/",
                "sprint-[id]-closeout-[YYYY-MM-DD].md",
                "milestone-[name]-closeout-[YYYY-MM-DD].md",
            ],
        ),
        (
            "milestone-review",
            [
                "memory_bank/t3_archive/sprint_snapshots/",
                "milestone-[name]-review-[YYYY-MM-DD].md",
                "next gate recommendation",
            ],
        ),
    ]
    for skill_name, snippets in workflow_contracts:
        for path in [SKILLS_DIR / skill_name / "SKILL.md", CODEX_SKILLS_DIR / skill_name / "SKILL.md"]:
            text = path.read_text(encoding="utf-8", errors="replace")
            for snippet in snippets:
                if snippet not in text:
                    findings.append(Finding("ERROR", f"{rel(path)} omits memory-bank evidence contract: {snippet}"))
        claude_text = (SKILLS_DIR / skill_name / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        codex_text = (CODEX_SKILLS_DIR / skill_name / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        for snippet in snippets:
            if (snippet in claude_text) != (snippet in codex_text):
                findings.append(Finding("ERROR", f"{skill_name} memory-bank evidence contract differs between .claude and .agents: {snippet}"))

    for path, mirror in [
        (GENERATE_PHASE_CHECKLISTS, "memory_bank/t2_execution/phase_checklists.md"),
        (GENERATE_GATE_REQUIRED, "memory_bank/t2_execution/gate_required_artifacts.md"),
    ]:
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in ["--memory-bank", mirror, "memory_bank/t2_execution does not exist"]:
            if snippet not in text:
                findings.append(Finding("ERROR", f"{rel(path)} omits memory-bank generator support: {snippet}"))

    stale_path = "memory_bank/t0_core/" + "knowledge_graph.md"
    allowed_markers = ["deprecated", "compatibility"]
    for path in iter_text_files([REPO_ROOT / ".claude", REPO_ROOT / ".agents", REPO_ROOT / "docs", REPO_ROOT / "scripts"]):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if stale_path in line and not any(marker in line.lower() for marker in allowed_markers):
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(path)}:{line_no} uses {stale_path} outside deprecated/compatibility wording; use memory_bank/t1_axioms/knowledge_graph.md",
                    )
                )

    return findings


def check_legacy_template_roots_removed() -> list[Finding]:
    findings: list[Finding] = []

    forbidden_paths = [
        TEMPLATES_DIR / "t0",
        TEMPLATES_DIR / "t1",
        TEMPLATES_DIR / "skill-test-spec.md",
    ]
    for path in forbidden_paths:
        if path.exists():
            findings.append(
                Finding(
                    "ERROR",
                    f"{rel(path)} is a legacy duplicate; use templates/memory-bank/* or skill_testing/templates/ instead",
                )
            )

    forbidden_snippets = [
        "templates/" + "t0",
        "templates\\" + "t0",
        "templates/" + "t1",
        "templates\\" + "t1",
    ]
    forbidden_patterns = [
        re.compile(r"(?<!skill_testing/)templates/skill-test-spec\.md"),
        re.compile(r"(?<!skill_testing\\)templates\\skill-test-spec\.md"),
    ]
    scan_roots = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs",
        SKILLS_DIR,
        CODEX_SKILLS_DIR,
        TEMPLATES_DIR,
        STANDARDS_DIR,
        SKILL_TESTING_DIR,
    ]
    for path in iter_text_files(scan_roots):
        if rel(path).startswith("docs/reference/archive/"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in forbidden_snippets:
            if snippet in text:
                findings.append(Finding("ERROR", f"{rel(path)} still references legacy template source {snippet}"))
        for pattern in forbidden_patterns:
            if pattern.search(text):
                findings.append(Finding("ERROR", f"{rel(path)} still references legacy top-level skill-test spec template"))

    return findings


def check_help_status_escalation_contract() -> list[Finding]:
    findings: list[Finding] = []
    for path in [
        SKILLS_DIR / "help" / "SKILL.md",
        CODEX_SKILLS_DIR / "help" / "SKILL.md",
    ]:
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in [
            "3 or more required steps",
            "/cdd-status --dry-run",
        ]:
            if snippet not in text:
                findings.append(Finding("ERROR", f"{rel(path)} omits help escalation snippet: {snippet}"))
    return findings


def check_surface_profile_contract() -> list[Finding]:
    findings: list[Finding] = []
    template = TEMPLATES_DIR / "surface-profile.md"
    if not template.exists():
        findings.append(Finding("ERROR", f"missing surface profile template: {rel(template)}"))

    checks = [
        (CATALOG, "product-surface-profile"),
        (CATALOG, "design/ux/surface-profile.md"),
        (GATE_CHECK, "design/ux/surface-profile.md"),
        (CODEX_SKILLS_DIR / "gate-check" / "SKILL.md", "design/ux/surface-profile.md"),
        (SKILLS_DIR / "help" / "SKILL.md", "design/ux/surface-profile.md"),
        (CODEX_SKILLS_DIR / "help" / "SKILL.md", "design/ux/surface-profile.md"),
        (SKILLS_DIR / "cdd-status" / "SKILL.md", "design/ux/surface-profile.md"),
        (CODEX_SKILLS_DIR / "cdd-status" / "SKILL.md", "design/ux/surface-profile.md"),
    ]
    for path, snippet in checks:
        text = path.read_text(encoding="utf-8", errors="replace")
        if snippet not in text:
            findings.append(Finding("ERROR", f"{rel(path)} must reference {snippet}"))
    return findings


def check_phase_checklist_contract() -> list[Finding]:
    findings: list[Finding] = []
    if not PHASE_CHECKLISTS.exists():
        return [Finding("ERROR", f"missing generated phase checklist: {rel(PHASE_CHECKLISTS)}")]

    try:
        from generate_phase_checklists import parse_catalog as parse_phase_catalog
        from generate_phase_checklists import render as render_phase_checklists
    except Exception as exc:  # pragma: no cover - reported through script output
        return [Finding("ERROR", f"cannot import phase checklist generator: {exc}")]

    expected = render_phase_checklists(parse_phase_catalog(CATALOG))
    actual = PHASE_CHECKLISTS.read_text(encoding="utf-8", errors="replace")
    if actual != expected:
        findings.append(
            Finding(
                "ERROR",
                "docs/PHASE-CHECKLISTS.md is stale; run python scripts/generate_phase_checklists.py --write",
            )
        )
    return findings


def check_skill_count_contract() -> list[Finding]:
    findings: list[Finding] = []
    known_commands = collect_known_commands()
    actual_claude = sum(1 for path in SKILLS_DIR.glob("*/SKILL.md") if path.is_file())
    actual_codex = sum(1 for path in CODEX_SKILLS_DIR.glob("*/SKILL.md") if path.is_file())
    if actual_claude != actual_codex:
        findings.append(
            Finding(
                "ERROR",
                f".claude skills ({actual_claude}) and .agents skills ({actual_codex}) must have matching counts",
            )
        )
    actual = actual_claude
    skill_testing_readme = SKILL_TESTING_DIR / "README.md"
    skill_testing_catalog = SKILL_TESTING_DIR / "catalog.yaml"

    checks = [
        (
            QUICK_START,
            [
                re.compile(r"skills/\s+--\s+(\d+)\s+slash command definitions"),
            ],
        ),
        (
            REPO_ROOT / "CHANGELOG.md",
            [
                re.compile(r"all\s+(\d+)\s+skills"),
            ],
        ),
        (
            WORKFLOW_GUIDE,
            [
                re.compile(r"(\d+)-agent system,\s+(\d+)\s+slash commands"),
                re.compile(r"All\s+(\d+)\s+Commands by Category"),
            ],
        ),
        (
            SKILLS_REFERENCE,
            [
                re.compile(r"^(\d+)\s+slash commands", re.MULTILINE),
            ],
        ),
        (
            skill_testing_readme,
            [
                re.compile(r"all\s+(\d+)\s+skills\s+and\s+53 agents"),
            ],
        ),
        (
            skill_testing_catalog,
            [
                re.compile(r"registry:\s*\n\s+skills:\s*\n(?:.*\n)*?\s+agents:", re.MULTILINE),
            ],
        ),
        (
            SKILLS_DIR / "skill-test" / "SKILL.md",
            [
                re.compile(r"SKILLS\s+\((\d+)\s+total\)"),
                re.compile(r"Specs written:\s+(\d+)\s+\(100%\)"),
                re.compile(r"Never static tested:\s+(\d+)"),
                re.compile(r"Never category tested:\s+(\d+)"),
                re.compile(r"Skill coverage:\s+(\d+)/(\d+)\s+specs"),
            ],
        ),
        (
            CODEX_SKILLS_DIR / "skill-test" / "SKILL.md",
            [
                re.compile(r"SKILLS\s+\((\d+)\s+total\)"),
                re.compile(r"Specs written:\s+(\d+)\s+\(100%\)"),
                re.compile(r"Never static tested:\s+(\d+)"),
                re.compile(r"Never category tested:\s+(\d+)"),
                re.compile(r"Skill coverage:\s+(\d+)/(\d+)\s+specs"),
            ],
        ),
    ]
    for path, patterns in checks:
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            matches = list(pattern.finditer(text))
            if not matches:
                findings.append(Finding("ERROR", f"{rel(path)} must state the current skill count ({actual})"))
                continue
            for match in matches:
                numbers = [int(value) for value in match.groups() if value and value.isdigit()]
                if not numbers:
                    continue
                documented = numbers[-1]
                if documented != actual:
                    findings.append(
                        Finding(
                            "ERROR",
                            f"{rel(path)} documents {documented} skills, but .claude/skills contains {actual}",
                        )
                    )

    stale_count_docs = [
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "docs" / "START-HERE.md",
        QUICK_START,
        WORKFLOW_GUIDE,
        SKILLS_REFERENCE,
        skill_testing_readme,
        skill_testing_catalog,
        SKILLS_DIR / "skill-test" / "SKILL.md",
        CODEX_SKILLS_DIR / "skill-test" / "SKILL.md",
    ]
    stale_patterns = [
        re.compile(r"\b73\s+skills\b", re.IGNORECASE),
        re.compile(r"\ball\s+73\b", re.IGNORECASE),
        re.compile(r"\b72\s+total\b", re.IGNORECASE),
        re.compile(r"\bSKILLS\s+\(72\s+total\)", re.IGNORECASE),
    ]
    for path in stale_count_docs:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in stale_patterns:
            if pattern.search(text):
                findings.append(Finding("ERROR", f"{rel(path)} keeps stale skill count wording: {pattern.pattern}"))

    for path in [SKILLS_REFERENCE]:
        text = path.read_text(encoding="utf-8", errors="replace")
        commands = {match.group(0) for match in COMMAND_REF.finditer(text)}
        missing = sorted(known_commands - commands)
        if missing:
            findings.append(
                Finding(
                    "ERROR",
                    f"{rel(path)} omits installed skill command(s): {', '.join(missing)}",
                )
            )
    return findings


def registry_block(text: str, key: str, next_key: str | None = None) -> str:
    marker = f"  {key}:"
    if marker not in text:
        return ""
    tail = text.split(marker, 1)[1]
    if next_key is not None:
        next_marker = f"\n  {next_key}:"
        if next_marker in tail:
            return tail.split(next_marker, 1)[0]
    return tail


def registry_names(block: str) -> set[str]:
    return {match.group(1).strip() for match in re.finditer(r"^\s+- name:\s*([^\n]+)$", block, re.MULTILINE)}


def check_skill_testing_memory_bank_contract() -> list[Finding]:
    findings: list[Finding] = []
    legacy_name = LEGACY_SKILL_TESTING_DIRNAME
    legacy_dir = REPO_ROOT / legacy_name

    if legacy_dir.exists():
        findings.append(Finding("ERROR", f"legacy top-level testing framework directory must not exist: {legacy_name}/"))

    scan_roots = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "docs",
        REPO_ROOT / ".claude",
        REPO_ROOT / ".agents",
        REPO_ROOT / "scripts",
    ]
    for path in iter_text_files(scan_roots):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if legacy_name in line:
                findings.append(Finding("ERROR", f"{rel(path)}:{line_no} references removed path {legacy_name}/"))

    required_paths = [
        SKILL_TESTING_DIR / "README.md",
        SKILL_TESTING_DIR / "catalog.yaml",
        SKILL_TESTING_DIR / "quality-rubric.md",
        SKILL_TESTING_DIR / "specs" / "skills",
        SKILL_TESTING_DIR / "specs" / "agents",
        SKILL_TESTING_DIR / "templates",
        SKILL_TESTING_DIR / "templates" / "skill-test-spec.md",
        SKILL_TESTING_DIR / "templates" / "agent-test-spec.md",
        SKILL_TESTING_T2_MOUNT / "README.md",
        SKILL_TESTING_T3 / "README.md",
        SKILL_TESTING_T3 / "coverage-index.yaml",
        SKILL_TESTING_T3 / "results" / "static" / "README.md",
        SKILL_TESTING_T3 / "results" / "spec" / "README.md",
        SKILL_TESTING_T3 / "results" / "category" / "README.md",
        SKILL_TESTING_T3 / "results" / "audit" / "README.md",
        SKILL_TESTING_T3 / "improvements" / "README.md",
    ]
    for path in required_paths:
        if not path.exists():
            findings.append(Finding("ERROR", f"missing skill testing asset: {rel(path)}"))

    forbidden_mount_children = [
        "catalog.yaml",
        "quality-rubric.md",
        "specs",
        "templates",
    ]
    for child in forbidden_mount_children:
        path = SKILL_TESTING_T2_MOUNT / child
        if path.exists():
            findings.append(Finding("ERROR", f"{rel(path)} must not be copied into memory-bank T2 mount; use skill_testing/"))

    catalog_path = SKILL_TESTING_DIR / "catalog.yaml"
    coverage_path = SKILL_TESTING_T3 / "coverage-index.yaml"
    if catalog_path.exists():
        catalog_text = catalog_path.read_text(encoding="utf-8", errors="replace")
        required_catalog_snippets = [
            "version: 3",
            "asset_scope: cross_project",
            "registry:",
            "skill_testing/specs/skills/",
            "skill_testing/specs/agents/",
        ]
        for snippet in required_catalog_snippets:
            if snippet not in catalog_text:
                findings.append(Finding("ERROR", f"{rel(catalog_path)} must contain {snippet}"))

        forbidden_history_fields = [
            "last_static",
            "last_static_result",
            "last_spec",
            "last_spec_result",
            "last_category",
            "last_category_result",
        ]
        for field in forbidden_history_fields:
            if field in catalog_text:
                findings.append(Finding("ERROR", f"{rel(catalog_path)} keeps T3 history field in T2 catalog: {field}"))

        for match in re.finditer(r"^\s+spec:\s*(.+)$", catalog_text, re.MULTILINE):
            spec = match.group(1).strip()
            if not spec.startswith("skill_testing/specs/"):
                findings.append(Finding("ERROR", f"{rel(catalog_path)} has non-canonical spec path: {spec}"))

        actual_skills = {path.parent.name for path in SKILLS_DIR.glob("*/SKILL.md") if path.is_file()}
        actual_agents = {path.stem for path in (REPO_ROOT / ".claude" / "agents").rglob("*.md") if path.is_file()}
        skill_names = registry_names(registry_block(catalog_text, "skills", "agents"))
        agent_names = registry_names(registry_block(catalog_text, "agents"))
        if skill_names != actual_skills:
            missing = sorted(actual_skills - skill_names)
            extra = sorted(skill_names - actual_skills)
            findings.append(
                Finding(
                    "ERROR",
                    f"{rel(catalog_path)} skill registry mismatch; missing={missing}, extra={extra}",
                )
            )
        if agent_names != actual_agents:
            missing = sorted(actual_agents - agent_names)
            extra = sorted(agent_names - actual_agents)
            findings.append(
                Finding(
                    "ERROR",
                    f"{rel(catalog_path)} agent registry mismatch; missing={missing}, extra={extra}",
                )
            )

    if coverage_path.exists():
        coverage_text = coverage_path.read_text(encoding="utf-8", errors="replace")
        for snippet in ["version: 1", "skills:", "agents:"]:
            if snippet not in coverage_text:
                findings.append(Finding("ERROR", f"{rel(coverage_path)} must contain {snippet}"))

    document_map = MEMORY_BANK_TEMPLATE_DIR / "document_map.yaml"
    if document_map.exists():
        document_map_text = document_map.read_text(encoding="utf-8", errors="replace")
        for snippet in [
            "skill_testing/catalog.yaml",
            "skill_testing/quality-rubric.md",
            "skill_testing/specs/skills/**",
            "skill_testing/specs/agents/**",
            "memory_bank/t3_archive/skill_testing/coverage-index.yaml",
            "memory_bank/t3_archive/skill_testing/results/**",
            "memory_bank/t3_archive/skill_testing/improvements/**",
        ]:
            if snippet not in document_map_text:
                findings.append(Finding("ERROR", f"{rel(document_map)} must map {snippet}"))

    skill_contracts = [
        (
            "skill-test",
            [
                "skill_testing/catalog.yaml",
                "skill_testing/quality-rubric.md",
                "memory_bank/t3_archive/skill_testing/results/static/",
                "memory_bank/t3_archive/skill_testing/results/spec/",
                "memory_bank/t3_archive/skill_testing/results/category/",
                "memory_bank/t3_archive/skill_testing/results/audit/",
                "memory_bank/t3_archive/skill_testing/coverage-index.yaml",
            ],
        ),
        (
            "skill-improve",
            [
                "skill_testing/catalog.yaml",
                "skill_testing/quality-rubric.md",
                "memory_bank/t3_archive/skill_testing/improvements/",
                "memory_bank/t3_archive/skill_testing/coverage-index.yaml",
            ],
        ),
    ]
    for skill_name, snippets in skill_contracts:
        for skill_root in [SKILLS_DIR, CODEX_SKILLS_DIR]:
            path = skill_root / skill_name / "SKILL.md"
            text = path.read_text(encoding="utf-8", errors="replace")
            for snippet in snippets:
                if snippet not in text:
                    findings.append(Finding("ERROR", f"{rel(path)} must reference {snippet}"))
            if legacy_name in text:
                findings.append(Finding("ERROR", f"{rel(path)} still references removed testing framework path"))

    for doc_path in [USER_MANUAL, QUICK_START, SKILLS_REFERENCE]:
        text = doc_path.read_text(encoding="utf-8", errors="replace")
        for snippet in [
            "skill_testing/",
            "memory_bank/t3_archive/skill_testing",
        ]:
            if snippet not in text:
                findings.append(Finding("ERROR", f"{rel(doc_path)} must describe {snippet}"))

    return findings


def check_release_phase_contract() -> list[Finding]:
    findings: list[Finding] = []
    catalog_text = CATALOG.read_text(encoding="utf-8", errors="replace")
    release_block = block_between(catalog_text, "  release:", "\n\nquality_gates:")
    required_commands: dict[str, bool] = {}
    current_command: str | None = None
    for raw in release_block.splitlines():
        line = raw.strip()
        if line.startswith("command: "):
            current_command = line.split(":", 1)[1].strip()
            continue
        if line.startswith("required: ") and current_command:
            required_commands[current_command] = line.endswith("true")
            current_command = None

    expected = ["/release-checklist", "/launch-checklist", "/team-release"]
    for command in expected:
        if required_commands.get(command) is not True:
            findings.append(Finding("ERROR", f"workflow-catalog.yaml Release phase must require {command}"))

    order_positions = [release_block.find(command) for command in expected]
    if not all(position >= 0 for position in order_positions) or order_positions != sorted(order_positions):
        findings.append(
            Finding(
                "ERROR",
                "workflow-catalog.yaml must order Release as /release-checklist -> /launch-checklist -> /team-release",
            )
        )

    phase_gate_phrases = [
        "before proceeding to release",
        "before launch",
    ]
    for skill_path in [
        SKILLS_DIR / "release-checklist" / "SKILL.md",
        SKILLS_DIR / "launch-checklist" / "SKILL.md",
    ]:
        text = skill_path.read_text(encoding="utf-8", errors="replace")
        for phrase in phase_gate_phrases:
            if phrase in text:
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(skill_path)} must not require a repeated phase gate {phrase}",
                    )
                )

    stale_release_sequence = re.compile(
        r"/release-checklist\s*->\s*/launch-checklist\s*->\s*/changelog\s*->\s*/patch-notes\s*->\s*/hotfix"
    )
    normal_release_sequence = re.compile(
        r"/release-checklist\s*->\s*/launch-checklist\s*->\s*/team-release"
    )
    for skill_path in [
        SKILLS_DIR / "constitute" / "SKILL.md",
        CODEX_SKILLS_DIR / "constitute" / "SKILL.md",
    ]:
        text = skill_path.read_text(encoding="utf-8", errors="replace")
        normalized = text.replace("→", "->").replace("`", "")
        if stale_release_sequence.search(normalized):
            findings.append(
                Finding(
                    "ERROR",
                    f"{rel(skill_path)} must not present /changelog, /patch-notes, or /hotfix as the normal Release Phase chain",
                )
            )
        if not normal_release_sequence.search(normalized):
            findings.append(
                Finding(
                    "ERROR",
                    f"{rel(skill_path)} must present Release Phase as /release-checklist -> /launch-checklist -> /team-release",
                )
            )
        lower = text.lower()
        if ("/changelog" in text or "/patch-notes" in text) and "optional release communication artifacts" not in lower:
            findings.append(
                Finding(
                    "ERROR",
                    f"{rel(skill_path)} must describe /changelog and /patch-notes as optional release communication artifacts",
                )
            )
        if "/hotfix" in text and "emergency-only" not in lower:
            findings.append(
                Finding(
                    "ERROR",
                    f"{rel(skill_path)} must describe /hotfix as emergency-only",
                )
            )
    return findings


def check_skill_user_guide_contract() -> list[Finding]:
    findings: list[Finding] = []
    required_labels = [
        "When to use:",
        "Inputs:",
        "Outputs:",
        "Memory-bank writes:",
        "Next steps:",
    ]
    guide_pattern = re.compile(r"(?ms)^## User Guide\s*\n(?P<body>.*?)(?=^#{1,2}\s|\Z)")

    for skills_root in [SKILLS_DIR, CODEX_SKILLS_DIR]:
        for skill_path in sorted(skills_root.glob("*/SKILL.md")):
            text = skill_path.read_text(encoding="utf-8", errors="replace")
            match = guide_pattern.search(text)
            if not match:
                findings.append(Finding("ERROR", f"{rel(skill_path)} must include a ## User Guide block"))
                continue
            body = match.group("body")
            missing = [label for label in required_labels if label not in body]
            if missing:
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(skill_path)} User Guide is missing label(s): {', '.join(missing)}",
                    )
                )

    for help_path in [
        SKILLS_DIR / "help" / "SKILL.md",
        CODEX_SKILLS_DIR / "help" / "SKILL.md",
    ]:
        text = help_path.read_text(encoding="utf-8", errors="replace")
        match = guide_pattern.search(text)
        body = match.group("body") if match else ""
        required_help_snippets = [
            "Memory-bank writes: None",
            "read-only",
            "reads `memory_bank/t0_core/basic_law_index.md`",
        ]
        for snippet in required_help_snippets:
            if snippet not in body:
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(help_path)} User Guide must describe /help as read-only and only reading memory_bank/t0_core/basic_law_index.md",
                    )
                )
                break

    docs_to_check = [
        USER_MANUAL,
        QUICK_START,
    ]
    for doc_path in docs_to_check:
        text = doc_path.read_text(encoding="utf-8", errors="replace")
        required_doc_snippets = [
            "User Guide",
            "when to use",
            "inputs",
            "outputs",
            "memory-bank writes",
            "next steps",
        ]
        lower = text.lower()
        for snippet in required_doc_snippets:
            if snippet.lower() not in lower:
                findings.append(Finding("ERROR", f"{rel(doc_path)} must describe the slash-command User Guide contract"))
                break
        if "auto-run" not in lower and "automatic execution" not in lower:
            findings.append(Finding("ERROR", f"{rel(doc_path)} must state recommended next steps do not auto-run"))

    return findings


def check_template_count_contract() -> list[Finding]:
    findings: list[Finding] = []
    actual = sum(1 for path in TEMPLATES_DIR.rglob("*") if path.is_file())
    checks = [
        (
            QUICK_START,
            [
                re.compile(r"(\d+)\s+document templates"),
            ],
        ),
    ]
    for path, patterns in checks:
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            matches = list(pattern.finditer(text))
            if not matches:
                findings.append(Finding("ERROR", f"{rel(path)} must state the current template count ({actual})"))
                continue
            for match in matches:
                documented = int(match.group(1))
                if documented != actual:
                    findings.append(
                        Finding(
                            "ERROR",
                            f"{rel(path)} documents {documented} templates, but templates/ contains {actual}",
                        )
                )
    return findings


def iter_hook_commands(value: object) -> list[str]:
    commands: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "command" and isinstance(item, str):
                commands.append(item)
            else:
                commands.extend(iter_hook_commands(item))
    elif isinstance(value, list):
        for item in value:
            commands.extend(iter_hook_commands(item))
    return commands


def normalized_hook_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def normalized_root_instruction_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def check_codex_adapter_contract() -> list[Finding]:
    findings: list[Finding] = []

    required_paths = [
        AGENTS_MD,
        CLAUDE_MD,
        CODEX_SKILLS_DIR,
        CODEX_AGENTS_DIR,
        CODEX_HOOKS_DIR,
        CODEX_DIR / "hooks.json",
    ]
    for path in required_paths:
        if not path.exists():
            findings.append(Finding("ERROR", f"missing Codex adapter asset: {rel(path)}"))

    if AGENTS_MD.exists() and CLAUDE_MD.exists():
        if normalized_root_instruction_text(AGENTS_MD) != normalized_root_instruction_text(CLAUDE_MD):
            findings.append(
                Finding(
                    "ERROR",
                    "AGENTS.md and CLAUDE.md must stay text-identical after normalizing line endings",
                )
            )

    legacy_prefix = "." + "Codex"
    legacy_path_fragments = [legacy_prefix + "/", legacy_prefix + "\\"]
    local_prefix = "D:" + "\\Users\\Administrator\\Desktop\\Constitution-Driven-Development"
    for path in iter_text_files(DELIVERY_SCAN_ROOTS):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if any(fragment in line for fragment in legacy_path_fragments):
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(path)}:{line_no} uses a non-existent uppercase Codex adapter path",
                    )
                )
            if local_prefix in line:
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(path)}:{line_no} contains a machine-specific absolute path",
                    )
                )

    hooks_json_path = CODEX_DIR / "hooks.json"
    if hooks_json_path.exists():
        try:
            hooks_config = json.loads(hooks_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            findings.append(Finding("ERROR", f"{rel(hooks_json_path)} is not valid JSON: {exc}"))
            hooks_config = {}
        for command in iter_hook_commands(hooks_config):
            normalized = command.replace("\\", "/")
            if local_prefix.replace("\\", "/") in normalized or ":/" in normalized:
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(hooks_json_path)} contains non-portable hook command: {command}",
                    )
                )
            if " .codex/hooks/" not in normalized and not normalized.startswith("bash .codex/hooks/"):
                findings.append(
                    Finding(
                        "ERROR",
                        f"{rel(hooks_json_path)} hook command must use relative .codex/hooks path: {command}",
                    )
                )

    if CODEX_AGENTS_DIR.exists():
        for agent_file in sorted(CODEX_AGENTS_DIR.glob("*.toml")):
            try:
                tomllib.loads(agent_file.read_text(encoding="utf-8"))
            except tomllib.TOMLDecodeError as exc:
                findings.append(Finding("ERROR", f"{rel(agent_file)} is not valid TOML: {exc}"))

    if CLAUDE_HOOKS_DIR.exists() and CODEX_HOOKS_DIR.exists():
        claude_hooks = {path.name: path for path in CLAUDE_HOOKS_DIR.glob("*.sh")}
        codex_hooks = {path.name: path for path in CODEX_HOOKS_DIR.glob("*.sh")}
        for name, claude_hook in sorted(claude_hooks.items()):
            codex_hook = codex_hooks.get(name)
            if codex_hook is None:
                findings.append(Finding("ERROR", f"missing Codex hook counterpart for .claude/hooks/{name}"))
                continue
            if normalized_hook_text(claude_hook) != normalized_hook_text(codex_hook):
                findings.append(
                    Finding(
                        "ERROR",
                        f".codex/hooks/{name} must match .claude/hooks/{name}",
                    )
                )
        for name in sorted(set(codex_hooks) - set(claude_hooks)):
            findings.append(Finding("ERROR", f".codex/hooks/{name} has no .claude/hooks counterpart"))

    return findings


def check_adapter_boundary_contract() -> list[Finding]:
    findings: list[Finding] = []

    required_roots = [
        WORKFLOW_DIR / "workflow-catalog.yaml",
        TEMPLATES_DIR,
        STANDARDS_DIR,
        SKILL_TESTING_DIR / "catalog.yaml",
        REPO_ROOT / "adapters" / "README.md",
        REPO_ROOT / "adapters" / "claude" / "README.md",
        REPO_ROOT / "adapters" / "codex" / "README.md",
    ]
    for path in required_roots:
        if not path.exists():
            findings.append(Finding("ERROR", f"missing neutral common asset root: {rel(path)}"))

    forbidden_adapter_paths = [
        REPO_ROOT / ".claude" / "docs" / "templates",
        REPO_ROOT / ".claude" / "docs" / "workflow-catalog.yaml",
        REPO_ROOT / ".claude" / "docs" / "generated",
        REPO_ROOT / ".claude" / "docs" / "technical-preferences.md",
        REPO_ROOT / ".claude" / "docs" / "director-gates.md",
        REPO_ROOT / ".claude" / "docs" / "coding-standards.md",
        REPO_ROOT / ".claude" / "docs" / "context-management.md",
        REPO_ROOT / ".claude" / "docs" / "coordination-rules.md",
        REPO_ROOT / ".claude" / "docs" / "directory-structure.md",
    ]
    for path in forbidden_adapter_paths:
        if path.exists():
            findings.append(Finding("ERROR", f"{rel(path)} must not be canonical under the Claude adapter"))

    adapters_readme = REPO_ROOT / "adapters" / "README.md"
    if adapters_readme.exists():
        text = adapters_readme.read_text(encoding="utf-8", errors="replace")
        for snippet in [
            "workflow/",
            "templates/",
            "standards/",
            "skill_testing/",
            "docs/",
            ".claude/",
            ".agents/",
            ".codex/",
            "Do not move canonical",
        ]:
            if snippet not in text:
                findings.append(Finding("ERROR", f"{rel(adapters_readme)} omits adapter boundary snippet: {snippet}"))

    allowed_claude_docs = {
        "CLAUDE-local-template.md",
        "quick-start.md",
        "settings-local-template.md",
    }
    claude_docs = REPO_ROOT / ".claude" / "docs"
    if claude_docs.exists():
        for path in claude_docs.rglob("*"):
            if path.is_file() and path.name not in allowed_claude_docs:
                findings.append(Finding("ERROR", f"{rel(path)} is not an allowed Claude adapter doc"))

    adapter_docs_path = ".claude/" + "docs"
    forbidden_snippets = [
        f"{adapter_docs_path}/workflow-catalog.yaml",
        f"{adapter_docs_path}/templates",
        f"{adapter_docs_path}/generated",
        f"{adapter_docs_path}/technical-preferences.md",
        f"{adapter_docs_path}/director-gates.md",
        f"{adapter_docs_path}/coding-standards.md",
        f"{adapter_docs_path}/context-management.md",
        f"{adapter_docs_path}/coordination-rules.md",
        f"{adapter_docs_path}/directory-structure.md",
    ]
    scan_roots = [
        REPO_ROOT / "README.md",
        AGENTS_MD,
        CLAUDE_MD,
        REPO_ROOT / "docs",
        SKILLS_DIR,
        CODEX_SKILLS_DIR,
        REPO_ROOT / "scripts",
        TEMPLATES_DIR,
        STANDARDS_DIR,
        SKILL_TESTING_DIR,
    ]
    for path in iter_text_files(scan_roots):
        if rel(path).startswith("docs/reference/archive/"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in forbidden_snippets:
            if snippet in text:
                findings.append(Finding("ERROR", f"{rel(path)} still treats {snippet} as a common source"))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warnings-as-errors", action="store_true", help="Treat WARN findings as errors.")
    args = parser.parse_args()

    known_commands = collect_known_commands()
    steps = parse_catalog()
    findings: list[Finding] = []
    findings.extend(check_catalog_commands(steps, known_commands))
    findings.extend(check_doc_commands(known_commands))
    findings.extend(check_required_catalog_artifacts(steps, known_commands))
    findings.extend(check_gate_artifact_trace(steps))
    findings.extend(check_story_path_drift())
    findings.extend(check_example_phase_boundaries())
    findings.extend(check_accessibility_entry_paths())
    findings.extend(check_quick_start_complete_paths())
    findings.extend(check_old_workflow_drift())
    findings.extend(check_art_bible_phase_drift())
    findings.extend(check_workflow_guide_phase_boundaries())
    findings.extend(check_validation_quantity_boundaries())
    findings.extend(check_gate_required_semantics())
    findings.extend(check_gate_required_artifacts_contract())
    findings.extend(check_customer_delivery_contract())
    findings.extend(check_customer_acceptance_contract())
    findings.extend(check_user_manual_contract())
    findings.extend(check_status_dashboard_contract())
    findings.extend(check_memory_bank_contract())
    findings.extend(check_legacy_template_roots_removed())
    findings.extend(check_memory_bank_entrypoint_contract())
    findings.extend(check_help_status_escalation_contract())
    findings.extend(check_surface_profile_contract())
    findings.extend(check_phase_checklist_contract())
    findings.extend(check_release_phase_contract())
    findings.extend(check_skill_user_guide_contract())
    findings.extend(check_skill_testing_memory_bank_contract())
    findings.extend(check_skill_count_contract())
    findings.extend(check_template_count_contract())
    findings.extend(check_adapter_boundary_contract())
    findings.extend(check_codex_adapter_contract())

    errors = sum(1 for item in findings if item.severity == "ERROR")
    warnings = sum(1 for item in findings if item.severity == "WARN")
    for item in findings:
        print(f"{item.severity}: {item.message}")
    print(f"workflow-consistency summary: {errors} error(s), {warnings} warning(s)")
    if errors or (args.warnings_as_errors and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
