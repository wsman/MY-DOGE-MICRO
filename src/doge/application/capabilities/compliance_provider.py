"""Compliance tool execution provider."""

from __future__ import annotations

from typing import Any


class ComplianceToolProvider:
    """Executes approval and compliance screening tools."""

    def tool_methods(self) -> dict[str, Any]:
        return {
            "request_approval": self.request_approval,
            "screen_compliance_risk": self.screen_compliance_risk,
        }

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
