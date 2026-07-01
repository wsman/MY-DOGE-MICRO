"""Governance test for production import boundaries (K-1).

Asserts that no production code under ``src/doge/`` imports the compatibility
shims ``doge.interfaces.api.routers.v1`` or ``doge.application.agent.tools``.
The clean tree has a zero baseline, so any new offender fails immediately.
"""

from pathlib import Path

from scripts.validate_import_boundaries import validate


def test_clean_repo_has_no_production_shim_importers():
    findings = validate()
    assert findings == [], (
        "production code under src/doge/ must not import compatibility shims; "
        + "; ".join(f.format() for f in findings)
    )


def test_scanner_flags_a_forbidden_absolute_import(tmp_path: Path):
    pkg = tmp_path / "src" / "doge" / "offending"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "uses_shim.py").write_text(
        "import doge.application.agent.tools\n", encoding="utf-8"
    )

    findings = validate(tmp_path)

    assert any("doge.application.agent.tools" in f.module for f in findings)


def test_scanner_flags_a_forbidden_v1_router_import(tmp_path: Path):
    pkg = tmp_path / "src" / "doge" / "offending"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "uses_v1.py").write_text(
        "from doge.interfaces.api.routers.v1 import runs\n", encoding="utf-8"
    )

    findings = validate(tmp_path)

    assert any("doge.interfaces.api.routers.v1" in f.module for f in findings)


def test_scanner_flags_a_forbidden_relative_import(tmp_path: Path):
    # `from ..agent.tools import x` from a sibling package must resolve to the
    # forbidden doge.application.agent.tools module.
    pkg = tmp_path / "src" / "doge" / "application" / "other"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "uses_v1.py").write_text(
        "from ..agent.tools import something\n", encoding="utf-8"
    )

    findings = validate(tmp_path)

    assert any("doge.application.agent.tools" in f.module for f in findings)


def test_scanner_ignores_the_shim_files_themselves(tmp_path: Path):
    shim = tmp_path / "src" / "doge" / "application" / "agent"
    shim.mkdir(parents=True)
    (shim / "__init__.py").write_text("", encoding="utf-8")
    # The shim file may import the canonical module; it must never be flagged.
    (shim / "tools.py").write_text(
        "from doge.application.tools import register\n", encoding="utf-8"
    )

    findings = validate(tmp_path)

    assert findings == []
