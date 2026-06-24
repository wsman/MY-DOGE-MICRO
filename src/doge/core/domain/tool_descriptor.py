"""Canonical descriptor for agent-callable tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from doge.core.domain.tool_policy import ToolCategory


@dataclass(frozen=True)
class ToolDescriptor:
    """Single source of truth for tool schema and governance metadata."""

    name: str
    description: str
    properties: dict[str, Any] = field(default_factory=dict)
    required: tuple[str, ...] = ()
    category: ToolCategory = ToolCategory.READ_ONLY
    provider: str = "tool_application_service"
    method_name: str | None = None
    timeout_seconds: float | None = None
    status: str = "available"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.method_name is None:
            object.__setattr__(self, "method_name", self.name)

    def to_schema(self) -> dict[str, Any]:
        """Return the OpenAI/Kimi-compatible function schema."""

        schema_metadata = {
            "provider": self.provider,
            "method_name": self.method_name,
            **self.metadata,
        }
        if self.timeout_seconds is not None:
            schema_metadata["timeout_seconds"] = self.timeout_seconds
        return {
            "type": "function",
            "x-doge-category": self.category.value,
            "x-doge-status": self.status,
            "x-doge-metadata": schema_metadata,
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.properties,
                    "required": list(self.required),
                },
            },
        }

    def capability_metadata(self) -> dict[str, Any]:
        """Return metadata shared by capability discovery surfaces."""

        data = {
            "provider": self.provider,
            "method_name": self.method_name,
            **self.metadata,
        }
        if self.timeout_seconds is not None:
            data["timeout_seconds"] = self.timeout_seconds
        return data

    @classmethod
    def from_schema(
        cls,
        schema: dict[str, Any],
        *,
        category: ToolCategory,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ToolDescriptor":
        """Build a descriptor from a legacy schema dictionary."""

        function = schema.get("function", {})
        parameters = function.get("parameters", {})
        return cls(
            name=str(function.get("name", "")),
            description=str(function.get("description", "")),
            properties=dict(parameters.get("properties", {})),
            required=tuple(parameters.get("required", ()) or ()),
            category=category,
            status=status or str(schema.get("x-doge-status", "available")),
            metadata=metadata or dict(schema.get("x-doge-metadata", {})),
        )
