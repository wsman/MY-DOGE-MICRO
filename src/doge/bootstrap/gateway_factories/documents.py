"""Gateway factory helpers for document/RAG services."""
from __future__ import annotations
from doge.application.services.citation_service import CitationService
from doge.application.services.claim_validation_service import ClaimValidationService
from doge.application.services.file_upload_service import FileUploadService
from doge.application.services.page_extraction_service import PageExtractionService
from doge.application.services.rag_service import RAGService
from doge.infrastructure.database.embedding_cache import SQLiteEmbeddingCache
from doge.infrastructure.documents.local_parser import LocalDocumentParser
from doge.infrastructure.llm.embedding_client import HashingEmbeddingProvider
from doge.infrastructure.llm.kimi_files_client import KimiFilesClient
from doge.infrastructure.vector.sqlite_store import SQLiteVectorStore
from doge.config import get_settings
from doge.bootstrap.gateway_factories.secrets import build_secret_provider


def build_rag_service(db_path, runtime_container_fn):
    runtime = runtime_container_fn()
    return RAGService(
        evidence_repository=runtime.build_agent_evidence_repository(),
        embedding_provider=HashingEmbeddingProvider(),
        vector_store=SQLiteVectorStore(db_path),
        embedding_cache=SQLiteEmbeddingCache(db_path),
    )


def build_claim_repository(db_path):
    from doge.infrastructure.database.claim_repository import SQLiteClaimRepository

    return SQLiteClaimRepository(db_path)


def build_file_upload_service(db_path, runtime_container_fn, *, kimi_files_client=None):
    settings = get_settings()
    secret_provider = build_secret_provider()
    if kimi_files_client is None and secret_provider.get_secret("kimi.api_key"):
        kimi_files_client = KimiFilesClient(secret_provider=secret_provider)
    runtime = runtime_container_fn()
    parser = _build_document_parser(settings)
    return FileUploadService(
        runtime.build_agent_document_repository(),
        storage_dir=settings.documents.storage_dir,
        max_file_bytes=settings.documents.max_file_bytes,
        parser=parser,
        kimi_files_client=kimi_files_client,
        extraction_service=PageExtractionService(
            evidence_repository=runtime.build_agent_evidence_repository(),
            parser=parser,
        ),
    )


def build_page_extraction_service(runtime_container_fn):
    settings = get_settings()
    runtime = runtime_container_fn()
    return PageExtractionService(
        evidence_repository=runtime.build_agent_evidence_repository(),
        parser=_build_document_parser(settings),
    )


def _build_document_parser(settings):
    if settings.features.slot_platform:
        from doge.bootstrap.runtime_factories.slots import build_slot_aware_document_parser

        parser = build_slot_aware_document_parser(settings=settings)
        if parser is not None:
            return parser
    return LocalDocumentParser()
