"""Quantitative analysis tool execution provider."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from doge.application.capabilities.tool_utils import (
    ServiceFactory,
    looks_mutating_sql,
    resolve,
    unsafe_python,
)


class QuantToolProvider:
    """Executes bounded SQL, Python, and view-listing analysis tools."""

    def __init__(
        self,
        *,
        view_service_factory: ServiceFactory | None = None,
        view_repository_factory: ServiceFactory | None = None,
    ) -> None:
        self._view_service_factory = view_service_factory
        self._view_repository_factory = view_repository_factory

    def tool_methods(self) -> dict[str, Any]:
        return {
            "list_views": self.list_views,
            "run_sql_query": self.run_sql_query,
            "run_python_analysis": self.run_python_analysis,
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
        if unsafe_python(code):
            return {"ok": False, "error": "Code uses disallowed operations in the demo sandbox."}
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-c", code],
                text=True,
                capture_output=True,
                timeout=max(1.0, min(float(timeout), 10.0)),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Python analysis timed out."}
        return {
            "ok": completed.returncode == 0,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-2000:] if completed.returncode else "",
            "returncode": completed.returncode,
        }

    def _view_service(self):
        return resolve(self._view_service_factory, "view_service")

    def _view_repository(self):
        return resolve(self._view_repository_factory, "view_repository")
