"""Canonical modular MCP server — all tools delegate to doge.core.services.

The legacy root monolith was retired; doge_mcp.py is the canonical entrypoint.
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
import re
import subprocess as _sp
import sys
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

import anyio

from doge.bootstrap import build_app_container
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
LOG_DIR.mkdir(parents=True, exist_ok=True)

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

# Bound the PID history so startup/heartbeat work stays predictable even when
# previous server processes did not shut down cleanly.
_PID_HISTORY_LIMIT = 20


def _register_pid():
    """Append current PID to PID file, keeping only recent history."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    pids = []
    if PID_FILE.exists():
        pids = [line.strip() for line in PID_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    pids.append(str(os.getpid()))
    # Keep the file bounded so async startup never scans an unbounded list.
    pids = pids[-_PID_HISTORY_LIMIT:]
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
            PID_FILE.write_text("\n".join(pids[-_PID_HISTORY_LIMIT:]) + "\n", encoding="utf-8")
        else:
            PID_FILE.unlink(missing_ok=True)
    except (OSError, ValueError) as exc:
        # Fail-open: the reader tolerates a stale/malformed PID file, so a write
        # failure here only risks a false-positive orphan warning later. Log at
        # DEBUG (do not swallow KeyboardInterrupt/SystemExit — no bare except).
        logger.debug("PID unregister failed: %s", exc, exc_info=True)


async def _detect_orphan_processes():
    """Log warning if orphaned MCP server processes are detected.

    The underlying PowerShell CIM / ``/proc`` lookups are synchronous and can
    block the event loop when the PID file is large. Running them in a worker
    thread prevents an accumulated stale PID file from stalling the SSE handshake.
    """
    if not PID_FILE.exists():
        return
    await anyio.to_thread.run_sync(_sync_detect_orphan_processes)


def _sync_detect_orphan_processes():
    """Synchronous orphan detection (executed in a worker thread)."""
    # Match the canonical repo-root entrypoint for this server.
    _markers = ("doge_mcp.py",)
    try:
        pids = [p.strip() for p in PID_FILE.read_text(encoding="utf-8").splitlines() if p.strip()]
        # Cap scanning to the most recent entries; _register_pid bounds the file,
        # but this is a second line of defense against external corruption.
        pids = pids[-_PID_HISTORY_LIMIT:]
        alive = []
        for pid_str in pids:
            try:
                pid = int(pid_str)
            except ValueError:
                continue
            if pid == os.getpid():
                continue
            if _IS_WINDOWS:
                # wmic is deprecated on Windows 11 / Server 2025. Use PowerShell
                # CIM which is the supported replacement and avoids the WMIC binary.
                r = _sp.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"Get-CimInstance Win32_Process -Filter 'ProcessId={pid}' | "
                        f"Select-Object CommandLine | Format-List",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
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


# ── Client-safe error formatting ─────────────────────
# Internal paths and credential fragments can leak into exception messages.
# Sanitize before returning anything to an MCP client (stdio or SSE).
_PATH_RE = re.compile(r"[A-Za-z]:\\[^ ]+|/(?:home|Users|tmp|var|opt|etc|root|srv)[^ ]*", re.IGNORECASE)
_CRED_RE = re.compile(r"(key|token|secret|password|api_key)\s*[=:]\s*['\"]?[^&\s'\"]+", re.IGNORECASE)


def _sanitize_error(exc: BaseException) -> str:
    """Return a client-safe error string with internal paths/credentials redacted."""
    msg = str(exc)
    msg = _PATH_RE.sub("<path>", msg)
    msg = _CRED_RE.sub(r"\1=<redacted>", msg)
    return f"Error: {type(exc).__name__}: {msg}"


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
                return _sanitize_error(exc)
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


def _json_result(payload: Any) -> str:
    return json.dumps(_serialize(payload), ensure_ascii=False, indent=2)


def _serialize(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {key: _serialize(value) for key, value in asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _serialize(value) for key, value in obj.items()}
    return obj


def _workspace_container():
    return build_app_container().workspace


def _case_execution_request(
    template_id: str,
    *,
    question: str | None = None,
    workflow: str | None = None,
    session_id: str | None = None,
    market: str = "us",
    language: str = "en",
    document_ids: list[str] | None = None,
    portfolio_id: str | None = None,
    inputs: dict[str, Any] | None = None,
    model_policy: dict[str, Any] | None = None,
    skip_preflight: bool = False,
    trigger_channel: str = "mcp",
):
    from doge.platform.workspace import CaseExecutionCreate

    return CaseExecutionCreate(
        template_id=template_id,
        question=question,
        workflow=workflow,
        session_id=session_id,
        market=_validate_market(market),
        language=language,
        document_ids=document_ids or [],
        portfolio_id=portfolio_id,
        inputs=inputs or {},
        model_policy=model_policy or {},
        skip_preflight=skip_preflight,
        trigger_channel=trigger_channel,
    )


# ── Server factory ───────────────────────────────────
def create_mcp_server():
    """Create and configure the MCP server with all tools wired through services."""
    from mcp.server.fastmcp import FastMCP

    @asynccontextmanager
    async def _lifespan(app: FastMCP):
        logger.info("=== SERVER START ===")
        _register_pid()
        await _detect_orphan_processes()
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

    @mcp.tool(name="seed_workflow_templates")
    @_timed("seed_workflow_templates")
    async def tool_seed_workflow_templates(dry_run: bool = False) -> str:
        """写入内置金融 Workflow Template，供 Case 工作流复用。"""
        from doge.platform.workspace import seed_workflow_templates

        result = seed_workflow_templates(_workspace_container().build_platform_repository(), dry_run=dry_run)
        return _json_result(result.to_dict())

    @mcp.tool(name="list_workflow_templates")
    @_timed("list_workflow_templates")
    async def tool_list_workflow_templates(limit: int = 100) -> str:
        """列出可执行的 Workflow Template。"""
        from doge.platform.workspace import PlatformRequestContext

        n = _validate_int("limit", limit, 1, 500)
        service = _workspace_container().build_workflow_service()
        templates = service.list(PlatformRequestContext(), limit=n)
        return _json_result({"workflow_templates": templates})

    @mcp.tool(name="show_workflow_template")
    @_timed("show_workflow_template")
    async def tool_show_workflow_template(template_id: str) -> str:
        """查看指定 Workflow Template 的输入、策略和输出契约。"""
        from doge.platform.workspace import PlatformRequestContext

        service = _workspace_container().build_workflow_service()
        template = service.get(PlatformRequestContext(), template_id)
        return _json_result(template)

    @mcp.tool(name="list_research_cases")
    @_timed("list_research_cases")
    async def tool_list_research_cases(project_id: str | None = None, limit: int = 20) -> str:
        """列出 Research Case，作为模板执行入口。"""
        from doge.platform.workspace import PlatformRequestContext

        n = _validate_int("limit", limit, 1, 500)
        service = _workspace_container().build_research_case_service()
        cases = service.list(PlatformRequestContext(), project_id=project_id, limit=n)
        return _json_result({"research_cases": cases})

    @mcp.tool(name="preflight_case_execution")
    @_timed("preflight_case_execution")
    async def tool_preflight_case_execution(
        case_id: str,
        template_id: str,
        inputs: dict[str, Any] | None = None,
        market: str = "us",
        language: str = "en",
    ) -> str:
        """在 Research Case 中预检模板执行所需输入、能力和资产。"""
        from doge.platform.workspace import PlatformRequestContext

        service = _workspace_container().build_research_case_service()
        preflight = service.preflight_template_execution(
            PlatformRequestContext(),
            case_id,
            _case_execution_request(template_id, inputs=inputs, market=market, language=language),
            workflow_templates_enabled=True,
        )
        return _json_result(preflight.to_dict())

    @mcp.tool(name="execute_case_template")
    @_timed("execute_case_template")
    async def tool_execute_case_template(
        case_id: str,
        template_id: str,
        inputs: dict[str, Any] | None = None,
        question: str | None = None,
        market: str = "us",
        language: str = "en",
        skip_preflight: bool = False,
    ) -> str:
        """在 Research Case 中执行 Workflow Template 并返回 execution/run 信息。"""
        from doge.platform.workspace import PlatformRequestContext

        service = _workspace_container().build_research_case_service()
        result = await service.execute_template(
            PlatformRequestContext(),
            case_id,
            _case_execution_request(
                template_id,
                question=question,
                inputs=inputs,
                market=market,
                language=language,
                skip_preflight=skip_preflight,
            ),
            workflow_templates_enabled=True,
        )
        return _json_result(result.to_dict())

    @mcp.tool(name="record_case_decision")
    @_timed("record_case_decision")
    async def tool_record_case_decision(
        case_id: str,
        decision_type: str,
        rationale: str = "",
        source_run_ids: list[str] | None = None,
        source_execution_ids: list[str] | None = None,
    ) -> str:
        """记录 Research Case 的审批、驳回、暂缓或升级决策。"""
        from doge.platform.workspace import CaseDecisionCreate, PlatformRequestContext

        service = _workspace_container().build_research_case_service()
        decision = service.record_decision(
            PlatformRequestContext(),
            case_id,
            CaseDecisionCreate(
                decision_type=decision_type,
                rationale=rationale,
                source_run_ids=source_run_ids or [],
                source_execution_ids=source_execution_ids or [],
            ),
        )
        return _json_result(decision)

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
            if "database does not exist" in str(exc).lower():
                return JSONResponse({"status": "ok", "detail": "duckdb missing"})
            logger.error("Health check failed: %s", exc, exc_info=True)
            return JSONResponse({"status": "error", "detail": _sanitize_error(exc)}, status_code=503)

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
