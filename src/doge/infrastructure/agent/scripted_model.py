"""Deterministic agent model for offline demos and tests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from doge.core.ports.agent_model import AgentMessage, AgentResponse, IAgentModel


@dataclass(frozen=True)
class ScriptedToolCall:
    """Declarative tool call emitted by a scripted scenario step."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ScriptedToolCall":
        return cls(
            name=str(data["name"]),
            arguments=dict(data.get("arguments") or {}),
            call_id=data.get("id") or data.get("call_id"),
        )


@dataclass(frozen=True)
class ScriptedStep:
    """One scenario transition keyed by already completed tool names."""

    required_tools: tuple[str, ...] = ()
    required_portfolio_marker: bool = False
    reasoning_content: str = ""
    tool_call: ScriptedToolCall | None = None
    final_memo: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any], *, base_dir: Path) -> "ScriptedStep":
        final_memo = data.get("final_memo")
        final_memo_path = data.get("final_memo_path")
        if final_memo is None and final_memo_path:
            final_memo = (base_dir / str(final_memo_path)).read_text(encoding="utf-8")
        tool_call_data = data.get("tool_call") or data.get("next_tool_call")
        return cls(
            required_tools=tuple(str(item) for item in data.get("required_tools", ())),
            required_portfolio_marker=bool(data.get("required_portfolio_marker", False)),
            reasoning_content=str(data.get("reasoning_content") or ""),
            tool_call=ScriptedToolCall.from_mapping(tool_call_data) if tool_call_data else None,
            final_memo=final_memo,
        )


@dataclass(frozen=True)
class ScriptedScenario:
    """JSON-loadable offline model scenario."""

    steps: tuple[ScriptedStep, ...]

    @classmethod
    def from_mapping(cls, data: dict[str, Any], *, base_dir: Path) -> "ScriptedScenario":
        steps = tuple(ScriptedStep.from_mapping(item, base_dir=base_dir) for item in data.get("steps", ()))
        if not steps:
            raise ValueError("scripted scenario requires at least one step")
        return cls(steps=steps)

    @classmethod
    def from_path(cls, path: str | Path) -> "ScriptedScenario":
        config_path = Path(path)
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return cls.from_mapping(data, base_dir=config_path.parent)


class ScriptedAgentModel(IAgentModel):
    """Deterministic model used when no live Kimi key is available."""

    def __init__(self, scenario: ScriptedScenario | None = None) -> None:
        self._scenario = scenario

    @classmethod
    def from_config(cls, path: str | Path) -> "ScriptedAgentModel":
        return cls(ScriptedScenario.from_path(path))

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
        if self._scenario is not None:
            yield _scenario_response(self._scenario, messages, model=model)
            return

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
            yield _memo_response(_default_memo(), model=model)


def _scenario_response(
    scenario: ScriptedScenario,
    messages: list[AgentMessage],
    *,
    model: str | None,
) -> AgentResponse:
    tool_result_names = {message.name for message in messages if message.role == "tool"}
    portfolio_id = _authorized_portfolio_id(messages)
    eligible = [
        step
        for step in scenario.steps
        if set(step.required_tools).issubset(tool_result_names)
        and (not step.required_portfolio_marker or bool(portfolio_id))
    ]
    for step in sorted(
        eligible,
        key=lambda item: (len(item.required_tools), item.required_portfolio_marker),
        reverse=True,
    ):
        if step.tool_call is not None:
            return _tool_call_response(step, portfolio_id=portfolio_id)
        if step.final_memo is not None:
            return _memo_response(step.final_memo, model=model)
    return _memo_response(_default_memo(), model=model)


def _tool_call_response(step: ScriptedStep, *, portfolio_id: str | None) -> AgentResponse:
    assert step.tool_call is not None
    arguments = _render_arguments(step.tool_call.arguments, portfolio_id=portfolio_id)
    tool_name = step.tool_call.name
    call_id = step.tool_call.call_id or f"call-{tool_name.replace('_', '-')}"
    return AgentResponse(message=AgentMessage(
        role="assistant",
        content="",
        reasoning_content=step.reasoning_content or f"Need {tool_name} before continuing.",
        tool_calls=[{
            "id": call_id,
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": json.dumps(arguments, separators=(",", ":")),
            },
        }],
    ))


def _memo_response(content: str, *, model: str | None) -> AgentResponse:
    return AgentResponse(
        message=AgentMessage(role="assistant", content=content),
        finish_reason="stop",
        usage={
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cached_tokens": 0,
            "total_tokens": 0,
            "model": model or "scripted",
            "latency_ms": 0.0,
            "cost_usd": 0.0,
        },
    )


def _render_arguments(value: Any, *, portfolio_id: str | None) -> Any:
    if isinstance(value, str):
        return value.replace("{portfolio_id}", portfolio_id or "")
    if isinstance(value, list):
        return [_render_arguments(item, portfolio_id=portfolio_id) for item in value]
    if isinstance(value, dict):
        return {key: _render_arguments(item, portfolio_id=portfolio_id) for key, item in value.items()}
    return value


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
