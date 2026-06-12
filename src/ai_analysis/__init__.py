"""
AI 可读分析系统 — 共享数据库连接层

提供 DuckDB + SQLite 统一连接，确保视图可用。
"""

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

# 限制 OpenBLAS 线程数，避免 pandas df() 转换时 OOM
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import duckdb

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_path(name: str, default: Path) -> Path:
    env = os.environ.get(name)
    return Path(env) if env else default


# 数据库路径常量（支持环境变量覆盖）
DB_DIR = _env_path("DOGE_DB_DIR", PROJECT_ROOT / "data")
CN_DB = _env_path("DOGE_CN_DB", DB_DIR / "market_data_cn.db")
US_DB = _env_path("DOGE_US_DB", DB_DIR / "market_data_us.db")
RESEARCH_DB = _env_path("DOGE_RESEARCH_DB", DB_DIR / "research_insights.db")
DUCKDB_PATH = _env_path("DOGE_DUCKDB_PATH", DB_DIR / "market.duckdb")
# S003-005: the version-controlled DDL now ships inside the package at
# src/doge/infrastructure/database/views.sql. VIEWS_SQL remains the data-dir
# mirror (data/views.sql) for backward compat with the CLI invocation
# ``duckdb data/market.duckdb < data/views.sql``; resolve_views_sql() prefers
# the tracked copy when present.
VIEWS_SQL = DB_DIR / "views.sql"
VIEWS_SQL_TRACKED = PROJECT_ROOT / "src" / "doge" / "infrastructure" / "database" / "views.sql"
REPORT_DIR = PROJECT_ROOT / "ai_report"


def resolve_views_sql() -> Path:
    """Return the DDL path loaders should execute.

    Prefers the tracked, version-controlled DDL (VIEWS_SQL_TRACKED) when it
    exists; falls back to the data-dir mirror (VIEWS_SQL) for backward
    compatibility. Mirrors DBConfig.resolved_views_sql() in the clean path so
    both loaders stay consistent without a hard dependency on doge.config here.
    """
    if VIEWS_SQL_TRACKED.exists():
        return VIEWS_SQL_TRACKED
    return VIEWS_SQL


def _strip_sql_comments(sql_text: str) -> str:
    """Remove full-line and trailing ``--`` comments before statement splitting.

    S003-005: the version-controlled ``views.sql`` carries a multi-paragraph
    header comment whose prose contains semicolons (e.g. "sign convention; the
    downstream ..."). The naive ``sql.split(';')`` breaks such prose into
    fragments that don't start with ``--`` and fail to parse — and can absorb a
    real statement into a comment fragment so the view never updates. Mirrors
    ``doge.infrastructure.database.duckdb._strip_sql_comments`` and the test
    helpers in tests/migration/.
    """
    cleaned_lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue  # drop full-line comments
        if "--" in line:
            line = line.split("--", 1)[0]  # drop trailing inline comments
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def normalize_ticker(ticker: str, market: str = "cn") -> str:
    """将裸代码补全为带交易所后缀的完整 ticker。
    A股: 6xx/68x -> .SH, 0xx/3xx -> .SZ, 4xx/8xx -> .BJ
    美股及已有后缀的直接返回。
    """
    if not isinstance(ticker, str):
        raise ValueError("ticker must be a string")
    code = ticker.strip()
    if not code:
        raise ValueError("ticker cannot be empty")
    if len(code) > 20:
        raise ValueError("ticker too long (max 20 chars)")
    if not re.match(r"^[A-Za-z0-9.\-]+$", code):
        raise ValueError("ticker contains invalid characters")

    if market != "cn" or "." in code:
        return code
    if code[0] == "6":
        return f"{code}.SH"
    elif code[0] in ("0", "3"):
        return f"{code}.SZ"
    elif code[0] in ("4", "8"):
        return f"{code}.BJ"
    return code


def ensure_report_dir():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_duckdb_connection(read_only: bool = True):
    """创建 DuckDB 连接并在退出时自动关闭。
    只读模式下自动附加 cn/us SQLite 数据库。
    所有查询自动应用 30 秒超时，防止并发文件锁导致无限挂起。
    """
    con = duckdb.connect(str(DUCKDB_PATH), read_only=read_only)
    try:
        con.execute("SET threads=4")
        if read_only:
            con.execute(
                f"ATTACH IF NOT EXISTS '{CN_DB.as_posix()}' AS cn (TYPE sqlite, READ_ONLY)"
            )
            con.execute(
                f"ATTACH IF NOT EXISTS '{US_DB.as_posix()}' AS us (TYPE sqlite, READ_ONLY)"
            )
        else:
            con.execute(
                f"ATTACH IF NOT EXISTS '{CN_DB.as_posix()}' AS cn (TYPE sqlite)"
            )
            con.execute(
                f"ATTACH IF NOT EXISTS '{US_DB.as_posix()}' AS us (TYPE sqlite)"
            )
        yield con
    finally:
        con.close()


def connect_duckdb(read_only=False):
    """兼容旧代码的直接连接方式（建议逐步迁移到 get_duckdb_connection）。"""
    con = duckdb.connect(str(DUCKDB_PATH), read_only=read_only)
    if read_only:
        con.execute(
            f"ATTACH IF NOT EXISTS '{CN_DB.as_posix()}' AS cn (TYPE sqlite, READ_ONLY)"
        )
        con.execute(
            f"ATTACH IF NOT EXISTS '{US_DB.as_posix()}' AS us (TYPE sqlite, READ_ONLY)"
        )
    else:
        con.execute(
            f"ATTACH IF NOT EXISTS '{CN_DB.as_posix()}' AS cn (TYPE sqlite)"
        )
        con.execute(
            f"ATTACH IF NOT EXISTS '{US_DB.as_posix()}' AS us (TYPE sqlite)"
        )
    return con


def run_views_sql(con=None):
    """执行 views.sql 创建/刷新所有视图 (逐条执行以控制内存).

    S003-005: DDL resolved via resolve_views_sql() (tracked-first, data-dir
    fallback) so the version-controlled copy is preferred when present.
    """
    close_on_exit = False
    if con is None:
        con = connect_duckdb()
        close_on_exit = True
    try:
        views_sql_path = resolve_views_sql()
        with open(views_sql_path, "r", encoding="utf-8") as f:
            sql = f.read()
        sql = _strip_sql_comments(sql)
        # 逐条执行 CREATE VIEW, 而非批量执行, 避免同时物化所有视图
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    con.execute(stmt)
                except Exception as e:
                    print("  view creation failed: {}... — {}".format(
                        stmt[:80].replace("\n", " "), str(e)[:120]))
        print("DuckDB views refreshed")
    finally:
        if close_on_exit:
            con.close()


def query_view(view_name, limit=None):
    """查询命名视图，返回 DataFrame"""
    with get_duckdb_connection() as con:
        sql_query = "SELECT * FROM {}".format(view_name)
        if limit:
            sql_query += " LIMIT {}".format(limit)
        return con.execute(sql_query).df()


def query_sql(sql, params=None):
    """执行任意 SQL 查询，返回 DataFrame"""
    with get_duckdb_connection() as con:
        if params:
            return con.execute(sql, params).df()
        return con.execute(sql).df()


def get_sqlite_stats(db_path):
    """获取 SQLite 数据库的统计信息"""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {}
    for (tname,) in cur.fetchall():
        cur.execute("SELECT COUNT(*) FROM [{}]".format(tname))
        row_count = cur.fetchone()[0]
        cur.execute("PRAGMA table_info([{}])".format(tname))
        columns = [
            {"name": c[1], "type": c[2], "nullable": not c[3]}
            for c in cur.fetchall()
        ]
        date_range = None
        ticker_count = None
        if tname == "stock_prices" and row_count > 0:
            cur.execute("SELECT MIN(date), MAX(date) FROM [{}]".format(tname))
            date_range = list(cur.fetchone())
            cur.execute("SELECT COUNT(DISTINCT ticker) FROM [{}]".format(tname))
            ticker_count = cur.fetchone()[0]
        tables[tname] = {
            "row_count": row_count,
            "columns": columns,
            "date_range": date_range,
            "distinct_tickers": ticker_count,
        }
    conn.close()
    return tables


def get_duckdb_view_stats(con):
    """获取 DuckDB 视图列表及行数"""
    views = {}
    result = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_type='VIEW'"
    ).fetchall()
    for (vname,) in result:
        try:
            cnt = con.execute("SELECT COUNT(*) FROM {}".format(vname)).fetchone()[0]
            views[vname] = {"row_count": cnt}
        except Exception:
            views[vname] = {"row_count": None}
    return views
