"""Architecture guard for RuntimeKernel responsibility split."""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_runtime_kernel_delegates_to_second_stage_collaborators() -> None:
    """RuntimeKernel delegates to lifecycle, stepper, transition, approval, and artifact collaborators."""
    source = Path("src/doge/application/agent/runtime_kernel.py").read_text(encoding="utf-8")

    for required in [
        "IRunLifecycleService",
        "IRunStepper",
        "ITransitionRecorder",
        "IApprovalCoordinator",
        "IArtifactFinalizer",
    ]:
        assert required in source, f"RuntimeKernel must depend on {required}"
    assert "doge.core.ports.runtime_services" in source
    for forbidden in [
        "doge.platform.runtime",
    ]:
        assert forbidden not in source, f"RuntimeKernel must not import {forbidden}"


def test_runtime_kernel_delegates_execution_services() -> None:
    """Execution services (model/tool/artifact) are delegated by RunStepper and RunLifecycleService, not RuntimeKernel directly."""
    source = Path("src/doge/application/agent/runtime_kernel.py").read_text(encoding="utf-8")

    # RuntimeKernel no longer imports execution services directly; those are
    # wired into the second-stage collaborators (RunStepper, RunLifecycleService).
    assert "IModelExecutionService" not in source
    assert "IToolExecutionService" not in source
    assert "IArtifactEvaluationService" not in source
    assert "CitationService" not in source
    assert "NumericalConsistencyService" not in source
    assert "inspect.signature" not in source
    assert "def _chat_stream" not in source
    assert "def _artifact_metrics" not in source
    assert "def _can_execute_tool" not in source
    assert "def _tool_schemas_for" not in source
    assert "def _budget_exceeded" not in source


def test_runtime_services_define_split_boundaries() -> None:
    source = Path("src/doge/platform/runtime/services.py").read_text(encoding="utf-8")

    for required in [
        "class ModelExecutionService",
        "class ToolExecutionService",
        "class ArtifactEvaluationService",
        "from doge.core.ports.runtime_services import ModelExecutionResult, ToolResult",
    ]:
        assert required in source


def test_core_runtime_services_define_ports_and_result_types() -> None:
    source = Path("src/doge/core/ports/runtime_services.py").read_text(encoding="utf-8")

    for required in [
        "class IModelExecutionService",
        "class IToolExecutionService",
        "class IArtifactEvaluationService",
        "class ModelExecutionResult",
        "class ToolResult",
    ]:
        assert required in source


def test_runtime_kernel_does_not_exceed_line_target() -> None:
    source = (PROJECT_ROOT / "src" / "doge" / "application" / "agent" / "runtime_kernel.py").read_text(
        encoding="utf-8"
    )
    lines = source.splitlines()
    assert len(lines) <= 400, f"RuntimeKernel has {len(lines)} lines"


def test_runtime_kernel_imports_second_stage_collaborators() -> None:
    source = (PROJECT_ROOT / "src" / "doge" / "application" / "agent" / "runtime_kernel.py").read_text(
        encoding="utf-8"
    )
    for collaborator in [
        "IRunLifecycleService",
        "IRunStepper",
        "ITransitionRecorder",
        "IApprovalCoordinator",
        "IArtifactFinalizer",
    ]:
        assert collaborator in source, f"RuntimeKernel should depend on {collaborator}"


def test_second_stage_collaborator_files_exist() -> None:
    for filename in [
        "run_lifecycle_service.py",
        "run_stepper.py",
        "transition_recorder.py",
        "approval_coordinator.py",
        "artifact_finalizer.py",
    ]:
        path = PROJECT_ROOT / "src" / "doge" / "application" / "agent" / filename
        assert path.exists(), f"missing collaborator: {filename}"
