"""
行业分析路由
"""

import os
from fastapi import APIRouter, Depends, HTTPException

from doge.core.ports.repository import IReportRepository
from doge.interfaces.api import deps

router = APIRouter()


@router.get("/reports")
async def list_research_reports(
    repo: IReportRepository = Depends(deps.get_report_repository),
):
    db_path = str(deps.get_settings_dep().db.research_db)
    if not os.path.exists(db_path):
        return {"reports": []}
    return {"reports": repo.list_research_reports()}


@router.get("/reports/{report_id}")
async def get_research_report(
    report_id: int,
    repo: IReportRepository = Depends(deps.get_report_repository),
):
    row = repo.get_research_report(report_id)
    if not row:
        raise HTTPException(404, "not found")
    return dict(row)
