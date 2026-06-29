"""Layer gate: doge.interfaces.api must not import legacy or database drivers.

These gates protect the API interface layer while Sprint 007 migrates the
legacy ``src/api/`` surface onto ``doge.interfaces.api``. The gates here block
the forbidden patterns that S007-002 explicitly addresses:

- direct ``sqlite3`` / ``duckdb`` imports in routers
- importing the old ``src.api`` surface from the new canonical surface
- importing the deprecated ``doge.core.services.composition`` directly
"""

import inspect
from pathlib import Path


def _router_package_paths() -> tuple[Path, ...]:
    import doge.interfaces.api.routers as api_routers
    import doge.interfaces.api_legacy.routers as legacy_routers
    import doge.interfaces.gateway.routers as gateway_routers

    return (
        Path(inspect.getfile(api_routers)).parent,
        Path(inspect.getfile(legacy_routers)).parent,
        Path(inspect.getfile(gateway_routers)).parent,
    )


class TestApiLayerGate:
    def test_api_routers_do_not_import_sqlite3_or_duckdb(self):
        """Interface routers must not open database connections directly."""
        forbidden = [
            "import sqlite3",
            "from sqlite3",
            "import duckdb",
            "from duckdb",
        ]
        for pkg_path in _router_package_paths():
            for source_path in pkg_path.rglob("*.py"):
                if source_path.name == "__init__.py":
                    continue
                text = source_path.read_text(encoding="utf-8")
                for pattern in forbidden:
                    assert pattern not in text, (
                        f"{source_path.relative_to(pkg_path)} imports DB driver directly: {pattern}"
                    )

    def test_api_routers_do_not_import_deprecated_core_services_composition(self):
        """Routers must use deps/bootstrap seams, not the deprecated shim."""
        forbidden = [
            "from doge.core.services.composition",
            "import doge.core.services.composition",
        ]
        for pkg_path in _router_package_paths():
            for source_path in pkg_path.rglob("*.py"):
                if source_path.name == "__init__.py":
                    continue
                text = source_path.read_text(encoding="utf-8")
                for pattern in forbidden:
                    assert pattern not in text, (
                        f"{source_path.relative_to(pkg_path)} imports deprecated composition: {pattern}"
                    )

    def test_canonical_surfaces_do_not_import_src_api(self):
        """Canonical packages must not depend on the deprecated src.api shim."""
        import doge.interfaces.api as api_pkg
        import doge.interfaces.api_legacy as api_legacy_pkg
        import doge.interfaces.gateway as gateway_pkg
        import doge.application as app_pkg
        import doge.infrastructure as infra_pkg

        legacy_api = "src.api"
        forbidden = [f"from {legacy_api}", f"import {legacy_api}"]
        for pkg in (api_pkg, api_legacy_pkg, gateway_pkg, app_pkg, infra_pkg):
            pkg_path = Path(inspect.getfile(pkg)).parent
            for source_path in pkg_path.rglob("*.py"):
                text = source_path.read_text(encoding="utf-8")
                for pattern in forbidden:
                    assert pattern not in text, (
                        f"{source_path} imports deprecated {legacy_api}: {pattern}"
                    )

    def test_api_deps_is_the_only_infra_import_site(self):
        """Only deps.py may import infrastructure adapters in the API package."""
        import doge.interfaces.api as api_pkg

        pkg_path = Path(inspect.getfile(api_pkg)).parent
        for source_path in pkg_path.rglob("*.py"):
            if source_path.name == "deps.py":
                continue
            text = source_path.read_text(encoding="utf-8")
            assert "from doge.infrastructure" not in text, (
                f"{source_path.relative_to(pkg_path)} imports infrastructure directly"
            )
            assert "import doge.infrastructure" not in text, (
                f"{source_path.relative_to(pkg_path)} imports infrastructure directly"
            )
