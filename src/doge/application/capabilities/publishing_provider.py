"""Publishing and proposal tool execution provider."""

from __future__ import annotations

from typing import Any


class PublishingToolProvider:
    """Executes high-risk publishing and portfolio proposal tools."""

    def tool_methods(self) -> dict[str, Any]:
        return {
            "publish_investment_memo": self.publish_investment_memo,
            "propose_portfolio_rebalance": self.propose_portfolio_rebalance,
        }

    def publish_investment_memo(self, memo_id: str, distribution_list: list[str] | None = None) -> dict[str, Any]:
        return {
            "approval_required": True,
            "action": f"publish investment memo {memo_id}",
            "risk_level": "high",
            "distribution_list": distribution_list or [],
        }

    def propose_portfolio_rebalance(
        self,
        portfolio_id: str,
        proposed_changes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "approval_required": True,
            "action": f"propose rebalance for portfolio {portfolio_id}",
            "risk_level": "high",
            "portfolio_id": portfolio_id,
            "proposed_changes": proposed_changes or [],
        }
