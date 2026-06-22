"""Capability discovery providers."""

from doge.application.capabilities.compliance_provider import ComplianceToolProvider
from doge.application.capabilities.fundamental_provider import FundamentalToolProvider
from doge.application.capabilities.market_provider import MarketToolProvider
from doge.application.capabilities.portfolio_provider import PortfolioToolProvider
from doge.application.capabilities.publishing_provider import PublishingToolProvider
from doge.application.capabilities.quant_provider import QuantToolProvider
from doge.application.capabilities.registry import (
    ApiCapabilityProvider,
    FeatureCapabilityProvider,
    MaturityCapabilityProvider,
    ModelProviderCapabilityProvider,
    ToolExecutionProviderRegistry,
    ToolRegistryCapabilityProvider,
)
from doge.application.capabilities.research_provider import ResearchToolProvider

__all__ = [
    "ApiCapabilityProvider",
    "ComplianceToolProvider",
    "FeatureCapabilityProvider",
    "FundamentalToolProvider",
    "MarketToolProvider",
    "MaturityCapabilityProvider",
    "ModelProviderCapabilityProvider",
    "PortfolioToolProvider",
    "PublishingToolProvider",
    "QuantToolProvider",
    "ResearchToolProvider",
    "ToolExecutionProviderRegistry",
    "ToolRegistryCapabilityProvider",
]
