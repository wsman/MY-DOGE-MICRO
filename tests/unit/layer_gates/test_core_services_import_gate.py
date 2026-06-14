"""Layer gate: doge.core.services must not directly import doge.infrastructure."""

import inspect
from pathlib import Path


class TestCoreServicesImportGate:
    def test_core_services_modules_do_not_import_infrastructure(self):
        """No module under doge.core.services imports doge.infrastructure directly."""
        import doge.core.services as services_pkg

        pkg_path = Path(inspect.getfile(services_pkg)).parent
        for source_path in pkg_path.rglob("*.py"):
            if source_path.name == "__init__.py":
                continue
            text = source_path.read_text(encoding="utf-8")
            assert "from doge.infrastructure" not in text, (
                f"{source_path.relative_to(pkg_path)} imports infrastructure directly"
            )
            assert "import doge.infrastructure" not in text, (
                f"{source_path.relative_to(pkg_path)} imports infrastructure directly"
            )

    def test_core_services_modules_do_not_import_legacy_surface(self):
        """Core services must not import micro/macro/ai_analysis/api/interface."""
        import doge.core.services as services_pkg

        pkg_path = Path(inspect.getfile(services_pkg)).parent
        forbidden = ["from micro", "import micro", "from macro", "import macro",
                     "from ai_analysis", "import ai_analysis",
                     "from src.api", "import src.api",
                     "from src.interface", "import src.interface"]
        for source_path in pkg_path.rglob("*.py"):
            if source_path.name == "__init__.py":
                continue
            text = source_path.read_text(encoding="utf-8")
            for pattern in forbidden:
                assert pattern not in text, (
                    f"{source_path.relative_to(pkg_path)} imports legacy surface: {pattern}"
                )

    def test_core_services_composition_is_shim_only(self):
        """The deprecated core.services.composition re-exports from application."""
        import doge.core.services.composition as legacy_comp

        source = Path(inspect.getfile(legacy_comp)).read_text(encoding="utf-8")
        assert "from doge.application.composition import" in source
        # It no longer contains direct infrastructure imports.
        assert "from doge.infrastructure" not in source
        assert "import doge.infrastructure" not in source
