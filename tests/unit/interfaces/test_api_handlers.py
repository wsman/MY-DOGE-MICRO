"""Unit tests for FastAPI-free API handlers."""

from __future__ import annotations

import pytest

from doge.core.domain.agent_models import AgentRun, AgentSession, EventType, RunStatus
from doge.core.domain.enterprise_context import EnterpriseContext, IdentitySnapshot
from doge.interfaces.api.handlers import (
    CancelRunHandler,
    CreateSessionHandler,
    ExecuteWorkflowHandler,
    GetRunHandler,
    GetRunSummaryHandler,
    ListArtifactsHandler,
    ListEventsHandler,
    ListRunsHandler,
    ListSessionsHandler,
    ListWorkspaceObjectsHandler,
    ProjectHandler,
    ResearchCaseHandler,
    ResearchCaseRunHandler,
    RunAccessContext,
    ResolveApprovalHandler,
    RunNotFound,
    RunStreamHandler,
    SessionNotFound,
    SubmitSessionTurnCommand,
    SubmitSessionTurnHandler,
    UploadDocumentCommand,
    UploadDocumentHandler,
    WorkflowTemplateHandler,
    WorkspaceHandler,
)
from doge.shared.scope import TenantScope


class FakeSessions:
    def __init__(self) -> None:
        self.items: dict[str, AgentSession] = {}

    def save(self, session, scope=None, *, tenant_id=None):
        tenant = getattr(scope, "tenant_id", scope) if scope is not None else tenant_id
        session.tenant_id = tenant
        self.items[session.session_id] = session

    def get(self, session_id, scope=None, *, tenant_id=None):
        tenant = getattr(scope, "tenant_id", scope) if scope is not None else tenant_id
        session = self.items.get(session_id)
        if session is None or (tenant is not None and session.tenant_id != tenant):
            return None
        return session

    def list_recent(self, scope=None, limit=20, *, tenant_id=None):
        if isinstance(scope, int):
            limit = scope
            scope = None
        tenant = getattr(scope, "tenant_id", scope) if scope is not None else tenant_id
        return [
            item for item in list(self.items.values())[:limit]
            if tenant is None or item.tenant_id == tenant
        ]


class FakeWorker:
    def __init__(self) -> None:
        self.calls = []

    async def enqueue_run(self, *args, **kwargs):
        self.calls.append(("enqueue_run", args, kwargs))
        return "run-1"

    async def cancel_run(self, run_id, *, scope):
        self.calls.append(("cancel_run", run_id, scope))
        return {"run_id": run_id, "status": "cancelling"}

    async def resolve_approval(self, run_id, approval_id, approved, *, scope):
        self.calls.append(("resolve_approval", run_id, approval_id, approved, scope))
        return {"run_id": run_id, "approval_id": approval_id, "approved": approved}


class FakeCaseExecutionService:
    def __init__(self) -> None:
        self.calls = []

    def preflight_template_execution(
        self,
        context,
        case_id,
        command,
        *,
        workflow_templates_enabled,
    ):
        self.calls.append(("preflight", context, case_id, command, workflow_templates_enabled))
        return {"case_id": case_id, "preflight": True}

    async def execute_template(
        self,
        context,
        case_id,
        command,
        *,
        workflow_templates_enabled,
        worker,
    ):
        self.calls.append(
            {
                "context": context,
                "case_id": case_id,
                "command": command,
                "workflow_templates_enabled": workflow_templates_enabled,
                "worker": worker,
            }
        )
        return {"execution_id": "exec-1", "run_id": "run-1"}

    def list_workflow_executions_for_case(self, context, case_id, *, limit=100):
        self.calls.append(("list_executions", context, case_id, limit))
        return [{"execution_id": "exec-1", "limit": limit}]

    def get_workflow_execution(self, context, case_id, execution_id):
        self.calls.append(("get_execution", context, case_id, execution_id))
        return {"execution_id": execution_id}

    async def create_run_link(
        self,
        context,
        case_id,
        command,
        *,
        workflow_templates_enabled,
    ):
        self.calls.append(("link_run", context, case_id, command, workflow_templates_enabled))
        return {"case_id": case_id, "run_id": command.run_id}

    def build_case_review(self, context, case_id):
        self.calls.append(("review", context, case_id))
        run = AgentRun.create(workflow="investment_research", question="q", run_id="run-1")
        return {"case": {"case_id": case_id}, "latest_run": run}


class FakeUploadService:
    def __init__(self) -> None:
        self.calls = []

    def register_text(self, **kwargs):
        self.calls.append(("text", kwargs))
        return {"document_id": kwargs.get("document_id") or "doc-text"}

    def register_bytes(self, **kwargs):
        self.calls.append(("bytes", kwargs))
        return {"document_id": "doc-bytes"}


class FakeRuntime:
    def __init__(self) -> None:
        self.run = AgentRun.create(workflow="investment_research", question="q", run_id="run-1")
        self.event_one = self.run.add_event(EventType.RUN_CREATED, {"n": 1})
        self.event_two = self.run.add_event(EventType.TOOL_RESULT, {"n": 2})
        self.event_one.sequence = 1
        self.event_two.sequence = 2
        self.artifact = self.run.add_artifact("memo", "Memo", "content")
        self.scopes = []

    def get_run(self, scope, run_id):
        self.scopes.append(("get_run", scope))
        return self.run if run_id == self.run.run_id else None

    def list_events(self, scope, run_id):
        self.scopes.append(("list_events", scope))
        return [self.event_one, self.event_two] if run_id == self.run.run_id else []

    def list_artifacts(self, scope, run_id):
        self.scopes.append(("list_artifacts", scope))
        return [self.artifact] if run_id == self.run.run_id else []

    def list_runs(self, scope, session_id=None, limit=20):
        self.scopes.append(("list_runs", scope, session_id, limit))
        return [self.run][:limit]


class FakeRunSummaryUseCase:
    def __init__(self) -> None:
        self.calls = []

    def build(self, run, scope=None):
        self.calls.append((run.run_id, scope))
        return {
            "summary": {"run_id": run.run_id},
            "claims": [],
            "citations": [
                {"document_id": "doc-denied", "snippet": "secret", "accessible": True},
            ],
            "eval": {"failed_checks": [], "accessible_citation_count": 1},
        }


class FakeGovernance:
    def __init__(self) -> None:
        self.decisions = []
        self.audit_events = []

    def list_allowed_resource_ids(self, context, resource_type, permission):
        return set()

    def is_allowed(self, context, resource_type, resource_id, permission):
        return False

    def record_approval_decision(self, decision):
        self.decisions.append(decision)

    def append_audit_event(self, event):
        self.audit_events.append(event)


class FakeWorkspaceListService:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = []

    def list(self, context, limit=100, **filters):
        self.calls.append((context, limit, filters))
        return [{"kind": self.name, "limit": limit, "filters": filters}]


class FakePlatformObjectService:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.calls = []

    def list(self, context, **kwargs):
        self.calls.append(("list", context, kwargs))
        return [{"kind": self.kind, **kwargs}]

    def create(self, context, **kwargs):
        self.calls.append(("create", context, kwargs))
        return {"kind": self.kind, **kwargs}

    def get(self, context, object_id):
        self.calls.append(("get", context, object_id))
        return {"kind": self.kind, "id": object_id}


class FakeResearchCaseService:
    def __init__(self) -> None:
        self.calls = []

    def build_home_queue(self, context, *, limit=20):
        self.calls.append(("home_queue", context, limit))
        return [{"kind": "home", "limit": limit}]

    def add_case_asset(self, context, case_id, command):
        self.calls.append(("add_asset", context, case_id, command))
        return {"case_id": case_id, "asset_id": command.asset_id}

    def record_decision(self, context, case_id, command):
        self.calls.append(("record_decision", context, case_id, command))
        return {"case_id": case_id, "decision_type": command.decision_type}


class FakeSubscriber:
    def __init__(self, events) -> None:
        self.events = events
        self.calls = []

    async def subscribe(self, run_id, *, after_sequence=0):
        self.calls.append((run_id, after_sequence))
        for event in self.events:
            if event.sequence > after_sequence:
                yield event


def test_session_handlers_create_and_list_without_fastapi() -> None:
    sessions = FakeSessions()

    created = CreateSessionHandler(sessions).handle(title="Research", tenant_id="tenant-a")
    listed = ListSessionsHandler(sessions).handle(limit=10, tenant_id="tenant-a")

    assert created.title == "Research"
    assert listed == [created]


@pytest.mark.asyncio
async def test_submit_session_turn_handler_enqueues_worker_run() -> None:
    sessions = FakeSessions()
    worker = FakeWorker()
    session = CreateSessionHandler(sessions).handle(title="Research", tenant_id="tenant-a")

    run_id = await SubmitSessionTurnHandler(sessions=sessions, worker=worker).handle(
        SubmitSessionTurnCommand(
            session_id=session.session_id,
            message="Analyze AAPL",
            tenant_id="tenant-a",
            document_ids=["doc-1"],
            idempotency_key="idem-1",
        )
    )

    assert run_id == "run-1"
    assert worker.calls[0][0] == "enqueue_run"
    assert worker.calls[0][1] == (session.session_id, "Analyze AAPL")
    assert worker.calls[0][2]["document_ids"] == ["doc-1"]


@pytest.mark.asyncio
async def test_submit_session_turn_handler_rejects_missing_session() -> None:
    with pytest.raises(SessionNotFound):
        await SubmitSessionTurnHandler(sessions=FakeSessions(), worker=FakeWorker()).handle(
            SubmitSessionTurnCommand(session_id="missing", message="Analyze AAPL")
        )


@pytest.mark.asyncio
async def test_submit_session_turn_handler_applies_enterprise_access_without_fastapi() -> None:
    sessions = FakeSessions()
    worker = FakeWorker()
    governance = FakeGovernance()
    session = CreateSessionHandler(sessions).handle(title="Research", tenant_id="tenant-a")
    access = RunAccessContext(
        scope=TenantScope.enterprise("tenant-a", "user-a"),
        enterprise_context=EnterpriseContext(
            tenant_id="tenant-a",
            user_hash="user-a",
            document_acl=frozenset({"doc-1"}),
            portfolio_permission=frozenset({"portfolio-1"}),
        ),
        request_id="req-1",
    )

    run_id = await SubmitSessionTurnHandler(
        sessions=sessions,
        worker=worker,
        governance=governance,
    ).handle_and_audit(
        SubmitSessionTurnCommand(
            session_id=session.session_id,
            message="Analyze AAPL",
            document_ids=["doc-1"],
            portfolio_id="portfolio-1",
            model_policy={"tenant_id": "spoofed", "max_tool_rounds": 2},
        ),
        access=access,
    )

    assert run_id == "run-1"
    kwargs = worker.calls[0][2]
    assert kwargs["model_policy"] == {"max_tool_rounds": 2}
    assert kwargs["identity_snapshot"]["tenant_id"] == "tenant-a"
    assert kwargs["identity_snapshot"]["document_acl"] == ["doc-1"]
    assert governance.audit_events[0].event_type == "run_create"


@pytest.mark.asyncio
async def test_run_action_handlers_delegate_to_worker() -> None:
    worker = FakeWorker()
    scope = TenantScope.local()

    cancelled = await CancelRunHandler(worker=worker).handle(run_id="run-1", scope=scope)
    resolved = await ResolveApprovalHandler(worker=worker).handle(
        run_id="run-1",
        approval_id="appr-1",
        approved=True,
        scope=scope,
    )

    assert cancelled["status"] == "cancelling"
    assert resolved["approved"] is True
    assert [call[0] for call in worker.calls] == ["cancel_run", "resolve_approval"]


@pytest.mark.asyncio
async def test_resolve_approval_handler_records_enterprise_actor_without_fastapi() -> None:
    runtime = FakeRuntime()
    runtime.run.identity_snapshot = IdentitySnapshot(tenant_id="tenant-a", user_hash="user-a")
    worker = FakeWorker()
    governance = FakeGovernance()
    context = EnterpriseContext(
        tenant_id="tenant-a",
        user_hash="user-a",
        approval_authority=frozenset({"appr-1"}),
    )

    result = await ResolveApprovalHandler(
        worker=worker,
        runtime=runtime,
        governance=governance,
    ).handle(
        run_id="run-1",
        approval_id="appr-1",
        approved=True,
        access=RunAccessContext(
            scope=TenantScope.enterprise("tenant-a", "user-a"),
            enterprise_context=context,
            request_id="req-1",
        ),
    )

    assert result["approved"] is True
    assert governance.decisions[0].request_id == "req-1"
    assert governance.audit_events[0].event_type == "approval_decision"


@pytest.mark.asyncio
async def test_execute_workflow_handler_delegates_to_service_with_worker() -> None:
    service = FakeCaseExecutionService()
    worker = FakeWorker()
    context = object()
    command = object()

    result = await ExecuteWorkflowHandler(service=service, worker=worker).handle(
        context=context,
        case_id="case-1",
        command=command,
        workflow_templates_enabled=True,
    )

    assert result == {"execution_id": "exec-1", "run_id": "run-1"}
    assert service.calls == [
        {
            "context": context,
            "case_id": "case-1",
            "command": command,
            "workflow_templates_enabled": True,
            "worker": worker,
        }
    ]


@pytest.mark.asyncio
async def test_research_case_run_handler_delegates_without_fastapi() -> None:
    from doge.platform.workspace import CaseExecutionCreate, CaseRunCreate

    service = FakeCaseExecutionService()
    context = object()
    handler = ResearchCaseRunHandler(service=service)

    preflight = handler.preflight(
        context=context,
        case_id="case-1",
        command=CaseExecutionCreate(template_id="tpl-1"),
        workflow_templates_enabled=True,
    )
    executions = handler.list_executions(context=context, case_id="case-1", limit=2)
    execution = handler.get_execution(context=context, case_id="case-1", execution_id="exec-1")
    linked = await handler.link_run(
        context=context,
        case_id="case-1",
        command=CaseRunCreate(run_id="run-1"),
        workflow_templates_enabled=True,
    )
    review = handler.review(
        context=context,
        case_id="case-1",
        run_summary_enabled=True,
        summary_use_case=FakeRunSummaryUseCase(),
        access=RunAccessContext(scope=TenantScope.local()),
    )

    assert preflight == {"case_id": "case-1", "preflight": True}
    assert executions == [{"execution_id": "exec-1", "limit": 2}]
    assert execution == {"execution_id": "exec-1"}
    assert linked == {"case_id": "case-1", "run_id": "run-1"}
    assert review["summary"]["run_id"] == "run-1"


def test_upload_document_handler_delegates_text_and_bytes_without_fastapi() -> None:
    upload = FakeUploadService()
    scope = TenantScope.local()

    text = UploadDocumentHandler(upload_service=upload).handle(
        UploadDocumentCommand(filename="memo.txt", content="hello", document_id="doc-1"),
        scope=scope,
    )
    blob = UploadDocumentHandler(upload_service=upload).handle(
        UploadDocumentCommand(filename="scan.pdf", payload=b"%PDF"),
        scope=scope,
    )

    assert text == {"document_id": "doc-1"}
    assert blob == {"document_id": "doc-bytes"}
    assert upload.calls[0] == (
        "text",
        {"filename": "memo.txt", "content": "hello", "document_id": "doc-1", "scope": scope},
    )
    assert upload.calls[1] == (
        "bytes",
        {"filename": "scan.pdf", "payload": b"%PDF", "scope": scope},
    )


def test_run_query_handlers_delegate_to_runtime_without_fastapi() -> None:
    runtime = FakeRuntime()
    scope = TenantScope.enterprise("tenant-a", "user-a")

    run = GetRunHandler(runtime=runtime).handle(run_id="run-1", scope=scope)
    events = ListEventsHandler(runtime=runtime).handle(run_id="run-1", scope=scope, after_sequence=1)
    artifacts = ListArtifactsHandler(runtime=runtime).handle(run_id="run-1", scope=scope)
    runs = ListRunsHandler(runtime=runtime).handle(scope=scope, session_id="ses-1", limit=1)

    assert run.run_id == "run-1"
    assert [event.sequence for event in events] == [2]
    assert [artifact.artifact_id for artifact in artifacts] == [runtime.artifact.artifact_id]
    assert runs == [runtime.run]
    with pytest.raises(RunNotFound):
        GetRunHandler(runtime=runtime).handle(run_id="missing", scope=scope)


def test_run_query_handler_rejects_enterprise_tenant_mismatch_without_fastapi() -> None:
    runtime = FakeRuntime()
    runtime.run.identity_snapshot = IdentitySnapshot(tenant_id="tenant-b", user_hash="user-b")
    access = RunAccessContext(
        scope=TenantScope.enterprise("tenant-a", "user-a"),
        enterprise_context=EnterpriseContext(tenant_id="tenant-a", user_hash="user-a"),
    )

    with pytest.raises(RunNotFound):
        GetRunHandler(runtime=runtime).handle(run_id="run-1", access=access)


def test_run_summary_and_workspace_query_handlers_are_fastapi_free() -> None:
    runtime = FakeRuntime()
    scope = TenantScope.local()
    summary_use_case = FakeRunSummaryUseCase()
    workspaces = FakeWorkspaceListService("workspace")

    summary = GetRunSummaryHandler(use_case=summary_use_case).handle(run=runtime.run, scope=scope)
    listed = ListWorkspaceObjectsHandler(workspace_service=workspaces).handle(
        object_type="workspaces",
        context={"tenant": "local"},
        limit=3,
    )

    assert summary["summary"]["run_id"] == "run-1"
    assert summary_use_case.calls == [("run-1", scope)]
    assert listed == [{"kind": "workspace", "limit": 3, "filters": {}}]
    with pytest.raises(ValueError, match="unsupported workspace object type"):
        ListWorkspaceObjectsHandler().handle(object_type="cases", context=None)


def test_run_summary_handler_redacts_enterprise_citations_without_fastapi() -> None:
    runtime = FakeRuntime()
    scope = TenantScope.enterprise("tenant-a", "user-a")
    context = EnterpriseContext(tenant_id="tenant-a", user_hash="user-a")
    governance = FakeGovernance()

    summary = GetRunSummaryHandler(
        use_case=FakeRunSummaryUseCase(),
        governance=governance,
    ).handle(
        run=runtime.run,
        access=RunAccessContext(scope=scope, enterprise_context=context, request_id="req-1"),
        audit_event_type="run_summary_read",
    )

    assert summary["citations"][0]["accessible"] is False
    assert summary["citations"][0]["snippet"] == ""
    assert governance.audit_events[0].event_type == "run_summary_read"
    assert governance.audit_events[0].request_id == "req-1"


def test_platform_object_handlers_delegate_without_fastapi() -> None:
    context = object()
    workspace_service = FakePlatformObjectService("workspace")
    project_service = FakePlatformObjectService("project")
    workflow_service = FakePlatformObjectService("workflow")

    workspace = WorkspaceHandler(service=workspace_service).create(
        context=context,
        name="Desk",
        description="Research",
    )
    projects = ProjectHandler(service=project_service).list(
        context=context,
        workspace_id="ws-1",
        limit=2,
    )
    template = WorkflowTemplateHandler(service=workflow_service).get(
        context=context,
        template_id="tpl-1",
    )

    assert workspace == {"kind": "workspace", "name": "Desk", "description": "Research"}
    assert projects == [{"kind": "project", "workspace_id": "ws-1", "limit": 2}]
    assert template == {"kind": "workflow", "id": "tpl-1"}


def test_research_case_handler_delegates_without_fastapi() -> None:
    from doge.platform.workspace import CaseAssetCreate, CaseDecisionCreate

    context = object()
    service = FakeResearchCaseService()
    handler = ResearchCaseHandler(service=service)

    queue = handler.home_queue(context=context, limit=4)
    asset = handler.add_asset(
        context=context,
        case_id="case-1",
        command=CaseAssetCreate(asset_type="document", asset_id="doc-1"),
    )
    decision = handler.record_decision(
        context=context,
        case_id="case-1",
        command=CaseDecisionCreate(decision_type="approve"),
    )

    assert queue == [{"kind": "home", "limit": 4}]
    assert asset == {"case_id": "case-1", "asset_id": "doc-1"}
    assert decision == {"case_id": "case-1", "decision_type": "approve"}


@pytest.mark.asyncio
async def test_run_stream_handler_iterates_events_without_fastapi() -> None:
    runtime = FakeRuntime()
    runtime.run.status = RunStatus.COMPLETED
    access = RunAccessContext(scope=TenantScope.local())
    subscriber = FakeSubscriber([runtime.event_one, runtime.event_two])

    events = [
        event
        async for event in RunStreamHandler(runtime=runtime, subscriber=subscriber).open(
            run_id="run-1",
            access=access,
            after_sequence=1,
        )
    ]

    assert [event.sequence for event in events] == [2]
    assert subscriber.calls == [("run-1", 1)]
