"""Focused service for research-case decisions."""

from __future__ import annotations

from doge.core.domain.platform_models import CaseDecision, ResearchCase
from doge.core.ports.platform_repository import IPlatformRepository
from doge.platform.workspace.application.case_service import (
    CaseDecisionCreate,
    PlatformAccessService,
    PlatformNotFoundError,
    PlatformRequestContext,
    PlatformValidationError,
)


class CaseDecisionService:
    """Owns case decision validation and persistence."""

    def __init__(self, repo: IPlatformRepository, access: PlatformAccessService) -> None:
        self._repo = repo
        self._access = access

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
        self._repo.save_case_decision(decision, context.tenant_scope)
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
        return self._repo.list_case_decisions(context.tenant_scope, case_id)

    def _require_case(
        self,
        context: PlatformRequestContext,
        case_id: str,
        permission: str,
    ) -> ResearchCase:
        research_case = self._repo.get_case(case_id, context.tenant_scope)
        if research_case is None:
            raise PlatformNotFoundError("research case not found")
        self._access.ensure(context, "research_case", case_id, permission)
        return research_case


__all__ = ["CaseDecisionService"]
