"""Gateway/API bootstrap container."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from doge.bootstrap.gateway_factories import documents
from doge.bootstrap.gateway_factories import llm
from doge.bootstrap.gateway_factories import market
from doge.bootstrap.gateway_factories import repositories
from doge.bootstrap.gateway_factories import secrets
from doge.bootstrap.gateway_factories import tools
from doge.bootstrap.gateway_factories import use_cases


@dataclass(frozen=True)
class GatewayContainer:
    """Typed entry point for interface gateway wiring."""

    db_path: Path | str | None = None
    graph_provider: Callable[[], Any] | None = field(default=None, repr=False, compare=False)

    # -- Secrets --
    def build_secret_provider(self): return secrets.build_secret_provider()

    # -- LLM --
    def build_kimi_agent_model(self, secret_provider=None): return llm.build_kimi_agent_model(secret_provider)
    def build_default_text_llm_client(self): return llm.build_default_text_llm_client()

    # -- Repositories --
    def build_report_repository(self): return repositories.build_report_repository()
    def build_schema_browser(self): return repositories.build_schema_browser()
    def build_stock_repository(self): return repositories.build_stock_repository()
    def build_note_repository(self): return repositories.build_note_repository()
    def build_stock_name_repository(self): return repositories.build_stock_name_repository()
    def build_view_repository(self, *, read_only: bool = True): return repositories.build_view_repository(read_only=read_only)
    def build_claim_repository(self): return repositories.build_claim_repository(self.db_path)
    def build_storage_repository(self): return repositories.build_storage_repository()

    # -- Market services --
    def build_view_service(self, repo=None): return market.build_view_service(repo)
    def build_stock_service(self, repo=None): return market.build_stock_service(repo)
    def build_ranking_service(self, repo=None): return market.build_ranking_service(repo)
    def build_breadth_service(self, repo=None): return market.build_breadth_service(repo)
    def build_anomaly_service(self, repo=None): return market.build_anomaly_service(repo)
    def build_metadata_source(self, max_retries: int | None = None, retry_delay: float | None = None): return market.build_metadata_source(max_retries, retry_delay)
    def build_tdx_server_list(self): return market.build_tdx_server_list()
    def build_tdx_data_source(self, preferred_server: str | None = None): return market.build_tdx_data_source(preferred_server)
    def refresh_views(self) -> None: market.refresh_views()

    # -- Documents / RAG --
    def build_rag_service(self): return documents.build_rag_service(self.db_path, self.runtime_container)
    def build_file_upload_service(self, *, kimi_files_client=None): return documents.build_file_upload_service(self.db_path, self.runtime_container, kimi_files_client=kimi_files_client)
    def build_page_extraction_service(self): return documents.build_page_extraction_service(self.runtime_container)

    # -- Use cases --
    def build_manage_notes_use_case(self, note_repo=None): return use_cases.build_manage_notes_use_case(note_repo)
    def build_generate_macro_report_use_case(self, view_repo=None, llm_client=None, report_repo=None): return use_cases.build_generate_macro_report_use_case(view_repo, llm_client, report_repo)
    def build_generate_industry_report_use_case(self, ranking_service=None, llm_client=None, stock_service=None, rag_service=None, report_repository=None, claim_repository=None):
        return use_cases.build_generate_industry_report_use_case(ranking_service, llm_client, stock_service=stock_service, rag_service=rag_service, report_repository=report_repository, claim_repository=claim_repository, db_path=self.db_path)
    def build_scan_market_use_case(self, stock_repo=None, data_source=None, file_scanner=None, refresh_views_callable=None): return use_cases.build_scan_market_use_case(stock_repo, data_source, file_scanner, refresh_views_callable)
    def build_query_ticker_use_case(self, stock_repo=None, note_repo=None, metadata_source=None): return use_cases.build_query_ticker_use_case(stock_repo, note_repo, metadata_source)
    def build_generate_market_overview_use_case(self, view_repo=None, breadth_service=None, ranking_service=None, anomaly_service=None): return use_cases.build_generate_market_overview_use_case(view_repo, breadth_service, ranking_service, anomaly_service)
    def build_generate_anomaly_report_use_case(self, view_repo=None, anomaly_service=None): return use_cases.build_generate_anomaly_report_use_case(view_repo, anomaly_service)
    def build_catalog_use_case(self, schema_browser=None, view_service=None): return use_cases.build_catalog_use_case(schema_browser, view_service)
    def build_populate_stock_names_use_case(self, stock_repo=None, name_repo=None, metadata_source=None): return use_cases.build_populate_stock_names_use_case(stock_repo, name_repo, metadata_source)

    # -- Tools / Product services --
    def build_risk_factor_source(self): return tools.build_risk_factor_source()
    def build_industry_classification_source(self): return tools.build_industry_classification_source()
    def build_portfolio_service(self): return tools.build_portfolio_service(self.workspace_container)
    def build_risk_service(self): return tools.build_risk_service(self.workspace_container)
    def build_scenario_service(self): return tools.build_scenario_service(self.workspace_container)
    def build_financial_statement_repository(self): return tools.build_financial_statement_repository(self.build_stock_service())
    def build_company_announcement_repository(self): return tools.build_company_announcement_repository(self.build_note_repository())
    def build_consensus_estimate_repository(self): return tools.build_consensus_estimate_repository()
    def build_python_analysis_executor(self, settings=None): return tools.build_python_analysis_executor(settings)
    def build_slot_runtime_executor(self, settings=None):
        from doge.bootstrap.runtime_factories.slots import build_slot_runtime_executor
        return build_slot_runtime_executor(settings)
    def build_tool_application_service(self): return tools.build_tool_application_service(self.db_path, self.runtime_container, self.workspace_container, documents.build_rag_service, use_cases.build_generate_industry_report_use_case)

    # -- Process graph collaborators --
    def runtime_container(self): return self._process_graph().runtime_container
    def workspace_container(self): return self._process_graph().workspace_container
    def _process_graph(self):
        if self.graph_provider is not None: return self.graph_provider()
        from doge.bootstrap.processes import build_embedded_process
        return build_embedded_process(db_path=self.db_path)


def build_gateway_container(db_path: Path | str | None = None) -> GatewayContainer:
    """Build the gateway container."""
    from doge.bootstrap.processes import build_embedded_process
    return build_embedded_process(db_path=db_path).gateway_container
