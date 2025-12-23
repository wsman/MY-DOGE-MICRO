import sqlite3
import pandas as pd
import os
import sys
from datetime import datetime
from collections import Counter
from scipy import stats
import numpy as np

# 路径自适应
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
data_dir = os.path.join(project_root, 'data')

class MomentumRanker:
    def __init__(self):
        pass

    def calculate_rsrs_z(self, high_series, low_series, window=18):
        """
        计算 RSRS 标准分 (Z-Score)
        """
        if len(high_series) < window + 2:
            return 0.0
            
        high_vals = high_series.values
        low_vals = low_series.values
        
        # 计算过去 60 天的 beta (如果数据足够)
        lookback = min(len(high_vals), 300)
        start_idx = len(high_vals) - lookback
        
        betas = []
        # 至少需要 window 个数据点才能计算一个 beta
        if start_idx + window >= len(high_vals):
             # 数据太少，只计算最后一个
             start_idx = len(high_vals) - window - 1
             if start_idx < 0: return 0.0

        for i in range(start_idx + window, len(high_vals) + 1):
            y = high_vals[i-window:i]
            x = low_vals[i-window:i]
            # 简单的线性回归
            slope, _, _, _, _ = stats.linregress(x, y)
            betas.append(slope)
            
        if not betas:
            return 0.0
            
        betas_arr = np.array(betas)
        if len(betas_arr) < 10:
            # 历史数据不足以计算 Z-Score，直接返回 0 或 beta 本身
            return 0.0
            
        # Z-Score
        mean = np.mean(betas_arr)
        std = np.std(betas_arr)
        
        if std == 0:
            return 0.0
            
        current_beta = betas_arr[-1]
        z_score = (current_beta - mean) / std
        return z_score

    def get_connection(self, db_name):
        db_path = os.path.join(data_dir, db_name)
        if not os.path.exists(db_path):
            print(f"❌ 数据库不存在: {db_path}")
            return None
        return sqlite3.connect(db_path)

    def analyze_market(self, market_type, db_name, amount_threshold):
        print(f"\n🚀 正在分析 {market_type} 市场动量...")
        print(f"   ⚙️ 筛选标准: 60日涨幅排名 | 60日日均成交额 > {amount_threshold/10000:.0f}万")
        
        conn = self.get_connection(db_name)
        if not conn: return

        try:
            # 1. 获取最新日期
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM stock_prices")
            max_date = cursor.fetchone()[0]
            if not max_date:
                print("⚠️ 数据库为空")
                return

            # 2. 加载最近半年数据
            print("⏳ 正在加载数据到内存...")
            # [MODIFIED] 增加 high, low 用于计算 RSRS
            query = f"""
                SELECT ticker, date, close, high, low, amount 
                FROM stock_prices 
                WHERE date >= date('{max_date}', '-180 days')
                ORDER BY ticker, date ASC
            """
            df = pd.read_sql_query(query, conn)
            
        except Exception as e:
            print(f"❌ 读取错误: {e}")
            return
        finally:
            conn.close()

        if df.empty:
            print("⚠️ 无数据")
            return

        print(f"📊 数据加载完成，开始计算 {len(df['ticker'].unique())} 只股票...")
        
        results = []
        global_start_dates = []
        global_end_dates = []

        # 3. 向量化/分组计算
        grouped = df.groupby('ticker')
        
        # 定义美股黑名单 (包含杠杆、反向、期权策略 ETF)
        us_blacklist = {
            # Leveraged/Inverse
            'SQQQ', 'TQQQ', 'SOXL', 'SOXS', 'SPXU', 'SPXS', 'SDS', 'SSO', 'UPRO', 
            'QID', 'QLD', 'TNA', 'TZA', 'UVXY', 'VIXY', 'SVXY', 'LABU', 'LABD', 
            'YANG', 'YINN', 'FNGU', 'FNGD', 'WEBL', 'WEBS', 'KOLD', 'BOIL',
            # YieldMax / Option Strategies (High Yield / Re-split frequent)
            'TSLY', 'NVDY', 'AMDY', 'MSTY', 'CONY', 'APLY', 'GOOY', 'MSFY', 'AMZY',
            'FBY', 'OARK', 'XOMO', 'JPMO', 'DISO', 'NFLY', 'SQY', 'PYPY', 'AIYY',
            'YMAX', 'YMAG', 'ULTY', 'SVOL', 'TLTW', 'HYGW', 'LQDW', 'BITX'
        }

        for ticker, group in grouped:
            if len(group) < 61: continue
            
            # --- 1. 黑名单过滤 ---
            if market_type == 'US':
                if ticker in us_blacklist: continue
                # 过滤常见的 warrant (权证) 或异类后缀 (5字符以上通常要注意)
                if len(ticker) > 4 and ticker not in ['GOOGL', 'BRK.B']: 
                    # 简单启发式：美股正股代码通常 <= 4 位 (除了个别)
                    # YieldMax 很多是 4 位，所以必须靠 blacklist
                    pass

            # --- 2. A股过滤 ---
            if market_type == 'CN':
                # 确保 ticker 是字符串
                ticker_str = str(ticker)
                raw_code = ticker_str.split('.')[0]
                if not raw_code.startswith(('00', '30', '60', '68')): continue
            
            # --- 3. 流动性过滤 (60日均额) ---
            avg_amt = group['amount'].tail(60).mean()
            if avg_amt < amount_threshold: continue

            curr_row = group.iloc[-1]
            prev_row = group.iloc[-61]
            
            p_curr = curr_row['close']
            p_prev = prev_row['close']
            
            if p_prev == 0: continue
            
            change_pct = (p_curr - p_prev) / p_prev * 100
            
            # --- 4. 虚假暴涨熔断 (收紧至 400%) ---
            # 过滤掉因反向拆股 (Reverse Split) 导致的不复权数据暴涨
            # 仅对美股应用此过滤器
            if market_type == 'US' and change_pct > 400: 
                continue

            # --- 5. [NEW] RSRS 计算 ---
            rsrs_z = 0.0
            if 'high' in group.columns and 'low' in group.columns:
                # 简单的空值检查
                if not group['high'].isnull().all() and not group['low'].isnull().all():
                    # 填充 NaN 以防万一 (使用 ffill() 和 bfill() 替代 method 参数)
                    h = group['high'].ffill().bfill()
                    l = group['low'].ffill().bfill()
                    rsrs_z = self.calculate_rsrs_z(h, l)
            
            results.append({
                'ticker': ticker,
                'price_60d_ago': round(p_prev, 2),
                'price_current': round(p_curr, 2),
                'change_percent': round(change_pct, 2),
                'avg_daily_volume': round(avg_amt, 0),
                'rsrs_z': round(rsrs_z, 2), # [NEW]
                'start_date': prev_row['date'],
                'end_date': curr_row['date']
            })
            
            global_start_dates.append(prev_row['date'])
            global_end_dates.append(curr_row['date'])

        # 4. 汇总输出
        if not results:
            print("⚠️ 没有符合条件的标的")
            return

        res_df = pd.DataFrame(results)
        res_df.sort_values('change_percent', ascending=False, inplace=True)
        top_200 = res_df.head(200)
        
        # 5. 文件名日期逻辑优化
        # End Date: 取最大值 (最新日期)
        # Start Date: 取众数 (绝大多数股票的起始日期)，过滤停牌股干扰
        if global_end_dates:
            file_end = max(global_end_dates).replace('-', '')
        else:
            file_end = datetime.now().strftime('%Y%m%d')
            
        if global_start_dates:
            # 获取出现次数最多的日期 (Mode)
            most_common_start = Counter(global_start_dates).most_common(1)[0][0]
            file_start = most_common_start.replace('-', '')
        else:
            file_start = "00000000"
        
        filename = f"Top200_Momentum_{market_type}_{file_start}-{file_end}.csv"
        save_path = os.path.join(project_root, filename)
        
        output_cols = ['ticker', 'price_60d_ago', 'price_current', 'change_percent', 'avg_daily_volume', 'rsrs_z']
        top_200[output_cols].to_csv(save_path, index=False)
        
        print(f"✅ {market_type} 榜单已生成: {filename}")
        print(f"   🥇 榜首: {top_200.iloc[0]['ticker']} (+{top_200.iloc[0]['change_percent']}%) | RSRS: {top_200.iloc[0]['rsrs_z']}")

def main():
    ranker = MomentumRanker()
    
    # A股 (1亿 RMB)
    ranker.analyze_market('CN', 'market_data_cn.db', 200000000)
    
    # 美股 (1000万 USD)
    ranker.analyze_market('US', 'market_data_us.db', 20000000)

if __name__ == "__main__":
    main()
