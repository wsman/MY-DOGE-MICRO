from pathlib import Path

from scripts.validate_governance_yaml_shape import validate_file, validate_files


def test_validate_governance_yaml_shape_accepts_current_default_files():
    payload = validate_files(
        [
            Path("docs/progress/runtime-maturity.yaml"),
            Path("production/sprint-status.yaml"),
            Path("docs/registry/architecture.yaml"),
            Path("docs/registry/entities.yaml"),
            Path("docs/architecture/tr-registry.yaml"),
        ]
    )

    assert payload["passed"] is True
    assert payload["summary"] == {"files": 5, "findings": 0}


def test_validate_governance_yaml_shape_rejects_tabs(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("version: 1\n\tbad: true\n", encoding="utf-8")

    findings = validate_file(path)

    assert any("tabs are not allowed" in finding.message for finding in findings)


def test_validate_governance_yaml_shape_rejects_odd_indentation(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("version: 1\n bad: true\n", encoding="utf-8")

    findings = validate_file(path)

    assert any("even two-space" in finding.message for finding in findings)


def test_validate_governance_yaml_shape_rejects_duplicate_top_level_keys(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("version: 1\nversion: 2\n", encoding="utf-8")

    findings = validate_file(path)

    assert any("duplicate top-level key 'version'" in finding.message for finding in findings)


def test_validate_governance_yaml_shape_rejects_missing_required_top_level_key(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("version: 1\n", encoding="utf-8")

    findings = validate_file(path, required_keys={"version", "rollup"})

    assert any("missing required top-level key 'rollup'" in finding.message for finding in findings)


def test_validate_governance_yaml_shape_rejects_cr_only_line_endings(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_bytes(b"version: 1\rrollup: {}\n")

    findings = validate_file(path)

    assert any("CR-only line ending" in finding.message for finding in findings)
