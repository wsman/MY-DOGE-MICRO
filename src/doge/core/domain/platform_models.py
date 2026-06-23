"""Domain models for platform workspaces, cases, and templates."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from doge.core.domain.agent_models import utc_now


@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    name: str
    description: str = ""
    status: str = "active"
    tenant_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    deleted_at: str | None = None

    @classmethod
    def create(cls, *, name: str, description: str = "", tenant_id: str | None = None) -> "Workspace":
        now = utc_now()
        return cls(
            workspace_id=f"wsp-{uuid4().hex[:12]}",
            tenant_id=tenant_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Workspace":
        return cls(
            workspace_id=data["workspace_id"],
            tenant_id=data.get("tenant_id"),
            name=data["name"],
            description=data.get("description") or "",
            status=data.get("status") or "active",
            metadata=_json_obj(data.get("metadata")),
            created_at=data.get("created_at") or utc_now(),
            updated_at=data.get("updated_at") or utc_now(),
            deleted_at=data.get("deleted_at"),
        )


@dataclass(frozen=True)
class Project:
    project_id: str
    workspace_id: str
    name: str
    description: str = ""
    status: str = "active"
    default_market: str | None = None
    tenant_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    deleted_at: str | None = None

    @classmethod
    def create(
        cls,
        *,
        workspace_id: str,
        name: str,
        description: str = "",
        default_market: str | None = None,
        tenant_id: str | None = None,
    ) -> "Project":
        now = utc_now()
        return cls(
            project_id=f"prj-{uuid4().hex[:12]}",
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            name=name,
            description=description,
            default_market=default_market,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Project":
        return cls(
            project_id=data["project_id"],
            tenant_id=data.get("tenant_id"),
            workspace_id=data["workspace_id"],
            name=data["name"],
            description=data.get("description") or "",
            status=data.get("status") or "active",
            default_market=data.get("default_market"),
            metadata=_json_obj(data.get("metadata")),
            created_at=data.get("created_at") or utc_now(),
            updated_at=data.get("updated_at") or utc_now(),
            deleted_at=data.get("deleted_at"),
        )


@dataclass(frozen=True)
class ResearchCase:
    case_id: str
    project_id: str
    title: str
    thesis: str = ""
    status: str = "open"
    decision: str | None = None
    tenant_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    deleted_at: str | None = None

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        title: str,
        thesis: str = "",
        tenant_id: str | None = None,
    ) -> "ResearchCase":
        now = utc_now()
        return cls(
            case_id=f"case-{uuid4().hex[:12]}",
            tenant_id=tenant_id,
            project_id=project_id,
            title=title,
            thesis=thesis,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ResearchCase":
        return cls(
            case_id=data["case_id"],
            tenant_id=data.get("tenant_id"),
            project_id=data["project_id"],
            title=data["title"],
            thesis=data.get("thesis") or "",
            status=data.get("status") or "open",
            decision=data.get("decision"),
            metadata=_json_obj(data.get("metadata")),
            created_at=data.get("created_at") or utc_now(),
            updated_at=data.get("updated_at") or utc_now(),
            deleted_at=data.get("deleted_at"),
        )


@dataclass(frozen=True)
class WorkflowTemplate:
    template_id: str
    slug: str
    name: str
    description: str = ""
    status: str = "active"
    current_version: str = "1"
    input_schema: dict[str, Any] = field(default_factory=dict)
    run_instructions: str = ""
    tool_policy: dict[str, Any] = field(default_factory=dict)
    evidence_policy: dict[str, Any] = field(default_factory=dict)
    output_contract: dict[str, Any] = field(default_factory=dict)
    tenant_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        slug: str,
        name: str,
        description: str = "",
        tenant_id: str | None = None,
        current_version: str = "1",
    ) -> "WorkflowTemplate":
        now = utc_now()
        return cls(
            template_id=f"tpl-{uuid4().hex[:12]}",
            tenant_id=tenant_id,
            slug=slug,
            name=name,
            description=description,
            current_version=current_version,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "WorkflowTemplate":
        return cls(
            template_id=data["template_id"],
            tenant_id=data.get("tenant_id"),
            slug=data["slug"],
            name=data["name"],
            description=data.get("description") or "",
            status=data.get("status") or "active",
            current_version=data.get("current_version") or "1",
            input_schema=_json_obj(data.get("input_schema")),
            run_instructions=data.get("run_instructions") or "",
            tool_policy=_json_obj(data.get("tool_policy")),
            evidence_policy=_json_obj(data.get("evidence_policy")),
            output_contract=_json_obj(data.get("output_contract")),
            metadata=_json_obj(data.get("metadata")),
            created_at=data.get("created_at") or utc_now(),
            updated_at=data.get("updated_at") or utc_now(),
        )


@dataclass(frozen=True)
class CaseAssetLink:
    asset_link_id: str
    case_id: str
    asset_type: str
    asset_id: str
    asset_name: str = ""
    role: str = "source"
    version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tenant_id: str | None = None
    linked_at: str = field(default_factory=utc_now)
    deleted_at: str | None = None

    @classmethod
    def create(
        cls,
        *,
        case_id: str,
        asset_type: str,
        asset_id: str,
        asset_name: str = "",
        role: str = "source",
        version: str | None = None,
        metadata: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> "CaseAssetLink":
        return cls(
            asset_link_id=f"cal-{uuid4().hex[:12]}",
            case_id=case_id,
            asset_type=asset_type,
            asset_id=asset_id,
            asset_name=asset_name,
            role=role,
            version=version,
            metadata=metadata or {},
            tenant_id=tenant_id,
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "CaseAssetLink":
        return cls(
            asset_link_id=data["asset_link_id"],
            case_id=data["case_id"],
            tenant_id=data.get("tenant_id"),
            asset_type=data["asset_type"],
            asset_id=data["asset_id"],
            asset_name=data.get("asset_name") or "",
            role=data.get("role") or "source",
            version=data.get("version"),
            metadata=_json_obj(data.get("metadata")),
            linked_at=data.get("linked_at") or utc_now(),
            deleted_at=data.get("deleted_at"),
        )


@dataclass(frozen=True)
class WorkflowExecution:
    execution_id: str
    case_id: str
    template_id: str
    template_slug: str = ""
    template_version: str = "1"
    run_id: str | None = None
    status: str = "created"
    input_snapshot: dict[str, Any] = field(default_factory=dict)
    preflight_result: dict[str, Any] = field(default_factory=dict)
    trigger_channel: str = "api"
    tenant_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        case_id: str,
        template_id: str,
        template_slug: str = "",
        template_version: str = "1",
        run_id: str | None = None,
        status: str = "created",
        input_snapshot: dict[str, Any] | None = None,
        preflight_result: dict[str, Any] | None = None,
        trigger_channel: str = "api",
        tenant_id: str | None = None,
    ) -> "WorkflowExecution":
        now = utc_now()
        return cls(
            execution_id=f"exec-{uuid4().hex[:12]}",
            case_id=case_id,
            template_id=template_id,
            template_slug=template_slug,
            template_version=template_version,
            run_id=run_id,
            status=status,
            input_snapshot=input_snapshot or {},
            preflight_result=preflight_result or {},
            trigger_channel=trigger_channel,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "WorkflowExecution":
        return cls(
            execution_id=data["execution_id"],
            case_id=data["case_id"],
            tenant_id=data.get("tenant_id"),
            template_id=data["template_id"],
            template_slug=data.get("template_slug") or "",
            template_version=data.get("template_version") or "1",
            run_id=data.get("run_id"),
            status=data.get("status") or "created",
            input_snapshot=_json_obj(data.get("input_snapshot")),
            preflight_result=_json_obj(data.get("preflight_result")),
            trigger_channel=data.get("trigger_channel") or "api",
            created_at=data.get("created_at") or utc_now(),
            updated_at=data.get("updated_at") or utc_now(),
        )


@dataclass(frozen=True)
class CaseDecision:
    decision_id: str
    case_id: str
    decision_type: str
    rationale: str = ""
    actor_hash: str | None = None
    source_run_ids: list[str] = field(default_factory=list)
    source_execution_ids: list[str] = field(default_factory=list)
    tenant_id: str | None = None
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        case_id: str,
        decision_type: str,
        rationale: str = "",
        actor_hash: str | None = None,
        source_run_ids: list[str] | None = None,
        source_execution_ids: list[str] | None = None,
        tenant_id: str | None = None,
    ) -> "CaseDecision":
        return cls(
            decision_id=f"dec-{uuid4().hex[:12]}",
            case_id=case_id,
            decision_type=decision_type,
            rationale=rationale,
            actor_hash=actor_hash,
            source_run_ids=source_run_ids or [],
            source_execution_ids=source_execution_ids or [],
            tenant_id=tenant_id,
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "CaseDecision":
        return cls(
            decision_id=data["decision_id"],
            case_id=data["case_id"],
            tenant_id=data.get("tenant_id"),
            decision_type=data["decision_type"],
            rationale=data.get("rationale") or "",
            actor_hash=data.get("actor_hash"),
            source_run_ids=_json_list(data.get("source_run_ids")),
            source_execution_ids=_json_list(data.get("source_execution_ids")),
            created_at=data.get("created_at") or utc_now(),
        )


@dataclass(frozen=True)
class TemplatePreflightResult:
    valid: bool
    input_errors: list[dict[str, Any]] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    missing_assets: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    estimated_cost: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "input_errors": self.input_errors,
            "missing_capabilities": self.missing_capabilities,
            "missing_assets": self.missing_assets,
            "warnings": self.warnings,
            "estimated_cost": self.estimated_cost,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "TemplatePreflightResult":
        return cls(
            valid=bool(data.get("valid")),
            input_errors=list(data.get("input_errors") or []),
            missing_capabilities=list(data.get("missing_capabilities") or []),
            missing_assets=list(data.get("missing_assets") or []),
            warnings=list(data.get("warnings") or []),
            estimated_cost=_json_obj(data.get("estimated_cost")),
        )


@dataclass(frozen=True)
class CaseRunLink:
    case_id: str
    run_id: str
    link_type: str = "primary"
    tenant_id: str | None = None
    linked_at: str = field(default_factory=utc_now)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "CaseRunLink":
        return cls(
            case_id=data["case_id"],
            run_id=data["run_id"],
            tenant_id=data.get("tenant_id"),
            link_type=data.get("link_type") or "primary",
            linked_at=data.get("linked_at") or utc_now(),
        )


@dataclass(frozen=True)
class WorkflowTemplateRunLink:
    template_id: str
    run_id: str
    tenant_id: str | None = None
    linked_at: str = field(default_factory=utc_now)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "WorkflowTemplateRunLink":
        return cls(
            template_id=data["template_id"],
            run_id=data["run_id"],
            tenant_id=data.get("tenant_id"),
            linked_at=data.get("linked_at") or utc_now(),
        )


def to_dict(value) -> dict[str, Any]:
    data = dict(value.__dict__)
    return data


def _json_obj(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    return {}


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, str) and value:
        loaded = json.loads(value)
        if isinstance(loaded, list):
            return [str(item) for item in loaded if item is not None]
    return []
