"""Rebuild model context from persisted agent events."""

from __future__ import annotations

import json

from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType
from doge.core.ports.agent_model import AgentMessage


class ContextBuilder:
    """Build OpenAI-compatible messages from run metadata and event history."""

    def build(self, run: AgentRun, events: list[AgentEvent]) -> list[AgentMessage]:
        messages = [
            AgentMessage(
                role="system",
                content=(
                    "You are MY-DOGE Enterprise Research Copilot. Use tools for "
                    "material numbers, preserve citations, and request approval "
                    "for high-risk publication actions."
                ),
            ),
            AgentMessage(role="user", content=run.question),
        ]
        for event in sorted(events, key=lambda item: item.sequence):
            if event.event_type == EventType.MODEL_RESPONSE:
                payload = event.payload.get("message", {})
                messages.append(AgentMessage(
                    role=payload.get("role", "assistant"),
                    content=payload.get("content", ""),
                    reasoning_content=payload.get("reasoning_content"),
                    tool_calls=payload.get("tool_calls", []),
                ))
            elif event.event_type == EventType.TOOL_RESULT:
                messages.append(AgentMessage(
                    role="tool",
                    tool_call_id=event.payload.get("tool_call_id"),
                    name=event.payload.get("name"),
                    content=json.dumps(event.payload.get("result", {}), ensure_ascii=False),
                ))
            elif event.event_type == EventType.APPROVAL_RESOLVED:
                status = "approved" if event.payload.get("approved") else "denied"
                messages.append(AgentMessage(
                    role="user",
                    content=f"Human approval {event.payload.get('approval_id')} was {status}. Continue accordingly.",
                ))
        return messages
