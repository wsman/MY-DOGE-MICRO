"""Runtime execution services used by RuntimeKernel."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable

from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.tools import ToolRegistry, ToolResult
from doge.application.agent.web_search_stage import WebSearchStage
from doge.application.services.citation_service import CitationService
from doge.application.services.numerical_consistency_service import NumericalConsistencyService
from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.domain.execution_profile import ProfileRegistry
from doge.core.domain.model_policy import ModelPolicy
from doge.core.ports.agent_backend import IAgentBackend
from doge.core.ports.agent_model import IAgentModel
from doge.core.ports.enterprise_governance import EnterpriseAuditEvent, IEnterpriseGovernanceRepository
from doge.core.ports.model_router import IModelRouter, RoutingDecision


@dataclass(frozen=True)
class ModelExecutionResult:
    response: Any
    routing: RoutingDecision | None
    routing_payload: dict[str, Any]
    budget_exceeded: bool = False


class ModelExecutionService:
    """Execute the model turn after RuntimeKernel prepares run context."""

    def __init__(
        self,
        *,
        model: IAgentModel,
        response_assembler: ModelResponseAssembler | None = None,
        model_router: IModelRouter | None = None,
        web_search_stage: WebSearchStage | None = None,
        agent_backends: dict[str, IAgentBackend] | None = None,
    ) -> None:
        self._model = model
        self._response_assembler = response_assembler or ModelResponseAssembler()
        self._model_router = model_router
        self._web_search_stage = web_search_stage
        self._agent_backends = agent_backends or {}

    async def execute(
        self,
        *,
        run: AgentRun,
        policy: ModelPolicy,
        messages: list[Any],
        tool_schemas_for: Callable[[RoutingDecision | None], list[dict[str, Any]]],
    ) -> ModelExecutionResult:
        profile = ProfileRegistry.get(policy.execution_profile)
        if policy.web_search_enabled or (policy.web_search_enabled is None and profile.web_search_enabled):
            stage = self._web_search_stage or WebSearchStage(self._model)
            messages = await stage.execute(messages, run.question)
        routing = self._model_router.route(run, policy) if self._model_router is not None else None
        tool_schemas = tool_schemas_for(routing)
        chat_kwargs = self._chat_kwargs(run, policy, routing, tool_schemas)
        chat_stream = self._chat_stream(messages, routing, chat_kwargs)
        response = await self._response_assembler.assemble(chat_stream)
        return ModelExecutionResult(
            response=response,
            routing=routing,
            routing_payload=routing_payload(routing),
            budget_exceeded=budget_exceeded(getattr(response, "usage", None) or {}, routing),
        )

    def _chat_kwargs(
        self,
        run: AgentRun,
        policy: ModelPolicy,
        routing: RoutingDecision | None,
        tool_schemas: list[dict[str, Any]],
    ) -> dict[str, Any]:
        chat_kwargs: dict[str, Any] = {
            "tools": tool_schemas,
            "tool_choice": "auto",
            "max_tokens": policy.max_tokens,
            "max_completion_tokens": policy.max_completion_tokens,
            "stream": policy.stream,
            "response_format": None,
            "prompt_cache_key": None,
            "safety_identifier": policy.user_hash,
            "request_metadata": {
                "run_id": run.run_id,
                "workflow": run.workflow,
                "execution_profile": policy.execution_profile,
            },
        }
        if routing is not None and self._model_accepts_routing_kwargs():
            chat_kwargs.update({
                "model": routing.model,
                "thinking_enabled": routing.thinking_enabled,
                "extra_body": routing.extra_body,
                "max_completion_tokens": routing.max_completion_tokens,
                "response_format": routing.response_format,
                "prompt_cache_key": routing.prompt_cache_key,
                "safety_identifier": routing.safety_identifier or policy.user_hash,
            })
        return chat_kwargs

    def _chat_stream(self, messages: list[Any], routing: RoutingDecision | None, chat_kwargs: dict[str, Any]):
        if routing is not None and routing.backend != "direct_kimi_api":
            backend = self._agent_backends.get(routing.backend)
            if backend is None:
                raise RuntimeError(f"agent backend is not configured: {routing.backend}")
            return backend.chat(
                messages,
                tools=chat_kwargs["tools"],
                tool_choice=chat_kwargs["tool_choice"],
                max_tokens=chat_kwargs["max_tokens"],
                request_metadata=chat_kwargs.get("request_metadata"),
                prompt_cache_key=chat_kwargs.get("prompt_cache_key"),
                model=(routing.model if routing is not None else None),
            )
        return self._model.chat(messages, **self._model_chat_kwargs(chat_kwargs))

    def _model_accepts_routing_kwargs(self) -> bool:
        signature = inspect.signature(self._model.chat)
        parameters = signature.parameters
        if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
            return True
        return {"model", "thinking_enabled", "extra_body"}.issubset(parameters)

    def _model_chat_kwargs(self, chat_kwargs: dict[str, Any]) -> dict[str, Any]:
        signature = inspect.signature(self._model.chat)
        parameters = signature.parameters
        if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
            return chat_kwargs
        accepted = {
            name for name, parameter in parameters.items()
            if name != "messages" and parameter.kind in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
        }
        return {key: value for key, value in chat_kwargs.items() if key in accepted}


class ToolExecutionService:
    """Filter schemas, enforce tool ACL, execute tools, and audit tool calls."""

    def __init__(
        self,
        *,
        tool_registry: ToolRegistry,
        governance_repository: IEnterpriseGovernanceRepository | None = None,
    ) -> None:
        self._tools = tool_registry
        self._governance = governance_repository

    def schemas_for(
        self,
        routing: RoutingDecision | None,
        context: EnterpriseContext | None = None,
    ) -> list[dict[str, Any]]:
        schemas = (
            self._tools.schemas_for_context(context)
            if hasattr(self._tools, "schemas_for_context")
            else self._tools.schemas
        )
        if routing is not None and routing.tool_names is not None:
            allowed = set(routing.tool_names)
            schemas = [
                schema for schema in schemas
                if schema.get("function", {}).get("name") in allowed
            ]
        return self._filter_tool_schemas_by_acl(schemas, context)

    async def execute(
        self,
        *,
        context: EnterpriseContext | None,
        tool_name: str,
        arguments: str,
        run_id: str,
        timeout_seconds: float | None,
        request_id: str | None,
    ) -> ToolResult:
        category = self._tool_category(tool_name)
        if not self._can_execute_tool(context, tool_name, category):
            self.audit(
                context,
                "tool_denied",
                "tool",
                tool_name,
                {"run_id": run_id},
                request_id=request_id,
            )
            return ToolResult(name=tool_name, data={}, ok=False, error="tool not permitted")
        self.audit(
            context,
            "tool_execute",
            "tool",
            tool_name,
            {"run_id": run_id},
            request_id=request_id,
        )
        return await self._tools.execute_async(
            tool_name,
            arguments,
            timeout_seconds=timeout_seconds,
            context=context,
        )

    def audit(
        self,
        context: EnterpriseContext | None,
        event_type: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> None:
        if not is_enterprise_context(context) or self._governance is None:
            return
        self._governance.append_audit_event(
            EnterpriseAuditEvent(
                tenant_id=context.tenant_id,
                actor_hash=context.user_hash,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=request_id,
                metadata=metadata or {},
            )
        )

    def _filter_tool_schemas_by_acl(
        self,
        schemas: list[dict[str, Any]],
        context: EnterpriseContext | None,
    ) -> list[dict[str, Any]]:
        if not is_enterprise_context(context):
            return schemas
        return [
            schema for schema in schemas
            if self._can_execute_tool(
                context,
                schema.get("function", {}).get("name", ""),
                schema.get("x-doge-category"),
            )
        ]

    def _can_execute_tool(
        self,
        context: EnterpriseContext | None,
        tool_name: str,
        category: str | None = None,
    ) -> bool:
        if not is_enterprise_context(context):
            return True
        if "*" in context.tool_entitlement or tool_name in context.tool_entitlement:
            return True
        if category is not None and category in context.tool_entitlement:
            return True
        if self._governance is None:
            return False
        return self._governance.is_allowed(context, "tool", tool_name, "execute")

    def _tool_category(self, tool_name: str) -> str | None:
        categories = getattr(self._tools, "_categories", {})
        category = categories.get(tool_name) if isinstance(categories, dict) else None
        if category is None:
            return None
        return getattr(category, "value", str(category))


class ArtifactEvaluationService:
    """Build artifact content defaults and deterministic eval metrics."""

    def artifact_content(self, content: str | None) -> str:
        return content or default_memo()

    def metrics(self, artifact_text: str, events: list[AgentEvent]) -> dict[str, Any]:
        results = [event.payload.get("result", {}) for event in events if event.event_type == EventType.TOOL_RESULT]
        tool_execution_success = None
        if results:
            ok_count = sum(1 for result in results if result.get("ok") is True)
            tool_execution_success = ok_count / len(results)
        evidence_records = evidence_records_from_results(results)
        return {
            "numerical_consistency": NumericalConsistencyService().score_artifact(artifact_text, events),
            "citation_precision": CitationService().citation_precision_score(artifact_text, evidence_records),
            "tool_execution_success": tool_execution_success,
        }


def routing_payload(routing: RoutingDecision | None) -> dict[str, Any]:
    if routing is None:
        return {}
    return {
        "backend": routing.backend,
        "model": routing.model,
        "model_family": routing.model_family,
        "max_completion_tokens": routing.max_completion_tokens,
        "prompt_cache_key": routing.prompt_cache_key,
        "run_budget_usd": routing.run_budget_usd,
        "preserve_reasoning_content": routing.preserve_reasoning_content,
    }


def budget_exceeded(usage: dict[str, Any], routing: RoutingDecision | None) -> bool:
    if routing is None or routing.run_budget_usd is None:
        return False
    cost = usage.get("cost_usd")
    return cost is not None and float(cost) > float(routing.run_budget_usd)


def evidence_records_from_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for result in results:
        data = result.get("data", {}) if isinstance(result, dict) else {}
        evidence = data.get("evidence") or data.get("results") or []
        if isinstance(evidence, list):
            records.extend(item for item in evidence if isinstance(item, dict))
    return records


def is_enterprise_context(context: EnterpriseContext | None) -> bool:
    return context is not None and context.tenant_id != "local"


def default_memo() -> str:
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
