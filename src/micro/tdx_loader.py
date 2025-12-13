"""
通达信数据加载器
用于从本地 TDX 数据目录读取股票日线数据
"""

import os
import struct
import glob
import pandas as pd
from datetime import datetime

class TDXReader:
    def __init__(self, root_dir):
        """
        初始化 TDX 读取器
        
        Args:
            root_dir (str): 通达信 vipdoc 根目录路径，例如 'D:\\Games\\New Tdx Vip2020\\vipdoc'
        """
        self.root_dir = root_dir

    def get_data(self, symbol, market_type=None):
        """
        获取指定股票的完整历史数据
        
        Args:
            symbol (str): 股票代码，格式如 '000001.SZ' 或 '600000.SH'（A股）或 'AAPL', 'NVDA'（美股）
            market_type (str, optional): 市场类型 ('cn' 或 'us')。如果为 None，则根据 symbol 推断。
            
        Returns:
            pd.DataFrame: 包含日期、开盘价、最高价、最低价、收盘价、成交量、成交额的 DataFrame
                         列为 ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
        """
        # 推断市场类型
        if market_type is None:
            if '.' in symbol:
                market_type = 'cn'
            else:
                market_type = 'us'

        # A股逻辑：有 . 后缀的情况
        if market_type == 'cn':
            code, market = symbol.split('.')
            # 转换为小写市场标识符（如 sz, sh）
            market = market.lower()
            
            # 构造文件路径
            file_path = os.path.join(self.root_dir, market, 'lday', f'{market}{code}.day')
        else:
            # 美股逻辑：无 . 后缀，查找 ds/lday 目录下的文件
            pattern = os.path.join(self.root_dir, 'ds', 'lday', f'*#{symbol}.day')
            files = glob.glob(pattern)
            
            if not files:
                raise FileNotFoundError(f"未找到 TDX 美股数据文件: {pattern}")
            
            file_path = files[0]  # 假设只找到一个匹配的文件
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"未找到 TDX 数据文件: {file_path}")
            
        return self._parse_file(file_path, market_type)

    def _parse_file(self, file_path, market_type='cn'):
        """
        解析 .day 文件
        
        Args:
            file_path (str): .day 文件的完整路径
            market_type (str): 市场类型 ('cn' 或 'us')
            
        Returns:
            pd.DataFrame: 解析后的数据
        """
        records = []
        
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(32)  # 每条记录32字节
                if len(data) < 32:
                    break
                    
                # 根据市场类型解析不同的格式
                if market_type == 'us':
                    # 美股：价格是 float，amount 是 float，volume 是 int
                    unpacked = struct.unpack('<IfffffII', data)
                    date_int, open_f, high_f, low_f, close_f, amount_f, volume, _ = unpacked
                    
                    # 解析日期 (YYYYMMDD格式的整数)
                    year = date_int // 10000
                    month = (date_int % 10000) // 100
                    day = date_int % 100
                    date_str = f"{year:04d}-{month:02d}-{day:02d}"
                    
                    # 直接使用浮点价格（无需除以100）
                    open_price = open_f
                    high_price = high_f
                    low_price = low_f
                    close_price = close_f
                    
                else:
                    # A股：价格是 int，需除以 100；amount 是 float (但实际为 uint)，volume 是 int
                    unpacked = struct.unpack('<IIIII fII', data)
                    date_int, open_i, high_i, low_i, close_i, amount_f, volume, _ = unpacked
                    
                    # 解析日期 (YYYYMMDD格式的整数)
                    year = date_int // 10000
                    month = (date_int % 10000) // 100
                    day = date_int % 100
                    date_str = f"{year:04d}-{month:02d}-{day:02d}"
                    
                    # 将价格除以100（TDX中价格单位为万分之一）
                    open_price = open_i / 100.0
                    high_price = high_i / 100.0
                    low_price = low_i / 100.0
                    close_price = close_i / 100.0
                    
                records.append({
                    'date': date_str,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume,
                    'amount': amount_f
                })
        
        # 创建 DataFrame 并按日期排序
        df = pd.DataFrame(records)
        df.sort_values('date', inplace=True)
        return df
