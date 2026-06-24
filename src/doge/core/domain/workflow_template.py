"""Workflow template run-request helpers."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.platform_models import WorkflowTemplate
from doge.core.domain.run_execution_context import WorkflowRunContext


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
    }
    policy = ModelPolicy.from_dict(merged_policy)
    workflow_context = WorkflowRunContext(
        workflow=run_input.workflow or template.slug or "investment_research",
        template_id=template.template_id,
        template_slug=template.slug,
        template_version=template.current_version,
        template_name=template.name,
        template_metadata={
            "template_id": template.template_id,
            "slug": template.slug,
            "name": template.name,
            "version": template.current_version,
            "inputs": dict(run_input.inputs or {}),
            "input_keys": sorted(str(key) for key in (run_input.inputs or {}).keys()),
            "tool_policy": dict(template.tool_policy or {}),
            "evidence_policy": dict(template.evidence_policy or {}),
            "output_contract": dict(template.output_contract or {}),
        },
    )
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
    request = {
        "workflow": workflow_context.workflow,
        "question": run_input.question or template.run_instructions or template.name,
        "session_id": run_input.session_id,
        "market": run_input.market or "us",
        "language": run_input.language or "en",
        "document_ids": list(run_input.document_ids or []),
        "portfolio_id": run_input.portfolio_id,
        "model_policy": policy.to_dict(),
        "workflow_context": workflow_context.to_dict(),
        "template": metadata,
    }
    if tenant_id is not None or user_hash is not None:
        request["identity_snapshot"] = IdentitySnapshot(
            tenant_id=tenant_id or "local",
            user_hash=user_hash or "local-user",
        ).to_dict()
    return request


def validate_template_inputs(template: WorkflowTemplate, inputs: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Validate a constrained template input schema.

    The project intentionally supports a small JSON-Schema-like subset here:
    required keys, scalar/container type checks, and enum membership. This keeps
    workflow preflight deterministic without introducing a full schema engine.
    """

    schema = template.input_schema if isinstance(template.input_schema, dict) else {}
    values = inputs or {}
    errors: list[dict[str, Any]] = []
    required = schema.get("required", [])
    if isinstance(required, list):
        for key in required:
            if not isinstance(key, str):
                continue
            if key not in values or values.get(key) in (None, ""):
                errors.append({"field": key, "code": "required", "message": f"{key} is required"})

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        properties = {}
    for key, rules in properties.items():
        if key not in values or not isinstance(rules, dict):
            continue
        value = values[key]
        expected_type = rules.get("type")
        if isinstance(expected_type, str) and not _matches_type(value, expected_type):
            errors.append({
                "field": key,
                "code": "type",
                "message": f"{key} must be {expected_type}",
                "expected": expected_type,
            })
            continue
        enum = rules.get("enum")
        if isinstance(enum, list) and value not in enum:
            errors.append({
                "field": key,
                "code": "enum",
                "message": f"{key} must be one of {enum}",
                "allowed": enum,
            })
    return errors


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


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    return True
