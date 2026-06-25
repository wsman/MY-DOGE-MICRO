"""Research-case execution API handlers without FastAPI dependencies."""

from __future__ import annotations

from doge.core.ports.enterprise_governance import EnterpriseAuditEvent
from doge.interfaces.api.handlers.queries import GetRunSummaryHandler, RunAccessContext


class ExecuteWorkflowHandler:
    def __init__(self, *, service, worker) -> None:
        self._service = service
        self._worker = worker

    async def handle(
        self,
        *,
        context,
        case_id: str,
        command,
        workflow_templates_enabled: bool,
    ):
        return await self._service.execute_template(
            context,
            case_id,
            command,
            workflow_templates_enabled=workflow_templates_enabled,
            worker=self._worker,
        )


class ResearchCaseRunHandler:
    def __init__(self, *, service, governance=None) -> None:
        self._service = service
        self._governance = governance

    def preflight(
        self,
        *,
        context,
        case_id: str,
        command,
        workflow_templates_enabled: bool,
    ):
        return self._service.preflight_template_execution(
            context,
            case_id,
            command,
            workflow_templates_enabled=workflow_templates_enabled,
        )

    def list_executions(self, *, context, case_id: str, limit: int = 100):
        return self._service.list_workflow_executions_for_case(context, case_id, limit=limit)

    def get_execution(self, *, context, case_id: str, execution_id: str):
        return self._service.get_workflow_execution(context, case_id, execution_id)

    async def link_run(
        self,
        *,
        context,
        case_id: str,
        command,
        workflow_templates_enabled: bool,
    ):
        return await self._service.create_run_link(
            context,
            case_id,
            command,
            workflow_templates_enabled=workflow_templates_enabled,
        )

    def review(
        self,
        *,
        context,
        case_id: str,
        run_summary_enabled: bool,
        summary_use_case=None,
        access: RunAccessContext | None = None,
    ) -> dict:
        review = self._service.build_case_review(context, case_id)
        latest_run = review.get("latest_run")
        if latest_run is not None and run_summary_enabled and summary_use_case is not None:
            result = GetRunSummaryHandler(
                use_case=summary_use_case,
                governance=self._governance,
            ).handle(run=latest_run, access=access)
            review.update(
                {
                    "summary": result["summary"],
                    "claims": result["claims"],
                    "citations": result["citations"],
                    "eval": result["eval"],
                }
            )
            self._append_review_audit(access, latest_run.run_id)
            return review
        review.update({"summary": None, "claims": [], "citations": [], "eval": None})
        if latest_run is not None:
            review["warnings"] = [*review.get("warnings", []), "run_summary_api_unavailable"]
        return review

    def _append_review_audit(self, access: RunAccessContext | None, run_id: str) -> None:
        if access is None or not access.is_enterprise or self._governance is None:
            return
        context = access.enterprise_context
        self._governance.append_audit_event(
            EnterpriseAuditEvent(
                tenant_id=context.tenant_id,
                actor_hash=context.user_hash,
                event_type="research_case_review_read",
                resource_type="research_case",
                resource_id=run_id,
                request_id=access.request_id,
                metadata={},
            )
        )
