"""评论路由 — CRUD

All storage access is now routed through ``ManageNotesUseCase`` via the
``deps.get_manage_notes_use_case`` provider. The response shapes are preserved
from the legacy direct-repository implementation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from doge.application.contracts.request import ManageNoteRequest
from doge.interfaces.api import deps

router = APIRouter()


class NoteCreate(BaseModel):
    ticker: str
    content: str
    market: str = "cn"
    note_type: str = "comment"
    title: Optional[str] = None
    tags: Optional[str] = None


@router.get("/ticker/{ticker}")
async def get_ticker_context(
    ticker: str,
    _uc=Depends(deps.get_manage_notes_use_case),
):
    """股票全景: 价格 + 名称 + 评论"""
    resp = _uc.execute(
        ManageNoteRequest(operation="get_context", ticker=ticker, market="cn")
    )
    ctx = resp.context
    # 将 DataFrame 转为可序列化格式
    if "price_data" in ctx and hasattr(ctx["price_data"], "to_dict"):
        ctx["price_data"] = ctx["price_data"].to_dict(orient="records")
    return ctx


@router.post("")
async def add_note(
    note: NoteCreate,
    _uc=Depends(deps.get_manage_notes_use_case),
):
    resp = _uc.execute(
        ManageNoteRequest(
            operation="add",
            ticker=note.ticker,
            note_text=note.content,
            market=note.market,
            note_type=note.note_type,
            title=note.title,
            tags=note.tags,
        )
    )
    return {"id": resp.note_id}


@router.get("/search")
async def search_notes(
    q: str = Query(..., min_length=1),
    limit: int = 50,
    _uc=Depends(deps.get_manage_notes_use_case),
):
    resp = _uc.execute(
        ManageNoteRequest(operation="search", keyword=q, limit=limit)
    )
    return {"results": resp.notes}


@router.get("/recent")
async def recent_notes(
    days: int = 7,
    limit: int = 100,
    _uc=Depends(deps.get_manage_notes_use_case),
):
    resp = _uc.execute(
        ManageNoteRequest(operation="recent", days=days, limit=limit)
    )
    return {"results": resp.notes}


@router.get("/tracked")
async def tracked_tickers(
    _uc=Depends(deps.get_manage_notes_use_case),
):
    resp = _uc.execute(ManageNoteRequest(operation="tracked"))
    return {"tickers": resp.notes}


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    _uc=Depends(deps.get_manage_notes_use_case),
):
    """Soft-delete a note.

    Returns 200 ``{"ok": true}`` when a note was deleted (soft-delete applied),
    404 when no active note with ``note_id`` exists (missing id, already
    deleted, or never existed).
    """
    resp = _uc.execute(
        ManageNoteRequest(operation="delete", note_id=note_id)
    )
    if not resp.success:
        raise HTTPException(404, "note not found")
    return {"ok": True}
