"""Provider-backed tool execution service."""

from __future__ import annotations

from typing import Any

from doge.application.capabilities.registry import ToolExecutionProviderRegistry
from doge.application.capabilities.tool_utils import ServiceFactory
from doge.application.tools.registry_factory import build_default_execution_provider_registry
from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.core.ports.code_executor import DisabledCodeExecutor, ICodeExecutor


class ToolExecutionService:
    """Execution service over the canonical tool execution provider registry."""

    def __init__(
        self,
        stock_service_factory: ServiceFactory | None = None,
        *,
        ranking_service_factory: ServiceFactory | None = None,
        breadth_service_factory: ServiceFactory | None = None,
        anomaly_service_factory: ServiceFactory | None = None,
        view_service_factory: ServiceFactory | None = None,
        portfolio_service_factory: ServiceFactory | None = None,
        risk_service_factory: ServiceFactory | None = None,
        scenario_service_factory: ServiceFactory | None = None,
        rag_service_factory: ServiceFactory | None = None,
        note_repository_factory: ServiceFactory | None = None,
        industry_report_use_case_factory: ServiceFactory | None = None,
        financial_statement_repository_factory: ServiceFactory | None = None,
        company_announcement_repository_factory: ServiceFactory | None = None,
        consensus_estimate_repository_factory: ServiceFactory | None = None,
        industry_classification_source_factory: ServiceFactory | None = None,
        view_repository_factory: ServiceFactory | None = None,
        code_executor: ICodeExecutor | None = None,
        use_capability_providers: bool = True,
        execution_provider_registry: ToolExecutionProviderRegistry | None = None,
    ) -> None:
        # `use_capability_providers` is retained as a compatibility parameter.
        # Provider Registry is now the single execution path.
        self._code_executor = code_executor or DisabledCodeExecutor()
        self._execution_provider_registry = execution_provider_registry or build_default_execution_provider_registry(
            stock_service_factory=stock_service_factory,
            ranking_service_factory=ranking_service_factory,
            breadth_service_factory=breadth_service_factory,
            anomaly_service_factory=anomaly_service_factory,
            view_service_factory=view_service_factory,
            portfolio_service_factory=portfolio_service_factory,
            risk_service_factory=risk_service_factory,
            scenario_service_factory=scenario_service_factory,
            rag_service_factory=rag_service_factory,
            note_repository_factory=note_repository_factory,
            industry_report_use_case_factory=industry_report_use_case_factory,
            financial_statement_repository_factory=financial_statement_repository_factory,
            company_announcement_repository_factory=company_announcement_repository_factory,
            consensus_estimate_repository_factory=consensus_estimate_repository_factory,
            industry_classification_source_factory=industry_classification_source_factory,
            view_repository_factory=view_repository_factory,
            code_executor=self._code_executor,
        )

    def execution_provider_method_names(self) -> tuple[str, ...]:
        """Return provider-backed method names for parity tests and diagnostics."""
        return self._execution_provider_registry.method_names()

    def tool_descriptors(self) -> tuple[ToolDescriptor, ...]:
        """Return provider-owned descriptors for default registry assembly."""
        return self._execution_provider_registry.tool_descriptors()

    def execute(self, method_name: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Execute a provider-owned tool method by name."""
        return self._provider_execute(method_name, *args, **kwargs)

    def python_analysis_capability_status(self) -> dict[str, Any]:
        """Return capability metadata for the Python analysis executor."""
        available = bool(getattr(self._code_executor, "available", False))
        metadata: dict[str, Any] = {
            "executor": str(getattr(self._code_executor, "executor_name", "unknown")),
        }
        if bool(getattr(self._code_executor, "isolation_enabled", False)):
            metadata["isolation_mode"] = str(getattr(self._code_executor, "isolation_mode", "unknown"))
            metadata["isolation_scope"] = "code_string_only"
        disabled_reason = getattr(self._code_executor, "disabled_reason", None)
        if disabled_reason:
            metadata["disabled_reason"] = str(disabled_reason)
        return {
            "status": "available" if available else "disabled",
            "metadata": metadata,
        }

    def _provider_execute(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        return self._execution_provider_registry.execute(method_name, *args, **kwargs)
