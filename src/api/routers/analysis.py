"""
行业分析路由
"""

import os
from fastapi import APIRouter, HTTPException

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
