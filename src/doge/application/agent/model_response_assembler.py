"""Aggregate streamed model deltas into one complete agent response."""

from __future__ import annotations

from typing import AsyncIterator

from doge.core.ports.agent_model import AgentMessage, AgentResponse


class ModelResponseAssembler:
    """Consumes ``IAgentModel.chat`` chunks and returns a single response."""

    async def assemble(self, chunks: AsyncIterator[AgentResponse]) -> AgentResponse | None:
        role = "assistant"
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_calls: dict[int, dict] = {}
        finish_reason = None
        usage = None
        raw = None

        async for chunk in chunks:
            message = chunk.message
            role = message.role or role
            if message.content:
                content_parts.append(str(message.content))
            if message.reasoning_content:
                reasoning_parts.append(message.reasoning_content)
            for fallback_index, call_delta in enumerate(message.tool_calls or []):
                index = int(call_delta.get("index", fallback_index) or 0)
                current = tool_calls.setdefault(
                    index,
                    {"id": call_delta.get("id"), "type": call_delta.get("type", "function"), "function": {}},
                )
                if call_delta.get("id"):
                    current["id"] = call_delta["id"]
                if call_delta.get("type"):
                    current["type"] = call_delta["type"]
                function_delta = call_delta.get("function", {}) or {}
                function = current.setdefault("function", {})
                if function_delta.get("name"):
                    function["name"] = function_delta["name"]
                if "arguments" in function_delta:
                    function["arguments"] = function.get("arguments", "") + (function_delta.get("arguments") or "")
            finish_reason = chunk.finish_reason or finish_reason
            usage = chunk.usage or usage
            raw = chunk.raw or raw

        if not content_parts and not reasoning_parts and not tool_calls and finish_reason is None:
            return None

        calls = [tool_calls[index] for index in sorted(tool_calls)]
        for idx, call in enumerate(calls):
            call.setdefault("id", f"call-{idx}")
            call.setdefault("type", "function")
            call.setdefault("function", {}).setdefault("arguments", "{}")
        return AgentResponse(
            message=AgentMessage(
                role=role,
                content="".join(content_parts),
                reasoning_content="".join(reasoning_parts) or None,
                tool_calls=calls,
            ),
            finish_reason=finish_reason,
            usage=usage,
            raw=raw,
        )
