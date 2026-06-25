"""Tests that the composition root lives in the application layer."""

import inspect
from pathlib import Path

import doge.application.composition as app_comp
import doge.bootstrap as bootstrap_pkg


class TestCompositionRootLocation:
    def test_application_composition_does_not_import_infrastructure(self):
        """P1B: doge.application.composition is a thin shim with no infra imports."""
        source = Path(inspect.getfile(app_comp)).read_text(encoding="utf-8")
        assert "from doge.infrastructure" not in source
        assert "import doge.infrastructure" not in source

    def test_application_composition_factories_delegate_to_containers(self):
        """P1B: every public factory delegates through a bootstrap container helper."""
        source = Path(inspect.getfile(app_comp)).read_text(encoding="utf-8")
        # The shim must route through one of the three container collaborators,
        # not construct adapters directly.
        assert "_runtime_container" in source
        assert "_gateway_container" in source
        assert "_workspace_container" in source
        # No direct adapter instantiation remains in the compatibility shim.
        for forbidden in (
            "SQLiteSessionRepository(",
            "SQLitePlatformRepository(",
            "SQLiteEnterpriseGovernanceRepository(",
            "SQLitePortfolioRepository(",
            "LocalDocumentParser(",
            "demo_portfolio(",
            "DuckDBMarketViewRepository(",
            "DuckDBStockRepository(",
        ):
            assert forbidden not in source, f"composition shim must not construct {forbidden}"

    def test_bootstrap_exports_typed_containers(self):
        """doge.bootstrap is the new typed container entry point."""
        assert "build_app_container" in bootstrap_pkg.__all__
        container = bootstrap_pkg.build_app_container()

        assert isinstance(container.runtime, bootstrap_pkg.RuntimeContainer)
        assert isinstance(container.workspace, bootstrap_pkg.WorkspaceContainer)
        assert isinstance(container.gateway, bootstrap_pkg.GatewayContainer)

    def test_api_deps_uses_bootstrap_container(self):
        """API deps wire through the bootstrap-backed API container, not the mega facade."""
        from doge.interfaces.api import container as api_container
        from doge.interfaces.api import deps

        deps_source = Path(inspect.getfile(deps)).read_text(encoding="utf-8")
        container_source = Path(inspect.getfile(api_container)).read_text(encoding="utf-8")
        # deps reaches the container through the dedicated API container module,
        # which owns the bootstrap-backed AppContainer singleton.
        assert "from doge.interfaces.api.container" in deps_source
        assert "from doge.bootstrap import build_api_process" in container_source
        assert "process_graph = build_api_process()" in container_source
        assert "app_composition" not in deps_source
        assert "from doge import application as" not in deps_source

    def test_use_case_modules_do_not_import_infrastructure(self):
        """Use cases import only ports, services, and contracts."""
        from doge.application import use_cases

        pkg_path = Path(inspect.getfile(use_cases)).parent
        for source_path in pkg_path.glob("*.py"):
            if source_path.name == "__init__.py":
                continue
            text = source_path.read_text(encoding="utf-8")
            assert "from doge.infrastructure" not in text, (
                f"{source_path.name} must not import infrastructure"
            )
            assert "import doge.infrastructure" not in text, (
                f"{source_path.name} must not import infrastructure"
            )

    def test_contract_modules_do_not_import_infrastructure(self):
        """Contracts are pure stdlib dataclasses."""
        from doge.application import contracts

        pkg_path = Path(inspect.getfile(contracts)).parent
        for source_path in pkg_path.glob("*.py"):
            if source_path.name == "__init__.py":
                continue
            text = source_path.read_text(encoding="utf-8")
            assert "from doge.infrastructure" not in text
            assert "import doge.infrastructure" not in text
            assert "doge.core.services.composition" not in text

    def test_application_composition_exports_all_use_case_factories(self):
        """All planned use-case factories are available."""
        required = [
            "build_scan_market_use_case",
            "build_generate_macro_report_use_case",
            "build_manage_notes_use_case",
            "build_query_ticker_use_case",
            "build_generate_market_overview_use_case",
            "build_generate_anomaly_report_use_case",
            "build_catalog_use_case",
            "build_populate_stock_names_use_case",
            "build_generate_industry_report_use_case",
        ]
        for name in required:
            assert hasattr(app_comp, name), f"missing factory: {name}"

    def test_application_composition_exports_service_factories(self):
        """Service factories remain accessible from the new composition root."""
        required = [
            "build_view_service",
            "build_stock_service",
            "build_ranking_service",
            "build_breadth_service",
            "build_anomaly_service",
            "build_metadata_source",
            "build_note_repository",
            "refresh_views",
        ]
        for name in required:
            assert hasattr(app_comp, name), f"missing factory: {name}"

    def test_factories_accept_injected_ports(self):
        """Factories can be called with injected fakes (no real DB/network)."""
        from doge.core.ports.market_view import IMarketViewRepository
        from doge.core.ports.repository import IStockRepository
        import pandas as pd

        class FakeViewRepo(IMarketViewRepository):
            def execute(self, sql, params=None):
                return pd.DataFrame({"table_name": []})

        class FakeStockRepo(IStockRepository):
            def get_prices(self, ticker, market, days=20):
                return []

            def get_overview(self, ticker, market):
                return {}

            def get_sync_state(self, tickers):
                return {}

            def ensure_schema(self, market):
                pass

            def save_prices(self, market, frame):
                return 0

            def get_kline(self, ticker, market, days=120):
                return []

            def list_distinct_tickers(self, market):
                return []

        view_svc = app_comp.build_view_service(repo=FakeViewRepo())
        assert isinstance(view_svc._view, FakeViewRepo)

        stock_svc = app_comp.build_stock_service(repo=FakeStockRepo())
        assert isinstance(stock_svc._repo, FakeStockRepo)

        query_uc = app_comp.build_query_ticker_use_case(
            stock_repo=FakeStockRepo(),
            note_repo=object(),
            metadata_source=object(),
        )
        assert isinstance(query_uc._stock_repo, FakeStockRepo)
