"""
宏观分析路由
"""

import json
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from doge.application.contracts.request import GenerateMacroReportRequest
from doge.application.use_cases.generate_macro_report import GenerateMacroReportUseCase
from doge.core.ports.repository import IReportRepository
from doge.interfaces.api import deps

logger = logging.getLogger(__name__)
router = APIRouter()


class MacroRunRequest(BaseModel):
    profile_name: Optional[str] = None
    market: str = "cn"
    custom_prompt: Optional[str] = None


@router.get("/reports")
async def list_macro_reports(
    repo: IReportRepository = Depends(deps.get_report_repository),
):
    """列出所有宏观报告"""
    db_path = str(deps.get_settings_dep().db.research_db)
    import os
    if not os.path.exists(db_path):
        return {"reports": []}
    return {"reports": repo.list_macro_reports()}


@router.get("/reports/latest")
async def latest_macro_report(
    repo: IReportRepository = Depends(deps.get_report_repository),
):
    """最新宏观报告"""
    db_path = str(deps.get_settings_dep().db.research_db)
    import os
    if not os.path.exists(db_path):
        raise HTTPException(404, "no reports")
    row = repo.get_latest_macro_report()
    if not row:
        raise HTTPException(404, "no reports")
    return dict(row)


@router.get("/reports/{report_id}")
async def get_macro_report(
    report_id: int,
    repo: IReportRepository = Depends(deps.get_report_repository),
):
    row = repo.get_macro_report(report_id)
    if not row:
        raise HTTPException(404, "not found")
    return dict(row)


@router.post("/run")
async def run_macro(
    body: MacroRunRequest,
    use_case: GenerateMacroReportUseCase = Depends(deps.get_generate_macro_report_use_case),
):
    """启动兼容宏观报告生成 (SSE); Research Copilot runs use /v1/runs."""
    from sse_starlette.sse import EventSourceResponse

    async def event_generator():
        try:
            yield {"event": "progress", "data": json.dumps({"progress": 10, "message": "fetching market views..."})}
            yield {"event": "progress", "data": json.dumps({"progress": 40, "message": "generating AI strategy report..."})}
            request = GenerateMacroReportRequest(
                market=body.market,
                analyst_model=body.profile_name or "deepseek-chat",
                custom_prompt=body.custom_prompt,
            )
            response = await asyncio.to_thread(use_case.execute, request)
            if response.error:
                yield {"event": "progress", "data": json.dumps({"progress": -1, "message": "macro run failed"})}
                return
            yield {"event": "progress", "data": json.dumps({"progress": 80, "message": "archiving report..."})}
            yield {"event": "progress", "data": json.dumps({"progress": 100, "message": "done"})}
        except Exception:
            # Operator-safe fixed message (ADR-0007 envelope convention);
            # the macro path can carry the API key — never leak str(e).
            logger.exception("macro run failed")
            yield {"event": "progress", "data": json.dumps({"progress": -1, "message": "macro run failed"})}

    return EventSourceResponse(event_generator())
