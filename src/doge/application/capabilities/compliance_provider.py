"""Compliance tool execution provider."""

from __future__ import annotations

from typing import Any

from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.core.domain.tool_policy import ToolCategory


class ComplianceToolProvider:
    """Executes approval and compliance screening tools."""

    def tool_methods(self) -> dict[str, Any]:
        return {
            "request_approval": self.request_approval,
            "screen_compliance_risk": self.screen_compliance_risk,
        }

    def tool_descriptors(self) -> tuple[ToolDescriptor, ...]:
        return (
            ToolDescriptor(
                name="request_approval",
                description="Request human approval for a high-risk action.",
                properties={
                    "action": {"type": "string"},
                    "risk_level": {"type": "string", "enum": ["medium", "high"]},
                },
                required=("action", "risk_level"),
                category=ToolCategory.HIGH_RISK,
            ),
            ToolDescriptor(
                name="screen_compliance_risk",
                description="Screen text for compliance risk phrases.",
                properties={"text": {"type": "string"}},
                required=("text",),
                category=ToolCategory.ANALYTICAL,
            ),
        )

    def request_approval(self, action: str, risk_level: str = "high") -> dict[str, Any]:
        return {"approval_required": True, "action": action, "risk_level": risk_level}

    def screen_compliance_risk(self, text: str) -> dict[str, Any]:
        lowered = text.lower()
        hits = [
            word
            for word in ("guaranteed return", "inside information", "auto trade", "无风险", "内幕")
            if word in lowered
        ]
        return {"risk": "high" if hits else "low", "matches": hits}
