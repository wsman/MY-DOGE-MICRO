"""Deterministic agent model for offline demos and tests."""

from __future__ import annotations

import json
import re
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
        max_completion_tokens: int | None = None,
        stream: bool = True,
        model: str | None = None,
        thinking_enabled: bool | None = None,
        response_format: dict[str, Any] | None = None,
        prompt_cache_key: str | None = None,
        safety_identifier: str | None = None,
        timeout: float | None = None,
        request_metadata: dict[str, Any] | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentResponse]:
        tool_result_names = {message.name for message in messages if message.role == "tool"}
        portfolio_id = _authorized_portfolio_id(messages)
        if "stock_overview" not in tool_result_names:
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
        elif portfolio_id and "get_portfolio_exposure" not in tool_result_names:
            yield AgentResponse(message=AgentMessage(
                role="assistant",
                content="",
                reasoning_content="Need explicitly attached portfolio concentration and exposure.",
                tool_calls=[{
                    "id": "call-portfolio",
                    "type": "function",
                    "function": {
                        "name": "get_portfolio_exposure",
                        "arguments": json.dumps({"portfolio_id": portfolio_id}, separators=(",", ":")),
                    },
                }],
            ))
        elif "request_approval" not in tool_result_names:
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
                usage={
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cached_tokens": 0,
                    "total_tokens": 0,
                    "model": model or "scripted",
                    "cost_usd": 0.0,
                },
            )


def _authorized_portfolio_id(messages: list[AgentMessage]) -> str | None:
    pattern = re.compile(r"Authorized run portfolio_id: (.*?)\. Use this exact portfolio_id")
    for message in messages:
        if message.role != "system" or not isinstance(message.content, str):
            continue
        match = pattern.search(message.content)
        if match:
            return match.group(1)
    return None


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
