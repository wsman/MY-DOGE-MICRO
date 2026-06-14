"""
评论路由 — CRUD
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from doge.interfaces.api import deps
from doge.core.ports.repository import INoteRepository

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
    repo: INoteRepository = Depends(deps.get_note_repository),
):
    """股票全景: 价格 + 名称 + 评论"""
    ctx = repo.get_ticker_with_context(ticker, market="cn")
    # 将 DataFrame 转为可序列化格式
    if "price_data" in ctx and hasattr(ctx["price_data"], "to_dict"):
        ctx["price_data"] = ctx["price_data"].to_dict(orient="records")
    return ctx


@router.post("")
async def add_note(
    note: NoteCreate,
    repo: INoteRepository = Depends(deps.get_note_repository),
):
    note_id = repo.add_note(
        ticker=note.ticker,
        note_text=note.content,
        market=note.market,
        note_type=note.note_type,
        title=note.title,
        tags=note.tags,
    )
    return {"id": note_id}


@router.get("/search")
async def search_notes(
    q: str = Query(..., min_length=1),
    limit: int = 50,
    repo: INoteRepository = Depends(deps.get_note_repository),
):
    results = repo.search_notes(q, limit=limit)
    return {"results": results}


@router.get("/recent")
async def recent_notes(
    days: int = 7,
    limit: int = 100,
    repo: INoteRepository = Depends(deps.get_note_repository),
):
    return {"results": repo.get_recent_notes(days=days, limit=limit)}


@router.get("/tracked")
async def tracked_tickers(
    repo: INoteRepository = Depends(deps.get_note_repository),
):
    return {"tickers": repo.list_tracked_tickers()}


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    repo: INoteRepository = Depends(deps.get_note_repository),
):
    """Soft-delete a note.

    Returns 200 ``{"ok": true}`` when a note was deleted (soft-delete applied),
    404 when no active note with ``note_id`` exists (missing id, already
    deleted, or never existed).
    """
    deleted = repo.delete_note(note_id)
    if not deleted:
        raise HTTPException(404, "note not found")
    return {"ok": True}
