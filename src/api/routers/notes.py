"""
评论路由 — CRUD
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class NoteCreate(BaseModel):
    ticker: str
    content: str
    market: str = "cn"
    note_type: str = "comment"
    title: Optional[str] = None
    tags: Optional[str] = None


@router.get("/ticker/{ticker}")
async def get_ticker_context(ticker: str):
    """股票全景: 价格 + 名称 + 评论"""
    # NOTE: unwrapped (S002-009). Failures surface via the global handler in
    # src/api/main.py, which logs server-side and returns the stable envelope.
    from src.ai_analysis.stock_notes import get_ticker_with_context
    ctx = get_ticker_with_context(ticker)
    # 将 DataFrame 转为可序列化格式
    if "price_data" in ctx and hasattr(ctx["price_data"], "to_dict"):
        ctx["price_data"] = ctx["price_data"].to_dict(orient="records")
    return ctx


@router.post("")
async def add_note(note: NoteCreate):
    from src.ai_analysis.stock_notes import add_note as _add
    note_id = _add(
        ticker=note.ticker,
        content=note.content,
        market=note.market,
        note_type=note.note_type,
        title=note.title,
        tags=note.tags,
    )
    return {"id": note_id}


@router.get("/search")
async def search_notes(q: str = Query(..., min_length=1), limit: int = 50):
    from src.ai_analysis.stock_notes import search_notes as _search
    results = _search(q, limit=limit)
    return {"results": results}


@router.get("/recent")
async def recent_notes(days: int = 7, limit: int = 100):
    from src.ai_analysis.stock_notes import get_recent_notes
    return {"results": get_recent_notes(days=days, limit=limit)}


@router.get("/tracked")
async def tracked_tickers():
    from src.ai_analysis.stock_notes import list_tracked_tickers
    return {"tickers": list_tracked_tickers()}


@router.delete("/{note_id}")
async def delete_note(note_id: int):
    """Soft-delete a note.

    Returns 200 ``{"ok": true}`` when a note was deleted (soft-delete applied),
    404 when no active note with ``note_id`` exists (missing id, already
    deleted, or never existed).
    """
    from src.ai_analysis.stock_notes import delete_note as _delete
    deleted = _delete(note_id)
    if not deleted:
        raise HTTPException(404, "note not found")
    return {"ok": True}
