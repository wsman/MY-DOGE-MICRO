"""Capability discovery registry.

Tool-execution providers now live in their canonical owners
(``doge.products.*.tools``, ``doge.platform.governance.tools``). This package
retains only the capability registry; the provider re-exports were removed in
Sprint M once no package-level consumers remained.
"""

from doge.application.capabilities.registry import (  # noqa: F401
    ApiCapabilityProvider,
    FeatureCapabilityProvider,
    MaturityCapabilityProvider,
    ModelProviderCapabilityProvider,
    ToolExecutionProviderRegistry,
    ToolRegistryCapabilityProvider,
)

__all__ = [
    "ApiCapabilityProvider",
    "FeatureCapabilityProvider",
    "MaturityCapabilityProvider",
    "ModelProviderCapabilityProvider",
    "ToolExecutionProviderRegistry",
    "ToolRegistryCapabilityProvider",
]
