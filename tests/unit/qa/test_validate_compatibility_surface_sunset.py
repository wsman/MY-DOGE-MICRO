from pathlib import Path

from scripts.validate_compatibility_surface_sunset import validate


def test_compatibility_surface_sunset_accepts_current_registry():
    assert validate() == []


def test_compatibility_surface_sunset_rejects_empty_gate(tmp_path: Path):
    registry = tmp_path / "compatibility-surfaces.md"
    registry.write_text(
        "\n".join(
            [
                "# Registry",
                "",
                "## Surface Registry",
                "",
                "| surface | type | parity_tests | earliest_removal |",
                "|---|---|---|---|",
                "| `old.path` | `import-shim` | TBD | - |",
            ]
        ),
        encoding="utf-8",
    )

    findings = validate(registry)

    assert any("parity_tests" in finding.message for finding in findings)
    assert any("earliest_removal" in finding.message for finding in findings)


def test_compatibility_surface_sunset_rejects_missing_column(tmp_path: Path):
    registry = tmp_path / "compatibility-surfaces.md"
    registry.write_text(
        "\n".join(
            [
                "# Registry",
                "",
                "## Surface Registry",
                "",
                "| surface | type | parity_tests |",
                "|---|---|---|",
                "| `old.path` | `import-shim` | test_file.py |",
            ]
        ),
        encoding="utf-8",
    )

    findings = validate(registry)

    assert findings
    assert "missing required columns" in findings[0].message
