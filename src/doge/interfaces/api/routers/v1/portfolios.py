"""v1 portfolio import routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from doge.application.services.portfolio_import_service import (
    PortfolioImportError,
    PortfolioImportService,
)
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import append_audit, enterprise_context, grant_creator_access, is_enterprise_request
from doge.shared.scope import TenantScope

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


@router.post("/portfolios/import")
async def import_portfolio_csv(
    request: Request,
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    portfolio_id: str | None = Form(default=None),
    service: PortfolioImportService = Depends(deps.get_portfolio_import_service),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "portfolio import requires a .csv file")
    try:
        payload = await file.read()
        content = payload.decode("utf-8-sig")
        portfolio = service.import_csv(content, name=name, portfolio_id=portfolio_id, scope=_portfolio_scope(request))
        grant_creator_access(
            request,
            governance,
            "portfolio",
            portfolio["portfolio_id"],
            provenance="portfolio_import",
        )
        append_audit(request, governance, "portfolio_import", "portfolio", portfolio["portfolio_id"])
        return portfolio
    except UnicodeDecodeError as exc:
        raise HTTPException(400, "portfolio csv must be utf-8 encoded") from exc
    except PortfolioImportError as exc:
        raise HTTPException(400, str(exc)) from exc


def _portfolio_scope(request: Request) -> TenantScope:
    if not is_enterprise_request(request):
        return TenantScope.local()
    context = enterprise_context(request)
    return TenantScope.enterprise(context.tenant_id, context.user_hash)
