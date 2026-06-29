"""Quantitative analysis tool execution provider.

Compatibility implementation; canonical facade is `doge.products.quant.tools`.
"""

from __future__ import annotations

import json
from typing import Any

from doge.application.capabilities.executors import DisabledCodeExecutor
from doge.application.capabilities.tool_utils import (
    ServiceFactory,
    looks_mutating_sql,
    resolve,
)
from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.core.domain.tool_policy import ToolCategory
from doge.core.ports.code_executor import ICodeExecutor


class QuantToolProvider:
    """Executes bounded SQL, Python, and view-listing analysis tools."""

    def __init__(
        self,
        *,
        view_service_factory: ServiceFactory | None = None,
        view_repository_factory: ServiceFactory | None = None,
        code_executor: ICodeExecutor | None = None,
    ) -> None:
        self._view_service_factory = view_service_factory
        self._view_repository_factory = view_repository_factory
        self._code_executor = code_executor or DisabledCodeExecutor()

    def tool_methods(self) -> dict[str, Any]:
        return {
            "list_views": self.list_views,
            "run_sql_query": self.run_sql_query,
            "run_python_analysis": self.run_python_analysis,
        }

    def tool_descriptors(self) -> tuple[ToolDescriptor, ...]:
        python_status = self.python_analysis_capability_status()
        return (
            ToolDescriptor(
                name="list_views",
                description="List available analytical views.",
                category=ToolCategory.READ_ONLY,
            ),
            ToolDescriptor(
                name="run_sql_query",
                description="Run a read-only SQL query against analytical views.",
                properties={
                    "sql": {"type": "string"},
                    "readonly": {"type": "boolean"},
                },
                required=("sql",),
                category=ToolCategory.ANALYTICAL,
            ),
            ToolDescriptor(
                name="run_python_analysis",
                description="Run bounded demo Python analysis.",
                properties={
                    "code": {"type": "string"},
                    "timeout": {"type": "number", "minimum": 1, "maximum": 10},
                },
                required=("code",),
                category=ToolCategory.HIGH_RISK,
                status=python_status["status"],
                metadata={
                    **python_status["metadata"],
                    "risk_level": "high",
                    "approval_required": True,
                },
            ),
        )

    def python_analysis_capability_status(self) -> dict[str, Any]:
        available = bool(getattr(self._code_executor, "available", False))
        metadata: dict[str, Any] = {
            "executor": str(getattr(self._code_executor, "executor_name", "unknown")),
        }
        disabled_reason = getattr(self._code_executor, "disabled_reason", None)
        if disabled_reason:
            metadata["disabled_reason"] = str(disabled_reason)
        return {
            "status": "available" if available else "disabled",
            "metadata": metadata,
        }

    def list_views(self) -> dict[str, Any]:
        payload = self._view_service().list_views()
        rows = json.loads(payload)
        return {"views": rows}

    def run_sql_query(self, sql: str, readonly: bool = True) -> dict[str, Any]:
        if not readonly or looks_mutating_sql(sql):
            return {"ok": False, "error": "Only read-only SELECT/WITH queries are allowed."}
        try:
            frame = self._view_repository().execute(sql, [])
            rows = frame.to_dict(orient="records") if hasattr(frame, "to_dict") else []
            return {"ok": True, "rows": rows[:100], "row_count": len(rows)}
        except Exception:
            return {"ok": False, "error": "SQL query failed."}

    def run_python_analysis(self, code: str, timeout: float = 5.0) -> dict[str, Any]:
        result = self._code_executor.execute(code, timeout)
        return {
            "ok": result.ok,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error": result.error,
        }

    def _view_service(self):
        return resolve(self._view_service_factory, "view_service")

    def _view_repository(self):
        return resolve(self._view_repository_factory, "view_repository")
