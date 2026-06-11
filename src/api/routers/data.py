"""
数据浏览路由 — 表列表、分页查询、K 线数据
"""

import json
import os
import sqlite3
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_DB_MAP = {
    "cn": os.path.join(_PROJECT_ROOT, "data", "market_data_cn.db"),
    "us": os.path.join(_PROJECT_ROOT, "data", "market_data_us.db"),
    "research": os.path.join(_PROJECT_ROOT, "data", "research_insights.db"),
}

router = APIRouter()


@router.get("/{market}/tables")
async def list_tables(market: str):
    if market not in _DB_MAP:
        raise HTTPException(400, f"market must be one of {list(_DB_MAP.keys())}")
    db_path = _DB_MAP[market]
    if not os.path.exists(db_path):
        return {"tables": []}
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    return {"tables": tables}


@router.get("/{market}/table/{table_name}")
async def query_table(
    market: str,
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
):
    if market not in _DB_MAP:
        raise HTTPException(400, "invalid market")
    db_path = _DB_MAP[market]
    if not os.path.exists(db_path):
        raise HTTPException(404, "database not found")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 安全检查表名
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, f"table '{table_name}' not found")

    # 获取列名
    cur.execute(f"PRAGMA table_info([{table_name}])")
    columns = [r[1] for r in cur.fetchall()]

    # 构建查询
    where = ""
    params = []
    if search and columns:
        conditions = " OR ".join([f"CAST([{col}] AS TEXT) LIKE ?" for col in columns[:5]])
        where = f"WHERE {conditions}"
        params = [f"%{search}%"] * min(5, len(columns))

    # 总行数
    cur.execute(f"SELECT COUNT(*) FROM [{table_name}] {where}", params)
    total = cur.fetchone()[0]

    # 排序
    order = ""
    if sort_by and sort_by in columns:
        direction = "DESC" if sort_order == "desc" else "ASC"
        order = f"ORDER BY [{sort_by}] {direction}"
    elif "date" in columns and "ticker" in columns:
        order = "ORDER BY date DESC, ticker ASC"

    # 分页
    offset = (page - 1) * page_size
    cur.execute(f"SELECT * FROM [{table_name}] {where} {order} LIMIT ? OFFSET ?",
                params + [page_size, offset])
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "columns": columns,
        "rows": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{market}/ticker/{ticker}/kline")
async def get_kline(market: str, ticker: str, days: int = Query(120, ge=1, le=365)):
    """获取 K 线 OHLCV 数据 (含 MA 指标)"""
    if market not in ("cn", "us"):
        raise HTTPException(400, "market must be cn or us")

    try:
        from src.ai_analysis import connect_duckdb
        con = connect_duckdb()

        if market == "cn":
            view = "vw_daily_enriched_cn"
            base_table = "cn.stock_prices"
        else:
            view = None
            base_table = "us.stock_prices"

        if view:
            df = con.execute(f"""
                SELECT date, open, high, low, close, volume,
                       ma_5, ma_10, ma_20, ma_60, atr_14
                FROM {view}
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT ?
            """, [ticker, days]).df()
        else:
            df = con.execute(f"""
                SELECT date, open, high, low, close, volume, amount
                FROM {base_table}
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT ?
            """, [ticker, days]).df()

        con.close()
        df = df.sort_values("date")
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(500, str(e))


# --- 股票名称映射缓存 ---
_ticker_names_cache: dict[str, dict[str, str]] = {}


def _load_ticker_names(market: str) -> dict[str, str]:
    """从本地 JSON 文件加载股票代码→名称映射（优先），否则在线获取"""
    if market in _ticker_names_cache:
        return _ticker_names_cache[market]

    names: dict[str, str] = {}

    # 1. 尝试从本地 JSON 文件加载
    json_path = os.path.join(_PROJECT_ROOT, "data", f"{market}_ticker_names.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                names = json.load(f)
            _ticker_names_cache[market] = names
            return names
        except Exception:
            pass

    # 2. 回退: 在线获取 (cn 用 akshare, us 暂无)
    if market == "cn":
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            for _, row in df.iterrows():
                code = str(row["code"]).zfill(6)
                name = str(row["name"])
                suffix = ".SH" if code.startswith("6") else ".SZ"
                names[code + suffix] = name
            # 缓存到文件
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(names, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        except Exception:
            pass

    _ticker_names_cache[market] = names
    return names


@router.get("/{market}/ticker-names")
async def get_ticker_names(market: str):
    """获取股票代码→名称映射"""
    if market not in ("cn", "us"):
        raise HTTPException(400, "market must be cn or us")

    names = _load_ticker_names(market)
    return {"names": names, "count": len(names)}
