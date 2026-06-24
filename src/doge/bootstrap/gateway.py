"""Gateway/API bootstrap container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from doge.application.services.file_upload_service import FileUploadService
from doge.application.services.page_extraction_service import PageExtractionService
from doge.application.services.citation_service import CitationService
from doge.application.services.claim_validation_service import ClaimValidationService
from doge.application.services.rag_service import RAGService
from doge.application.use_cases.generate_industry_report import GenerateIndustryReportUseCase
from doge.application.use_cases.generate_macro_report import GenerateMacroReportUseCase
from doge.application.use_cases.manage_notes import ManageNotesUseCase
from doge.application.use_cases.scan_market import ScanMarketUseCase
from doge.bootstrap.runtime import RuntimeContainer
from doge.config import get_settings
from doge.core.services.anomaly_service import AnomalyService
from doge.core.services.breadth_service import BreadthService
from doge.core.services.ranking_service import RankingService
from doge.core.services.stock_service import StockService
from doge.core.services.view_service import ViewService
from doge.infrastructure.database.market_view_repository import DuckDBMarketViewRepository
from doge.infrastructure.database.repositories import (
    DuckDBStockRepository,
    SQLiteNoteRepository,
    SQLiteReportRepository,
    SQLiteSchemaBrowser,
    SQLiteStockNameRepository,
)
from doge.infrastructure.database.claim_repository import SQLiteClaimRepository
from doge.infrastructure.database.embedding_cache import SQLiteEmbeddingCache
from doge.infrastructure.database.sqlite_storage import SQLiteStorageRepository
from doge.infrastructure.data_source.tdx_file_scanner import TDXFileScanner
from doge.infrastructure.data_source.tdx_server_list import ConfigTDXServerList
from doge.infrastructure.data_source.yfinance_metadata import YFinanceMetadataSource
from doge.infrastructure.documents.local_parser import LocalDocumentParser
from doge.infrastructure.llm.deepseek_client import DeepSeekClient
from doge.infrastructure.llm.embedding_client import HashingEmbeddingProvider
from doge.infrastructure.llm.kimi_client import KimiAgentModel
from doge.infrastructure.llm.kimi_files_client import KimiFilesClient
from doge.infrastructure.llm.kimi_text_client import KimiTextClient
from doge.infrastructure.secrets import EnvSecretProvider, ProcessSecretProvider
from doge.infrastructure.vector.sqlite_store import SQLiteVectorStore


@dataclass(frozen=True)
class GatewayContainer:
    """Typed entry point for interface gateway wiring."""

    db_path: Path | str | None = None

    def build_secret_provider(self):
        settings = get_settings()
        provider = settings.secrets.provider
        if provider == "env":
            return EnvSecretProvider()
        if provider == "process":
            return ProcessSecretProvider(
                command=settings.secrets.process_command,
                timeout_seconds=settings.secrets.process_timeout_seconds,
                allowed_names=frozenset(settings.secrets.allowed_names),
            )
        raise ValueError(f"Unsupported DOGE_SECRET_PROVIDER: {provider}")

    def build_kimi_agent_model(self, secret_provider=None):
        return KimiAgentModel(secret_provider=secret_provider or self.build_secret_provider())

    def build_default_text_llm_client(self):
        settings = get_settings()
        secret_provider = self.build_secret_provider()
        if settings.llm.text_provider.lower() == "deepseek":
            return DeepSeekClient(secret_provider=secret_provider)
        return KimiTextClient(KimiAgentModel(secret_provider=secret_provider))

    def build_report_repository(self):
        return SQLiteReportRepository()

    def build_schema_browser(self):
        return SQLiteSchemaBrowser()

    def build_stock_repository(self):
        return DuckDBStockRepository()

    def build_note_repository(self):
        return SQLiteNoteRepository()

    def build_stock_name_repository(self):
        return SQLiteStockNameRepository()

    def build_view_repository(self, *, read_only: bool = True):
        return DuckDBMarketViewRepository(read_only=read_only)

    def build_view_service(self, repo=None):
        return ViewService(repo if repo is not None else self.build_view_repository())

    def build_stock_service(self, repo=None):
        return StockService(repo if repo is not None else self.build_stock_repository())

    def build_ranking_service(self, repo=None):
        return RankingService(repo if repo is not None else self.build_view_repository())

    def build_breadth_service(self, repo=None):
        return BreadthService(repo if repo is not None else self.build_view_repository())

    def build_anomaly_service(self, repo=None):
        return AnomalyService(repo if repo is not None else self.build_view_repository())

    def build_manage_notes_use_case(self, note_repo=None):
        return ManageNotesUseCase(note_repo if note_repo is not None else self.build_note_repository())

    def build_generate_macro_report_use_case(
        self,
        view_repo=None,
        llm_client=None,
        report_repo=None,
    ):
        return GenerateMacroReportUseCase(
            view_repo if view_repo is not None else self.build_view_repository(),
            llm_client if llm_client is not None else self.build_default_text_llm_client(),
            report_repo if report_repo is not None else self.build_report_repository(),
        )

    def build_rag_service(self):
        runtime = RuntimeContainer(self.db_path)
        return RAGService(
            evidence_repository=runtime.build_agent_evidence_repository(),
            embedding_provider=HashingEmbeddingProvider(),
            vector_store=SQLiteVectorStore(self.db_path),
            embedding_cache=SQLiteEmbeddingCache(self.db_path),
        )

    def build_claim_repository(self):
        return SQLiteClaimRepository(self.db_path)

    def build_generate_industry_report_use_case(
        self,
        ranking_service=None,
        llm_client=None,
        stock_service=None,
        rag_service=None,
        report_repository=None,
        claim_repository=None,
    ):
        return GenerateIndustryReportUseCase(
            ranking_service if ranking_service is not None else self.build_ranking_service(),
            llm_client if llm_client is not None else self.build_default_text_llm_client(),
            stock_service=stock_service if stock_service is not None else self.build_stock_service(),
            rag_service=rag_service if rag_service is not None else self.build_rag_service(),
            report_repository=report_repository if report_repository is not None else self.build_report_repository(),
            claim_repository=claim_repository if claim_repository is not None else self.build_claim_repository(),
            citation_service=CitationService(),
            claim_validation_service=ClaimValidationService(),
        )

    def build_metadata_source(self, max_retries: int | None = None, retry_delay: float | None = None):
        return YFinanceMetadataSource(max_retries=max_retries, retry_delay=retry_delay)

    def build_storage_repository(self):
        return SQLiteStorageRepository()

    def build_tdx_server_list(self):
        return ConfigTDXServerList()

    def build_tdx_data_source(self, preferred_server: str | None = None):
        from doge.infrastructure.data_source.tdx import TDXDataSource

        return TDXDataSource(preferred_server=preferred_server)

    def build_scan_market_use_case(
        self,
        stock_repo=None,
        data_source=None,
        file_scanner=None,
        refresh_views_callable=None,
    ) -> ScanMarketUseCase:
        if stock_repo is None:
            stock_repo = self.build_storage_repository()
        if data_source is None:
            data_source = self.build_tdx_data_source()
        if file_scanner is None:
            file_scanner = TDXFileScanner()
        if refresh_views_callable is None:
            refresh_views_callable = self.refresh_views
        return ScanMarketUseCase(
            stock_repo,
            data_source=data_source,
            file_scanner=file_scanner,
            refresh_views_callable=refresh_views_callable,
        )

    def refresh_views(self) -> None:
        from doge.infrastructure.database.duckdb import DuckDBConnection

        DuckDBConnection(read_only=False).refresh_views()

    def build_file_upload_service(self, *, kimi_files_client=None):
        settings = get_settings()
        secret_provider = self.build_secret_provider()
        if kimi_files_client is None and secret_provider.get_secret("kimi.api_key"):
            kimi_files_client = KimiFilesClient(secret_provider=secret_provider)
        runtime = RuntimeContainer(self.db_path)
        return FileUploadService(
            runtime.build_agent_document_repository(),
            storage_dir=settings.documents.storage_dir,
            max_file_bytes=settings.documents.max_file_bytes,
            parser=LocalDocumentParser(),
            kimi_files_client=kimi_files_client,
            extraction_service=PageExtractionService(
                evidence_repository=runtime.build_agent_evidence_repository(),
                parser=LocalDocumentParser(),
            ),
        )


def build_gateway_container(db_path: Path | str | None = None) -> GatewayContainer:
    """Build the gateway container."""

    return GatewayContainer(db_path=db_path)
