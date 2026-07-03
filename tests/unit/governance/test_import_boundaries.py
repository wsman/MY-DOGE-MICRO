"""Governance test for production import boundaries (K-1).

Asserts that no production code under ``src/doge/`` imports retired
compatibility or demo-only paths outside the explicit allowlist. The clean tree
has a zero baseline, so any new offender fails immediately.
"""

from pathlib import Path

from scripts.validate_import_boundaries import validate


def test_clean_repo_has_no_production_shim_importers():
    findings = validate()
    assert findings == [], (
        "production code under src/doge/ must not import retired compatibility/demo paths; "
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


def test_scanner_flags_a_forbidden_api_legacy_import(tmp_path: Path):
    pkg = tmp_path / "src" / "doge" / "offending"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "uses_legacy.py").write_text(
        "import doge.interfaces.api_legacy\n", encoding="utf-8"
    )

    findings = validate(tmp_path)

    assert any("doge.interfaces.api_legacy" in f.module for f in findings)


def test_scanner_flags_a_forbidden_inmemory_runtime_import(tmp_path: Path):
    pkg = tmp_path / "src" / "doge" / "offending"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "uses_inmemory.py").write_text(
        "from doge.infrastructure.agent.inmemory_runtime import "
        "InMemoryResearchAgentRuntime\n",
        encoding="utf-8",
    )

    findings = validate(tmp_path)

    assert any("doge.infrastructure.agent.inmemory_runtime" in f.module for f in findings)


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


def test_scanner_ignores_legacy_route_mounting_allowlist(tmp_path: Path):
    pkg = tmp_path / "src" / "doge" / "interfaces" / "api"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "routes.py").write_text(
        "from doge.interfaces.api_legacy.routers import scan\n", encoding="utf-8"
    )

    findings = validate(tmp_path)

    assert findings == []


def test_scanner_ignores_api_router_shim_allowlist(tmp_path: Path):
    pkg = tmp_path / "src" / "doge" / "interfaces" / "api" / "routers"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "scan.py").write_text(
        "from doge.interfaces.api_legacy.routers.scan import *\n", encoding="utf-8"
    )

    findings = validate(tmp_path)

    assert findings == []


def test_scanner_ignores_api_legacy_itself(tmp_path: Path):
    pkg = tmp_path / "src" / "doge" / "interfaces" / "api_legacy" / "routers"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "from doge.interfaces.api_legacy.routers import scan\n", encoding="utf-8"
    )
    (pkg / "scan.py").write_text("router = object()\n", encoding="utf-8")

    findings = validate(tmp_path)

    assert findings == []


def test_scanner_ignores_demo_fallback_factory_allowlist(tmp_path: Path):
    pkg = tmp_path / "src" / "doge" / "bootstrap" / "runtime_factories"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "runtime_kernel.py").write_text(
        "from doge.infrastructure.agent.inmemory_runtime import "
        "InMemoryResearchAgentRuntime\n",
        encoding="utf-8",
    )

    findings = validate(tmp_path)

    assert findings == []


def test_scanner_flags_a_gateway_router_importing_infrastructure(tmp_path: Path):
    # Location-scoped rule: gateway routers must not import adapters/infrastructure
    # directly; they route through the sanctioned wiring seam at interfaces/api/deps.
    pkg = tmp_path / "src" / "doge" / "interfaces" / "gateway" / "routers"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "bad.py").write_text(
        "from doge.infrastructure.llm.scripted_agent_model import ScriptedAgentModel\n",
        encoding="utf-8",
    )

    findings = validate(tmp_path)

    assert any(
        "doge.infrastructure" in f.module and "gateway" in f.format() for f in findings
    )


def test_scanner_does_not_flag_non_gateway_infrastructure_import(tmp_path: Path):
    # The location-scoped rule targets gateway routers only; a non-gateway file
    # importing infrastructure is not flagged by this rule.
    pkg = tmp_path / "src" / "doge" / "offending"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "uses_infra.py").write_text(
        "from doge.infrastructure.llm.scripted_agent_model import ScriptedAgentModel\n",
        encoding="utf-8",
    )

    findings = validate(tmp_path)

    assert not any("doge.infrastructure" in f.module for f in findings)
