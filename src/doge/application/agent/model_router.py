"""Application-layer routing from business profiles to Kimi model policy."""

from __future__ import annotations

from doge.config.settings import Settings, get_settings
from doge.core.domain.agent_models import AgentRun
from doge.core.domain.execution_profile import ExecutionProfile, ProfileRegistry
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import RunExecutionContext
from doge.core.ports.document_repository import IDocumentRepository
from doge.core.ports.model_router import RoutingDecision


class ModelRouter:
    """Resolve an execution profile into a provider/model/tool policy."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        document_repository: IDocumentRepository | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._documents = document_repository

    def route(
        self,
        run: AgentRun,
        policy: ModelPolicy,
        *,
        execution_context: RunExecutionContext | None = None,
    ) -> RoutingDecision:
        policy = execution_context.model_policy if execution_context is not None else policy
        profile_id = _infer_profile(run, policy, execution_context)
        spec = ProfileRegistry.get(profile_id)
        model = getattr(self._settings.kimi, spec.model_setting)
        model_family = policy.model_family or _model_family(model, spec.backend)
        thinking_enabled = spec.thinking_enabled if policy.thinking_enabled is None else policy.thinking_enabled
        if spec.profile == ExecutionProfile.QUANT_CODE and not thinking_enabled:
            raise ValueError(
                "execution_profile=quant_code requires thinking_enabled=True; "
                "K2.7-code thinking must remain enabled or omitted"
            )
        if model_family == "k2.7-code" and not thinking_enabled:
            raise ValueError(
                "kimi-k2.7-code does not support thinking_enabled=False; "
                "thinking must remain enabled or omitted"
            )
        files_purpose = self._purpose_for_documents(run.document_ids) or spec.files_purpose
        max_completion_tokens = policy.max_completion_tokens or getattr(
            self._settings.kimi,
            "max_completion_tokens",
            policy.max_tokens,
        )
        response_format = _response_format(policy)
        prompt_cache_key = policy.prompt_cache_key
        if not prompt_cache_key and getattr(self._settings.kimi, "prompt_cache_enabled", False):
            prompt_cache_key = run.session_id or run.run_id
        identity_snapshot = (
            execution_context.identity_snapshot
            if execution_context is not None
            else run.identity_snapshot
        )
        return RoutingDecision(
            backend=spec.backend,
            model=model,
            thinking_enabled=thinking_enabled,
            model_family=model_family,
            max_completion_tokens=max_completion_tokens,
            response_format=response_format,
            prompt_cache_key=prompt_cache_key,
            safety_identifier=identity_snapshot.user_hash if identity_snapshot is not None else None,
            run_budget_usd=policy.run_budget_usd or getattr(self._settings.kimi, "run_budget_usd", 0.0) or None,
            preserve_reasoning_content=model_family == "k2.7-code",
            files_purpose=files_purpose,
            tool_names=list(spec.tool_names) if spec.tool_names is not None else None,
            extra_body={},
        )

    def _purpose_for_documents(self, document_ids: list[str]) -> str | None:
        if self._documents is None:
            return None
        purposes: list[str] = []
        for document_id in document_ids:
            document = self._documents.get(document_id)
            if not document:
                continue
            purpose = document.get("kimi_file_purpose") or _purpose_from_mime(document.get("mime_type"))
            if purpose:
                purposes.append(purpose)
        if "video" in purposes:
            return "video"
        if "image" in purposes:
            return "image"
        return purposes[0] if purposes else None


def _purpose_from_mime(mime_type: str | None) -> str | None:
    if not mime_type:
        return None
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("video/"):
        return "video"
    return None


def _infer_profile(
    run: AgentRun,
    policy: ModelPolicy,
    execution_context: RunExecutionContext | None = None,
) -> str:
    if policy.execution_profile != ExecutionProfile.FINANCIAL_RESEARCH.value:
        return policy.execution_profile
    workflow = execution_context.workflow.workflow if execution_context is not None else run.workflow
    question = execution_context.question if execution_context is not None else run.question
    text = f"{workflow} {question}".lower()
    if any(token in text for token in ("python", "pandas", "notebook")):
        return ExecutionProfile.PYTHON_ANALYSIS.value
    if any(token in text for token in ("sql", "duckdb", "query")):
        return ExecutionProfile.SQL_QUERY.value
    if "backtest" in text or "回测" in text:
        return ExecutionProfile.BACKTEST.value
    if any(token in text for token in ("data pipeline", "etl", "数据管道")):
        return ExecutionProfile.DATA_PIPELINE.value
    return policy.execution_profile


def _model_family(model: str, backend: str) -> str:
    if backend == "scripted":
        return "scripted"
    if model.startswith("kimi-k2.7-code"):
        return "k2.7-code"
    return "k2.6"


def _response_format(policy: ModelPolicy) -> dict[str, Any] | None:
    if policy.response_schema:
        return {"type": "json_schema", "json_schema": policy.response_schema}
    if isinstance(policy.response_format, dict):
        return policy.response_format
    if policy.response_format == "json_schema":
        return {"type": "json_schema", "json_schema": {}}
    if policy.response_format == "json_object":
        return {"type": "json_object"}
    return None
