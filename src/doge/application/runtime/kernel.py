"""DEPRECATED (ADR-0027): legacy runtime kernel facade.

Re-exports ``doge.application.agent.runtime_kernel``. Prefer the canonical
facade ``doge.platform.runtime``. Do not add behavior here.
"""

from doge.application.agent.runtime_kernel import (
    ApprovalCoordinator,
    ArtifactFinalizer,
    RunLifecycleService,
    RunStepper,
    RuntimeKernel,
    TransitionRecorder,
)

__all__ = [
    "ApprovalCoordinator",
    "ArtifactFinalizer",
    "RunLifecycleService",
    "RunStepper",
    "RuntimeKernel",
    "TransitionRecorder",
]
