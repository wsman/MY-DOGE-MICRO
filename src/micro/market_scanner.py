import os
import sys
import sqlite3
import glob
import re
import pandas as pd

# 路径自适应
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from tdx_loader import TDXReader
from database import init_db_custom, save_stock_data_custom
from tdx_downloader import (
    download_cn_kline as _tdx_download_cn,
    download_us_kline as _tdx_download_us,
    find_working_server,
    CN_SERVERS,
    US_SERVERS,
)

# 项目根目录下的 ai_analysis 包
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _refresh_duckdb_views():
    """数据导入后刷新 DuckDB 分析视图"""
    try:
        from src.ai_analysis import connect_duckdb, run_views_sql
        con = connect_duckdb()
        run_views_sql(con)
        con.close()
        print("[OK] DuckDB analysis views refreshed")
    except Exception as e:
        print("[WARN] DuckDB views refresh failed (non-fatal): {}".format(e))


def _tdx_server_sync(db_path, market="cn", tickers=None, progress_callback=None):
    """从 TDX 服务器下载最新数据, 自动回退到本地文件扫描"""
    try:
        from opentdx.tdxClient import TdxClient
        servers = CN_SERVERS if market == "cn" else US_SERVERS
        client, host = find_working_server(servers, market)

        if client and host:
            print("  using TDX server: {}".format(host))
            if market == "cn":
                _tdx_download_cn(client, tickers, db_path,
                                 progress_cb=progress_callback)
            else:
                _tdx_download_us(client, tickers, db_path,
                                 progress_cb=progress_callback)

            client.quotation_client.disconnect()
            if market == "us":
                try:
                    client.ex_quotation_client.disconnect()
                except Exception:
                    pass
            return True
    except ImportError:
        print("  opentdx not available, falling back to local files")
    except Exception as e:
        print("  TDX server sync failed: {}, falling back to local files".format(e))
    return False


class MarketScanner:
    def __init__(self, tdx_root):
        # 智能修正路径：如果目录下没有 vipdoc 但有 vipdoc 子目录，则追加
        if not os.path.basename(tdx_root) == 'vipdoc':
            potential_vipdoc = os.path.join(tdx_root, 'vipdoc')
            if os.path.exists(potential_vipdoc):
                tdx_root = potential_vipdoc
                print(f"[OK] auto-corrected TDX path: {tdx_root}")

        self.tdx_root = tdx_root
        self.reader = TDXReader(tdx_root)

    def scan_cn_market(self, db_path, progress_callback=None, use_server=True):
        """扫描 A 股 (sh/sz)

        Args:
            db_path: SQLite 数据库路径
            progress_callback: 进度回调 (percent, message)
            use_server: 是否优先从 TDX 服务器下载 (True=服务器优先, False=仅本地)
        """
        print(f"[SCAN] A-share scan -> {db_path}")
        init_db_custom(db_path) # 1. 初始化库

        tasks = []
        # 遍历 sh 和 sz 目录
        for market in ['sh', 'sz']:
            lday_dir = os.path.join(self.tdx_root, market, 'lday')
            if not os.path.exists(lday_dir):
                continue

            files = glob.glob(os.path.join(lday_dir, f'{market}*.day'))
            for f in files:
                fname = os.path.basename(f)
                code = fname[2:-4] # 去除前缀后缀
                # 核心修正：严格白名单过滤 (00: 深市主板, 30: 创业板, 60: 沪市主板, 68: 科创板)
                if code.startswith(('00', '30', '60', '68')) and len(code) == 6:
                    # 构造 ticker 格式：000001.SZ 或 600000.SH
                    ticker = f"{code}.{market.upper()}"
                    tasks.append(ticker)

        total = len(tasks)
        print(f"[INFO] filtered to {total} A-share stocks")

        # 0. 优先从 TDX 服务器同步最新数据
        if use_server:
            print("  attempting TDX server sync...")
            server_ok = _tdx_server_sync(db_path, "cn", tasks, progress_callback)
            if server_ok:
                if progress_callback:
                    progress_callback(100, "CN server sync complete")
                _refresh_duckdb_views()
                return

        # 批量处理 (本地文件回退)
        for i, ticker in enumerate(tasks):
            try:
                # 2. 读取数据
                df = self.reader.get_data(ticker, market_type='cn')
                
                # 3. 写入数据库 (关键逻辑)
                if not df.empty:
                    # 增加 ticker 列
                    df['ticker'] = ticker
                    save_stock_data_custom(df, db_path)
            except Exception as e:
                # 容错处理
                print(f"Error reading {ticker}: {e}")
                pass
            
            # 4. 更新进度条 (每100个或是1%更新一次，避免UI卡顿)
            if progress_callback and i % 50 == 0:
                progress_callback(int((i + 1) / total * 100), f"正在入库: {ticker}")
        
        if progress_callback:
            progress_callback(100, "CN local import complete")

        # 刷新 DuckDB 分析视图
        _refresh_duckdb_views()

    def scan_us_market(self, db_path, progress_callback=None, use_server=True):
        """扫描美股 (ds)

        Args:
            db_path: SQLite 数据库路径
            progress_callback: 进度回调
            use_server: 是否优先从 TDX 服务器下载
        """
        print(f"[SCAN] US market scan -> {db_path}")
        init_db_custom(db_path) # 1. 初始化库
        
        ds_dir = os.path.join(self.tdx_root, 'ds', 'lday')
        tasks = []
        
        if os.path.exists(ds_dir):
            files = glob.glob(os.path.join(ds_dir, '*.day'))
            for f in files:
                fname = os.path.basename(f)
                # 处理文件名如 74#AAPL.day
                raw_code = fname.replace('.day', '')
                if '#' in raw_code:
                    raw_code = raw_code.split('#')[-1]
                
                # 过滤：纯字母代码，排除 HK, 数字等
                if re.match(r'^[A-Z]+$', raw_code) and 'HK' not in raw_code:
                    tasks.append(raw_code)
        
        total = len(tasks)
        print(f"[INFO] found {total} US stocks, importing...")

        # 0. 优先从 TDX 扩展行情服务器同步
        if use_server:
            print("  attempting TDX server sync...")
            server_ok = _tdx_server_sync(db_path, "us", tasks, progress_callback)
            if server_ok:
                if progress_callback:
                    progress_callback(100, "US server sync complete")
                _refresh_duckdb_views()
                return

        for i, ticker in enumerate(tasks):
            try:
                # 2. 读取数据
                df = self.reader.get_data(ticker, market_type='us')
                
                # 3. 写入数据库 (关键逻辑)
                if not df.empty:
                    # 增加 ticker 列
                    df['ticker'] = ticker
                    save_stock_data_custom(df, db_path)
            except Exception as e:
                print(f"Error reading {ticker}: {e}")
                pass
            
            # 4. 更新进度条 (每100个或是1%更新一次，避免UI卡顿)
            if progress_callback and i % 50 == 0:
                progress_callback(int((i + 1) / total * 100), f"正在入库: {ticker}")
        
        if progress_callback:
            progress_callback(100, "US local import complete")

        # 刷新 DuckDB 分析视图
        _refresh_duckdb_views()
