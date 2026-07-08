import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _count_inline_items(text: str, key: str) -> int:
    in_block = False
    count = 0
    for line in text.splitlines():
        if not in_block:
            if line == f"{key}:":
                in_block = True
            continue
        if line and not line.startswith(" ") and not line.startswith("#"):
            break
        if line.strip().startswith("- {"):
            count += 1
    return count


def test_docs_index_points_to_current_product_docs():
    index = _read("docs/index.md")
    for target in [
        "product/overview.md",
        "guides/getting-started.md",
        "API.md",
        "CLI.md",
        "MCP_SERVER.md",
        "architecture/overview.md",
        "quality/status.md",
        "progress/runtime-maturity.yaml",
    ]:
        assert target in index


def test_readme_is_current_product_entry_not_legacy_architecture():
    readme = _read("README.md")
    assert readme.startswith("# OpenDoge")
    for stale in [
        "MY-DOGE QUANT SYSTEM",
        "15 modules",
        "20 product modules",
        "51 product routes",
        "三层架构",
    ]:
        assert stale not in readme
    for required in [
        "docs/index.md",
        "docs/API.md",
        "scripts/mcp_stdio.bat",
        "src/doge/interfaces/api/main.py",
        "DEEPSEEK_API_KEY",
        "REPLACE_WITH_DEEPSEEK_API_KEY",
        "production_ready: false",
        "stable_declaration: forbidden",
    ]:
        assert required in readme


def test_architecture_registry_has_eight_active_and_twenty_superseded_systems():
    registry = _read("docs/registry/architecture.yaml")
    assert _count_inline_items(registry, "systems") == 8
    assert _count_inline_items(registry, "superseded_systems") == 20
    assert 'status: "superseded_by: ADR-0021"' in registry
    assert 'status: "superseded_by: ADR-0022"' not in registry
    for context in [
        "Market Intelligence",
        "Research",
        "Portfolio & Risk",
        "Quant & Data Lab",
        "Workspace & Workflow",
        "Agent Runtime",
        "Knowledge & Evidence",
        "Governance & Evaluation",
    ]:
        assert context in registry


def test_dated_audits_are_archived_and_indexed():
    progress_hits = sorted((ROOT / "docs" / "progress").glob("*2026-06-23.md"))
    archive_hits = sorted((ROOT / "docs" / "archive" / "audits").glob("*2026-06-23.md"))
    progress_index = _read("docs/progress/README.md")

    assert progress_hits == []
    assert len(archive_hits) == 13
    for path in archive_hits:
        assert path.name in progress_index


def test_runtime_maturity_non_production_posture_is_unchanged():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    assert "production_ready: false" in maturity
    assert "stable_declaration: forbidden" in maturity


def test_runtime_maturity_marks_inmemory_as_non_production_and_pyqt_removed():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    readme = _read("README.md")
    getting_started = _read("docs/guides/getting-started.md")

    for required in [
        "in_memory_runtime:",
        "status: demo_test_only",
        "not the production-facing runtime path",
        "pyqt_desktop:",
        "status: removed",
        "legacy PyQt dashboard and gui extra were removed",
    ]:
        assert required in maturity

    assert "the in-memory agent runtime" in readme
    assert "compatibility or demo surfaces" in readme
    assert "PyQt desktop dashboard" in readme
    assert "removed in Sprint M" in readme
    assert "gui` extra is no longer shipped" in getting_started
    assert "Web/SDK/`/v1` path" in getting_started


def test_docs_validation_scripts_pass():
    commands = [
        [sys.executable, "scripts/validate_no_stale_counts.py"],
        [sys.executable, "scripts/validate_docs_links.py"],
        [sys.executable, "scripts/validate_docs_authority.py"],
        [sys.executable, "scripts/validate_adr_index_completeness.py"],
        [sys.executable, "scripts/validate_docs_guides_structure.py"],
        [sys.executable, "scripts/validate_docs_length.py"],
        [sys.executable, "scripts/validate_docs_maturity_claims.py"],
        [sys.executable, "scripts/validate_compatibility_surface_sunset.py"],
        [sys.executable, "scripts/validate_module_header.py"],
        [sys.executable, "scripts/generate_docs_status.py", "--check"],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert result.returncode == 0, result.stdout
