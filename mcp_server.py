"""
MY-DOGE Database Analysis MCP Server — Production Grade

Supports dual transport:
  stdio  : for local Claude Code integration
  sse    : for standalone HTTP deployment

Usage:
  python mcp_server.py --transport stdio
  python mcp_server.py --transport sse --host 127.0.0.1 --port 8902
"""

import argparse
import contextvars
import functools
import json
import logging
import logging.handlers
import os
import platform as _platform
import re
import signal as _signal
import sqlite3
import subprocess as _sp
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE / "src"))

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from ai_analysis import get_duckdb_connection, RESEARCH_DB, normalize_ticker

# ── Logging ───────────────────────────────────────────
LOG_DIR = _HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)

correlation_id = contextvars.ContextVar("correlation_id", default="-")


class _CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id.get() or "-"
        return True


def _setup_logging(level: int = logging.INFO) -> None:
    fmt = "%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt)

    fh = logging.handlers.RotatingFileHandler(
        LOG_DIR / "mcp_server.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(formatter)
    fh.addFilter(_CorrelationFilter())

    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(formatter)
    ch.addFilter(_CorrelationFilter())

    root = logging.getLogger()
    root.setLevel(level)
    # avoid duplicate handlers on re-import
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        root.addHandler(fh)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(ch)


_setup_logging()
logger = logging.getLogger("doge-mcp")

# ── Metrics (in-memory counters) ──────────────────────
REQUEST_COUNT: Dict[str, int] = {}
REQUEST_DURATION: Dict[str, List[float]] = {}

# ── PID file for orphan detection (read-only, no killing) ──
PID_FILE = _HERE / "data" / ".mcp_server.pid"
_IS_WINDOWS = _platform.system() == "Windows"


def _register_pid():
    """Append current PID to PID file. Each line: PID."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if PID_FILE.exists():
        existing = PID_FILE.read_text()
    pids = [line.strip() for line in existing.splitlines() if line.strip()]
    pids.append(str(os.getpid()))
    PID_FILE.write_text("\n".join(pids) + "\n")


def _unregister_pid():
    """Remove current PID from PID file."""
    if not PID_FILE.exists():
        return
    my_pid = str(os.getpid())
    try:
        pids = PID_FILE.read_text().splitlines()
        pids = [p for p in pids if p.strip() != my_pid]
        if pids:
            PID_FILE.write_text("\n".join(pids) + "\n")
        else:
            PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _detect_orphan_processes():
    """Log warning if orphaned mcp_server.py processes are detected."""
    if not PID_FILE.exists():
        return
    try:
        pids = [p.strip() for p in PID_FILE.read_text().splitlines() if p.strip()]
        alive = []
        for pid_str in pids:
            try:
                pid = int(pid_str)
            except ValueError:
                continue
            if pid == os.getpid():
                continue
            if _IS_WINDOWS:
                r = _sp.run(
                    ["wmic", "process", "where", f"ProcessId={pid}",
                     "get", "CommandLine", "/value"],
                    capture_output=True, text=True, timeout=5,
                )
                if "mcp_server.py" in r.stdout:
                    alive.append(pid)
            else:
                try:
                    cmdline = Path(f"/proc/{pid}/cmdline").read_text("\x00")
                    if "mcp_server.py" in cmdline:
                        alive.append(pid)
                except FileNotFoundError:
                    pass
        if alive:
            logger.warning(
                "Detected %d concurrent mcp_server.py process(es): %s. "
                "DuckDB read-only mode supports concurrent access.",
                len(alive), alive,
            )
    except Exception as exc:
        logger.debug("Orphan detection failed: %s", exc)


TOOL_TIMEOUT = 30  # seconds


def _timed(tool_name: str):
    """Decorator that logs entry/exit, sets correlation_id, records metrics,
    and enforces a timeout to prevent indefinite hangs."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            import asyncio
            cid = str(uuid.uuid4())[:8]
            correlation_id.set(cid)
            logger.info("TOOL CALL: %s args=%s", tool_name, kwargs)
            t0 = time.time()
            try:
                result = await asyncio.wait_for(fn(*args, **kwargs), timeout=TOOL_TIMEOUT)
                dur = time.time() - t0
                REQUEST_COUNT[tool_name] = REQUEST_COUNT.get(tool_name, 0) + 1
                REQUEST_DURATION.setdefault(tool_name, []).append(dur)
                logger.info(
                    "TOOL CALL: %s ok duration=%.3fs result_len=%d",
                    tool_name, dur, len(result) if isinstance(result, str) else 0,
                )
                return result
            except asyncio.TimeoutError:
                dur = time.time() - t0
                logger.error("TOOL CALL: %s TIMEOUT after %.1fs", tool_name, dur)
                return f"Error: {tool_name} timed out after {TOOL_TIMEOUT}s"
            except Exception as exc:
                dur = time.time() - t0
                logger.error(
                    "TOOL CALL: %s ERROR: %s: %s",
                    tool_name, type(exc).__name__, exc,
                    exc_info=True,
                )
                return f"Error: {type(exc).__name__}: {exc}"
        return wrapper
    return decorator


# ── Validation ────────────────────────────────────────
_MARKET_WHITELIST = {"cn", "us"}


def _validate_market(market: str) -> str:
    m = (market or "cn").lower()
    if m not in _MARKET_WHITELIST:
        raise ValueError(f"Invalid market: {market}. Must be one of {_MARKET_WHITELIST}.")
    return m


def _validate_ticker(ticker: str) -> str:
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("ticker is required")
    return normalize_ticker(ticker.strip())


def _validate_int(name: str, value: int, min_val: int = 1, max_val: int = 500) -> int:
    if not isinstance(value, int) or value < min_val or value > max_val:
        raise ValueError(f"{name} must be an integer between {min_val} and {max_val}")
    return value


def _validate_float(name: str, value: float, min_val: float = 0.0, max_val: float = 1e6) -> float:
    if not isinstance(value, (int, float)) or value < min_val or value > max_val:
        raise ValueError(f"{name} must be a number between {min_val} and {max_val}")
    return float(value)


# ── Formatting helpers ────────────────────────────────
def _fmt(columns: List[str], rows: List[Any]) -> str:
    if not rows:
        return ""
    cw = [len(c) for c in columns]
    sr = []
    for row in rows:
        tr = []
        for i, v in enumerate(row):
            s = f"{v:.2f}" if isinstance(v, float) else str(v)
            tr.append(s)
            cw[i] = max(cw[i], len(s))
        sr.append(tr)
    lines = ["  ".join(c.ljust(cw[i]) for i, c in enumerate(columns))]
    for r in sr:
        lines.append("  ".join(s.ljust(cw[i]) for i, s in enumerate(r)))
    return "\n".join(lines)


# ── Lifespan ──────────────────────────────────────────
@asynccontextmanager
async def _lifespan(app: FastMCP):
    logger.info("=== SERVER START ===")
    _register_pid()
    _detect_orphan_processes()
    try:
        with get_duckdb_connection() as con:
            con.execute("SELECT 1")
        logger.info("DuckDB pre-warm OK")
    except Exception as exc:
        logger.error("DuckDB pre-warm failed: %s", exc, exc_info=True)
    yield
    _unregister_pid()
    logger.info("=== SERVER SHUTDOWN ===")


mcp = FastMCP("doge-db", lifespan=_lifespan)


# ── Tools ─────────────────────────────────────────────
@mcp.tool()
@_timed("query_stock")
async def query_stock(ticker: str, market: str = "cn", days: int = 20) -> str:
    """查询个股行情数据（OHLCV、均线、ATR、波动率等技术指标）。"""
    m = _validate_market(market)
    t = _validate_ticker(ticker)
    d = _validate_int("days", days, 1, 500)

    with get_duckdb_connection() as con:
        if m == "cn":
            sql = (
                "SELECT date, open, high, low, close, volume, "
                "ROUND(return_pct,2) AS ret_pct, ma_5, ma_10, ma_20, ma_60, "
                "ROUND(atr_14,2) AS atr14, ROUND(ma60_deviation,2) AS ma60_dev, "
                "ROUND(volatility_20d,2) AS vol_20d "
                "FROM vw_daily_enriched_cn WHERE ticker=? ORDER BY date DESC LIMIT ?"
            )
        else:
            sql = (
                "SELECT date, open, high, low, close, volume, amount "
                "FROM us.stock_prices WHERE ticker=? ORDER BY date DESC LIMIT ?"
            )
        r = con.execute(sql, [t, d])
        cols = [desc[0] for desc in r.description]
        rows = r.fetchall()
        return _fmt(cols, rows) if rows else f"No data for {t}"


@mcp.tool()
@_timed("stock_overview")
async def stock_overview(ticker: str, market: str = "cn") -> str:
    """个股概览：名称、板块、最新价格、笔记。"""
    m = _validate_market(market)
    t = _validate_ticker(ticker)
    lines = [f"=== {t} ({m.upper()}) ==="]

    # 名称与板块
    try:
        conn = sqlite3.connect(str(RESEARCH_DB))
        cur = conn.cursor()
        row = cur.execute(
            "SELECT name_cn, sector FROM stock_names WHERE ticker=?", (t,)
        ).fetchone()
        if row:
            if row[0]:
                lines.append(f"名称: {row[0]}")
            if row[1]:
                lines.append(f"板块: {row[1]}")
        conn.close()
    except sqlite3.Error as exc:
        logger.error("stock_overview SQLite error (names): %s", exc, exc_info=True)

    # 最新价格
    try:
        with get_duckdb_connection() as con:
            db = "cn" if m == "cn" else "us"
            prices = con.execute(
                f"SELECT date, open, high, low, close, volume "
                f"FROM {db}.stock_prices WHERE ticker=? ORDER BY date DESC LIMIT 10",
                [t],
            ).fetchall()
            if prices:
                lines.append(f"\n最新: {prices[0][0]} 收盘: {prices[0][4]}")
                if len(prices) > 1:
                    chg = (prices[0][4] - prices[1][4]) / prices[1][4] * 100
                    lines.append(f"涨跌幅: {chg:.2f}%")
                for r in prices[:10]:
                    lines.append(f"  {r[0]} | O:{r[1]} H:{r[2]} L:{r[3]} C:{r[4]} V:{r[5]}")
    except Exception as exc:
        logger.error("stock_overview price query error: %s", exc, exc_info=True)
        lines.append(f"\n价格查询失败: {exc}")

    # 笔记
    try:
        conn = sqlite3.connect(str(RESEARCH_DB))
        cur = conn.cursor()
        n = cur.execute(
            "SELECT COUNT(*) FROM stock_notes WHERE ticker=?", (t,)
        ).fetchone()[0]
        notes = cur.execute(
            "SELECT created_at, content FROM stock_notes WHERE ticker=? ORDER BY created_at DESC LIMIT 5",
            (t,),
        ).fetchall()
        conn.close()
        if notes:
            lines.append(f"\n笔记 ({n} 条):")
            for x in notes:
                lines.append(f"  [{x[0]}] {x[1][:80]}")
        else:
            lines.append("\n暂无笔记")
    except sqlite3.Error as exc:
        logger.error("stock_overview SQLite error (notes): %s", exc, exc_info=True)
        lines.append("\n暂无笔记")

    return "\n".join(lines)


@mcp.tool()
@_timed("rsrs_ranking")
async def rsrs_ranking(market: str = "cn", top: int = 20) -> str:
    """RSRS 动量排名（最强趋势股票排行）。"""
    m = _validate_market(market)
    n = _validate_int("top", top, 1, 100)
    view = "vw_rsrs_ranking_cn" if m == "cn" else "vw_rsrs_ranking_us"

    with get_duckdb_connection() as con:
        r = con.execute(f"SELECT * FROM {view} LIMIT ?", [n])
        return _fmt([d[0] for d in r.description], r.fetchall()) or "No data"


@mcp.tool()
@_timed("market_breadth")
async def market_breadth(market: str = "cn", days: int = 10) -> str:
    """市场宽度（每日涨跌家数、上涨占比、平均涨跌幅）。"""
    m = _validate_market(market)
    d = _validate_int("days", days, 1, 100)
    view = "vw_market_breadth_cn" if m == "cn" else "vw_market_breadth_us"

    with get_duckdb_connection() as con:
        r = con.execute(f"SELECT * FROM {view} LIMIT ?", [d])
        return _fmt([d[0] for d in r.description], r.fetchall()) or "No data"


@mcp.tool()
@_timed("volume_anomalies")
async def volume_anomalies(min_ratio: float = 3.0, top: int = 20) -> str:
    """成交量异常股票（量比排名，发现放量异动）。"""
    ratio = _validate_float("min_ratio", min_ratio, 1.0, 1000.0)
    n = _validate_int("top", top, 1, 100)

    with get_duckdb_connection() as con:
        r = con.execute(
            "SELECT ticker, date, volume, ROUND(avg_vol_20d,0) AS avg_vol, "
            "ROUND(vol_ratio,2) AS vol_ratio, ROUND(intraday_return,2) AS ret_pct "
            "FROM vw_volume_anomalies_cn WHERE vol_ratio>=? ORDER BY vol_ratio DESC LIMIT ?",
            [ratio, n],
        )
        return _fmt([d[0] for d in r.description], r.fetchall()) or "No anomalies"


@mcp.tool()
@_timed("list_views")
async def list_views() -> str:
    """列出 DuckDB 中所有视图及其行数、列名。"""
    with get_duckdb_connection() as con:
        views = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_type='VIEW'"
        ).fetchall()
        rows = []
        for (vn,) in views:
            try:
                cnt = con.execute(f"SELECT COUNT(*) FROM {vn}").fetchone()[0]
                cols = con.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name=?",
                    [vn],
                ).fetchall()
                rows.append({
                    "view": vn,
                    "rows": cnt,
                    "columns": ", ".join(c[0] for c in cols),
                })
            except Exception as exc:
                logger.warning("list_views failed for %s: %s", vn, exc)
                rows.append({"view": vn, "rows": None, "columns": ""})
        return json.dumps(rows, indent=2, ensure_ascii=False)


# ── Health & metrics routes (SSE only) ────────────────
from starlette.requests import Request
from starlette.responses import JSONResponse

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request):
    try:
        with get_duckdb_connection() as con:
            con.execute("SELECT 1")
        return JSONResponse({"status": "ok"})
    except Exception as exc:
        logger.error("Health check failed: %s", exc, exc_info=True)
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=503)


@mcp.custom_route("/metrics", methods=["GET"])
async def metrics(request: Request):
    lines = []
    for tool, count in REQUEST_COUNT.items():
        lines.append(f'mcp_requests_total{{tool="{tool}"}} {count}')
        durations = REQUEST_DURATION.get(tool, [])
        if durations:
            lines.append(f'mcp_request_duration_seconds_sum{{tool="{tool}"}} {sum(durations):.6f}')
            lines.append(f'mcp_request_duration_seconds_count{{tool="{tool}"}} {len(durations)}')
    body = "\n".join(lines) if lines else "# no metrics yet"
    return JSONResponse({"metrics": body})


# ── Main ──────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MY-DOGE MCP Server")
    parser.add_argument(
        "--transport", choices=["stdio", "sse"], default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="SSE bind host")
    parser.add_argument("--port", type=int, default=8902, help="SSE bind port")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(level)

    if args.transport == "stdio":
        logger.info("Starting stdio transport")

        # ── Windows stdout 双重 TextIOWrapper 修复 ──
        # SDK 内部做 TextIOWrapper(sys.stdout.buffer, encoding="utf-8")，
        # 与 Python 原始 sys.stdout 共享同一个 BufferedWriter。
        # 在 Windows 上两个 TextIOWrapper 同时 flush 同一个 buffer → OSError。
        # 解决方案：接管 buffer，让 sys.stdout 指向 dummy，传自定义 stdout 给 SDK。
        import io as _io
        import anyio
        from mcp.server.stdio import stdio_server

        _stdout_buf = sys.stdout.buffer
        sys.stdout = _io.StringIO()

        async def _run():
            cl_stdout = anyio.wrap_file(_io.TextIOWrapper(_stdout_buf, encoding="utf-8"))
            async with stdio_server(stdout=cl_stdout) as (read_stream, write_stream):
                await mcp._mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp._mcp_server.create_initialization_options(),
                )

        anyio.run(_run)
    else:
        logger.info("Starting SSE transport on %s:%d", args.host, args.port)
        import uvicorn
        uvicorn.run(mcp.sse_app(), host=args.host, port=args.port)
