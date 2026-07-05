"""Tool registry for research-agent workflows."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Iterable
from typing import Any, Callable

from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.core.domain.tool_policy import ToolCategory
from doge.core.ports.runtime_services import ToolResult
from doge.core.ports.tool_entitlement import IToolEntitlementChecker
from doge.shared.errors import SafeError


class ToolRegistry:
    """Small synchronous registry for deterministic finance tools."""

    def __init__(
        self,
        *,
        entitlement_checker: IToolEntitlementChecker | None = None,
        context: Any = None,
    ) -> None:
        self._descriptors: dict[str, ToolDescriptor] = {}
        self._tools: dict[str, Callable[..., ToolResult]] = {}
        self._categories: dict[str, ToolCategory] = {}
        self._entitlement = entitlement_checker or _DefaultEntitlementChecker()
        self._context = context
        self.schemas: list[dict[str, Any]] = []

    def register(
        self,
        schema: dict[str, Any] | ToolDescriptor,
        func: Callable[..., ToolResult],
        category: ToolCategory | str | None = None,
    ) -> None:
        descriptor = schema if isinstance(schema, ToolDescriptor) else None
        if descriptor is not None:
            schema = descriptor.to_schema()
        name = schema["function"]["name"]
        resolved_category = _category(category or schema.get("x-doge-category") or ToolCategory.READ_ONLY)
        schema["x-doge-category"] = resolved_category.value
        if descriptor is None:
            descriptor = ToolDescriptor.from_schema(schema, category=resolved_category)
        self._descriptors[name] = descriptor
        self.schemas.append(schema)
        self._tools[name] = func
        self._categories[name] = resolved_category

    def include_descriptors(self, descriptors: Iterable[ToolDescriptor], executor: Any) -> None:
        """Register provider-owned descriptors against an execution facade."""

        for descriptor in descriptors:
            self.register(descriptor, _tool_func_for_descriptor(executor, descriptor))

    def descriptor_for(self, name: str) -> ToolDescriptor | None:
        """Return the canonical descriptor for a registered tool."""

        return self._descriptors.get(name)

    def descriptors(self) -> tuple[ToolDescriptor, ...]:
        """Return registered descriptors in schema order."""

        names = [schema.get("function", {}).get("name", "") for schema in self.schemas]
        return tuple(self._descriptors[name] for name in names if name in self._descriptors)

    def schemas_for_context(self, context: Any = None) -> list[dict[str, Any]]:
        effective_context = self._context if context is None else context
        allowed: list[dict[str, Any]] = []
        for schema in self.schemas:
            name = schema.get("function", {}).get("name", "")
            category = self._categories.get(name, ToolCategory.READ_ONLY)
            redacted = self._entitlement.redact_schema(effective_context, schema, category)
            if redacted is not None:
                allowed.append(redacted)
        return allowed

    def capability_records_for_context(self, context: Any = None) -> list[dict[str, Any]]:
        effective_context = self._context if context is None else context
        records: list[dict[str, Any]] = []
        for schema in self.schemas_for_context(effective_context):
            name = schema.get("function", {}).get("name", "")
            category = self._categories.get(name, ToolCategory.READ_ONLY)
            descriptor = self._descriptors.get(name)
            records.append({
                "name": name,
                "tool_name": name,
                "description": (
                    descriptor.description if descriptor is not None
                    else schema.get("function", {}).get("description", "")
                ),
                "category": category.value,
                "risk_level": _risk_level(category),
                "status": descriptor.status if descriptor is not None else schema.get("x-doge-status", "available"),
                "requires_approval": self._entitlement.requires_approval(effective_context, name, category),
                "metadata": (
                    descriptor.capability_metadata()
                    if descriptor is not None
                    else dict(schema.get("x-doge-metadata", {}))
                ),
            })
        return records

    def execute(self, name: str, arguments: str | dict[str, Any] | None = None, *, context: Any = None) -> ToolResult:
        if name not in self._tools:
            return _tool_error(name, "unknown_tool", "unknown tool")
        effective_context = self._context if context is None else context
        category = self._categories.get(name, ToolCategory.READ_ONLY)
        if not self._entitlement.can_execute(effective_context, name, category):
            return _tool_error(name, "tool_not_permitted", "tool not permitted")
        if isinstance(arguments, str):
            try:
                kwargs = json.loads(arguments or "{}")
            except json.JSONDecodeError:
                return _tool_error(name, "invalid_tool_arguments", "invalid JSON arguments")
        else:
            kwargs = arguments or {}
        try:
            result = _invoke_tool(self._tools[name], kwargs, effective_context)
            if self._entitlement.requires_approval(effective_context, name, category):
                result.data.setdefault("approval_required", True)
                result.data.setdefault("action", name)
                result.data.setdefault("risk_level", "high")
                result.data.setdefault("why_needed", "")
                result.data.setdefault("impact", "")
                result.data.setdefault("deny_consequence", "")
                result.data.setdefault("publish_target", "")
            return result
        except Exception:  # noqa: BLE001 - tool failures become trace data
            safe_error = SafeError.create("tool_execution_failed", "tool execution failed")
            return ToolResult(
                name=name,
                data={},
                ok=False,
                error=safe_error.public_message,
                safe_error=safe_error.to_event_payload(),
            )

    async def execute_async(
        self,
        name: str,
        arguments: str | dict[str, Any] | None = None,
        *,
        timeout_seconds: float | None = None,
        context: Any = None,
    ) -> ToolResult:
        """Execute a synchronous tool through a cancellable async boundary."""
        call = asyncio.to_thread(self.execute, name, arguments, context=context)
        if timeout_seconds is None:
            return await call
        try:
            return await asyncio.wait_for(call, timeout=timeout_seconds)
        except TimeoutError:
            return _tool_error(name, "tool_execution_timed_out", "tool execution timed out")


def _category(value: ToolCategory | str) -> ToolCategory:
    if isinstance(value, ToolCategory):
        return value
    return ToolCategory(str(value))


def _risk_level(category: ToolCategory) -> str:
    if category == ToolCategory.HIGH_RISK:
        return "high"
    if category in {ToolCategory.ANALYTICAL, ToolCategory.GENERATIVE}:
        return "medium"
    return "low"


def _invoke_tool(func: Callable[..., ToolResult], kwargs: dict[str, Any], context: Any) -> ToolResult:
    if "context" in inspect.signature(func).parameters and "context" not in kwargs:
        return func(**kwargs, context=context)
    return func(**kwargs)


def _tool_func_for_descriptor(executor: Any, descriptor: ToolDescriptor) -> Callable[..., ToolResult]:
    method_name = descriptor.method_name or descriptor.name

    def _tool_func(context: Any = None, **kwargs: Any) -> ToolResult:
        method = getattr(executor, method_name)
        if "context" in inspect.signature(method).parameters and "context" not in kwargs:
            data = method(**kwargs, context=context)
        else:
            data = method(**kwargs)
        if not isinstance(data, dict):
            data = dict(data)
        return ToolResult(
            descriptor.name,
            data=data,
            ok=bool(data.get("ok", True)),
            error=data.get("error"),
        )

    return _tool_func


def _tool_error(name: str, code: str, public_message: str) -> ToolResult:
    safe_error = SafeError.create(code, public_message)
    return ToolResult(
        name=name,
        data={},
        ok=False,
        error=safe_error.public_message,
        safe_error=safe_error.to_event_payload(),
    )


class _DefaultEntitlementChecker:
    def can_execute(self, context: Any, tool_name: str, category: ToolCategory) -> bool:
        return category != ToolCategory.FORBIDDEN

    def requires_approval(self, context: Any, tool_name: str, category: ToolCategory) -> bool:
        return category == ToolCategory.HIGH_RISK

    def redact_schema(self, context: Any, schema: dict[str, Any], category: ToolCategory) -> dict[str, Any] | None:
        if not self.can_execute(context, schema.get("function", {}).get("name", ""), category):
            return None
        return schema
