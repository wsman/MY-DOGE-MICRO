"""Adapters from Kimi Agent SDK events into MY-DOGE runtime contracts."""

from __future__ import annotations

import json
from typing import Any

from doge.core.ports.agent_model import AgentMessage, AgentResponse


class KimiSdkEventAdapter:
    """Map SDK prompt/session events into provider-neutral agent responses."""

    def messages_to_prompt(self, messages: list[AgentMessage]) -> str:
        return messages_to_prompt(messages)

    def to_response(self, message: Any) -> AgentResponse:
        return sdk_message_to_response(message)

    def to_runtime_payload(self, message: Any) -> dict[str, Any]:
        return safe_message_dump(message)


def messages_to_prompt(messages: list[AgentMessage]) -> str:
    lines: list[str] = []
    for message in messages:
        content = message_content_to_text(message.content)
        if content:
            lines.append(f"{message.role}: {content}")
    return "\n".join(lines)


def message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(message_content_to_text(item) for item in content)
    if hasattr(content, "text") and content.text:
        return str(content.text)
    if hasattr(content, "to_dict"):
        return json.dumps(content.to_dict(), ensure_ascii=False)
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return str(content) if content is not None else ""


def sdk_message_to_response(message: Any) -> AgentResponse:
    if hasattr(message, "extract_text"):
        content = message.extract_text()
        return AgentResponse(
            message=AgentMessage(role="assistant", content=content or ""),
            raw=safe_message_dump(message),
        )
    if message.__class__.__name__.endswith("ApprovalRequest"):
        approval_id = str(getattr(message, "id", "") or getattr(message, "approval_id", "") or "kimi-approval")
        action = str(getattr(message, "action", "") or getattr(message, "description", "") or "kimi agent action")
        return AgentResponse(
            message=AgentMessage(
                role="assistant",
                content="",
                tool_calls=[{
                    "id": approval_id,
                    "type": "function",
                    "function": {
                        "name": "request_approval",
                        "arguments": json.dumps({"action": action, "risk_level": "high"}, ensure_ascii=False),
                    },
                }],
            ),
            raw=safe_message_dump(message),
        )
    return AgentResponse(message=AgentMessage(role="assistant", content=str(message)), raw=safe_message_dump(message))


def safe_message_dump(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    if hasattr(message, "__dict__"):
        return dict(message.__dict__)
    return {"type": message.__class__.__name__, "value": str(message)}
