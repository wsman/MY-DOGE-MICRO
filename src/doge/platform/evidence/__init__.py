"""Knowledge & Evidence facade."""

from doge.application.services.citation_service import CitationService
from doge.application.services.claim_validation_service import ClaimValidationService
from doge.application.services.file_upload_service import FileUploadError, FileUploadService
from doge.application.services.financial_eval_service import FinancialEvalService
from doge.application.services.multimodal_evidence_service import (
    EvidenceBundle,
    EvidenceBundleRecord,
    MultimodalEvidenceService,
)
from doge.application.services.numerical_consistency_service import NumericalConsistencyService
from doge.application.services.page_extraction_service import (
    ChunkingService,
    ExtractionResult,
    PageExtractionService,
)
from doge.application.services.rag_service import RAGService
from doge.application.use_cases.run_summary import BuildRunSummary, redact_inaccessible_citations
from doge.core.domain.chunk_models import DocumentChunk
from doge.core.domain.claim_models import CitationRecord, ClaimRecord
from doge.core.domain.document_models import Document, DocumentStatus
from doge.core.domain.evidence_chunk_models import EvidenceChunk
from doge.core.domain.evidence_models import EvidenceRecord
from doge.core.domain.page_models import DocumentPage
from doge.core.ports.claim_repository import IClaimRepository
from doge.core.ports.document_repository import IDocumentRepository
from doge.core.ports.embedding import IEmbeddingCache, IEmbeddingProvider
from doge.core.ports.evidence_repository import IEvidenceRepository
from doge.core.ports.vector_store import IVectorStore, VectorRecord, VectorSearchResult

__all__ = [
    "BuildRunSummary",
    "ChunkingService",
    "CitationRecord",
    "CitationService",
    "ClaimRecord",
    "ClaimValidationService",
    "Document",
    "DocumentChunk",
    "DocumentPage",
    "DocumentStatus",
    "EvidenceBundle",
    "EvidenceBundleRecord",
    "EvidenceChunk",
    "EvidenceRecord",
    "ExtractionResult",
    "FileUploadError",
    "FileUploadService",
    "FinancialEvalService",
    "IClaimRepository",
    "IDocumentRepository",
    "IEmbeddingCache",
    "IEmbeddingProvider",
    "IEvidenceRepository",
    "IVectorStore",
    "MultimodalEvidenceService",
    "NumericalConsistencyService",
    "PageExtractionService",
    "RAGService",
    "VectorRecord",
    "VectorSearchResult",
    "redact_inaccessible_citations",
]
