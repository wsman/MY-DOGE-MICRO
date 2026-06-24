"""Workspace and workflow application services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from doge.core.domain.agent_models import AgentRun
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.domain.platform_models import (
    CaseAssetLink,
    CaseDecision,
    CaseRunLink,
    Project,
    ResearchCase,
    TemplatePreflightResult,
    WorkflowTemplate,
    WorkflowExecution,
    Workspace,
)
from doge.core.domain.workflow_template import (
    TemplateRunInput,
    build_template_run_request,
    validate_template_inputs,
)
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.enterprise_governance import (
    EnterpriseAclGrant,
    EnterpriseAuditEvent,
    IEnterpriseGovernanceRepository,
)
from doge.core.ports.platform_repository import IPlatformRepository


class PlatformServiceError(Exception):
    """Base error for platform workspace services."""


class PlatformNotFoundError(PlatformServiceError):
    """Requested platform object was not found."""


class PlatformAccessDeniedError(PlatformServiceError):
    """Actor is not allowed to access a platform object."""


class PlatformValidationError(PlatformServiceError):
    """Request data is structurally valid but not actionable."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class PlatformFeatureDisabledError(PlatformServiceError):
    """A required feature flag is disabled."""


@dataclass(frozen=True)
class PlatformRequestContext:
    """Request identity and audit context for platform services."""

    enterprise_context: EnterpriseContext = field(default_factory=EnterpriseContext)
    enterprise_request: bool = False
    request_id: str | None = None

    @property
    def tenant_id(self) -> str | None:
        return self.enterprise_context.tenant_id if self.enterprise_request else None

    @property
    def user_hash(self) -> str | None:
        return self.enterprise_context.user_hash if self.enterprise_request else None


@dataclass(frozen=True)
class CaseRunCreate:
    run_id: str | None = None
    template_id: str | None = None
    link_type: str = "primary"
    question: str | None = None
    workflow: str | None = None
    session_id: str | None = None
    market: str = "us"
    language: str = "en"
    document_ids: list[str] = field(default_factory=list)
    portfolio_id: str | None = None
    model_policy: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseAssetCreate:
    asset_type: str
    asset_id: str
    asset_name: str = ""
    role: str = "source"
    version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseDecisionCreate:
    decision_type: str
    rationale: str = ""
    source_run_ids: list[str] = field(default_factory=list)
    source_execution_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CaseExecutionCreate:
    template_id: str
    question: str | None = None
    workflow: str | None = None
    session_id: str | None = None
    market: str = "us"
    language: str = "en"
    document_ids: list[str] = field(default_factory=list)
    portfolio_id: str | None = None
    asset_link_ids: list[str] = field(default_factory=list)
    model_policy: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    skip_preflight: bool = False
    trigger_channel: str = "api"


@dataclass(frozen=True)
class CaseRunCreateResult:
    link: CaseRunLink
    run: AgentRun | None = None
    template: WorkflowTemplate | None = None

    def to_dict(self) -> dict[str, Any]:
        data = dict(self.link.__dict__)
        if self.template is not None:
            data["template_id"] = self.template.template_id
            data["template_slug"] = self.template.slug
        return data


@dataclass(frozen=True)
class CaseExecutionCreateResult:
    execution: WorkflowExecution
    run: AgentRun | None = None
    preflight: TemplatePreflightResult | None = None

    def to_dict(self) -> dict[str, Any]:
        data = dict(self.execution.__dict__)
        if self.run is not None:
            data["run_status"] = self.run.status.value
        if self.preflight is not None:
            data["preflight_result"] = self.preflight.to_dict()
        data["links"] = _execution_links(self.execution.run_id)
        return data


class WorkspaceService:
    """Application service for Workspace objects."""

    def __init__(self, repo: IPlatformRepository, governance: IEnterpriseGovernanceRepository) -> None:
        self._repo = repo
        self._access = PlatformAccessService(governance)

    def list(self, context: PlatformRequestContext, *, limit: int = 100) -> list[Workspace]:
        items = self._repo.list_workspaces(limit=limit, tenant_id=context.tenant_id)
        items = self._access.filter_items(context, "workspace", items, "workspace_id")
        self._access.audit(context, "workspace_list", "workspace", "*", metadata={"count": len(items)})
        return items

    def create(self, context: PlatformRequestContext, *, name: str, description: str = "") -> Workspace:
        workspace = Workspace.create(name=name, description=description, tenant_id=context.tenant_id)
        self._repo.save_workspace(workspace)
        self._access.grant_creator(context, "workspace", workspace.workspace_id, provenance="workspace_create")
        self._access.audit(context, "workspace_create", "workspace", workspace.workspace_id)
        return workspace

    def get(self, context: PlatformRequestContext, workspace_id: str) -> Workspace:
        workspace = self._repo.get_workspace(workspace_id, tenant_id=context.tenant_id)
        if workspace is None:
            raise PlatformNotFoundError("workspace not found")
        self._access.ensure(context, "workspace", workspace_id, "read")
        self._access.audit(context, "workspace_read", "workspace", workspace_id)
        return workspace


class ProjectService:
    """Application service for Project objects."""

    def __init__(self, repo: IPlatformRepository, governance: IEnterpriseGovernanceRepository) -> None:
        self._repo = repo
        self._access = PlatformAccessService(governance)

    def list(
        self,
        context: PlatformRequestContext,
        *,
        workspace_id: str | None = None,
        limit: int = 100,
    ) -> list[Project]:
        items = self._repo.list_projects(workspace_id=workspace_id, limit=limit, tenant_id=context.tenant_id)
        items = self._access.filter_items(context, "project", items, "project_id")
        self._access.audit(context, "project_list", "project", "*", metadata={"count": len(items)})
        return items

    def create(
        self,
        context: PlatformRequestContext,
        *,
        workspace_id: str,
        name: str,
        description: str = "",
        default_market: str | None = None,
    ) -> Project:
        workspace = self._repo.get_workspace(workspace_id, tenant_id=context.tenant_id)
        if workspace is None:
            raise PlatformNotFoundError("workspace not found")
        self._access.ensure(context, "workspace", workspace_id, "read")
        project = Project.create(
            workspace_id=workspace_id,
            name=name,
            description=description,
            default_market=default_market,
            tenant_id=context.tenant_id,
        )
        self._repo.save_project(project)
        self._access.grant_creator(context, "project", project.project_id, provenance="project_create")
        self._access.audit(context, "project_create", "project", project.project_id)
        return project

    def get(self, context: PlatformRequestContext, project_id: str) -> Project:
        project = self._repo.get_project(project_id, tenant_id=context.tenant_id)
        if project is None:
            raise PlatformNotFoundError("project not found")
        self._access.ensure(context, "project", project_id, "read")
        self._access.audit(context, "project_read", "project", project_id)
        return project


class ResearchCaseService:
    """Application service for Research Case objects and case-run links."""

    def __init__(
        self,
        repo: IPlatformRepository,
        governance: IEnterpriseGovernanceRepository,
        runtime: IResearchAgentRuntime,
        *,
        document_repository: Any | None = None,
        portfolio_repository: Any | None = None,
        capability_registry: Any | None = None,
        capability_registry_enabled: bool = False,
    ) -> None:
        self._repo = repo
        self._runtime = runtime
        self._documents = document_repository
        self._portfolios = portfolio_repository
        self._capability_registry = capability_registry
        self._capability_registry_enabled = capability_registry_enabled
        self._access = PlatformAccessService(governance)

    def list(
        self,
        context: PlatformRequestContext,
        *,
        project_id: str | None = None,
        limit: int = 100,
    ) -> list[ResearchCase]:
        items = self._repo.list_cases(project_id=project_id, limit=limit, tenant_id=context.tenant_id)
        items = self._access.filter_items(context, "research_case", items, "case_id")
        self._access.audit(context, "research_case_list", "research_case", "*", metadata={"count": len(items)})
        return items

    def create(
        self,
        context: PlatformRequestContext,
        *,
        project_id: str,
        title: str,
        thesis: str = "",
    ) -> ResearchCase:
        project = self._repo.get_project(project_id, tenant_id=context.tenant_id)
        if project is None:
            raise PlatformNotFoundError("project not found")
        self._access.ensure(context, "project", project_id, "read")
        research_case = ResearchCase.create(
            project_id=project_id,
            title=title,
            thesis=thesis,
            tenant_id=context.tenant_id,
        )
        self._repo.save_case(research_case)
        self._access.grant_creator(
            context,
            "research_case",
            research_case.case_id,
            provenance="research_case_create",
        )
        self._access.audit(context, "research_case_create", "research_case", research_case.case_id)
        return research_case

    def get(self, context: PlatformRequestContext, case_id: str) -> ResearchCase:
        research_case = self._repo.get_case(case_id, tenant_id=context.tenant_id)
        if research_case is None:
            raise PlatformNotFoundError("research case not found")
        self._access.ensure(context, "research_case", case_id, "read")
        self._access.audit(context, "research_case_read", "research_case", case_id)
        return research_case

    async def create_run_link(
        self,
        context: PlatformRequestContext,
        case_id: str,
        request: CaseRunCreate,
        *,
        workflow_templates_enabled: bool,
    ) -> CaseRunCreateResult:
        research_case = self._repo.get_case(case_id, tenant_id=context.tenant_id)
        if research_case is None:
            raise PlatformNotFoundError("research case not found")
        self._access.ensure(context, "research_case", case_id, "write")
        if request.run_id:
            return self._link_existing_run(context, case_id, request.run_id, request.link_type)
        if not request.template_id:
            raise PlatformValidationError("run_id or template_id required")
        if not workflow_templates_enabled:
            raise PlatformFeatureDisabledError("workflow templates API disabled")
        template = self._repo.get_workflow_template(request.template_id, tenant_id=context.tenant_id)
        if template is None:
            raise PlatformNotFoundError("workflow template not found")
        self._access.ensure(context, "workflow_template", template.template_id, "read")
        run_request = build_template_run_request(
            template,
            TemplateRunInput(
                question=request.question or research_case.title,
                workflow=request.workflow,
                session_id=request.session_id,
                market=request.market,
                language=request.language,
                document_ids=request.document_ids,
                portfolio_id=request.portfolio_id,
                model_policy=request.model_policy,
                inputs=request.inputs,
            ),
            tenant_id=context.tenant_id,
            user_hash=context.user_hash,
        )
        run = await self._runtime.create_run(run_request)
        self._repo.link_workflow_template_run(
            template_id=template.template_id,
            run_id=run.run_id,
            tenant_id=context.tenant_id,
        )
        link = self._repo.link_case_run(
            case_id=case_id,
            run_id=run.run_id,
            tenant_id=context.tenant_id,
            link_type=request.link_type,
        )
        self._access.audit(
            context,
            "research_case_run_create",
            "research_case",
            case_id,
            metadata={"run_id": run.run_id, "template_id": template.template_id},
        )
        return CaseRunCreateResult(link=link, run=run, template=template)

    def _link_existing_run(
        self,
        context: PlatformRequestContext,
        case_id: str,
        run_id: str,
        link_type: str,
    ) -> CaseRunCreateResult:
        run = self._runtime.get_run(run_id)
        if run is None:
            raise PlatformNotFoundError("run not found")
        if context.enterprise_request:
            run_tenant_id = run.identity_snapshot.tenant_id if run.identity_snapshot is not None else None
            if run_tenant_id != context.tenant_id:
                raise PlatformNotFoundError("run not found")
        link = self._repo.link_case_run(
            case_id=case_id,
            run_id=run_id,
            tenant_id=context.tenant_id,
            link_type=link_type,
        )
        self._access.audit(
            context,
            "research_case_run_link",
            "research_case",
            case_id,
            metadata={"run_id": run_id},
        )
        return CaseRunCreateResult(link=link, run=run)

    def add_case_asset(
        self,
        context: PlatformRequestContext,
        case_id: str,
        request: CaseAssetCreate,
    ) -> CaseAssetLink:
        self._require_case(context, case_id, "write")
        if request.asset_type not in {"document", "portfolio", "url"}:
            raise PlatformValidationError("unsupported asset_type")
        if not request.asset_id:
            raise PlatformValidationError("asset_id required")
        self._validate_asset_reference(context, request.asset_type, request.asset_id)
        link = CaseAssetLink.create(
            case_id=case_id,
            asset_type=request.asset_type,
            asset_id=request.asset_id,
            asset_name=request.asset_name,
            role=request.role,
            version=request.version,
            metadata=request.metadata,
            tenant_id=context.tenant_id,
        )
        self._repo.save_case_asset(link)
        self._access.audit(
            context,
            "case_asset_add",
            "research_case",
            case_id,
            metadata={"asset_link_id": link.asset_link_id, "asset_type": link.asset_type},
        )
        return link

    def list_case_assets(self, context: PlatformRequestContext, case_id: str) -> list[CaseAssetLink]:
        self._require_case(context, case_id, "read")
        return self._repo.list_case_assets(case_id, tenant_id=context.tenant_id)

    def remove_case_asset(self, context: PlatformRequestContext, case_id: str, asset_link_id: str) -> None:
        self._require_case(context, case_id, "write")
        self._repo.delete_case_asset(asset_link_id, tenant_id=context.tenant_id)
        self._access.audit(
            context,
            "case_asset_remove",
            "research_case",
            case_id,
            metadata={"asset_link_id": asset_link_id},
        )

    def record_decision(
        self,
        context: PlatformRequestContext,
        case_id: str,
        request: CaseDecisionCreate,
    ) -> CaseDecision:
        self._require_case(context, case_id, "write")
        if request.decision_type not in {"approve", "reject", "hold", "escalate"}:
            raise PlatformValidationError("unsupported decision_type")
        decision = CaseDecision.create(
            case_id=case_id,
            decision_type=request.decision_type,
            rationale=request.rationale,
            actor_hash=context.user_hash or "local-user",
            source_run_ids=request.source_run_ids,
            source_execution_ids=request.source_execution_ids,
            tenant_id=context.tenant_id,
        )
        self._repo.save_case_decision(decision)
        self._access.audit(
            context,
            "case_decision_record",
            "research_case",
            case_id,
            metadata={"decision_id": decision.decision_id, "decision_type": decision.decision_type},
        )
        return decision

    def list_case_decisions(self, context: PlatformRequestContext, case_id: str) -> list[CaseDecision]:
        self._require_case(context, case_id, "read")
        return self._repo.list_case_decisions(case_id, tenant_id=context.tenant_id)

    def list_workflow_executions_for_case(
        self,
        context: PlatformRequestContext,
        case_id: str,
        *,
        limit: int = 100,
    ) -> list[WorkflowExecution]:
        self._require_case(context, case_id, "read")
        executions = self._repo.list_workflow_executions(case_id, tenant_id=context.tenant_id, limit=limit)
        return [self._with_current_run_status(item) for item in executions]

    def get_workflow_execution(
        self,
        context: PlatformRequestContext,
        case_id: str,
        execution_id: str,
    ) -> WorkflowExecution:
        self._require_case(context, case_id, "read")
        execution = self._repo.get_workflow_execution(execution_id, tenant_id=context.tenant_id)
        if execution is None or execution.case_id != case_id:
            raise PlatformNotFoundError("workflow execution not found")
        return self._with_current_run_status(execution)

    def preflight_template_execution(
        self,
        context: PlatformRequestContext,
        case_id: str,
        request: CaseExecutionCreate,
        *,
        workflow_templates_enabled: bool,
    ) -> TemplatePreflightResult:
        self._require_case(context, case_id, "write")
        template = self._require_template(context, request.template_id, workflow_templates_enabled)
        input_errors = validate_template_inputs(template, request.inputs)
        missing_assets = self._missing_assets(context, case_id, request)
        missing_capabilities, warnings = self._capability_findings(context, template)
        valid = not input_errors and not missing_assets and not missing_capabilities
        return TemplatePreflightResult(
            valid=valid,
            input_errors=input_errors,
            missing_capabilities=missing_capabilities,
            missing_assets=missing_assets,
            warnings=warnings,
            estimated_cost={},
        )

    async def execute_template(
        self,
        context: PlatformRequestContext,
        case_id: str,
        request: CaseExecutionCreate,
        *,
        workflow_templates_enabled: bool,
        worker: Any | None = None,
    ) -> CaseExecutionCreateResult:
        research_case = self._require_case(context, case_id, "write")
        template = self._require_template(context, request.template_id, workflow_templates_enabled)
        if request.skip_preflight:
            preflight = TemplatePreflightResult(valid=True, warnings=["preflight_skipped"])
        else:
            preflight = self.preflight_template_execution(
                context,
                case_id,
                request,
                workflow_templates_enabled=workflow_templates_enabled,
            )
        input_snapshot = self._input_snapshot(request)
        if not preflight.valid:
            execution = WorkflowExecution.create(
                case_id=case_id,
                template_id=template.template_id,
                template_slug=template.slug,
                template_version=template.current_version,
                status="preflight_failed",
                input_snapshot=input_snapshot,
                preflight_result=preflight.to_dict(),
                trigger_channel=request.trigger_channel,
                tenant_id=context.tenant_id,
            )
            self._repo.save_workflow_execution(execution)
            raise PlatformValidationError(
                "template preflight failed",
                details={"execution": dict(execution.__dict__), "preflight_result": preflight.to_dict()},
            )

        run_request = build_template_run_request(
            template,
            TemplateRunInput(
                question=request.question or research_case.title,
                workflow=request.workflow,
                session_id=request.session_id,
                market=request.market,
                language=request.language,
                document_ids=request.document_ids,
                portfolio_id=request.portfolio_id,
                model_policy=request.model_policy,
                inputs=request.inputs,
            ),
            tenant_id=context.tenant_id,
            user_hash=context.user_hash,
        )
        run = await self._runtime.create_run(run_request)
        execution = WorkflowExecution.create(
            case_id=case_id,
            template_id=template.template_id,
            template_slug=template.slug,
            template_version=template.current_version,
            run_id=run.run_id,
            status="created",
            input_snapshot=input_snapshot,
            preflight_result=preflight.to_dict(),
            trigger_channel=request.trigger_channel,
            tenant_id=context.tenant_id,
        )
        self._repo.save_workflow_execution(execution)
        self._repo.link_workflow_template_run(
            template_id=template.template_id,
            run_id=run.run_id,
            tenant_id=context.tenant_id,
        )
        self._repo.link_case_run(
            case_id=case_id,
            run_id=run.run_id,
            tenant_id=context.tenant_id,
            link_type="primary",
        )
        run = await self._dispatch_run(run, worker)
        execution = self._repo.update_workflow_execution_status(
            execution.execution_id,
            _status_for_run(run),
            run_id=run.run_id,
            tenant_id=context.tenant_id,
        ) or execution
        self._access.audit(
            context,
            "case_execution_create",
            "research_case",
            case_id,
            metadata={
                "execution_id": execution.execution_id,
                "run_id": run.run_id,
                "template_id": template.template_id,
            },
        )
        return CaseExecutionCreateResult(execution=execution, run=run, preflight=preflight)

    def build_case_review(self, context: PlatformRequestContext, case_id: str) -> dict[str, Any]:
        research_case = self._require_case(context, case_id, "read")
        assets = self._repo.list_case_assets(case_id, tenant_id=context.tenant_id)
        executions = self.list_workflow_executions_for_case(context, case_id)
        decisions = self._repo.list_case_decisions(case_id, tenant_id=context.tenant_id)
        latest_run = None
        for execution in executions:
            if execution.run_id:
                latest_run = self._runtime.get_run(execution.run_id)
                if latest_run is not None:
                    break
        approvals = list(getattr(latest_run, "approvals", []) or []) if latest_run is not None else []
        return {
            "case": research_case,
            "assets": assets,
            "executions": executions,
            "latest_run": latest_run,
            "approvals": approvals,
            "decisions": decisions,
            "warnings": [],
        }

    def build_home_queue(self, context: PlatformRequestContext, *, limit: int = 20) -> dict[str, Any]:
        cases = self.list(context, limit=limit)
        pending_cases: list[dict[str, Any]] = []
        recent_executions: list[WorkflowExecution] = []
        failed_or_degraded_runs: list[dict[str, Any]] = []
        for research_case in cases:
            executions = self._repo.list_workflow_executions(
                research_case.case_id,
                tenant_id=context.tenant_id,
                limit=5,
            )
            hydrated = [self._with_current_run_status(item) for item in executions]
            recent_executions.extend(hydrated)
            if research_case.status == "open" and not hydrated:
                pending_cases.append({"case": research_case, "reason": "no_recent_execution"})
            elif research_case.status == "open" and hydrated[0].status in {"failed", "cancelled", "preflight_failed"}:
                pending_cases.append({"case": research_case, "reason": hydrated[0].status})
            for execution in hydrated:
                if execution.status in {"failed", "cancelled", "preflight_failed"}:
                    failed_or_degraded_runs.append({"execution": execution, "reason": execution.status})
        recent_runs = self._runtime.list_runs(limit=limit)
        pending_approvals = [
            run for run in recent_runs
            if _status_for_run(run) == "awaiting_approval" or any(
                approval.status == "pending" for approval in getattr(run, "approvals", [])
            )
        ]
        recent_memos = []
        for run in recent_runs:
            if _status_for_run(run) != "completed":
                continue
            artifacts = self._runtime.list_artifacts(run.run_id)
            if artifacts:
                recent_memos.append({"run": run, "artifact": artifacts[-1]})
        recent_executions = sorted(recent_executions, key=lambda item: item.updated_at, reverse=True)[:limit]
        return {
            "pending_cases": pending_cases[:limit],
            "pending_approvals": pending_approvals[:limit],
            "failed_or_degraded_runs": failed_or_degraded_runs[:limit],
            "recent_memos": recent_memos[:limit],
            "recent_executions": recent_executions,
            "data_freshness": None,
            "warnings": ["data_freshness_unavailable"],
        }

    def _require_case(
        self,
        context: PlatformRequestContext,
        case_id: str,
        permission: str,
    ) -> ResearchCase:
        research_case = self._repo.get_case(case_id, tenant_id=context.tenant_id)
        if research_case is None:
            raise PlatformNotFoundError("research case not found")
        self._access.ensure(context, "research_case", case_id, permission)
        return research_case

    def _require_template(
        self,
        context: PlatformRequestContext,
        template_id: str,
        workflow_templates_enabled: bool,
    ) -> WorkflowTemplate:
        if not workflow_templates_enabled:
            raise PlatformFeatureDisabledError("workflow templates API disabled")
        template = self._repo.get_workflow_template(template_id, tenant_id=context.tenant_id)
        if template is None:
            raise PlatformNotFoundError("workflow template not found")
        self._access.ensure(context, "workflow_template", template.template_id, "read")
        return template

    def _validate_asset_reference(self, context: PlatformRequestContext, asset_type: str, asset_id: str) -> None:
        if asset_type == "document" and self._documents is not None:
            if self._documents.get(asset_id, tenant_id=context.tenant_id) is None:
                raise PlatformNotFoundError("document not found")
        if asset_type == "portfolio" and self._portfolios is not None:
            if self._portfolios.get(asset_id, tenant_id=context.tenant_id) is None:
                raise PlatformNotFoundError("portfolio not found")

    def _missing_assets(
        self,
        context: PlatformRequestContext,
        case_id: str,
        request: CaseExecutionCreate,
    ) -> list[dict[str, Any]]:
        missing: list[dict[str, Any]] = []
        for document_id in request.document_ids:
            if self._documents is not None and self._documents.get(document_id, tenant_id=context.tenant_id) is None:
                missing.append({"asset_type": "document", "asset_id": document_id, "code": "not_found"})
        if request.portfolio_id and self._portfolios is not None:
            if self._portfolios.get(request.portfolio_id, tenant_id=context.tenant_id) is None:
                missing.append({"asset_type": "portfolio", "asset_id": request.portfolio_id, "code": "not_found"})
        if request.asset_link_ids:
            existing = {
                link.asset_link_id
                for link in self._repo.list_case_assets(case_id, tenant_id=context.tenant_id)
            }
            for asset_link_id in request.asset_link_ids:
                if asset_link_id not in existing:
                    missing.append({"asset_type": "case_asset_link", "asset_id": asset_link_id, "code": "not_found"})
        return missing

    def _capability_findings(
        self,
        context: PlatformRequestContext,
        template: WorkflowTemplate,
    ) -> tuple[list[str], list[str]]:
        required = _template_required_capabilities(template)
        if not required:
            return [], []
        if not self._capability_registry_enabled or self._capability_registry is None:
            return [], ["capability_registry_unavailable"]
        snapshot = self._capability_registry.build(context=context.enterprise_context if context.enterprise_request else None)
        available = {
            item.get("capability_id")
            for item in snapshot.get("capabilities", [])
            if item.get("status") == "available"
        }
        missing = [capability for capability in required if capability not in available]
        return missing, []

    def _input_snapshot(self, request: CaseExecutionCreate) -> dict[str, Any]:
        return {
            "inputs": dict(request.inputs or {}),
            "document_ids": list(request.document_ids or []),
            "portfolio_id": request.portfolio_id,
            "asset_link_ids": list(request.asset_link_ids or []),
            "market": request.market,
            "language": request.language,
            "model_policy": dict(request.model_policy or {}),
        }

    async def _dispatch_run(self, run: AgentRun, worker: Any | None) -> AgentRun:
        if worker is not None and hasattr(worker, "enqueue_continuation"):
            await worker.enqueue_continuation(run.run_id)
            return self._runtime.get_run(run.run_id) or run
        return await self._runtime.run_to_pause_or_completion(run.run_id)

    def _with_current_run_status(self, execution: WorkflowExecution) -> WorkflowExecution:
        if not execution.run_id:
            return execution
        run = self._runtime.get_run(execution.run_id)
        if run is None:
            return execution
        status = _status_for_run(run)
        if status == execution.status:
            return execution
        return WorkflowExecution(**{**execution.__dict__, "status": status})


class WorkflowService:
    """Application service for Workflow Template objects."""

    def __init__(self, repo: IPlatformRepository, governance: IEnterpriseGovernanceRepository) -> None:
        self._repo = repo
        self._access = PlatformAccessService(governance)

    def list(self, context: PlatformRequestContext, *, limit: int = 100) -> list[WorkflowTemplate]:
        items = self._repo.list_workflow_templates(limit=limit, tenant_id=context.tenant_id)
        items = self._access.filter_items(context, "workflow_template", items, "template_id")
        self._access.audit(context, "workflow_template_list", "workflow_template", "*", metadata={"count": len(items)})
        return items

    def create(
        self,
        context: PlatformRequestContext,
        *,
        slug: str,
        name: str,
        description: str = "",
        current_version: str = "1",
        input_schema: dict[str, Any] | None = None,
        run_instructions: str = "",
        tool_policy: dict[str, Any] | None = None,
        evidence_policy: dict[str, Any] | None = None,
        output_contract: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        required_capabilities: list[str] | None = None,
        eval_policy: list[str] | None = None,
        approval_policy: dict[str, Any] | None = None,
        ui_schema: dict[str, Any] | None = None,
    ) -> WorkflowTemplate:
        template = WorkflowTemplate.create(
            slug=slug,
            name=name,
            description=description,
            tenant_id=context.tenant_id,
            current_version=current_version,
        )
        template = WorkflowTemplate(
            **{
                **template.__dict__,
                "input_schema": input_schema or {},
                "run_instructions": run_instructions,
                "tool_policy": tool_policy or {},
                "evidence_policy": evidence_policy or {},
                "output_contract": output_contract or {},
                "metadata": _template_metadata(
                    metadata or {},
                    required_capabilities=required_capabilities,
                    eval_policy=eval_policy,
                    approval_policy=approval_policy,
                    ui_schema=ui_schema,
                ),
            }
        )
        self._repo.save_workflow_template(template)
        self._access.grant_creator(
            context,
            "workflow_template",
            template.template_id,
            provenance="workflow_template_create",
        )
        self._access.audit(context, "workflow_template_create", "workflow_template", template.template_id)
        return template

    def get(self, context: PlatformRequestContext, template_id: str) -> WorkflowTemplate:
        template = self._repo.get_workflow_template(template_id, tenant_id=context.tenant_id)
        if template is None:
            raise PlatformNotFoundError("workflow template not found")
        self._access.ensure(context, "workflow_template", template.template_id, "read")
        self._access.audit(context, "workflow_template_read", "workflow_template", template.template_id)
        return template


class PlatformAccessService:
    """Governance adapter used by workspace services."""

    def __init__(self, governance: IEnterpriseGovernanceRepository) -> None:
        self._governance = governance

    def ensure(
        self,
        context: PlatformRequestContext,
        resource_type: str,
        resource_id: str,
        permission: str,
    ) -> None:
        if not context.enterprise_request:
            return
        if self._governance.is_allowed(context.enterprise_context, resource_type, resource_id, permission):
            return
        raise PlatformAccessDeniedError(f"{resource_type} access denied")

    def filter_items(
        self,
        context: PlatformRequestContext,
        resource_type: str,
        items: list[Any],
        id_field: str,
    ) -> list[Any]:
        if not context.enterprise_request:
            return items
        resource_ids = [getattr(item, id_field) for item in items]
        allowed = self._governance.list_allowed_resource_ids(context.enterprise_context, resource_type, "read")
        if "*" in allowed:
            return items
        return [item for item in items if getattr(item, id_field) in allowed]

    def grant_creator(
        self,
        context: PlatformRequestContext,
        resource_type: str,
        resource_id: str,
        *,
        provenance: str,
    ) -> None:
        if not context.enterprise_request:
            return
        for permission in ("read", "write"):
            self._governance.grant(
                EnterpriseAclGrant(
                    tenant_id=context.enterprise_context.tenant_id,
                    subject_hash=context.enterprise_context.user_hash,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    permission=permission,
                    provenance=provenance,
                )
            )

    def audit(
        self,
        context: PlatformRequestContext,
        event_type: str,
        resource_type: str,
        resource_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not context.enterprise_request:
            return
        self._governance.append_audit_event(
            EnterpriseAuditEvent(
                tenant_id=context.enterprise_context.tenant_id,
                actor_hash=context.enterprise_context.user_hash,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=context.request_id,
                metadata=metadata or {},
            )
        )


def _status_for_run(run: AgentRun) -> str:
    return run.status.value if hasattr(run.status, "value") else str(run.status)


def _execution_links(run_id: str | None) -> dict[str, str]:
    if not run_id:
        return {}
    return {
        "run": f"/v1/runs/{run_id}",
        "stream": f"/v1/runs/{run_id}/stream",
        "summary": f"/v1/runs/{run_id}/summary",
        "claims": f"/v1/runs/{run_id}/claims",
        "citations": f"/v1/runs/{run_id}/citations",
        "eval": f"/v1/runs/{run_id}/eval",
    }


def _template_required_capabilities(template: WorkflowTemplate) -> list[str]:
    metadata = template.metadata if isinstance(template.metadata, dict) else {}
    contract = metadata.get("contract")
    if not isinstance(contract, dict):
        return []
    required = contract.get("required_capabilities")
    if not isinstance(required, list):
        return []
    return [str(item) for item in required if item is not None and str(item)]


def _template_metadata(
    metadata: dict[str, Any],
    *,
    required_capabilities: list[str] | None = None,
    eval_policy: list[str] | None = None,
    approval_policy: dict[str, Any] | None = None,
    ui_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(metadata or {})
    contract = dict(merged.get("contract") if isinstance(merged.get("contract"), dict) else {})
    if required_capabilities is not None:
        contract["required_capabilities"] = list(required_capabilities)
    if eval_policy is not None:
        contract["eval_policy"] = list(eval_policy)
    if approval_policy is not None:
        contract["approval_policy"] = dict(approval_policy)
    if ui_schema is not None:
        contract["ui_schema"] = dict(ui_schema)
    if contract:
        merged["contract"] = contract
    return merged
