"""Focused service for research-case asset links."""

from __future__ import annotations

from typing import Any

from doge.core.domain.platform_models import CaseAssetLink, ResearchCase
from doge.core.ports.platform_repository import IPlatformRepository
from doge.platform.workspace.application.case_service import (
    CaseAssetCreate,
    PlatformAccessService,
    PlatformNotFoundError,
    PlatformRequestContext,
    PlatformValidationError,
)


class CaseAssetService:
    """Owns asset validation and case asset link persistence."""

    def __init__(
        self,
        repo: IPlatformRepository,
        access: PlatformAccessService,
        *,
        document_repository: Any | None = None,
        portfolio_repository: Any | None = None,
    ) -> None:
        self._repo = repo
        self._access = access
        self._documents = document_repository
        self._portfolios = portfolio_repository

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

    def _validate_asset_reference(self, context: PlatformRequestContext, asset_type: str, asset_id: str) -> None:
        if asset_type == "document" and self._documents is not None:
            if self._documents.get(asset_id, tenant_id=context.tenant_id) is None:
                raise PlatformNotFoundError("document not found")
        if asset_type == "portfolio" and self._portfolios is not None:
            if self._portfolios.get(asset_id, tenant_id=context.tenant_id) is None:
                raise PlatformNotFoundError("portfolio not found")


__all__ = ["CaseAssetService"]
