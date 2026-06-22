"""Persisted research-agent runtime kernel."""

from __future__ import annotations

import json
import inspect
from typing import Any

from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.state_machine import ensure_transition
from doge.application.agent.tools import ToolRegistry
from doge.application.agent.tools import ToolResult
from doge.application.agent.web_search_stage import WebSearchStage
from doge.application.services.citation_service import CitationService
from doge.application.services.numerical_consistency_service import NumericalConsistencyService
from doge.core.domain.agent_models import (
    AgentEvent,
    AgentRun,
    EventType,
    RunStatus,
    utc_now,
)
from doge.core.domain.execution_profile import ProfileRegistry
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.domain.model_policy import ModelPolicy
from doge.core.ports.agent_model import IAgentModel
from doge.core.ports.agent_backend import IAgentBackend
from doge.core.ports.agent_repository import (
    IApprovalRepository,
    IArtifactRepository,
    IEventRepository,
    IRunRepository,
)
from doge.core.ports.event_publisher import IEventPublisher
from doge.core.ports.enterprise_governance import EnterpriseAuditEvent, IEnterpriseGovernanceRepository
from doge.core.ports.model_router import IModelRouter, RoutingDecision


class _NoopEventPublisher:
    async def publish(self, event: AgentEvent) -> None:
        return None


class RuntimeKernel:
    """Business logic for agent runs without owning storage policy."""

    def __init__(
        self,
        *,
        model: IAgentModel,
        tool_registry: ToolRegistry,
        run_repository: IRunRepository,
        event_repository: IEventRepository,
        artifact_repository: IArtifactRepository,
        approval_repository: IApprovalRepository,
        event_publisher: IEventPublisher | None = None,
        context_builder: ContextBuilder | None = None,
        response_assembler: ModelResponseAssembler | None = None,
        model_router: IModelRouter | None = None,
        web_search_stage: WebSearchStage | None = None,
        agent_backends: dict[str, IAgentBackend] | None = None,
        governance_repository: IEnterpriseGovernanceRepository | None = None,
    ) -> None:
        self._model = model
        self._tools = tool_registry
        self._runs = run_repository
        self._events = event_repository
        self._artifacts = artifact_repository
        self._approvals = approval_repository
        self._publisher = event_publisher or _NoopEventPublisher()
        self._context_builder = context_builder or ContextBuilder()
        self._response_assembler = response_assembler or ModelResponseAssembler()
        self._model_router = model_router
        self._web_search_stage = web_search_stage
        self._agent_backends = agent_backends or {}
        self._governance = governance_repository

    async def create_run(self, request: dict[str, Any]) -> AgentRun:
        run = AgentRun.create(
            workflow=request.get("workflow", "investment_research"),
            question=request.get("question", ""),
            session_id=request.get("session_id"),
            market=request.get("market", "us"),
            language=request.get("language", "en"),
            document_ids=list(request.get("document_ids", [])),
            portfolio_id=request.get("portfolio_id"),
            model_policy=ModelPolicy.from_dict(request.get("model_policy")),
        )
        self._runs.save(run)
        await self._add_event(run, EventType.RUN_CREATED, {"question": run.question, "workflow": run.workflow})
        return self._hydrate(run.run_id)

    async def run_to_pause_or_completion(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        policy = ModelPolicy.from_dict(run.model_policy)
        max_rounds = policy.max_tool_rounds
        for _ in range(max_rounds):
            run = await self.step(run_id)
            if run.status in {
                RunStatus.AWAITING_APPROVAL,
                RunStatus.CANCELLED,
                RunStatus.COMPLETED,
                RunStatus.FAILED,
            }:
                return run
        await self._fail(run, "max tool rounds exceeded")
        return self._hydrate(run_id)

    async def queue_run(self, run_id: str, reason: str = "queued") -> AgentRun:
        run = self._require_run(run_id)
        if run.status == RunStatus.QUEUED:
            return run
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        self._set_status(run, RunStatus.QUEUED)
        await self._add_event(run, EventType.RUN_QUEUED, {"reason": reason})
        return self._hydrate(run_id)

    async def step(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        if run.status == RunStatus.CANCELLING:
            return await self._mark_cancelled(run)

        self._set_status(run, RunStatus.RUNNING)
        policy = ModelPolicy.from_dict(run.model_policy)
        tenant_id = _tenant_id_for_policy(policy)
        enterprise_context = _enterprise_context_from_policy(policy)
        events = self._events.list_for_run(run.run_id, tenant_id=tenant_id)
        messages = self._context_builder.build(run, events, enterprise_context=enterprise_context)
        profile = ProfileRegistry.get(policy.execution_profile)
        if policy.web_search_enabled or (policy.web_search_enabled is None and profile.web_search_enabled):
            stage = self._web_search_stage or WebSearchStage(self._model)
            messages = await stage.execute(messages, run.question)
        routing = self._model_router.route(run, policy) if self._model_router is not None else None
        tool_schemas = self._tool_schemas_for(routing, enterprise_context)
        self._audit(
            enterprise_context,
            "model_route",
            "run",
            run.run_id,
            {
                "backend": getattr(routing, "backend", None),
                "model": getattr(routing, "model", None),
                "execution_profile": policy.execution_profile,
            },
            request_id=_request_id(policy),
        )
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
        chat_stream = self._chat_stream(messages, routing, chat_kwargs)
        response = await self._response_assembler.assemble(chat_stream)
        run = self._require_run(run_id)
        if run.status == RunStatus.CANCELLING:
            return await self._mark_cancelled(run)
        if response is None:
            await self._fail(run, "model unavailable")
            return self._hydrate(run.run_id)

        await self._add_event(run, EventType.MODEL_RESPONSE, {
            "message": response.message.to_api_dict(),
            "finish_reason": response.finish_reason,
            "usage": response.usage or {},
            "routing": _routing_payload(routing),
        })
        if _budget_exceeded(response.usage or {}, routing):
            await self._fail(run, "run budget exceeded")
            return self._hydrate(run.run_id)

        if response.message.tool_calls:
            for call in response.message.tool_calls:
                run = self._require_run(run_id)
                if run.status == RunStatus.CANCELLING:
                    return await self._mark_cancelled(run)
                function = call.get("function", {})
                name = function.get("name", "")
                arguments = function.get("arguments", "{}")
                await self._add_event(run, EventType.TOOL_CALL, {"tool_call": call})
                timeout = policy.tool_timeout_seconds
                if not self._can_execute_tool(enterprise_context, name, self._tool_category(name)):
                    result = ToolResult(name=name, data={}, ok=False, error="tool not permitted")
                    self._audit(
                        enterprise_context,
                        "tool_denied",
                        "tool",
                        name,
                        {"run_id": run.run_id},
                        request_id=_request_id(policy),
                    )
                else:
                    self._audit(
                        enterprise_context,
                        "tool_execute",
                        "tool",
                        name,
                        {"run_id": run.run_id},
                        request_id=_request_id(policy),
                    )
                    result = await self._tools.execute_async(
                        name,
                        arguments,
                        timeout_seconds=float(timeout) if timeout else None,
                        context=enterprise_context,
                    )
                run = self._require_run(run_id)
                if run.status == RunStatus.CANCELLING:
                    return await self._mark_cancelled(run)
                result_payload = json.loads(result.to_json())
                await self._add_event(run, EventType.TOOL_RESULT, {
                    "tool_call_id": call.get("id"),
                    "name": name,
                    "result": result_payload,
                })
                if result.data.get("approval_required"):
                    approval = run.add_approval(
                        action=result.data.get("action", name),
                        risk_level=result.data.get("risk_level", "high"),
                    )
                    self._approvals.save(approval, tenant_id=tenant_id)
                    self._set_status(run, RunStatus.AWAITING_APPROVAL)
                    await self._add_event(run, EventType.APPROVAL_REQUESTED, {
                        "approval_id": approval.approval_id,
                        "action": approval.action,
                        "risk_level": approval.risk_level,
                    })
                    return self._hydrate(run.run_id)
            self._set_status(run, RunStatus.RUNNING)
            return self._hydrate(run.run_id)

        content = response.message.content or _default_memo()
        artifact = run.add_artifact(
            kind="investment_memo",
            title="Investment Committee Memo",
            content=content,
            data={**self._artifact_metrics(run.run_id, content), "usage": response.usage or {}},
        )
        self._artifacts.save(artifact, tenant_id=tenant_id)
        self._set_status(run, RunStatus.COMPLETED)
        await self._add_event(run, EventType.ARTIFACT_CREATED, {
            "artifact_id": artifact.artifact_id,
            "kind": artifact.kind,
            "title": artifact.title,
        })
        return self._hydrate(run.run_id)

    async def resolve_approval(self, run_id: str, approval_id: str, approved: bool) -> AgentRun:
        run = self._require_run(run_id)
        tenant_id = _tenant_id_for_policy(run.model_policy)
        approval = self._approvals.get(approval_id, tenant_id=tenant_id)
        if approval is None or approval.run_id != run_id:
            raise KeyError(f"approval not found: {approval_id}")
        approval.status = "approved" if approved else "denied"
        approval.resolved_at = utc_now()
        self._approvals.save(approval, tenant_id=tenant_id)
        await self._add_event(run, EventType.APPROVAL_RESOLVED, {
            "approval_id": approval_id,
            "approved": approved,
        })
        if not approved:
            self._set_status(run, RunStatus.FAILED)
            return self._hydrate(run_id)
        self._set_status(run, RunStatus.QUEUED)
        await self._add_event(run, EventType.RUN_QUEUED, {"reason": "approval_resolved"})
        return self._hydrate(run_id)

    async def cancel_run(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        if run.status != RunStatus.CANCELLING:
            self._set_status(run, RunStatus.CANCELLING)
            run = self._require_run(run_id)
        run.cancel_requested_at = utc_now()
        self._runs.save(run)
        return self._hydrate(run_id)

    async def finalize_cancelled(self, run_id: str) -> AgentRun:
        run = self._require_run(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return run
        return await self._mark_cancelled(run)

    def get_run(self, run_id: str) -> AgentRun | None:
        return self._runs.get(run_id)

    def list_events(self, run_id: str) -> list[AgentEvent]:
        return self._events.list_for_run(run_id)

    def list_runs(self, session_id: str | None = None, limit: int = 20) -> list[AgentRun]:
        if session_id:
            return self._runs.list_by_session(session_id)
        return self._runs.list_recent(limit)

    def list_artifacts(self, run_id: str):
        return self._artifacts.list_for_run(run_id)

    async def _mark_cancelled(self, run: AgentRun) -> AgentRun:
        self._set_status(run, RunStatus.CANCELLED)
        await self._add_event(run, EventType.RUN_CANCELLED, {"cancelled": True})
        return self._hydrate(run.run_id)

    async def _fail(self, run: AgentRun, message: str) -> None:
        self._set_status(run, RunStatus.FAILED)
        await self._add_event(run, EventType.ERROR, {"message": message})

    def _set_status(self, run: AgentRun, status: RunStatus) -> None:
        ensure_transition(run.status, status)
        run.status = status
        run.updated_at = utc_now()
        self._runs.save(run)

    async def _add_event(self, run: AgentRun, event_type: EventType, payload: dict[str, Any]) -> AgentEvent:
        event = run.add_event(event_type, payload)
        event = self._events.append(event, tenant_id=_tenant_id_for_policy(run.model_policy))
        await self._publisher.publish(event)
        return event

    def _require_run(self, run_id: str) -> AgentRun:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

    def _hydrate(self, run_id: str) -> AgentRun:
        return self._require_run(run_id)

    def _artifact_metrics(self, run_id: str, artifact_text: str = "") -> dict[str, Any]:
        run = self._runs.get(run_id)
        tenant_id = _tenant_id_for_policy(run.model_policy) if run is not None else None
        events = self._events.list_for_run(run_id, tenant_id=tenant_id)
        results = [event.payload.get("result", {}) for event in events if event.event_type == EventType.TOOL_RESULT]
        tool_execution_success = None
        if results:
            ok_count = sum(1 for result in results if result.get("ok") is True)
            tool_execution_success = ok_count / len(results)
        evidence_records = _evidence_records_from_results(results)
        return {
            "numerical_consistency": NumericalConsistencyService().score_artifact(artifact_text, events),
            "citation_precision": CitationService().citation_precision_score(artifact_text, evidence_records),
            "tool_execution_success": tool_execution_success,
        }

    def _tool_schemas_for(
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

    def _filter_tool_schemas_by_acl(
        self,
        schemas: list[dict[str, Any]],
        context: EnterpriseContext | None,
    ) -> list[dict[str, Any]]:
        if not _is_enterprise_context(context):
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
        if not _is_enterprise_context(context):
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

    def _audit(
        self,
        context: EnterpriseContext | None,
        event_type: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> None:
        if not _is_enterprise_context(context) or self._governance is None:
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

    def _chat_stream(self, messages: list, routing: RoutingDecision | None, chat_kwargs: dict[str, Any]):
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


def _enterprise_context_from_policy(policy: ModelPolicy) -> EnterpriseContext:
    extra = policy.extra
    return EnterpriseContext(
        tenant_id=policy.tenant_id or _string_value(extra.get("tenant_id"), "local"),
        user_hash=policy.user_hash or _string_value(extra.get("user_hash"), "local-user"),
        role=_string_value(extra.get("role"), "analyst"),
        document_acl=frozenset(_string_set(extra.get("document_acl"))),
        tool_entitlement=frozenset(_string_set(extra.get("tool_entitlement"))),
        portfolio_permission=frozenset(_string_set(extra.get("portfolio_permission"))),
        data_classification=_string_value(extra.get("data_classification"), "internal"),
        approval_authority=frozenset(_string_set(extra.get("approval_authority"))),
        project_id=_string_value(extra.get("project_id"), "doge-dev"),
    )


def _request_id(policy: ModelPolicy) -> str | None:
    value = policy.extra.get("request_id")
    if value is None or value == "":
        return None
    return str(value)


def _tenant_id_for_policy(policy: ModelPolicy | dict[str, Any]) -> str | None:
    normalized = ModelPolicy.from_dict(policy)
    tenant_id = normalized.tenant_id or normalized.extra.get("tenant_id")
    return str(tenant_id) if tenant_id else None


def _is_enterprise_context(context: EnterpriseContext | None) -> bool:
    return context is not None and context.tenant_id != "local"


def _string_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return {str(item) for item in value if item is not None and str(item) != ""}
    return {str(value)}


def _string_value(value: Any, default: str) -> str:
    if value is None or value == "":
        return default
    return str(value)


def _routing_payload(routing: RoutingDecision | None) -> dict[str, Any]:
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


def _budget_exceeded(usage: dict[str, Any], routing: RoutingDecision | None) -> bool:
    if routing is None or routing.run_budget_usd is None:
        return False
    cost = usage.get("cost_usd")
    return cost is not None and float(cost) > float(routing.run_budget_usd)


def _evidence_records_from_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for result in results:
        data = result.get("data", {}) if isinstance(result, dict) else {}
        evidence = data.get("evidence") or data.get("results") or []
        if isinstance(evidence, list):
            records.extend(item for item in evidence if isinstance(item, dict))
    return records


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
