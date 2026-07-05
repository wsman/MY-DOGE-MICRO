"""Publishing and proposal tool execution provider.

Compatibility implementation; canonical facade is
`doge.platform.governance.tools`.
"""

from __future__ import annotations

from typing import Any

from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.core.domain.tool_policy import ToolCategory


class PublishingToolProvider:
    """Executes high-risk publishing and portfolio proposal tools."""

    def tool_methods(self) -> dict[str, Any]:
        return {
            "publish_investment_memo": self.publish_investment_memo,
            "propose_portfolio_rebalance": self.propose_portfolio_rebalance,
        }

    def tool_descriptors(self) -> tuple[ToolDescriptor, ...]:
        return (
            ToolDescriptor(
                name="publish_investment_memo",
                description="Request approval to publish an investment memo.",
                properties={
                    "memo_id": {"type": "string"},
                    "distribution_list": {"type": "array", "items": {"type": "string"}},
                },
                required=("memo_id",),
                category=ToolCategory.HIGH_RISK,
                metadata={"risk_level": "high", "approval_required": True},
            ),
            ToolDescriptor(
                name="propose_portfolio_rebalance",
                description="Request approval for a proposed rebalance.",
                properties={
                    "portfolio_id": {"type": "string"},
                    "proposed_changes": {"type": "array", "items": {"type": "object"}},
                },
                required=("portfolio_id",),
                category=ToolCategory.HIGH_RISK,
                metadata={"risk_level": "high", "approval_required": True},
            ),
        )

    def publish_investment_memo(self, memo_id: str, distribution_list: list[str] | None = None) -> dict[str, Any]:
        targets = distribution_list or []
        return {
            "approval_required": True,
            "action": f"publish investment memo {memo_id}",
            "risk_level": "high",
            "distribution_list": targets,
            "why_needed": "Publishing an investment memo is a governed action that can distribute research conclusions outside the draft workspace.",
            "impact": "Approval releases the memo content and its evidence trail to the selected audience.",
            "deny_consequence": "The memo remains unpublished and the run stops at the approval checkpoint.",
            "publish_target": ", ".join(targets) if targets else "not specified",
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
            "why_needed": "Portfolio rebalance proposals are high-risk investment actions that require human review before use.",
            "impact": "Approval records the proposal as reviewed and allows the workflow to continue with action candidates.",
            "deny_consequence": "The rebalance proposal is not advanced and the run stops at the approval checkpoint.",
            "publish_target": f"portfolio {portfolio_id}",
        }
