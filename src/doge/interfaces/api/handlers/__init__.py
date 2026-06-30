"""FastAPI-free API command/query handlers."""

from doge.interfaces.api.handlers.case_runs import ExecuteWorkflowHandler, ResearchCaseRunHandler
from doge.interfaces.api.handlers.documents import UploadDocumentCommand, UploadDocumentHandler
from doge.interfaces.api.handlers.queries import (
    GetRunHandler,
    GetRunSummaryHandler,
    ListArtifactsHandler,
    ListEventsHandler,
    ListRunsHandler,
    ListWorkspaceObjectsHandler,
    RunAccessContext,
    RunNotFound,
)
from doge.interfaces.api.handlers.platform_objects import (
    ProjectHandler,
    ResearchCaseHandler,
    WorkflowTemplateHandler,
    WorkspaceHandler,
)
from doge.interfaces.api.handlers.run_actions import CancelRunHandler, ResolveApprovalHandler, ResumeRunHandler
from doge.interfaces.api.handlers.sessions import (
    CreateSessionHandler,
    GetSessionHandler,
    ListSessionsHandler,
    SessionNotFound,
    SubmitSessionTurnCommand,
    SubmitSessionTurnHandler,
)
from doge.interfaces.api.handlers.streaming import RunStreamHandler

__all__ = [
    "CancelRunHandler",
    "CreateSessionHandler",
    "ExecuteWorkflowHandler",
    "GetSessionHandler",
    "GetRunHandler",
    "GetRunSummaryHandler",
    "ListArtifactsHandler",
    "ListEventsHandler",
    "ListRunsHandler",
    "ListSessionsHandler",
    "ListWorkspaceObjectsHandler",
    "ProjectHandler",
    "ResearchCaseHandler",
    "ResearchCaseRunHandler",
    "ResolveApprovalHandler",
    "ResumeRunHandler",
    "RunAccessContext",
    "RunNotFound",
    "RunStreamHandler",
    "SessionNotFound",
    "SubmitSessionTurnCommand",
    "SubmitSessionTurnHandler",
    "UploadDocumentCommand",
    "UploadDocumentHandler",
    "WorkflowTemplateHandler",
    "WorkspaceHandler",
]
