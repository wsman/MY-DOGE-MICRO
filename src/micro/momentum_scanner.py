import sqlite3
import pandas as pd
import os
import sys
import json
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
        self.config = self._load_config()

    def _load_config(self):
        """加载配置文件，如果不存在则使用默认值"""
        config_path = os.path.join(project_root, 'models_config.json')
        default_config = {
            "us_blacklist": ["SQQQ", "TQQQ", "SOXL", "SOXS", "SPXU", "SPXS", "SDS", "SSO", "UPRO", "QID", "QLD", "TNA", "TZA", "UVXY", "VIXY", "SVXY", "LABU", "LABD", "YANG", "YINN", "FNGU", "FNGD", "WEBL", "WEBS", "KOLD", "BOIL", "TSLY", "NVDY", "AMDY", "MSTY", "CONY", "APLY", "GOOY", "MSFY", "AMZY", "FBY", "OARK", "XOMO", "JPMO", "DISO", "NFLY", "SQY", "PYPY", "AIYY", "YMAX", "YMAG", "ULTY", "SVOL", "TLTW", "HYGW", "LQDW", "BITX"],
            "min_volume_cn": 200000000,
            "min_volume_us": 20000000,
            "max_change_pct": 400,
            "rsrs_window": 18
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 合并/覆盖默认配置，防止 key 缺失报错
                    if "scanner_filters" in data:
                        return data["scanner_filters"]
                    else:
                        print("[WARN] 配置文件中未找到 scanner_filters，使用默认配置")
            except Exception as e:
                print(f"[WARN] 配置文件加载失败: {e}, 使用默认配置")
        else:
            print("[WARN] 配置文件不存在，使用默认配置")
        
        return default_config

    def calculate_rsrs(self, series, window=18):
        """
        计算趋势强度 (RSRS 替代指标)
        返回: -1.0 ~ 1.0 (R2 * Sign(Slope))
        """
        try:
            if len(series) < window:
                return 0.0
            
            # 取最近 window 天的数据
            y = series.iloc[-window:].values
            x = np.arange(len(y))
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # R2 * Slope符号
            # 显式转换类型以消除 Pylance 警告
            r_sq = float(r_value) ** 2
            sign = 1.0 if float(slope) > 0 else -1.0
            
            trend_strength = r_sq * sign
            return trend_strength
        except Exception as e:
            # print(f"[WARN] RSRS计算异常: {e}")
            return 0.0

    def _calculate_rsrs_vectorized(self, price_matrix):
        """
        向量化计算 RSRS
        Args:
            price_matrix: numpy array, shape (N_stocks, window_size)
        Returns:
            rsrs_values: numpy array, shape (N_stocks,)
        """
        if price_matrix.size == 0:
            return np.array([])

        N, T = price_matrix.shape

        # 1. 准备 X (时间序列 0, 1, ..., T-1)
        x = np.arange(T)
        x_mean = x.mean()
        x_dev = x - x_mean             # Shape: (T,)
        x_var = np.sum(x_dev ** 2)     # Scalar (分母部分)

        # 2. 准备 Y (价格序列)
        y_mean = np.mean(price_matrix, axis=1, keepdims=True)
        y_dev = price_matrix - y_mean  # Shape: (N, T)

        # 3. 计算 Slope (斜率)
        # Cov(x, y) = sum(x_dev * y_dev)
        cov_xy = np.dot(y_dev, x_dev)  # Shape: (N,)
        slope = cov_xy / x_var

        # 4. 计算 R^2 (决定系数)
        # R^2 = (Cov(x,y)^2) / (Var(x) * Var(y))
        y_var = np.sum(y_dev ** 2, axis=1) # Shape: (N,)

        # 处理 y_var 为 0 的情况 (价格完全不变)，避免除零错误
        valid_mask = y_var > 1e-10
        r_sq = np.zeros(N)

        # 仅对有效数据计算
        r_sq[valid_mask] = (cov_xy[valid_mask] ** 2) / (x_var * y_var[valid_mask])

        # 5. 计算 RSRS = R^2 * Sign(Slope)
        rsrs = r_sq * np.sign(slope)

        return rsrs

    def test_rsrs_accuracy(self):
        """自检函数：对比向量化与Scipy的结果"""
        print("[TEST] 正在执行算法一致性自检...")
        # 生成随机测试数据
        np.random.seed(42)
        test_data = np.random.rand(100, 18) * 100  # 100只股票，18天数据

        # 1. 向量化计算
        vec_res = self._calculate_rsrs_vectorized(test_data)

        # 2. 循环计算 (使用旧方法)
        loop_res = []
        for row in test_data:
            loop_res.append(self.calculate_rsrs(pd.Series(row)))

        # 3. 对比
        diff = np.abs(vec_res - np.array(loop_res))
        max_diff = diff.max()

        if max_diff < 1e-6:
            print("[OK] 算法验证通过！误差极小。")
        else:
            print(f"[ERR] 算法存在差异，最大误差: {max_diff}")
        return max_diff

    def get_connection(self, db_name):
        db_path = os.path.join(data_dir, db_name)
        if not os.path.exists(db_path):
            print(f"[ERR] 数据库不存在: {db_path}")
            return None
        return sqlite3.connect(db_path)

    def analyze_market(self, market_type, db_name, amount_threshold):
        print(f"\n[GO] 正在分析 {market_type} 市场动量...")
        
        # 1. 优先使用传入参数，否则使用配置
        min_vol = amount_threshold  # 保留原参数，不做覆盖逻辑，以保持兼容
        blacklist = set(self.config.get('us_blacklist', []))
        window = self.config.get('rsrs_window', 18)
        max_change_pct = self.config.get('max_change_pct', 400)
        
        print(f"   [CFG] 筛选标准: 60日涨幅排名 | 60日日均成交额 > {min_vol/10000:.0f}万")
        
        conn = self.get_connection(db_name)
        if not conn: return

        try:
            # 获取最新日期
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM stock_prices")
            max_date = cursor.fetchone()[0]
            if not max_date:
                print("[WARN] 数据库为空")
                return

            # 加载最近半年数据
            print("[WAIT] 正在加载数据到内存...")
            query = f"""
                SELECT ticker, date, close, high, low, amount 
                FROM stock_prices 
                WHERE date >= date('{max_date}', '-180 days')
                ORDER BY ticker, date ASC
            """
            df = pd.read_sql_query(query, conn)
            
        except Exception as e:
            print(f"[ERR] 读取错误: {e}")
            return
        finally:
            conn.close()

        if df.empty:
            print("[WARN] 无数据")
            return

        print(f"[INFO] 数据加载完成，开始筛选 {len(df['ticker'].unique())} 只股票...")
        
        # --- 批处理容器 ---
        candidates_meta = []   # 存储元数据 (ticker, price, vol, etc.)
        candidates_prices = [] # 存储价格序列 (用于向量化计算)
        global_start_dates = []
        global_end_dates = []

        grouped = df.groupby('ticker')

        for ticker, group in grouped:
            if len(group) < 61: continue  # 确保有足够数据计算 60日涨幅
            
            # --- 过滤器逻辑 (从配置读取) ---
            if market_type == 'US':
                if ticker in blacklist: continue
                # 过滤常见的 warrant (权证) 或异类后缀 (5字符以上通常要注意)
                ticker_str = str(ticker)
                if len(ticker_str) > 4 and ticker_str not in ['GOOGL', 'BRK.B']: 
                    # 简单启发式：美股正股代码通常 <= 4 位 (除了个别)
                    # YieldMax 很多是 4 位，所以必须靠 blacklist
                    pass

            if market_type == 'CN':
                # 确保 ticker 是字符串
                ticker_str = str(ticker)
                raw_code = ticker_str.split('.')[0]
                if not raw_code.startswith(('00', '30', '60', '68')): continue
            
            # --- 流动性过滤 ---
            avg_amt = group['amount'].tail(60).mean()
            if avg_amt < min_vol: continue

            # --- 涨跌幅计算 ---
            curr_row = group.iloc[-1]
            prev_row = group.iloc[-61]
            p_curr = curr_row['close']
            p_prev = prev_row['close']
            if p_prev == 0: continue
            
            change_pct = (p_curr - p_prev) / p_prev * 100
            
            # 虚假暴涨熔断过滤
            if market_type == 'US' and change_pct > max_change_pct:
                continue
                
            # [OK] 关键改动: 此时不计算 RSRS，只收集数据
            # 获取最近 window 天的收盘价
            recent_prices = group['close'].values[-window:]
            
            # 如果数据不足 window 天 (虽然前面检查了61天，但以防万一)，补0或跳过
            if len(recent_prices) < window:
                continue

            candidates_prices.append(recent_prices)
            candidates_meta.append({
                'ticker': ticker,
                'price_60d_ago': round(p_prev, 2),
                'price_current': round(p_curr, 2),
                'change_percent': round(change_pct, 2),
                'avg_daily_volume': round(avg_amt, 0),
                'start_date': prev_row['date'],
                'end_date': curr_row['date']
            })
            
            global_start_dates.append(prev_row['date'])
            global_end_dates.append(curr_row['date'])

        # --- 向量化计算阶段 ---
        if not candidates_meta:
            print("[WARN] 没有符合条件的标的")
            return

        print(f"[FAST] 正在对 {len(candidates_meta)} 只优选股票进行 RSRS 向量化计算...")

        # 转换为 numpy 矩阵 (N, window)
        price_matrix = np.array(candidates_prices)

        # [GO] 一次性计算所有 RSRS
        rsrs_scores = self._calculate_rsrs_vectorized(price_matrix)

        # 将结果合并回元数据
        for i, meta in enumerate(candidates_meta):
            meta['rsrs_z'] = round(rsrs_scores[i], 2)
            
        # --- 后续输出逻辑 ---
        results = pd.DataFrame(candidates_meta)
        results.sort_values('change_percent', ascending=False, inplace=True)
        top_200 = results.head(200)
        
        # 文件名日期逻辑优化
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
        
        print(f"[OK] {market_type} 榜单已生成: {filename}")
        print(f"   #1 榜首: {top_200.iloc[0]['ticker']} (+{top_200.iloc[0]['change_percent']}%) | RSRS: {top_200.iloc[0]['rsrs_z']}")

def main():
    ranker = MomentumRanker()
    
    # A股 (2亿 RMB)
    ranker.analyze_market('CN', 'market_data_cn.db', 200000000)
    
    # 美股 (2000万 USD)
    ranker.analyze_market('US', 'market_data_us.db', 20000000)

if __name__ == "__main__":
    main()
