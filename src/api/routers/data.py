"""
数据浏览路由 — 表列表、分页查询、K 线数据
"""

import json
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from doge.config import get_settings
from doge.core.ports.repository import ISchemaBrowser, IStockRepository
from doge.interfaces.api import deps

# S002-009 / TR-011: project root sourced from get_settings() (ADR-0001
# forbidden pattern ``_PROJECT_ROOT`` dirname-walk). The module-global name is
# KEPT only for the ticker-names JSON cache, which is file I/O rather than a
# database connection.
_PROJECT_ROOT = str(get_settings().project_root)

router = APIRouter()


@router.get("/{market}/tables")
async def list_tables(
    market: str,
    browser: ISchemaBrowser = Depends(deps.get_schema_browser),
):
    valid_markets = {"cn", "us", "research"}
    if market not in valid_markets:
        raise HTTPException(400, f"market must be one of {sorted(valid_markets)}")
    return {"tables": browser.list_tables(market)}


@router.get("/{market}/table/{table_name}")
async def query_table(
    market: str,
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    browser: ISchemaBrowser = Depends(deps.get_schema_browser),
):
    valid_markets = {"cn", "us", "research"}
    if market not in valid_markets:
        raise HTTPException(400, "invalid market")

    try:
        return browser.query_table(
            market=market,
            table_name=table_name,
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{market}/ticker/{ticker}/kline")
async def get_kline(
    market: str,
    ticker: str,
    days: int = Query(120, ge=1, le=365),
    repo: IStockRepository = Depends(deps.get_stock_repository),
):
    """获取 K 线 OHLCV 数据 (含 MA 指标)"""
    if market not in ("cn", "us"):
        raise HTTPException(400, "market must be cn or us")

    data = repo.get_kline(ticker=ticker, market=market, days=days)
    return {"data": data}


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
