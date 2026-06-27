"""Gateway factory helpers for use-case wiring."""
from __future__ import annotations
from doge.application.use_cases.generate_anomaly_report import GenerateAnomalyReportUseCase
from doge.application.use_cases.generate_catalog import GenerateCatalogUseCase
from doge.application.use_cases.generate_industry_report import GenerateIndustryReportUseCase
from doge.application.use_cases.generate_macro_report import GenerateMacroReportUseCase
from doge.application.use_cases.generate_market_overview import GenerateMarketOverviewUseCase
from doge.application.use_cases.manage_notes import ManageNotesUseCase
from doge.application.use_cases.populate_stock_names import PopulateStockNamesUseCase
from doge.application.use_cases.query_ticker import QueryTickerUseCase
from doge.application.use_cases.scan_market import ScanMarketUseCase
from doge.infrastructure.data_source.tdx_file_scanner import TDXFileScanner
from doge.bootstrap.gateway_factories.llm import build_default_text_llm_client
from doge.bootstrap.gateway_factories.market import (
    build_anomaly_service,
    build_breadth_service,
    build_metadata_source,
    build_ranking_service,
    build_stock_service,
    build_tdx_data_source,
    build_view_service,
    refresh_views,
)
from doge.bootstrap.gateway_factories.repositories import (
    build_note_repository,
    build_report_repository,
    build_schema_browser,
    build_stock_name_repository,
    build_stock_repository,
    build_view_repository,
    build_claim_repository,
    build_storage_repository,
)


def build_manage_notes_use_case(note_repo=None):
    return ManageNotesUseCase(note_repo if note_repo is not None else build_note_repository())


def build_generate_macro_report_use_case(
    view_repo=None,
    llm_client=None,
    report_repo=None,
):
    return GenerateMacroReportUseCase(
        view_repo if view_repo is not None else build_view_repository(),
        llm_client if llm_client is not None else build_default_text_llm_client(),
        report_repo if report_repo is not None else build_report_repository(),
    )


def build_generate_industry_report_use_case(
    ranking_service=None,
    llm_client=None,
    stock_service=None,
    rag_service=None,
    report_repository=None,
    claim_repository=None,
    db_path=None,
):
    from doge.application.services.citation_service import CitationService
    from doge.application.services.claim_validation_service import ClaimValidationService
    from doge.bootstrap.gateway_factories.documents import build_rag_service

    return GenerateIndustryReportUseCase(
        ranking_service if ranking_service is not None else build_ranking_service(),
        llm_client if llm_client is not None else build_default_text_llm_client(),
        stock_service=stock_service if stock_service is not None else build_stock_service(),
        rag_service=rag_service if rag_service is not None else build_rag_service(db_path, lambda: None),
        report_repository=report_repository if report_repository is not None else build_report_repository(),
        claim_repository=claim_repository if claim_repository is not None else build_claim_repository(db_path),
        citation_service=CitationService(),
        claim_validation_service=ClaimValidationService(),
    )


def build_scan_market_use_case(
    stock_repo=None,
    data_source=None,
    file_scanner=None,
    refresh_views_callable=None,
) -> ScanMarketUseCase:
    if stock_repo is None:
        stock_repo = build_storage_repository()
    if data_source is None:
        data_source = build_tdx_data_source()
    if file_scanner is None:
        file_scanner = TDXFileScanner()
    if refresh_views_callable is None:
        refresh_views_callable = refresh_views
    return ScanMarketUseCase(
        stock_repo,
        data_source=data_source,
        file_scanner=file_scanner,
        refresh_views_callable=refresh_views_callable,
    )


def build_query_ticker_use_case(stock_repo=None, note_repo=None, metadata_source=None) -> QueryTickerUseCase:
    return QueryTickerUseCase(
        stock_repo if stock_repo is not None else build_stock_repository(),
        note_repo if note_repo is not None else build_note_repository(),
        metadata_source if metadata_source is not None else build_metadata_source(),
    )


def build_generate_market_overview_use_case(
    view_repo=None,
    breadth_service=None,
    ranking_service=None,
    anomaly_service=None,
) -> GenerateMarketOverviewUseCase:
    return GenerateMarketOverviewUseCase(
        view_repo if view_repo is not None else build_view_repository(),
        breadth_service if breadth_service is not None else build_breadth_service(),
        ranking_service if ranking_service is not None else build_ranking_service(),
        anomaly_service if anomaly_service is not None else build_anomaly_service(),
    )


def build_generate_anomaly_report_use_case(
    view_repo=None,
    anomaly_service=None,
) -> GenerateAnomalyReportUseCase:
    return GenerateAnomalyReportUseCase(
        view_repo if view_repo is not None else build_view_repository(),
        anomaly_service if anomaly_service is not None else build_anomaly_service(),
    )


def build_catalog_use_case(schema_browser=None, view_service=None) -> GenerateCatalogUseCase:
    return GenerateCatalogUseCase(
        schema_browser if schema_browser is not None else build_schema_browser(),
        view_service if view_service is not None else build_view_service(),
    )


def build_populate_stock_names_use_case(
    stock_repo=None,
    name_repo=None,
    metadata_source=None,
) -> PopulateStockNamesUseCase:
    return PopulateStockNamesUseCase(
        stock_repo if stock_repo is not None else build_stock_repository(),
        name_repo if name_repo is not None else build_stock_name_repository(),
        metadata_source if metadata_source is not None else build_metadata_source(),
    )
