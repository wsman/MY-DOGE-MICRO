"""Research agent runtime."""

from __future__ import annotations

import asyncio
import json
import warnings
from typing import Any, AsyncIterator

from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.tools import ToolRegistry, build_default_tool_registry
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun, EventType, RunStatus, utc_now
from doge.core.ports.agent_model import AgentMessage, IAgentModel
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel


warnings.warn(
    "doge.application.agent.research_runtime.ResearchAgentRuntime is deprecated; "
    "use RuntimeKernel-backed infrastructure runtimes instead.",
    DeprecationWarning,
    stacklevel=2,
)


class ResearchAgentRuntime(IResearchAgentRuntime):
    """In-memory research-agent runtime suitable for the interview demo."""

    def __init__(
        self,
        model: IAgentModel | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        warnings.warn(
            "ResearchAgentRuntime is deprecated; use build_research_agent_runtime() "
            "or PersistedResearchAgentRuntime instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._model = model or ScriptedAgentModel()
        self._tools = tool_registry or build_default_tool_registry()
        self._runs: dict[str, AgentRun] = {}
        self._assembler = ModelResponseAssembler()

    async def create_run(self, request: dict[str, Any]) -> AgentRun:
        run = AgentRun.create(
            workflow=request.get("workflow", "investment_research"),
            question=request.get("question", ""),
            market=request.get("market", "us"),
            language=request.get("language", "en"),
            session_id=request.get("session_id"),
            document_ids=list(request.get("document_ids", [])),
            portfolio_id=request.get("portfolio_id"),
            model_policy=dict(request.get("model_policy", {})),
        )
        run.add_event(EventType.RUN_CREATED, {"question": run.question, "workflow": run.workflow})
        self._runs[run.run_id] = run
        return run

    async def run_to_pause_or_completion(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        max_rounds = int(run.model_policy.get("max_tool_rounds", 8) or 8)
        run.status = RunStatus.RUNNING
        for _ in range(max_rounds):
            await self.step(run_id)
            if run.status in (RunStatus.AWAITING_APPROVAL, RunStatus.CANCELLED, RunStatus.COMPLETED, RunStatus.FAILED):
                return run
        run.status = RunStatus.FAILED
        run.add_event(EventType.ERROR, {"message": "max tool rounds exceeded"})
        return run

    async def step(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status == RunStatus.CANCELLING:
            run.status = RunStatus.CANCELLED
            run.add_event(EventType.RUN_CANCELLED, {"cancelled": True})
            return run
        messages = self._build_messages(run)
        response = await self._assembler.assemble(
            self._model.chat(
                messages,
                tools=self._tools.schemas,
                tool_choice="auto",
                max_tokens=int(run.model_policy.get("max_tokens", 16384) or 16384),
                stream=bool(run.model_policy.get("stream", False)),
            )
        )
        if response is None:
            run.status = RunStatus.FAILED
            run.add_event(EventType.ERROR, {"message": "model unavailable"})
            return run

        message_dict = response.message.to_api_dict()
        run.add_event(EventType.MODEL_RESPONSE, {
            "message": message_dict,
            "finish_reason": response.finish_reason,
            "usage": response.usage or {},
        })

        if response.message.tool_calls:
            for call in response.message.tool_calls:
                function = call.get("function", {})
                name = function.get("name", "")
                arguments = function.get("arguments", "{}")
                run.add_event(EventType.TOOL_CALL, {"tool_call": call})
                result = self._tools.execute(name, arguments)
                run.add_event(EventType.TOOL_RESULT, {
                    "tool_call_id": call.get("id"),
                    "name": name,
                    "result": json.loads(result.to_json()),
                })
                if result.data.get("approval_required"):
                    approval = run.add_approval(
                        action=result.data.get("action", name),
                        risk_level=result.data.get("risk_level", "high"),
                    )
                    run.status = RunStatus.AWAITING_APPROVAL
                    run.add_event(EventType.APPROVAL_REQUESTED, {
                        "approval_id": approval.approval_id,
                        "action": approval.action,
                        "risk_level": approval.risk_level,
                    })
                    return run
            run.status = RunStatus.RUNNING
            return run

        content = response.message.content or _default_memo()
        artifact = run.add_artifact(
            kind="investment_memo",
            title="Investment Committee Memo",
            content=content,
            data={
                "numerical_consistency": None,
                "citation_precision": None,
                "tool_execution_success": _tool_execution_success(run.events),
                "usage": response.usage or {},
            },
        )
        run.status = RunStatus.COMPLETED
        run.add_event(EventType.ARTIFACT_CREATED, {
            "artifact_id": artifact.artifact_id,
            "kind": artifact.kind,
            "title": artifact.title,
        })
        return run

    def get_run(self, run_id: str) -> AgentRun | None:
        return self._runs.get(run_id)

    def list_runs(self, session_id: str | None = None, limit: int = 20) -> list[AgentRun]:
        runs = list(self._runs.values())
        if session_id:
            runs = [run for run in runs if run.session_id == session_id]
        return sorted(runs, key=lambda run: run.updated_at, reverse=True)[:limit]

    def list_events(self, run_id: str) -> list[AgentEvent]:
        run = self._require_run(run_id)
        return list(run.events)

    def list_artifacts(self, run_id: str) -> list[AgentArtifact]:
        run = self._require_run(run_id)
        return list(run.artifacts)

    async def stream_events(self, run_id: str) -> AsyncIterator[AgentEvent]:
        for event in self.list_events(run_id):
            yield event
            await asyncio.sleep(0)

    async def resolve_approval(self, run_id: str, approval_id: str, approved: bool) -> AgentRun:
        run = self._require_run(run_id)
        approval = next((item for item in run.approvals if item.approval_id == approval_id), None)
        if approval is None:
            raise KeyError(f"approval not found: {approval_id}")
        approval.status = "approved" if approved else "denied"
        approval.resolved_at = utc_now()
        run.add_event(EventType.APPROVAL_RESOLVED, {
            "approval_id": approval_id,
            "approved": approved,
        })
        if approved:
            run.status = RunStatus.RUNNING
            return await self.run_to_pause_or_completion(run_id)
        else:
            run.status = RunStatus.FAILED
        return run

    async def cancel_run(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            return run
        run.status = RunStatus.CANCELLING
        run.cancel_requested_at = utc_now()
        run.status = RunStatus.CANCELLED
        run.add_event(EventType.RUN_CANCELLED, {"cancelled": True})
        return run

    def _require_run(self, run_id: str) -> AgentRun:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

    def _build_messages(self, run: AgentRun) -> list[AgentMessage]:
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
        for event in run.events:
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


def _tool_execution_success(events: list[AgentEvent]) -> float | None:
    results = [
        event.payload.get("result", {})
        for event in events
        if event.event_type == EventType.TOOL_RESULT
    ]
    if not results:
        return None
    ok_count = sum(1 for result in results if result.get("ok") is True)
    return ok_count / len(results)
