"""Layer gate: doge.interfaces.api must not import legacy or database drivers.

These gates protect the API interface layer while Sprint 007 migrates the
legacy ``src/api/`` surface onto ``doge.interfaces.api``. They are intentionally
narrower than the final S007-008 gates: macro/scan routers may still reference
legacy ``src.macro`` / ``src.micro`` modules because those stories (S007-005/006)
will migrate them onto application use cases. The gates here only block the
forbidden patterns that S007-002 explicitly addresses:

- direct ``sqlite3`` / ``duckdb`` imports in routers
- importing the old ``src.api`` surface from the new canonical surface
- importing the deprecated ``doge.core.services.composition`` directly
"""

import inspect
from pathlib import Path


class TestApiLayerGate:
    def test_api_routers_do_not_import_sqlite3_or_duckdb(self):
        """Interface routers must not open database connections directly."""
        import doge.interfaces.api.routers as routers_pkg

        pkg_path = Path(inspect.getfile(routers_pkg)).parent
        forbidden = [
            "import sqlite3",
            "from sqlite3",
            "import duckdb",
            "from duckdb",
        ]
        for source_path in pkg_path.rglob("*.py"):
            if source_path.name == "__init__.py":
                continue
            text = source_path.read_text(encoding="utf-8")
            for pattern in forbidden:
                assert pattern not in text, (
                    f"{source_path.relative_to(pkg_path)} imports DB driver directly: {pattern}"
                )

    def test_api_routers_do_not_import_deprecated_core_services_composition(self):
        """Routers must use doge.application.composition, not the deprecated shim."""
        import doge.interfaces.api.routers as routers_pkg

        pkg_path = Path(inspect.getfile(routers_pkg)).parent
        forbidden = [
            "from doge.core.services.composition",
            "import doge.core.services.composition",
        ]
        for source_path in pkg_path.rglob("*.py"):
            if source_path.name == "__init__.py":
                continue
            text = source_path.read_text(encoding="utf-8")
            for pattern in forbidden:
                assert pattern not in text, (
                    f"{source_path.relative_to(pkg_path)} imports deprecated composition: {pattern}"
                )

    def test_api_package_does_not_import_src_api(self):
        """The new canonical surface must not depend on the legacy src.api shim."""
        import doge.interfaces.api as api_pkg

        pkg_path = Path(inspect.getfile(api_pkg)).parent
        forbidden = ["from src.api", "import src.api"]
        for source_path in pkg_path.rglob("*.py"):
            text = source_path.read_text(encoding="utf-8")
            for pattern in forbidden:
                assert pattern not in text, (
                    f"{source_path.relative_to(pkg_path)} imports legacy src.api: {pattern}"
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
