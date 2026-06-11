"""
宏观分析路由
"""

import os
import json
import asyncio
import threading
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

router = APIRouter()


class MacroRunRequest(BaseModel):
    profile_name: Optional[str] = None


@router.get("/reports")
async def list_macro_reports():
    """列出所有宏观报告"""
    import sqlite3
    db_path = os.path.join(_PROJECT_ROOT, "data", "research_insights.db")
    if not os.path.exists(db_path):
        return {"reports": []}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, date, timestamp, tags, analyst, risk_signal, volatility FROM macro_reports ORDER BY date DESC, timestamp DESC")
    reports = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"reports": reports}


@router.get("/reports/latest")
async def latest_macro_report():
    """最新宏观报告"""
    import sqlite3
    db_path = os.path.join(_PROJECT_ROOT, "data", "research_insights.db")
    if not os.path.exists(db_path):
        raise HTTPException(404, "no reports")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM macro_reports ORDER BY date DESC, timestamp DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "no reports")
    return dict(row)


@router.get("/reports/{report_id}")
async def get_macro_report(report_id: int):
    import sqlite3
    db_path = os.path.join(_PROJECT_ROOT, "data", "research_insights.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM macro_reports WHERE id = ?", (report_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "not found")
    return dict(row)


@router.post("/run")
async def run_macro(body: MacroRunRequest):
    """启动宏观分析 (SSE)"""
    from sse_starlette.sse import EventSourceResponse

    async def event_generator():
        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def callback(pct, msg):
            try:
                asyncio.run_coroutine_threadsafe(
                    queue.put({"progress": pct, "message": str(msg)}), loop
                )
            except Exception:
                pass

        def run():
            try:
                from src.macro.data_loader import GlobalMacroLoader
                from src.macro.strategist import DeepSeekStrategist
                from src.micro.database import save_macro_report

                callback(10, "fetching global market data...")
                loader = GlobalMacroLoader()
                data_df = loader.fetch_combined_data()

                callback(40, "calculating metrics...")
                metrics = loader.calculate_metrics(data_df)

                callback(60, "generating AI strategy report...")
                strategist = DeepSeekStrategist()
                report = strategist.generate_strategy_report(metrics, data_df)

                callback(80, "archiving report...")
                save_macro_report(
                    content=report,
                    risk_signal=metrics.get("risk_signal", "N/A"),
                    volatility=metrics.get("current_volatility", "N/A"),
                )

                asyncio.run_coroutine_threadsafe(
                    queue.put({"progress": 100, "message": "done"}), loop
                )
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    queue.put({"progress": -1, "message": f"error: {e}"}), loop
                )

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        while True:
            event = await queue.get()
            yield {"event": "progress", "data": json.dumps(event)}
            if event.get("progress") in (100, -1):
                break

    return EventSourceResponse(event_generator())
