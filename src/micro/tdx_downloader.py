"""
通达信服务器数据下载器 — 支持两种模式:

  模式 1 — K 线 API (get_kline):  每只股票一次 API 调用, 返回 700 条结构化日线
  模式 2 — 原始 .day 文件 (download_day_file): 从服务器下载 32字节/条 的二进制日线,
           直接写入本地 vipdoc 目录或内存解析后写入 SQLite

Usage:
    python src/micro/tdx_downloader.py --market cn --method kline
    python src/micro/tdx_downloader.py --market cn --method raw --local-dir "D:/Games/New Tdx Vip2020/vipdoc"
"""

import os
import sys
import struct
import sqlite3
import time
import argparse
from datetime import datetime

import pandas as pd

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db_custom, save_stock_data_custom, get_tickers_sync_state
from opentdx.tdxClient import TdxClient
from opentdx.const import MARKET, EX_MARKET, PERIOD, ADJUST

# === 服务器列表 ===
def _load_servers_from_opentdx():
    """优先从 opentdx.const 加载服务器列表, 失败则回退到硬编码"""
    try:
        from opentdx.const import main_hosts, ex_hosts
        cn = [h[1] for h in main_hosts]
        us = [h[1] for h in ex_hosts]
        return cn, us
    except ImportError:
        pass
    return (
        ["180.153.18.170", "180.153.18.171", "60.191.117.167",
         "115.238.56.198", "218.75.126.9"],
        ["112.74.214.43", "120.25.218.6", "43.139.173.246",
         "159.75.90.107", "139.9.191.175"],
    )

CN_SERVERS, US_SERVERS = _load_servers_from_opentdx()


def find_working_server(servers, test_market, timeout=5):
    """自动选择可用服务器 (并发探测前 20 台, 取最快响应)"""
    import concurrent.futures

    def _test(host):
        try:
            client = TdxClient()
            port = 7709 if test_market == "cn" else 7727
            client.quotation_client.connect(host, port=port, time_out=timeout)
            client.quotation_client.login()
            if test_market == "us":
                client.ex_quotation_client.connect(host, port=7727, time_out=timeout)
                client.ex_quotation_client.login()
            return client, host
        except Exception:
            return None, None

    candidates = servers[:20]
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(candidates)))
    futures = {pool.submit(_test, h): h for h in candidates}
    try:
        for future in concurrent.futures.as_completed(futures, timeout=timeout + 2):
            client, host = future.result()
            if client:
                for f in futures:
                    f.cancel()
                print("  connected to {}".format(host))
                return client, host
    except concurrent.futures.TimeoutError:
        pass
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return None, None


# ---------------------------------------------------------------------------
#  增量下载辅助
# ---------------------------------------------------------------------------

def _get_latest_market_date(client, market="cn"):
    """通过查询一只活跃指数获取市场最新交易日"""
    try:
        if market == "cn":
            bars = client.stock_kline(MARKET.SH, "000001", PERIOD.DAILY, start=0, count=5)
        else:
            bars = client.goods_kline(EX_MARKET.US_STOCK, "AAPL", PERIOD.DAILY, start=0, count=5)
        if bars:
            dt_col = 'datetime' if 'datetime' in bars[0] else 'date_time'
            return pd.to_datetime([b[dt_col] for b in bars]).max().strftime('%Y-%m-%d')
    except Exception:
        pass
    return None


def _compute_fetch_params(ticker, sync_state, latest_market_date, buffer=10):
    """根据 DB 同步状态计算 TDX API 的 start / count。

    Returns:
        (start, count, reason)  若 count <= 0 表示无需下载
    """
    state = sync_state.get(ticker, {"latest_date": None, "row_count": 0})
    latest_date = state["latest_date"]
    row_count = state["row_count"]

    # 1. 首次下载 → 全量
    if not latest_date or row_count == 0:
        return 0, 800, "full"

    # 2. 已是最新 → 跳过
    if latest_date == latest_market_date:
        return 0, 0, "skip"

    # 3. 增量：按条数偏移，留 buffer 应对停牌
    start = max(0, row_count - buffer)
    # 最多请求 30 条（足够覆盖最近交易日 + buffer）
    count = min(800, 20 + buffer)
    if count <= 0:
        return 0, 0, "skip"
    return start, count, "incr"


def _ticker_to_market_code(ticker):
    """'000001.SZ' -> (MARKET.SZ, '000001')"""
    if '.' in ticker:
        code, suffix = ticker.split('.')
        if suffix.upper() == 'SH':
            return MARKET.SH, code
        elif suffix.upper() == 'SZ':
            return MARKET.SZ, code
        elif suffix.upper() == 'BJ':
            return MARKET.BJ, code
        else:
            return MARKET.SZ, code
    return None, ticker


def _bars_to_df(bars, ticker, max_rows=120):
    """将 get_kline 返回的 list[dict] 转为标准 DataFrame

    stock_kline (A 股) 返回的日期键名是 'datetime'
    goods_kline (美股) 返回的日期键名是 'date_time'
    """
    if not bars:
        return None
    df = pd.DataFrame(bars)
    # 兼容两种 API 的日期字段名
    dt_col = 'datetime' if 'datetime' in df.columns else 'date_time'
    df['date'] = df[dt_col].dt.strftime('%Y-%m-%d')
    df = df.rename(columns={'vol': 'volume'})
    df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
    df['ticker'] = ticker
    df = df.sort_values('date')
    if len(df) > max_rows:
        df = df.tail(max_rows).reset_index(drop=True)
    return df


# ========================================================================
#  模式 1: K 线 API 下载 (get_kline)
# ========================================================================

def download_cn_kline(client, tickers, db_path, max_bars=120, progress_cb=None,
                      incremental=True):
    """A 股: stock_kline() 方式, 支持增量请求 + 断线自动重连"""
    init_db_custom(db_path)
    total = len(tickers)
    consecutive_failures = 0
    skipped = 0
    fetched = 0

    # 批量查询同步状态
    sync_state = get_tickers_sync_state(db_path, tickers) if incremental else {}
    latest_market_date = _get_latest_market_date(client, "cn") if incremental else None

    for i, ticker in enumerate(tickers):
        try:
            # 计算增量参数
            if incremental and latest_market_date:
                start, count, reason = _compute_fetch_params(
                    ticker, sync_state, latest_market_date)
                if count <= 0:
                    skipped += 1
                    if progress_cb and i % 200 == 0:
                        progress_cb(int((i + 1) / total * 100),
                                    "skip {}/{}".format(skipped, ticker))
                    continue
            else:
                start, count, reason = 0, 800, "full"

            mkt, code = _ticker_to_market_code(ticker)
            bars = client.stock_kline(mkt, code, PERIOD.DAILY,
                                      start=start, count=count)
            df = _bars_to_df(bars, ticker, max_bars)
            if df is not None:
                save_stock_data_custom(df, db_path)
                fetched += 1
            consecutive_failures = 0
        except Exception as e:
            consecutive_failures += 1
            if consecutive_failures >= 5:
                print("  {} consecutive failures, reconnecting...".format(
                    consecutive_failures))
                try:
                    client.quotation_client.disconnect()
                except Exception:
                    pass
                client, _ = find_working_server(CN_SERVERS, "cn")
                if client is None:
                    print("  reconnect failed, aborting")
                    return
                consecutive_failures = 0

        if progress_cb and i % 50 == 0:
            progress_cb(int((i + 1) / total * 100),
                        "kline: {} (skip {}, fetch {})".format(
                            ticker, skipped, fetched))
    if progress_cb:
        progress_cb(100, "kline complete (skipped {}, fetched {})".format(
            skipped, fetched))


def download_us_kline(client, tickers, db_path, max_bars=120, progress_cb=None,
                      incremental=True):
    """美股: goods_kline() 方式, 支持增量请求 + 断线自动重连"""
    init_db_custom(db_path)
    total = len(tickers)
    consecutive_failures = 0
    skipped = 0
    fetched = 0

    sync_state = get_tickers_sync_state(db_path, tickers) if incremental else {}
    latest_market_date = _get_latest_market_date(client, "us") if incremental else None

    for i, ticker in enumerate(tickers):
        try:
            if incremental and latest_market_date:
                start, count, reason = _compute_fetch_params(
                    ticker, sync_state, latest_market_date)
                if count <= 0:
                    skipped += 1
                    if progress_cb and i % 200 == 0:
                        progress_cb(int((i + 1) / total * 100),
                                    "skip {}/{}".format(skipped, ticker))
                    continue
            else:
                start, count, reason = 0, 800, "full"

            bars = client.goods_kline(EX_MARKET.US_STOCK, ticker,
                                      PERIOD.DAILY, start=start, count=count)
            df = _bars_to_df(bars, ticker, max_bars)
            if df is not None:
                save_stock_data_custom(df, db_path)
                fetched += 1
            consecutive_failures = 0
        except Exception as e:
            consecutive_failures += 1
            if consecutive_failures >= 5:
                print("  {} consecutive failures, reconnecting...".format(
                    consecutive_failures))
                try:
                    client.quotation_client.disconnect()
                    client.ex_quotation_client.disconnect()
                except Exception:
                    pass
                client, _ = find_working_server(US_SERVERS, "us")
                if client is None:
                    print("  reconnect failed, aborting")
                    return
                consecutive_failures = 0

        if progress_cb and i % 50 == 0:
            progress_cb(int((i + 1) / total * 100),
                        "kline: {} (skip {}, fetch {})".format(
                            ticker, skipped, fetched))
    if progress_cb:
        progress_cb(100, "kline complete (skipped {}, fetched {})".format(
            skipped, fetched))


# ========================================================================
#  模式 2: 原始 .day 文件下载 (32 字节二进制格式)
# ========================================================================

# TDX .day 二进制格式
# A 股: <IIIIIfII  (date, open, high, low, close, amount, volume, _) — 价格÷100
# 美股: <IfffffII  (date, open, high, low, close, amount, volume, _) — 价格直接浮点
DAY_FMT_CN = struct.Struct('<IIIIIfII')
DAY_FMT_US = struct.Struct('<IfffffII')
DAY_REC_SIZE = 32


def parse_day_records(raw_data, market="cn"):
    """解析 32 字节/条的 .day 二进制数据为 list[dict]"""
    if not raw_data or len(raw_data) < DAY_REC_SIZE:
        return []

    fmt = DAY_FMT_CN if market in ('cn', 'sh', 'sz') else DAY_FMT_US
    rec_count = len(raw_data) // DAY_REC_SIZE
    records = []

    for i in range(rec_count):
        offset = i * DAY_REC_SIZE
        fields = fmt.unpack(raw_data[offset:offset + DAY_REC_SIZE])
        date_int = fields[0]

        if date_int < 19900101 or date_int > 20991231:
            continue  # skip garbage

        y = date_int // 10000
        m = (date_int % 10000) // 100
        d = date_int % 100
        date_str = "{:04d}-{:02d}-{:02d}".format(y, m, d)

        if market in ('cn', 'sh', 'sz'):
            open_p, high_p, low_p, close_p = fields[1:5]
            open_p /= 100.0
            high_p /= 100.0
            low_p /= 100.0
            close_p /= 100.0
            amount = fields[5]
        else:
            open_p, high_p, low_p, close_p, amount = fields[1:6]

        records.append({
            'date': date_str,
            'open': round(open_p, 4),
            'high': round(high_p, 4),
            'low': round(low_p, 4),
            'close': round(close_p, 4),
            'volume': fields[6],
            'amount': amount,
        })

    return records


def _day_filename(ticker, market):
    """构造 TDX 服务器上的 .day 文件名

    A 股: sh600000.day 或 sz000001.day
    美股: ds/74#AAPL.day (扩展行情用 goods_kline)
    """
    if market in ('sh', 'sz'):
        mkt, code = _ticker_to_market_code(ticker)
        prefix = "sh" if mkt == MARKET.SH else "sz"
        return "{}{}.day".format(prefix, code)
    elif market == 'bj':
        mkt, code = _ticker_to_market_code(ticker)
        return "bj{}.day".format(code)
    return None


def download_day_file_raw(client, ticker, market="cn"):
    """[DEPRECATED] 从服务器下载一个标的的原始 .day 文件

    协议 0x6B9 (FileDownload) 在多数服务器返回空数据。
    推荐使用 kline 模式 (download_cn_kline / download_us_kline)。
    保留此函数仅用于兼容性, 未来可能移除。
    """
    if market == "us":
        # 美股通过扩展行情 goods_kline 获取, 不走 .day 文件
        bars = client.goods_kline(EX_MARKET.US_STOCK, ticker,
                                  PERIOD.DAILY, start=0, count=800)
        return [{'date': b['date_time'].strftime('%Y-%m-%d'),
                 'open': b['open'], 'high': b['high'], 'low': b['low'],
                 'close': b['close'], 'volume': b['vol'],
                 'amount': b['amount']} for b in bars] if bars else []

    # A 股: 确定市场和文件名
    if '.' in ticker:
        mkt_str = ticker.split('.')[1].lower()  # 'sh' or 'sz'
    else:
        mkt_str = market  # fallback

    fname = _day_filename(ticker, mkt_str)
    if not fname:
        return []

    # 使用协议 0x6b9 下载
    from opentdx.parser.quotation import FileDownload

    qc = client.quotation_client
    fd = FileDownload(file_name=fname, start=0, size=0x20000)

    try:
        qc._check_sp_mode()
        qc._send(fd.serialize())
        resp = qc._recv()
        result = fd.deserialize(resp['data'])
        raw = result.get('data', b'')
        if raw:
            return parse_day_records(raw, mkt_str)
    except Exception as e:
        pass

    return []


def download_cn_raw(client, tickers, db_path, local_dir=None,
                    max_bars=120, progress_cb=None):
    """A 股: 原始 .day 文件方式下载

    Args:
        local_dir: 如果指定, 同时将 .day 文件写入本目录 (用于本地备份)
    """
    init_db_custom(db_path)
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        try:
            records = download_day_file_raw(client, ticker, "cn")
            if records:
                df = pd.DataFrame(records)
                df['ticker'] = ticker
                if len(df) > max_bars:
                    df = df.sort_values('date').tail(max_bars).reset_index(drop=True)

                # 写入 SQLite
                save_stock_data_custom(df, db_path)

                # 同时写入本地 vipdoc (如果指定)
                if local_dir:
                    _write_local_day_file(local_dir, ticker, records)
        except Exception:
            pass

        if progress_cb and i % 50 == 0:
            progress_cb(int((i + 1) / total * 100), "raw: {}".format(ticker))
    if progress_cb:
        progress_cb(100, "raw complete")


def _write_local_day_file(root_dir, ticker, records, market="cn"):
    """将 records 写回本地 vipdoc 目录, 格式与通达信一致"""
    if '.' not in ticker:
        return

    code, suffix = ticker.split('.')
    s = suffix.lower()

    if s == 'sh':
        sub_dir = os.path.join(root_dir, 'sh', 'lday')
        fname = "sh{}.day".format(code)
        fmt = DAY_FMT_CN
        def pack(rec):
            return fmt.pack(
                int(rec['date'].replace('-', '')),
                int(rec['open'] * 100), int(rec['high'] * 100),
                int(rec['low'] * 100), int(rec['close'] * 100),
                rec['amount'], rec['volume'], 0)
    elif s == 'sz':
        sub_dir = os.path.join(root_dir, 'sz', 'lday')
        fname = "sz{}.day".format(code)
        fmt = DAY_FMT_CN
        def pack(rec):
            return fmt.pack(
                int(rec['date'].replace('-', '')),
                int(rec['open'] * 100), int(rec['high'] * 100),
                int(rec['low'] * 100), int(rec['close'] * 100),
                rec['amount'], rec['volume'], 0)
    else:
        return

    os.makedirs(sub_dir, exist_ok=True)
    filepath = os.path.join(sub_dir, fname)

    # 与通达信一致: 按日期倒序排列
    records_sorted = sorted(records, key=lambda r: r['date'], reverse=True)
    with open(filepath, 'wb') as f:
        for rec in records_sorted:
            f.write(pack(rec))


# ========================================================================
#  辅助
# ========================================================================

def get_known_tickers_from_db(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker")
    tickers = [r[0] for r in cur.fetchall()]
    conn.close()
    return tickers


def get_known_tickers_from_csv(market="cn"):
    csv_path = os.path.join(_PROJECT_ROOT, "data", "stock_names_cn.csv")
    if not os.path.exists(csv_path):
        return []
    df = pd.read_csv(csv_path, dtype=str)
    tickers = df['ticker'].tolist()
    if market == "cn":
        tickers = [t for t in tickers if '.' in t and len(t.split('.')[0]) == 6]
    return tickers


def _refresh_views():
    try:
        from src.ai_analysis import connect_duckdb, run_views_sql
        con = connect_duckdb()
        run_views_sql(con)
        con.close()
        print("DuckDB views refreshed")
    except Exception:
        pass


# ========================================================================
#  CLI
# ========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TDX Server Data Downloader")
    parser.add_argument("--market", default="cn", choices=["cn", "us"])
    parser.add_argument("--method", default="kline", choices=["kline", "raw"],
                        help="kline=API, raw=.day file download")
    parser.add_argument("--db", default=None,
                        help="Target SQLite DB (default: data/market_data_{cn|us}.db)")
    parser.add_argument("--local-dir", default=None,
                        help="vipdoc root for saving .day files (raw mode only)")
    parser.add_argument("--from-csv", action="store_true")
    parser.add_argument("--server", default=None)
    parser.add_argument("--only", default=None,
                        help="Comma-separated tickers")
    parser.add_argument("--max-bars", type=int, default=120,
                        help="Max records per ticker (default: 120)")
    parser.add_argument("--no-incremental", action="store_true",
                        help="Disable incremental download, fetch full history every time")

    args = parser.parse_args()

    if args.db is None:
        db_name = "market_data_{}.db".format(args.market)
        args.db = os.path.join(_PROJECT_ROOT, "data", db_name)

    if args.only:
        tickers = [t.strip() for t in args.only.split(",")]
    elif args.from_csv:
        tickers = get_known_tickers_from_csv(args.market)
    else:
        tickers = get_known_tickers_from_db(args.db)
        if not tickers and args.market == "cn":
            tickers = get_known_tickers_from_csv("cn")

    if not tickers:
        print("No tickers found. Use --from-csv or --only")
        sys.exit(1)

    incremental = not args.no_incremental
    print("Market: {} | Method: {} | Tickers: {} | DB: {} | Incremental: {}".format(
        args.market, args.method, len(tickers), args.db, incremental))

    servers = CN_SERVERS if args.market == "cn" else US_SERVERS
    if args.server:
        servers = [args.server]

    client, host = find_working_server(servers, args.market)
    if not client or not host:
        print("No server available")
        sys.exit(1)

    start_time = time.time()

    if args.method == "kline":
        if args.market == "cn":
            download_cn_kline(client, tickers, args.db, args.max_bars,
                              incremental=incremental)
        else:
            download_us_kline(client, tickers, args.db, args.max_bars,
                              incremental=incremental)
    else:  # raw
        if args.market == "us":
            # 美股 .day 文件也走 goods_kline
            download_us_kline(client, tickers, args.db, args.max_bars,
                              incremental=incremental)
        else:
            download_cn_raw(client, tickers, args.db, args.local_dir,
                            args.max_bars)

    client.quotation_client.disconnect()
    if args.market == "us":
        try:
            client.ex_quotation_client.disconnect()
        except Exception:
            pass

    _refresh_views()
    elapsed = time.time() - start_time
    print("Done in {:.1f}s".format(elapsed))
