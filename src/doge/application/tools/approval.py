"""Approval and high-risk publishing tool facade exports."""

from __future__ import annotations

from doge.application.tools.schemas import descriptors_for_names, schemas_for_names
from doge.platform.governance.tools import ComplianceToolProvider, PublishingToolProvider

APPROVAL_TOOL_NAMES = (
    "request_approval",
    "publish_investment_memo",
)


def approval_tool_descriptors():
    return descriptors_for_names(APPROVAL_TOOL_NAMES)


def approval_tool_schemas():
    return schemas_for_names(APPROVAL_TOOL_NAMES)


__all__ = [
    "APPROVAL_TOOL_NAMES",
    "ComplianceToolProvider",
    "PublishingToolProvider",
    "approval_tool_descriptors",
    "approval_tool_schemas",
]
