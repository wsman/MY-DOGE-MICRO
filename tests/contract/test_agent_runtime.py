"""Contract tests for canonical agent runtime imports."""

from __future__ import annotations


def test_canonical_agent_domain_import_matches_legacy_module() -> None:
    from doge.core.domain import agent as canonical
    from doge.core.domain import agent_models as legacy

    assert canonical.AgentSession is legacy.AgentSession
    assert canonical.AgentTurn is legacy.AgentTurn
    assert canonical.AgentRun is legacy.AgentRun
    assert canonical.AgentEvent is legacy.AgentEvent
    assert canonical.AgentApproval is legacy.AgentApproval
    assert canonical.AgentArtifact is legacy.AgentArtifact
    assert canonical.EventType is legacy.EventType
    assert canonical.RunStatus is legacy.RunStatus


def test_canonical_runtime_kernel_import_matches_legacy_module() -> None:
    from doge.application.agent import runtime_kernel as legacy
    from doge.platform import runtime as canonical

    assert canonical.RuntimeKernel is legacy.RuntimeKernel
    assert canonical.RunLifecycleService is legacy.RunLifecycleService
    assert canonical.RunStepper is legacy.RunStepper
    assert canonical.ApprovalCoordinator is legacy.ApprovalCoordinator


def test_canonical_scripted_agent_model_import_matches_legacy_module() -> None:
    from doge.infrastructure.agent.scripted_model import ScriptedAgentModel as legacy
    from doge.infrastructure.llm.scripted_agent_model import ScriptedAgentModel as canonical

    assert canonical is legacy
