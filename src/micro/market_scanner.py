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

class MarketScanner:
    def __init__(self, tdx_root):
        # 智能修正路径：如果目录下没有 vipdoc 但有 vipdoc 子目录，则追加
        if not os.path.basename(tdx_root) == 'vipdoc':
            potential_vipdoc = os.path.join(tdx_root, 'vipdoc')
            if os.path.exists(potential_vipdoc):
                tdx_root = potential_vipdoc
                print(f"✅ 自动修正通达信路径为: {tdx_root}")
        
        self.tdx_root = tdx_root
        self.reader = TDXReader(tdx_root)

    def scan_cn_market(self, db_path, progress_callback=None):
        """扫描 A 股 (sh/sz)"""
        print(f"🚀 启动 A股扫描 -> {db_path}")
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
        print(f"📊 经严格过滤，锁定 {total} 只 A 股正股标的")
        
        # 批量处理
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
            progress_callback(100, "✅ A股入库完成")

    def scan_us_market(self, db_path, progress_callback=None):
        """扫描美股 (ds)"""
        print(f"🚀 启动 美股扫描 -> {db_path}")
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
        print(f"📊 发现 {total} 只 美股标的，开始入库...")
        
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
            progress_callback(100, "✅ 美股入库完成")
