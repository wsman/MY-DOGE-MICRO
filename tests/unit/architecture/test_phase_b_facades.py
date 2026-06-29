"""Phase B facade compatibility tests.

These tests lock the ADR-0022 facade-first migration: new bounded-context import
paths resolve to the current implementation objects while old paths stay valid.
"""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_runtime_facade_exports_current_runtime_symbols() -> None:
    from doge.application.agent.runtime_kernel import RuntimeKernel as OldRuntimeKernel
    from doge.application.agent.tool_service import ToolApplicationService as OldToolApplicationService
    from doge.application.agent.tools import ToolRegistry as OldToolRegistry
    from doge.platform.runtime import RuntimeKernel, ToolApplicationService, ToolRegistry

    assert RuntimeKernel is OldRuntimeKernel
    assert ToolApplicationService is OldToolApplicationService
    assert ToolRegistry is OldToolRegistry


def test_workspace_facade_exports_current_platform_symbols() -> None:
    from doge.core.domain.platform_models import ResearchCase as OldResearchCase
    from doge.core.domain.platform_models import WorkflowTemplate as OldWorkflowTemplate
    from doge.core.domain.platform_models import Workspace as OldWorkspace
    from doge.platform.workspace import ResearchCase, WorkflowTemplate, Workspace

    assert Workspace is OldWorkspace
    assert ResearchCase is OldResearchCase
    assert WorkflowTemplate is OldWorkflowTemplate


def test_evidence_facade_exports_current_evidence_symbols() -> None:
    from doge.application.services.citation_service import CitationService as OldCitationService
    from doge.application.use_cases.run_summary import BuildRunSummary as OldBuildRunSummary
    from doge.core.domain.claim_models import CitationRecord as OldCitationRecord
    from doge.platform.evidence import BuildRunSummary, CitationRecord, CitationService

    assert CitationService is OldCitationService
    assert BuildRunSummary is OldBuildRunSummary
    assert CitationRecord is OldCitationRecord


def test_governance_facade_exports_current_policy_symbols() -> None:
    from doge.application.use_cases.capability_registry import BuildCapabilityRegistry as OldBuildCapabilityRegistry
    from doge.core.ports.enterprise_governance import EnterpriseAuditEvent as OldEnterpriseAuditEvent
    from doge.core.ports.secrets import ISecretProvider as OldISecretProvider
    from doge.platform.governance import EnterpriseAuditEvent, ISecretProvider
    from doge.platform.workspace import BuildCapabilityRegistry

    assert BuildCapabilityRegistry is OldBuildCapabilityRegistry
    assert EnterpriseAuditEvent is OldEnterpriseAuditEvent
    assert ISecretProvider is OldISecretProvider


def test_product_facades_export_current_product_symbols() -> None:
    from doge.application.capabilities.market_provider import MarketToolProvider as OldMarketToolProvider
    from doge.application.capabilities.portfolio_provider import PortfolioToolProvider as OldPortfolioToolProvider
    from doge.application.capabilities.quant_provider import QuantToolProvider as OldQuantToolProvider
    from doge.application.capabilities.research_provider import ResearchToolProvider as OldResearchToolProvider
    from doge.application.services.portfolio_service import PortfolioService as OldPortfolioService
    from doge.core.services.stock_service import StockService as OldStockService
    from doge.products.market import MarketToolProvider, StockService
    from doge.products.portfolio import PortfolioService, PortfolioToolProvider
    from doge.products.quant import QuantToolProvider
    from doge.products.research import ResearchToolProvider

    assert MarketToolProvider is OldMarketToolProvider
    assert StockService is OldStockService
    assert PortfolioService is OldPortfolioService
    assert PortfolioToolProvider is OldPortfolioToolProvider
    assert QuantToolProvider is OldQuantToolProvider
    assert ResearchToolProvider is OldResearchToolProvider


def test_phase_b_package_markers_import_cleanly() -> None:
    import doge.adapters
    import doge.bootstrap
    import doge.entrypoints
    import doge.platform
    import doge.products
    import doge.shared

    assert doge.adapters.__all__ == []
    assert {
        "AppContainer",
        "GatewayContainer",
        "ProcessGraph",
        "RuntimeContainer",
        "WorkspaceContainer",
        "build_api_process",
        "build_embedded_process",
        "build_worker_process",
    }.issubset(set(doge.bootstrap.__all__))
    assert doge.entrypoints.__all__ == []
    assert doge.platform.__all__ == []
    assert doge.products.__all__ == []
    assert "Settings" in doge.shared.__all__


def test_facade_boundaries_do_not_import_other_product_contexts() -> None:
    for path in (PROJECT_ROOT / "src" / "doge" / "products").glob("*/__init__.py"):
        imports = _module_imports(path)
        illegal = [item for item in imports if item.startswith("doge.products.")]
        assert illegal == [], f"{path} imports another product context: {illegal}"


def test_runtime_facade_does_not_import_product_contexts() -> None:
    path = PROJECT_ROOT / "src" / "doge" / "platform" / "runtime" / "__init__.py"
    imports = _module_imports(path)

    assert not any(item.startswith("doge.products.") for item in imports)


def _module_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports
