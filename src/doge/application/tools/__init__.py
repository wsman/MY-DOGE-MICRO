"""Application-layer tool registry package."""

from doge.application.tools.registry import ToolRegistry
from doge.core.ports.runtime_services import ToolResult


def build_default_tool_registry(*args, **kwargs):
    from doge.application.tools.factory import build_default_tool_registry as _build_default_tool_registry

    return _build_default_tool_registry(*args, **kwargs)

__all__ = ["ToolRegistry", "ToolResult", "build_default_tool_registry"]
