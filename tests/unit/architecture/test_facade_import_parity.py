"""Sprint E facade import parity checks."""

from __future__ import annotations


def test_runtime_facade_exports_split_runtime_collaborators() -> None:
    from doge.application.agent.approval_coordinator import ApprovalCoordinator as OldApprovalCoordinator
    from doge.application.agent.artifact_finalizer import ArtifactFinalizer as OldArtifactFinalizer
    from doge.application.agent.run_lifecycle_service import RunLifecycleService as OldRunLifecycleService
    from doge.application.agent.run_stepper import RunStepper as OldRunStepper
    from doge.application.agent.transition_recorder import TransitionRecorder as OldTransitionRecorder
    from doge.platform.runtime import (
        ApprovalCoordinator,
        ArtifactFinalizer,
        RunLifecycleService,
        RunStepper,
        TransitionRecorder,
    )

    assert RunStepper is OldRunStepper
    assert ApprovalCoordinator is OldApprovalCoordinator
    assert ArtifactFinalizer is OldArtifactFinalizer
    assert TransitionRecorder is OldTransitionRecorder
    assert RunLifecycleService is OldRunLifecycleService


def test_runtime_facade_exports_runtime_service_protocols() -> None:
    from doge.core.ports.runtime_services import IRunStepper as OldIRunStepper
    from doge.core.ports.runtime_services import IToolExecutionService as OldIToolExecutionService
    from doge.platform.runtime import IRunStepper, IToolExecutionService

    assert IRunStepper is OldIRunStepper
    assert IToolExecutionService is OldIToolExecutionService


def test_evidence_facade_exports_evidence_chunk() -> None:
    from doge.core.domain.evidence_chunk_models import EvidenceChunk as OldEvidenceChunk
    from doge.platform.evidence import EvidenceChunk

    assert EvidenceChunk is OldEvidenceChunk


def test_tool_provider_facades_preserve_legacy_class_identity() -> None:
    from doge.application.capabilities.compliance_provider import ComplianceToolProvider as OldComplianceToolProvider
    from doge.application.capabilities.fundamental_provider import FundamentalToolProvider as OldFundamentalToolProvider
    from doge.application.capabilities.market_provider import MarketToolProvider as OldMarketToolProvider
    from doge.application.capabilities.portfolio_provider import PortfolioToolProvider as OldPortfolioToolProvider
    from doge.application.capabilities.publishing_provider import PublishingToolProvider as OldPublishingToolProvider
    from doge.application.capabilities.quant_provider import QuantToolProvider as OldQuantToolProvider
    from doge.application.capabilities.research_provider import ResearchToolProvider as OldResearchToolProvider
    from doge.platform.governance.tools import ComplianceToolProvider, PublishingToolProvider
    from doge.products.market.tools import MarketToolProvider
    from doge.products.portfolio.tools import PortfolioToolProvider
    from doge.products.quant.tools import QuantToolProvider
    from doge.products.research.tools import FundamentalToolProvider, ResearchToolProvider

    assert MarketToolProvider is OldMarketToolProvider
    assert PortfolioToolProvider is OldPortfolioToolProvider
    assert ResearchToolProvider is OldResearchToolProvider
    assert FundamentalToolProvider is OldFundamentalToolProvider
    assert QuantToolProvider is OldQuantToolProvider
    assert ComplianceToolProvider is OldComplianceToolProvider
    assert PublishingToolProvider is OldPublishingToolProvider
