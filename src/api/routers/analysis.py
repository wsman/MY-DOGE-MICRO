"""
行业分析路由
"""

import os
from fastapi import APIRouter, HTTPException

# S002-009 / TR-011: project root sourced from get_settings() (ADR-0001
# forbidden pattern ``_PROJECT_ROOT`` dirname-walk). The module-global name is
# KEPT so the contract test (tests/test_api_routers.py:151) can monkeypatch it
# to a temp dir; only the *derivation* changed (settings vs os.path.dirname
# walk). The router STILL does sqlite3.connect directly; the clean-layer
# router DI is deferred to Batch-5 (out of scope here).
from doge.config import get_settings

_PROJECT_ROOT = str(get_settings().project_root)

router = APIRouter()


@router.get("/reports")
async def list_research_reports():
    import sqlite3
    db_path = os.path.join(_PROJECT_ROOT, "data", "research_insights.db")
    if not os.path.exists(db_path):
        return {"reports": []}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, date, timestamp, tags, analyst, title FROM research_reports ORDER BY date DESC")
    reports = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"reports": reports}


@router.get("/reports/{report_id}")
async def get_research_report(report_id: int):
    import sqlite3
    db_path = os.path.join(_PROJECT_ROOT, "data", "research_insights.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM research_reports WHERE id = ?", (report_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "not found")
    return dict(row)
