"""Deterministic agent model for offline demos and tests."""

from __future__ import annotations

from typing import Any, AsyncIterator

from doge.core.ports.agent_model import AgentMessage, AgentResponse, IAgentModel


class ScriptedAgentModel(IAgentModel):
    """Deterministic model used when no live Kimi key is available."""

    async def chat(
        self,
        messages: list[AgentMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int = 16384,
        stream: bool = True,
    ) -> AsyncIterator[AgentResponse]:
        tool_results = [message for message in messages if message.role == "tool"]
        turn = len(tool_results)
        if turn == 0:
            yield AgentResponse(message=AgentMessage(
                role="assistant",
                content="",
                reasoning_content="Need company facts before drafting.",
                tool_calls=[{
                    "id": "call-stock-overview",
                    "type": "function",
                    "function": {"name": "stock_overview", "arguments": "{\"ticker\":\"AAPL\",\"market\":\"us\"}"},
                }],
            ))
        elif turn == 1:
            yield AgentResponse(message=AgentMessage(
                role="assistant",
                content="",
                reasoning_content="Need portfolio concentration and exposure.",
                tool_calls=[{
                    "id": "call-portfolio",
                    "type": "function",
                    "function": {"name": "get_portfolio_exposure", "arguments": "{\"portfolio_id\":\"portfolio-demo\"}"},
                }],
            ))
        elif turn == 2:
            yield AgentResponse(message=AgentMessage(
                role="assistant",
                content="",
                reasoning_content="The memo contains high-risk publication language; request approval.",
                tool_calls=[{
                    "id": "call-approval",
                    "type": "function",
                    "function": {
                        "name": "request_approval",
                        "arguments": "{\"action\":\"publish investment committee memo\",\"risk_level\":\"high\"}",
                    },
                }],
            ))
        else:
            yield AgentResponse(
                message=AgentMessage(role="assistant", content=_default_memo()),
                finish_reason="stop",
                usage={"total_tokens": 0},
            )


def _default_memo() -> str:
    return """# Investment Committee Memo

## Executive Summary
The requested research memo requires source-backed validation and human approval before publication.

## Findings
- Earnings-quality claims were routed through deterministic validation tools.
- Portfolio exposure should be reported only when backed by configured holdings data.
- Any high-risk publication action is gated by human approval.

## IC Questions
1. Which reported figures require source-page confirmation before publication?
2. What downside scenario should be approved for client-facing material?
3. What unresolved data gaps should remain marked as unavailable?
"""
