"""Architecture guard for RuntimeKernel responsibility split."""

from pathlib import Path


def test_runtime_kernel_delegates_execution_services() -> None:
    source = Path("src/doge/application/agent/runtime_kernel.py").read_text(encoding="utf-8")

    for required in [
        "IModelExecutionService",
        "IToolExecutionService",
        "IArtifactEvaluationService",
    ]:
        assert required in source
    assert "doge.core.ports.runtime_services" in source
    for forbidden in [
        "doge.platform.runtime",
        "CitationService",
        "NumericalConsistencyService",
        "inspect.signature",
        "def _chat_stream",
        "def _artifact_metrics",
        "def _can_execute_tool",
        "def _tool_schemas_for",
        "def _budget_exceeded",
    ]:
        assert forbidden not in source


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
