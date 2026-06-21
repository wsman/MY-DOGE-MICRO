"""
扫描路由 — POST /api/scan/{market}  (SSE)
          GET  /api/servers          (服务器列表)
          POST /api/servers/test     (测试连通性)
"""

import json
import asyncio
import threading
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sse_starlette.sse import EventSourceResponse

# S002-005 (TR-011 / TR-040): the interface layer MUST NOT open SQLite/DuckDB
# connections, import the legacy schema-init / DuckDB-connect writers, or
# recompute a project-root path inline (ADR-0001 forbidden patterns).
# All DB needs are routed through the clean layer:
#   - schema bootstrap + writes: SQLiteStorageRepository (single logical writer)
#   - market reads (US ticker list, kline, overview): IStockRepository via
#     ``deps.get_stock_repository`` (S005-009 — replaces the direct
#     SQLiteConnection adapter call that previously lived in this router)
#   - DuckDB view materialization: ViewService.refresh_views
#   - all paths: get_settings().db.* (never a local root derivation)
from doge.config import get_settings
from doge.application.contracts.request import ScanMarketRequest
from doge.core.ports.repository import IStockRepository
from doge.core.ports.tdx_server_list import ITDXServerList
from doge.application import refresh_views
from doge.interfaces.api import deps

logger = logging.getLogger(__name__)


def _db_path_for(market: str) -> str:
    """Resolve the market SQLite path via centralized settings (never a local root)."""
    settings = get_settings()
    return str(settings.db.cn_db if market == "cn" else settings.db.us_db)


# 扫描锁: 同一市场同时只能跑一个扫描
_scan_locks = {"cn": threading.Lock(), "us": threading.Lock()}
_scan_status = {"cn": "idle", "us": "idle"}

router = APIRouter()


# ---------------------------------------------------------------------------
#  服务器管理
# ---------------------------------------------------------------------------

@router.get("/servers")
async def get_servers(
    server_list: ITDXServerList = Depends(deps.get_tdx_server_list),
):
    """返回 CN / US 服务器列表"""
    return {
        "cn": [server.to_dict() for server in server_list.list_servers("cn")],
        "us": [server.to_dict() for server in server_list.list_servers("us")],
    }


class ServerTestRequest(BaseModel):
    market: str


@router.post("/servers/test")
async def test_servers(
    body: ServerTestRequest,
    server_list: ITDXServerList = Depends(deps.get_tdx_server_list),
):
    """并发测试所有服务器, 返回每个 IP 的延迟"""
    if body.market not in ("cn", "us"):
        raise HTTPException(400, "market must be 'cn' or 'us'")

    servers = server_list.list_servers(body.market)
    if not servers:
        return {"results": []}

    import concurrent.futures

    def _test(host: str):
        return server_list.test_server(host, body.market).to_dict()

    results = []
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(servers)))
    futures = {pool.submit(_test, server.host): server.host for server in servers}
    try:
        for future in concurrent.futures.as_completed(futures, timeout=15):
            results.append(future.result())
    except concurrent.futures.TimeoutError:
        for f in futures:
            if not f.done():
                host = futures[f]
                results.append({"host": host, "ok": False, "latency_ms": None, "error": "timeout"})
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    # 保持原始顺序
    host_order = {server.host: i for i, server in enumerate(servers)}
    results.sort(key=lambda r: host_order.get(r["host"], 999))
    return {"results": results}


# ---------------------------------------------------------------------------
#  扫描
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    tdx_path: str = ""
    use_server: bool = True
    server: Optional[str] = None   # 指定服务器 IP, null = 自动选择


@router.get("/status")
async def scan_status():
    return _scan_status


@router.post("/{market}")
async def start_scan(
    market: str,
    body: ScanRequest,
    stock_repo: IStockRepository = Depends(deps.get_stock_repository),
    storage_repo = Depends(deps.get_storage_repository),
):
    if market not in ("cn", "us"):
        raise HTTPException(400, "market must be 'cn' or 'us'")

    if not _scan_locks[market].acquire(blocking=False):
        raise HTTPException(409, f"{market} scan already running")

    _scan_status[market] = "running"

    # Capture the injected adapters at handler entry. ``run_scan`` below runs in
    # a BACKGROUND THREAD — calling ``Depends()`` there is not supported by
    # FastAPI (dependency resolution is bound to the request lifecycle, which
    # ends when the handler returns the EventSourceResponse). Passing the
    # already-resolved adapters into the closure keeps the DI seam intact while
    # preserving the existing streaming/threading shape (S005-009).
    repo = stock_repo
    storage = storage_repo

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

        def run_scan():
            try:
                # S002-005: schema bootstrap routed through the clean layer
                # (SQLiteStorageRepository.ensure_schema) instead of a direct
                # interface-layer import of the legacy schema-init function.
                # Path sourced from centralized settings, never a local root.
                db_path = _db_path_for(market)
                storage.ensure_schema(market)

                if body.use_server:
                    callback(2, f"preparing {market.upper()} server scan")
                    tickers = _load_scan_tickers(market, repo)
                    if tickers:
                        _run_server_scan(market, body, tickers, callback, storage)
                    else:
                        _run_local_scan(market, body.tdx_path, db_path, callback, storage)
                else:
                    _run_local_scan(market, body.tdx_path, db_path, callback, storage)

                # 刷新 DuckDB — routed through the clean ViewService.refresh_views
                # seam (S002-005). A refresh failure is LOGGED (logger.warning)
                # rather than silently swallowed, so a stuck/failed refresh is
                # observable on the server side (half of the S002-010
                # stuck-running concern). The scan still completes.
                try:
                    refresh_views()
                except Exception as refresh_err:
                    logger.warning(
                        "DuckDB view refresh failed after %s scan: %s",
                        market, refresh_err, exc_info=True,
                    )

                asyncio.run_coroutine_threadsafe(
                    queue.put({"progress": 100, "message": "done"}), loop
                )
            except Exception as e:
                # Operator-safe fixed message (ADR-0007 envelope convention);
                # never leak str(e) over SSE.
                logger.exception("scan failed")
                asyncio.run_coroutine_threadsafe(
                    queue.put({"progress": -1, "message": "scan failed"}), loop
                )
            finally:
                _scan_locks[market].release()
                _scan_status[market] = "idle"

        thread = threading.Thread(target=run_scan, daemon=True)
        thread.start()

        while True:
            event = await queue.get()
            yield {"event": "progress", "data": json.dumps(event)}
            if event.get("progress") in (100, -1):
                break

    return EventSourceResponse(event_generator())


def _run_local_scan(market, tdx_path, db_path, callback, storage_repo):
    """回退到本地 .day 文件扫描 via ScanMarketUseCase."""
    if not tdx_path:
        callback(0, "no tdx_path provided, skipping local scan")
        return

    from doge.application.composition import build_scan_market_use_case

    uc = build_scan_market_use_case(
        stock_repo=storage_repo,
        data_source=None,
        refresh_views_callable=lambda: None,
    )
    request = ScanMarketRequest(
        market=market,
        source="tdx-local",
        tdx_path=tdx_path,
    )

    def _wrapped_callback(pct, msg):
        callback(pct, msg)

    try:
        resp = uc.execute(request, progress_callback=_wrapped_callback)
        callback(100, f"local scan complete: {resp.success_count}/{resp.total_tickers} success")
    except Exception as e:
        logger.exception("local scan failed")
        callback(-1, "local scan failed")


def _load_scan_tickers(market: str, repo: IStockRepository) -> list[str]:
    if market == "cn":
        csv_path = Path(get_settings().stock_names_csv)
        if not csv_path.exists():
            return []
        try:
            import pandas as pd

            df = pd.read_csv(csv_path, dtype=str)
            values = df["ticker"].dropna().tolist() if "ticker" in df.columns else []
            return [
                str(ticker)
                for ticker in values
                if "." in str(ticker) and len(str(ticker).split(".")[0]) == 6
            ]
        except Exception:
            logger.exception("failed to load CN ticker CSV")
            return []
    return repo.list_distinct_tickers(market)


def _run_server_scan(market, body, tickers, callback, storage_repo):
    """Run remote TDX download through the application use case."""
    from doge.application.composition import build_scan_market_use_case, build_tdx_data_source

    if body.server:
        callback(2, f"using specified server {body.server}")
    uc = build_scan_market_use_case(
        stock_repo=storage_repo,
        data_source=build_tdx_data_source(preferred_server=body.server),
        refresh_views_callable=lambda: None,
    )
    request = ScanMarketRequest(
        market=market,
        source="tdx-server",
        tickers=tickers,
    )
    try:
        resp = uc.execute(request, progress_callback=callback)
        if resp.success_count == 0 and body.tdx_path:
            callback(0, "no server data available, trying local files...")
            _run_local_scan(market, body.tdx_path, _db_path_for(market), callback, storage_repo)
            return
        callback(100, f"server scan complete: {resp.success_count}/{resp.total_tickers} success")
    except Exception:
        logger.exception("server scan failed")
        if body.tdx_path:
            callback(0, "server scan failed, trying local files...")
            _run_local_scan(market, body.tdx_path, _db_path_for(market), callback, storage_repo)
        else:
            callback(-1, "server scan failed")
