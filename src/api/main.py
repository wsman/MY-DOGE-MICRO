"""
MY-DOGE-MICRO FastAPI Backend
Tauri sidecar — runs on localhost:8901
"""

import os

# ── 路径设置 ──────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── OpenBLAS 安全设置 ────────────────────────────────
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import scan, data, notes, macro, analysis, config

app = FastAPI(title="MY-DOGE API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 仅 localhost, 无安全风险
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ─────────────────────────────────────────
app.include_router(scan.router,   prefix="/api/scan",     tags=["scan"])
app.include_router(data.router,   prefix="/api/data",     tags=["data"])
app.include_router(notes.router,  prefix="/api/notes",    tags=["notes"])
app.include_router(macro.router,  prefix="/api/macro",    tags=["macro"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(config.router, prefix="/api/config",   tags=["config"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/stats")
async def stats():
    """数据库概览统计"""
    import sqlite3
    result = {}
    data_dir = os.path.join(_PROJECT_ROOT, "data")
    for db_name in ["market_data_cn.db", "market_data_us.db", "research_insights.db"]:
        db_path = os.path.join(data_dir, db_name)
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            db_stats = {}
            for t in tables:
                cur.execute(f"SELECT COUNT(*) FROM [{t}]")
                db_stats[t] = cur.fetchone()[0]
            conn.close()
            result[db_name] = db_stats
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8901)
