"""v1 workflow-template routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from doge.interfaces.api import deps
from doge.interfaces.api.handlers import WorkflowTemplateHandler
from doge.interfaces.gateway.routers._common import serialize
from doge.interfaces.gateway.routers._platform_common import (
    build_workflow_service,
    platform_context,
    raise_platform_error,
    require_workflow_templates,
)
from doge.platform.workspace import PlatformServiceError, WorkflowService

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class WorkflowTemplateCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    current_version: str = "1"
    input_schema: dict[str, Any] = Field(default_factory=dict)
    run_instructions: str = ""
    tool_policy: dict[str, Any] = Field(default_factory=dict)
    evidence_policy: dict[str, Any] = Field(default_factory=dict)
    output_contract: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    required_capabilities: list[str] | None = None
    eval_policy: list[str] | None = None
    approval_policy: dict[str, Any] | None = None
    ui_schema: dict[str, Any] | None = None


@router.get("/workflow-templates", dependencies=[Depends(require_workflow_templates)])
async def list_workflow_templates(
    request: Request,
    limit: int = 100,
    service: WorkflowService = Depends(build_workflow_service),
):
    try:
        items = WorkflowTemplateHandler(service=service).list(
            context=platform_context(request),
            limit=limit,
        )
        return {"workflow_templates": serialize(items)}
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.post("/workflow-templates", dependencies=[Depends(require_workflow_templates)], status_code=201)
async def create_workflow_template(
    request: Request,
    body: WorkflowTemplateCreate,
    service: WorkflowService = Depends(build_workflow_service),
):
    try:
        template = WorkflowTemplateHandler(service=service).create(
            context=platform_context(request),
            slug=body.slug,
            name=body.name,
            description=body.description,
            current_version=body.current_version,
            input_schema=body.input_schema,
            run_instructions=body.run_instructions,
            tool_policy=body.tool_policy,
            evidence_policy=body.evidence_policy,
            output_contract=body.output_contract,
            metadata=body.metadata,
            required_capabilities=body.required_capabilities,
            eval_policy=body.eval_policy,
            approval_policy=body.approval_policy,
            ui_schema=body.ui_schema,
        )
        return serialize(template)
    except PlatformServiceError as exc:
        raise_platform_error(exc)


@router.get("/workflow-templates/{template_id}", dependencies=[Depends(require_workflow_templates)])
async def get_workflow_template(
    request: Request,
    template_id: str,
    service: WorkflowService = Depends(build_workflow_service),
):
    try:
        template = WorkflowTemplateHandler(service=service).get(
            context=platform_context(request),
            template_id=template_id,
        )
        return serialize(template)
    except PlatformServiceError as exc:
        raise_platform_error(exc)
