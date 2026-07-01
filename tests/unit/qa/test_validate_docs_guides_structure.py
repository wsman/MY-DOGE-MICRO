from pathlib import Path

from scripts.validate_docs_guides_structure import validate, validate_file


def test_docs_guides_structure_accepts_current_reader_paths():
    assert validate() == []


def test_docs_guides_structure_rejects_missing_required_section(tmp_path: Path):
    path = tmp_path / "guide.md"
    path.write_text("# Guide\n\nSee [API](../API.md).\n", encoding="utf-8")

    findings = validate_file(path)

    assert any("Your 3-step" in finding.message for finding in findings)
    assert any("When To Leave" in finding.message for finding in findings)


def test_docs_guides_structure_rejects_pure_redirect(tmp_path: Path):
    path = tmp_path / "guide.md"
    path.write_text(
        "# Guide\n\n## Your 3-step first path\n\nSee [API](../API.md).\n\n## When To Leave This Page\n\nLeave.\n",
        encoding="utf-8",
    )

    findings = validate_file(path)

    assert any("more than a redirect" in finding.message for finding in findings)


def test_docs_guides_structure_rejects_missing_canonical_link(tmp_path: Path):
    path = tmp_path / "guide.md"
    path.write_text(
        "# Guide\n\n## Your 3-step first path\n\n"
        + "\n".join(f"Line {i}." for i in range(25))
        + "\n\n## When To Leave This Page\n\nDone.\n",
        encoding="utf-8",
    )

    findings = validate_file(path)

    assert any("missing link" in finding.message for finding in findings)
