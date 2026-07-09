"""Adapters from Kimi Agent SDK events into OpenDoge runtime contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from doge.core.ports.agent_model import AgentMessage, AgentResponse


@dataclass(frozen=True)
class KimiSdkPromptRequest:
    prompt: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    tool_choice: str | None
    max_tokens: int
    metadata: dict[str, Any]


class KimiSdkEventAdapter:
    """Map SDK prompt/session events into provider-neutral agent responses."""

    def messages_to_prompt(self, messages: list[AgentMessage]) -> str:
        return messages_to_prompt(messages)

    def build_prompt_request(
        self,
        messages: list[AgentMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int = 16384,
        request_metadata: dict[str, Any] | None = None,
        prompt_cache_key: str | None = None,
        model: str | None = None,
    ) -> KimiSdkPromptRequest:
        return build_prompt_request(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            request_metadata=request_metadata,
            prompt_cache_key=prompt_cache_key,
            model=model,
        )

    def to_prompt_kwargs(self, request: KimiSdkPromptRequest) -> dict[str, Any]:
        return prompt_request_to_kwargs(request)

    def to_response(self, message: Any) -> AgentResponse:
        return sdk_message_to_response(message)

    def to_runtime_payload(self, message: Any) -> dict[str, Any]:
        return safe_message_dump(message)


def build_prompt_request(
    messages: list[AgentMessage],
    *,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    max_tokens: int = 16384,
    request_metadata: dict[str, Any] | None = None,
    prompt_cache_key: str | None = None,
    model: str | None = None,
) -> KimiSdkPromptRequest:
    serialized_messages = [message.to_api_dict() for message in messages]
    metadata = {
        "request_metadata": request_metadata or {},
        "prompt_cache_key": prompt_cache_key,
        "model": model,
        "message_count": len(messages),
        "has_multimodal": any(_message_has_multimodal(message) for message in serialized_messages),
        "tool_count": len(tools or []),
    }
    return KimiSdkPromptRequest(
        prompt=messages_to_prompt(messages),
        messages=serialized_messages,
        tools=list(tools or []),
        tool_choice=tool_choice,
        max_tokens=max_tokens,
        metadata={key: value for key, value in metadata.items() if value not in (None, "", [])},
    )


def prompt_request_to_kwargs(request: KimiSdkPromptRequest) -> dict[str, Any]:
    """Return optional SDK kwargs; unsupported keys are filtered by the backend."""
    return {
        "messages": request.messages,
        "tools": request.tools,
        "tool_choice": request.tool_choice,
        "max_tokens": request.max_tokens,
        "metadata": request.metadata,
        "session_id": request.metadata.get("request_metadata", {}).get("session_id"),
    }


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
    raw = safe_message_dump(message)
    if _is_approval_request(message, raw):
        return _approval_request_to_response(message, raw)
    tool_calls = _extract_tool_calls(message, raw)
    content = _extract_text(message, raw)
    reasoning = _first_value(message, raw, "reasoning_content", "reasoning", "thinking")
    usage = _extract_usage(message, raw)
    finish_reason = _first_value(message, raw, "finish_reason", "stop_reason")
    if tool_calls or content is not None or reasoning or usage or finish_reason:
        return AgentResponse(
            message=AgentMessage(
                role=str(raw.get("role") or "assistant"),
                content=content or "",
                reasoning_content=str(reasoning) if reasoning else None,
                tool_calls=tool_calls,
                tool_call_id=_optional_str(_first_value(message, raw, "tool_call_id")),
            ),
            finish_reason=_optional_str(finish_reason),
            usage=usage,
            raw=raw,
        )
    if hasattr(message, "extract_text"):
        content = message.extract_text()
        return AgentResponse(
            message=AgentMessage(role="assistant", content=content or ""),
            raw=raw,
        )
    return AgentResponse(message=AgentMessage(role="assistant", content=str(message)), raw=raw)


def safe_message_dump(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        payload = message.model_dump(exclude_none=True)
        if isinstance(payload, dict):
            return {"sdk_event_type": message.__class__.__name__, **payload}
    if hasattr(message, "__dict__"):
        return {"sdk_event_type": message.__class__.__name__, **dict(message.__dict__)}
    return {"type": message.__class__.__name__, "value": str(message)}


def _message_has_multimodal(message: dict[str, Any]) -> bool:
    content = message.get("content")
    if isinstance(content, list):
        return any(isinstance(item, dict) and item.get("type") not in {"text", "input_text"} for item in content)
    if isinstance(content, dict):
        return content.get("type") not in {"text", "input_text"}
    return False


def _extract_text(message: Any, raw: dict[str, Any]) -> str | None:
    if hasattr(message, "extract_text"):
        text = message.extract_text()
        if text:
            return str(text)
    for key in ("content", "text", "delta", "message"):
        value = raw.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict) and isinstance(value.get("content"), str):
            return value["content"]
    return None


def _is_approval_request(message: Any, raw: dict[str, Any]) -> bool:
    event_type = str(raw.get("type") or raw.get("sdk_event_type") or message.__class__.__name__).lower()
    return "approval" in event_type and ("request" in event_type or raw.get("approval_required") is True)


def _approval_request_to_response(message: Any, raw: dict[str, Any]) -> AgentResponse:
    approval_id = _optional_str(_first_value(message, raw, "id", "approval_id")) or "kimi-approval"
    action = _optional_str(_first_value(message, raw, "action", "description")) or "kimi agent action"
    risk_level = _optional_str(_first_value(message, raw, "risk_level")) or "high"
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    return AgentResponse(
        message=AgentMessage(
            role="assistant",
            content="",
            tool_calls=[{
                "id": approval_id,
                "type": "function",
                "function": {
                    "name": "request_approval",
                    "arguments": json.dumps({
                        "action": action,
                        "risk_level": risk_level,
                        "approval_id": approval_id,
                        "metadata": metadata,
                    }, ensure_ascii=False),
                },
            }],
        ),
        raw=raw,
    )


def _extract_tool_calls(message: Any, raw: dict[str, Any]) -> list[dict[str, Any]]:
    raw_calls = raw.get("tool_calls") or raw.get("toolCalls")
    if isinstance(raw_calls, list):
        return [_normalize_tool_call(item) for item in raw_calls if isinstance(item, dict)]
    name = _first_value(message, raw, "tool_name", "name")
    if not name and isinstance(raw.get("function"), dict):
        name = raw["function"].get("name")
    event_type = str(raw.get("type") or raw.get("sdk_event_type") or message.__class__.__name__).lower()
    if "tool" not in event_type and not name:
        return []
    if not name:
        return []
    return [_normalize_tool_call({
        "id": _first_value(message, raw, "id", "tool_call_id"),
        "name": name,
        "arguments": _first_value(message, raw, "arguments", "args", "input", "parameters"),
    })]


def _normalize_tool_call(call: dict[str, Any]) -> dict[str, Any]:
    function = call.get("function") if isinstance(call.get("function"), dict) else {}
    name = call.get("name") or call.get("tool_name") or function.get("name")
    arguments = call.get("arguments") or call.get("args") or call.get("input") or call.get("parameters")
    if arguments is None:
        arguments = function.get("arguments", {})
    if not isinstance(arguments, str):
        arguments = json.dumps(arguments or {}, ensure_ascii=False)
    return {
        "id": str(call.get("id") or call.get("tool_call_id") or "kimi-tool-call"),
        "type": "function",
        "function": {
            "name": str(name or "unknown_tool"),
            "arguments": arguments,
        },
    }


def _extract_usage(message: Any, raw: dict[str, Any]) -> dict[str, Any] | None:
    usage = raw.get("usage") or raw.get("token_usage")
    if not isinstance(usage, dict):
        return None
    return dict(usage)


def _first_value(message: Any, raw: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in raw and raw[name] not in (None, ""):
            return raw[name]
        value = getattr(message, name, None)
        if value not in (None, ""):
            return value
    return None


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
