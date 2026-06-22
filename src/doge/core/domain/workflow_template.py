"""Workflow template run-request helpers."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.platform_models import WorkflowTemplate


@dataclass(frozen=True)
class TemplateRunInput:
    question: str | None = None
    workflow: str | None = None
    session_id: str | None = None
    market: str = "us"
    language: str = "en"
    document_ids: list[str] = field(default_factory=list)
    portfolio_id: str | None = None
    model_policy: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)


_MODEL_POLICY_FIELDS = {item.name for item in fields(ModelPolicy) if item.name != "extra"}


def build_template_run_request(
    template: WorkflowTemplate,
    run_input: TemplateRunInput,
    *,
    tenant_id: str | None = None,
    user_hash: str | None = None,
) -> dict[str, Any]:
    """Build a RuntimeKernel request from a workflow template and user input."""

    template_policy = _extract_template_model_policy(template.tool_policy)
    merged_policy = {
        **template_policy,
        **(run_input.model_policy or {}),
        "template_id": template.template_id,
        "template_slug": template.slug,
        "template_version": template.current_version,
        "template_name": template.name,
    }
    if tenant_id is not None and not merged_policy.get("tenant_id"):
        merged_policy["tenant_id"] = tenant_id
    if user_hash is not None and not merged_policy.get("user_hash"):
        merged_policy["user_hash"] = user_hash
    policy = ModelPolicy.from_dict(merged_policy)
    metadata = {
        "template_id": template.template_id,
        "slug": template.slug,
        "name": template.name,
        "version": template.current_version,
        "inputs": dict(run_input.inputs or {}),
        "input_keys": sorted(str(key) for key in (run_input.inputs or {}).keys()),
        "tool_policy": dict(template.tool_policy or {}),
        "evidence_policy": dict(template.evidence_policy or {}),
        "output_contract": dict(template.output_contract or {}),
    }
    return {
        "workflow": run_input.workflow or template.slug or "investment_research",
        "question": run_input.question or template.run_instructions or template.name,
        "session_id": run_input.session_id,
        "market": run_input.market or "us",
        "language": run_input.language or "en",
        "document_ids": list(run_input.document_ids or []),
        "portfolio_id": run_input.portfolio_id,
        "model_policy": policy.to_dict(),
        "template": metadata,
    }


def _extract_template_model_policy(tool_policy: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(tool_policy, dict):
        return {}
    policy: dict[str, Any] = {}
    nested = tool_policy.get("model_policy")
    if isinstance(nested, dict):
        policy.update(nested)
    for key in _MODEL_POLICY_FIELDS:
        if key in tool_policy:
            policy[key] = tool_policy[key]
    return policy
