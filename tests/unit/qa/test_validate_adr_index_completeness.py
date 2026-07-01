from pathlib import Path

from scripts.validate_adr_index_completeness import validate


def test_adr_index_completeness_accepts_current_registry():
    assert validate() == []


def test_adr_index_completeness_rejects_missing_adr(tmp_path: Path):
    arch = tmp_path / "docs" / "architecture"
    registry = tmp_path / "docs" / "registry" / "architecture.yaml"
    arch.mkdir(parents=True)
    registry.parent.mkdir(parents=True)
    (arch / "adr-0001-example.md").write_text("# ADR-0001\n", encoding="utf-8")
    (arch / "adr-0002-example.md").write_text("# ADR-0002\n", encoding="utf-8")
    registry.write_text("adr_index:\n  - id: ADR-0001\n", encoding="utf-8")

    findings = validate(arch, registry)

    assert len(findings) == 1
    assert "ADR-0002 is missing" in findings[0].message


def test_adr_index_completeness_accepts_all_indexed_adrs(tmp_path: Path):
    arch = tmp_path / "docs" / "architecture"
    registry = tmp_path / "docs" / "registry" / "architecture.yaml"
    arch.mkdir(parents=True)
    registry.parent.mkdir(parents=True)
    (arch / "adr-0001-example.md").write_text("# ADR-0001\n", encoding="utf-8")
    registry.write_text("adr_index:\n  - id: ADR-0001\n", encoding="utf-8")

    assert validate(arch, registry) == []
