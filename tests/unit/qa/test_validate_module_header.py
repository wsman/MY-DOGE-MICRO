from pathlib import Path

from scripts.validate_module_header import validate_module_file, validate_template_files


def test_module_header_accepts_current_template_files():
    assert validate_template_files() == []


def test_module_header_accepts_complete_header(tmp_path: Path):
    path = tmp_path / "module.md"
    path.write_text(
        "\n".join(
            [
                "Canonical owner: doge.products.research",
                "Bounded context: Research",
                "Allowed imports: shared ports",
                "Forbidden imports: legacy APIs",
                "Public contract: docs/API.md",
                "Maturity: experimental",
            ]
        ),
        encoding="utf-8",
    )

    assert validate_module_file(path) == []


def test_module_header_rejects_missing_field(tmp_path: Path):
    path = tmp_path / "module.md"
    path.write_text("Canonical owner: doge.products.research\n", encoding="utf-8")

    findings = validate_module_file(path)

    assert any("Bounded context:" in finding.message for finding in findings)


def test_module_header_rejects_unknown_context(tmp_path: Path):
    path = tmp_path / "module.md"
    path.write_text(
        "\n".join(
            [
                "Canonical owner: doge.products.research",
                "Bounded context: New Module",
                "Allowed imports: shared ports",
                "Forbidden imports: legacy APIs",
                "Public contract: docs/API.md",
                "Maturity: experimental",
            ]
        ),
        encoding="utf-8",
    )

    findings = validate_module_file(path)

    assert any("unknown bounded context" in finding.message for finding in findings)
