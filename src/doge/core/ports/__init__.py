"""Core port exports."""

from doge.core.ports.agent_backend import IAgentBackend
from doge.core.ports.agent_model import AgentContentPart, AgentMessage, AgentResponse, IAgentModel
from doge.core.ports.agent_repository import (
    IApprovalRepository,
    IArtifactRepository,
    IEventRepository,
    IRunRepository,
    ISessionRepository,
)
from doge.core.ports.document_repository import IDocumentRepository
from doge.core.ports.embedding import IEmbeddingCache, IEmbeddingProvider
from doge.core.ports.enterprise_auth import (
    AuthenticatedPrincipal,
    EnterpriseAuthError,
    IEnterpriseAuthProvider,
)
from doge.core.ports.enterprise_governance import (
    ApprovalActorDecision,
    EnterpriseAclGrant,
    EnterpriseAuditEvent,
    IEnterpriseGovernanceRepository,
)
from doge.core.ports.evidence_repository import IEvidenceRepository
from doge.core.ports.financial_connectors import (
    ICompanyAnnouncementRepository,
    IConsensusEstimateRepository,
    IFinancialStatementRepository,
    IIndustryClassificationSource,
    IRiskFactorSource,
)
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.cache import ITickerNameCache
from doge.core.ports.capability_provider import ICapabilityProvider
from doge.core.ports.claim_repository import IClaimRepository
from doge.core.ports.data_source import IMarketDataSource
from doge.core.ports.event_publisher import IEventPublisher
from doge.core.ports.file_scanner import ITdxFileScanner
from doge.core.ports.idempotency_store import IIdempotencyStore
from doge.core.ports.llm import ILLMClient
from doge.core.ports.market_view import IMarketViewRepository
from doge.core.ports.metadata import ITickerMetadataSource
from doge.core.ports.model_router import IModelRouter, RoutingDecision
from doge.core.ports.model_gateway import IEnterpriseModelGateway
from doge.core.ports.platform_repository import IPlatformRepository
from doge.core.ports.portfolio_repository import IPortfolioRepository
from doge.core.ports.tdx_server_list import ITDXServerList, TDXServer
from doge.core.ports.tool_entitlement import IToolEntitlementChecker
from doge.core.ports.repository import (
    INoteRepository,
    IReportRepository,
    ISchemaBrowser,
    IStockNameRepository,
    IStockRepository,
    StorageWriteError,
)
from doge.core.ports.secrets import ISecretProvider
from doge.core.ports.unit_of_work import IAgentUnitOfWork
from doge.core.ports.worker_queue import IRunQueue
from doge.core.ports.vector_store import IVectorStore, VectorRecord, VectorSearchResult

__all__ = [
    "AgentMessage",
    "AgentContentPart",
    "AgentResponse",
    "IAgentBackend",
    "IAgentModel",
    "IAgentUnitOfWork",
    "IApprovalRepository",
    "IArtifactRepository",
    "ICapabilityProvider",
    "IClaimRepository",
    "ICompanyAnnouncementRepository",
    "IConsensusEstimateRepository",
    "IDocumentRepository",
    "IEvidenceRepository",
    "IEmbeddingCache",
    "IEmbeddingProvider",
    "IFinancialStatementRepository",
    "AuthenticatedPrincipal",
    "EnterpriseAuthError",
    "ApprovalActorDecision",
    "EnterpriseAclGrant",
    "EnterpriseAuditEvent",
    "IEnterpriseAuthProvider",
    "IEnterpriseGovernanceRepository",
    "IEventPublisher",
    "IEventRepository",
    "IIdempotencyStore",
    "ILLMClient",
    "IMarketDataSource",
    "IMarketViewRepository",
    "IIndustryClassificationSource",
    "IModelRouter",
    "IEnterpriseModelGateway",
    "INoteRepository",
    "IPlatformRepository",
    "IPortfolioRepository",
    "IReportRepository",
    "IResearchAgentRuntime",
    "IRunQueue",
    "IRunRepository",
    "IRiskFactorSource",
    "ISecretProvider",
    "ISchemaBrowser",
    "ISessionRepository",
    "IStockNameRepository",
    "IStockRepository",
    "ITdxFileScanner",
    "ITDXServerList",
    "IToolEntitlementChecker",
    "ITickerMetadataSource",
    "ITickerNameCache",
    "IVectorStore",
    "VectorRecord",
    "VectorSearchResult",
    "RoutingDecision",
    "TDXServer",
    "StorageWriteError",
]
