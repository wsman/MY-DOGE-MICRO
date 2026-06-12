"""Modular MCP server — all tools delegate to doge.core.services.

This is a drop-in replacement for the monolithic mcp_server.py.
It wires tools through the service layer, not direct DB access.
"""

import argparse
import contextvars
import functools
import json
import logging
import logging.handlers
import os
import platform as _platform
import subprocess as _sp
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List

import anyio

from doge.config import get_settings
from doge.interfaces.mcp.tools import (
    query_stock,
    stock_overview,
    rsrs_ranking,
    market_breadth,
    volume_anomalies,
    list_views,
)

# ── Logging ───────────────────────────────────────────
LOG_DIR = Path(get_settings().data_dir) / "logs"
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
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        root.addHandler(fh)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(ch)


_setup_logging()
logger = logging.getLogger("doge-mcp")

# ── Metrics ──────────────────────────────────────────
REQUEST_COUNT: Dict[str, int] = {}
REQUEST_DURATION: Dict[str, List[float]] = {}

TOOL_TIMEOUT = 30

# ── PID file for orphan detection (read-only, no killing) ──
# Migrated from the legacy monolith: stdio servers launched by .mcp.json can
# stack up if a previous process did not shut down cleanly. We log a warning
# when concurrent live servers are detected (DuckDB read-only mode tolerates
# concurrent access, so this is advisory only — no killing).
PID_FILE = Path(get_settings().data_dir) / ".mcp_server.pid"
_IS_WINDOWS = _platform.system() == "Windows"


def _register_pid():
    """Append current PID to PID file. Each line: PID."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if PID_FILE.exists():
        existing = PID_FILE.read_text(encoding="utf-8")
    pids = [line.strip() for line in existing.splitlines() if line.strip()]
    pids.append(str(os.getpid()))
    PID_FILE.write_text("\n".join(pids) + "\n", encoding="utf-8")


def _unregister_pid():
    """Remove current PID from PID file."""
    if not PID_FILE.exists():
        return
    my_pid = str(os.getpid())
    try:
        pids = PID_FILE.read_text(encoding="utf-8").splitlines()
        pids = [p for p in pids if p.strip() != my_pid]
        if pids:
            PID_FILE.write_text("\n".join(pids) + "\n", encoding="utf-8")
        else:
            PID_FILE.unlink(missing_ok=True)
    except (OSError, ValueError) as exc:
        # Fail-open: the reader tolerates a stale/malformed PID file, so a write
        # failure here only risks a false-positive orphan warning later. Log at
        # DEBUG (do not swallow KeyboardInterrupt/SystemExit — no bare except).
        logger.debug("PID unregister failed: %s", exc, exc_info=True)


def _detect_orphan_processes():
    """Log warning if orphaned MCP server processes are detected."""
    if not PID_FILE.exists():
        return
    # Match the entrypoint this server runs as. Both legacy mcp_server.py and
    # the modular doge_mcp.py serve the same role, so flag either.
    _markers = ("mcp_server.py", "doge_mcp.py")
    try:
        pids = [p.strip() for p in PID_FILE.read_text(encoding="utf-8").splitlines() if p.strip()]
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
                if any(m in r.stdout for m in _markers):
                    alive.append(pid)
            else:
                try:
                    cmdline = Path(f"/proc/{pid}/cmdline").read_text("\x00")
                    if any(m in cmdline for m in _markers):
                        alive.append(pid)
                except FileNotFoundError:
                    pass
        if alive:
            logger.warning(
                "Detected %d concurrent MCP server process(es): %s. "
                "DuckDB read-only mode supports concurrent access.",
                len(alive), alive,
            )
    except Exception as exc:
        logger.debug("Orphan detection failed: %s", exc)


def _timed(tool_name: str):
    """Decorator: log entry/exit, set correlation_id, record metrics, enforce timeout."""
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
                logger.info("TOOL CALL: %s ok duration=%.3fs", tool_name, dur)
                return result
            except asyncio.TimeoutError:
                dur = time.time() - t0
                logger.error("TOOL CALL: %s TIMEOUT after %.1fs", tool_name, dur)
                return f"Error: {tool_name} timed out after {TOOL_TIMEOUT}s"
            except Exception as exc:
                dur = time.time() - t0
                logger.error("TOOL CALL: %s ERROR: %s: %s", tool_name, type(exc).__name__, exc, exc_info=True)
                return f"Error: {type(exc).__name__}: {exc}"
        return wrapper
    return decorator


# ── Validation ───────────────────────────────────────
_MARKET_WHITELIST = {"cn", "us"}


def _validate_market(market: str) -> str:
    m = (market or "cn").lower()
    if m not in _MARKET_WHITELIST:
        raise ValueError(f"Invalid market: {market}. Must be one of {_MARKET_WHITELIST}.")
    return m


def _validate_ticker(ticker: str) -> str:
    from doge.interfaces.mcp.tools.query_stock import normalize_ticker
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


# ── Formatting helper ────────────────────────────────
# Exposed at module level for parity with the legacy monolith (tests import it).
# The per-tool modules keep their own copies; this is the canonical shared one.
def _fmt(columns: List[str], rows: List[Any]) -> str:
    """Render a column-aligned text table. Empty rows -> empty string."""
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


# ── Server factory ───────────────────────────────────
def create_mcp_server():
    """Create and configure the MCP server with all tools wired through services."""
    from mcp.server.fastmcp import FastMCP

    @asynccontextmanager
    async def _lifespan(app: FastMCP):
        logger.info("=== SERVER START ===")
        _register_pid()
        _detect_orphan_processes()
        try:
            from doge.infrastructure.database.duckdb import DuckDBConnection
            with DuckDBConnection(read_only=True).connect() as con:
                con.execute("SELECT 1")
            logger.info("DuckDB pre-warm OK")
        except Exception as exc:
            logger.error("DuckDB pre-warm failed: %s", exc, exc_info=True)
        try:
            yield
        finally:
            _unregister_pid()
            logger.info("=== SERVER SHUTDOWN ===")

    mcp = FastMCP("doge-db", lifespan=_lifespan)

    @mcp.tool(name="query_stock")
    @_timed("query_stock")
    async def tool_query_stock(ticker: str, market: str = "cn", days: int = 20) -> str:
        """查询个股行情数据（OHLCV、均线、ATR、波动率等技术指标）。"""
        m = _validate_market(market)
        t = _validate_ticker(ticker)
        d = _validate_int("days", days, 1, 500)
        return await query_stock(t, m, d)

    @mcp.tool(name="stock_overview")
    @_timed("stock_overview")
    async def tool_stock_overview(ticker: str, market: str = "cn") -> str:
        """个股概览：名称、板块、最新价格、笔记。"""
        m = _validate_market(market)
        t = _validate_ticker(ticker)
        return await stock_overview(t, m)

    @mcp.tool(name="rsrs_ranking")
    @_timed("rsrs_ranking")
    async def tool_rsrs_ranking(market: str = "cn", top: int = 20) -> str:
        """RSRS 动量排名（最强趋势股票排行）。"""
        m = _validate_market(market)
        n = _validate_int("top", top, 1, 100)
        return await rsrs_ranking(m, n)

    @mcp.tool(name="market_breadth")
    @_timed("market_breadth")
    async def tool_market_breadth(market: str = "cn", days: int = 10) -> str:
        """市场宽度（每日涨跌家数、上涨占比、平均涨跌幅）。"""
        m = _validate_market(market)
        d = _validate_int("days", days, 1, 100)
        return await market_breadth(m, d)

    @mcp.tool(name="volume_anomalies")
    @_timed("volume_anomalies")
    async def tool_volume_anomalies(min_ratio: float = 3.0, top: int = 20) -> str:
        """成交量异常股票（量比排名，发现放量异动）。"""
        ratio = _validate_float("min_ratio", min_ratio, 1.0, 1000.0)
        n = _validate_int("top", top, 1, 100)
        return await volume_anomalies(ratio, n)

    @mcp.tool(name="list_views")
    @_timed("list_views")
    async def tool_list_views() -> str:
        """列出 DuckDB 中所有视图及其行数、列名。"""
        return await list_views()

    # Health & metrics routes (SSE only)
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request):
        try:
            from doge.infrastructure.database.duckdb import DuckDBConnection
            with DuckDBConnection(read_only=True).connect() as con:
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

    return mcp


# ── Entry point ──────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="MY-DOGE MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8902)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(level)

    mcp = create_mcp_server()

    if args.transport == "stdio":
        logger.info("Starting stdio transport")
        import io as _io
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


if __name__ == "__main__":
    main()
