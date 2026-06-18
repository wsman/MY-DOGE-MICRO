"""
扫描路由 — POST /api/scan/{market}  (SSE)
          GET  /api/servers          (服务器列表)
          POST /api/servers/test     (测试连通性)
"""

import json
import os
import asyncio
import threading
import time
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
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
from doge.core.ports.repository import IStockRepository
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

def _load_servers():
    """加载 TDX 服务器列表"""
    try:
        from src.micro.tdx_downloader import CN_SERVERS, US_SERVERS
        return list(CN_SERVERS), list(US_SERVERS)
    except ImportError:
        return (
            ["180.153.18.170", "180.153.18.171", "60.191.117.167",
             "115.238.56.198", "218.75.126.9"],
            ["112.74.214.43", "120.25.218.6", "43.139.173.246",
             "159.75.90.107", "139.9.191.175"],
        )


@router.get("/servers")
async def get_servers():
    """返回 CN / US 服务器列表"""
    cn, us = _load_servers()
    return {
        "cn": [{"host": h, "port": 7709, "latency_ms": None} for h in cn],
        "us": [{"host": h, "port": 7727, "latency_ms": None} for h in us],
    }


class ServerTestRequest(BaseModel):
    market: str


@router.post("/servers/test")
async def test_servers(body: ServerTestRequest):
    """并发测试所有服务器, 返回每个 IP 的延迟"""
    if body.market not in ("cn", "us"):
        raise HTTPException(400, "market must be 'cn' or 'us'")

    cn, us = _load_servers()
    servers = cn if body.market == "cn" else us
    port = 7709 if body.market == "cn" else 7727

    import concurrent.futures

    def _test(host):
        try:
            from opentdx.tdxClient import TdxClient
            client = TdxClient()
            t0 = time.time()
            client.quotation_client.connect(host, port=port, time_out=5)
            client.quotation_client.login()
            if body.market == "us":
                client.ex_quotation_client.connect(host, port=7727, time_out=5)
                client.ex_quotation_client.login()
            latency = int((time.time() - t0) * 1000)
            try:
                client.quotation_client.disconnect()
                if body.market == "us":
                    client.ex_quotation_client.disconnect()
            except Exception:
                pass
            return {"host": host, "ok": True, "latency_ms": latency}
        except Exception as e:
            return {"host": host, "ok": False, "latency_ms": None, "error": str(e)}

    results = []
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(servers)))
    futures = {pool.submit(_test, h): h for h in servers}
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
    host_order = {h: i for i, h in enumerate(servers)}
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
                    # 优先走服务器下载
                    from src.micro.tdx_downloader import (
                        find_working_server, download_cn_kline, download_us_kline,
                        CN_SERVERS, US_SERVERS,
                    )

                    csv_path = str(get_settings().stock_names_csv)

                    if market == "cn":
                        import pandas as pd
                        if os.path.exists(csv_path):
                            df = pd.read_csv(csv_path, dtype=str)
                            tickers = df['ticker'].tolist()
                            tickers = [t for t in tickers if '.' in t and len(t.split('.')[0]) == 6]
                        else:
                            tickers = []
                        servers = CN_SERVERS
                        download_fn = download_cn_kline
                    else:
                        # 美股: read distinct US tickers via the injected
                        # IStockRepository port (S005-009). Previously this
                        # branch called ``SQLiteConnection(db_path).execute(
                        # "SELECT DISTINCT ticker FROM stock_prices")``
                        # directly from the router — a raw-SQL read in the
                        # interface layer. The port-backed call preserves the
                        # exact same read (DuckDB attaches the US SQLite file
                        # read-only and queries ``us.stock_prices``) while
                        # keeping the literal ``sqlite3`` symbol out of this
                        # module. ``[]`` is a benign "no tickers tracked" and
                        # flows through to the no-server-scan branch below.
                        tickers = repo.list_distinct_tickers(market)
                        servers = US_SERVERS
                        download_fn = download_us_kline

                    if tickers and servers:
                        # 如果指定了服务器, 直接用它
                        if body.server:
                            servers = [body.server]
                            callback(2, f"using specified server {body.server}")
                        client, host = find_working_server(servers, market)
                        if client:
                            callback(5, f"connected to {host}")
                            download_fn(client, tickers, db_path, progress_cb=callback)
                            client.quotation_client.disconnect()
                            if market == "us":
                                try:
                                    client.ex_quotation_client.disconnect()
                                except Exception:
                                    pass
                        else:
                            callback(0, "no server available, trying local files...")
                            _run_local_scan(market, body.tdx_path, db_path, callback, storage)
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
    from doge.application.contracts.request import ScanMarketRequest

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
